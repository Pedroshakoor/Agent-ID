import type {
  AgentIDConfig,
  AgentInfo,
  AuditEntry,
  Credential,
  LogActionInput,
  VerifyResult,
} from "./types.js";
import {
  AgentIDError,
  AuthError,
  PolicyDeniedError,
  RateLimitError,
} from "./types.js";

/**
 * AgentID TypeScript/Node.js client.
 *
 * Handles token issuance, auto-refresh, audit logging, and policy verification.
 *
 * @example
 * ```typescript
 * import { AgentIDClient } from "@agentid/sdk";
 *
 * const client = new AgentIDClient({
 *   baseUrl: "http://localhost:8000",
 *   agentId: "your-agent-id",
 *   apiKey: "agid_your_key",
 * });
 *
 * // Get a valid JWT (auto-refreshes)
 * const token = await client.getToken();
 *
 * // Log an action
 * await client.logAction({ action: "email:send", resource: "user@example.com" });
 *
 * // Verify before acting
 * const { allowed, reason } = await client.verify("email:send", "user@example.com");
 * ```
 */
export class AgentIDClient {
  private readonly config: Required<AgentIDConfig>;
  private credential: Credential | null = null;
  private refreshPromise: Promise<void> | null = null;

  constructor(config: AgentIDConfig) {
    this.config = {
      ttlMinutes: 15,
      autoRefresh: true,
      refreshBufferSeconds: 60,
      ...config,
      baseUrl: config.baseUrl.replace(/\/$/, ""),
    };
  }

  // ── Token management ──────────────────────────────────────────────────────

  /** Get a valid JWT, refreshing if expired or near expiry. */
  async getToken(): Promise<string> {
    if (this.shouldRefresh()) {
      // Deduplicate concurrent refresh calls
      if (!this.refreshPromise) {
        this.refreshPromise = this.refreshToken().finally(() => {
          this.refreshPromise = null;
        });
      }
      await this.refreshPromise;
    }
    return this.credential!.token;
  }

  private shouldRefresh(): boolean {
    if (!this.credential) return true;
    const now = new Date();
    if (now >= this.credential.expiresAt) return true;
    if (this.config.autoRefresh) {
      const refreshAt = new Date(
        this.credential.expiresAt.getTime() -
          this.config.refreshBufferSeconds * 1000
      );
      return now >= refreshAt;
    }
    return false;
  }

  private async refreshToken(): Promise<void> {
    const data = await this.request<{
      token: string;
      credential_id: string;
      jti: string;
      expires_at: string;
      scope: Credential["scope"];
    }>("POST", "/v1/credentials/issue", {
      agent_id: this.config.agentId,
      ttl_minutes: this.config.ttlMinutes,
    });

    this.credential = {
      token: data.token,
      credentialId: data.credential_id,
      jti: data.jti,
      expiresAt: new Date(data.expires_at),
      scope: data.scope,
    };
  }

  // ── Audit logging ─────────────────────────────────────────────────────────

  /** Log an action performed by this agent to the AgentID audit trail. */
  async logAction(input: LogActionInput): Promise<AuditEntry> {
    const token = await this.getToken();
    const body: Record<string, unknown> = {
      action: input.action,
      result: input.result ?? "allowed",
    };
    if (input.resource) body.resource = input.resource;
    if (input.promptSnippet) body.prompt_snippet = input.promptSnippet.slice(0, 1024);
    if (input.toolCalled) body.tool_called = input.toolCalled;
    if (input.resultSummary) body.result_summary = input.resultSummary;
    if (input.costUsd != null) body.cost_usd = input.costUsd;
    if (input.durationMs != null) body.duration_ms = input.durationMs;

    const data = await this.request<{ logged: boolean; log_id: string; created_at: string }>(
      "POST",
      "/v1/audit/log",
      body,
      { Authorization: `Bearer ${token}` }
    );

    return {
      id: data.log_id,
      agentId: this.config.agentId,
      action: input.action,
      resource: input.resource,
      result: input.result ?? "allowed",
      createdAt: data.created_at,
    };
  }

  // ── Policy verification ───────────────────────────────────────────────────

  /** Verify if this agent is allowed to perform an action on a resource. */
  async verify(action: string, resource: string): Promise<VerifyResult> {
    const token = await this.getToken();
    return this.request<VerifyResult>(
      "POST",
      "/v1/verify",
      { action, resource },
      { Authorization: `Bearer ${token}` }
    );
  }

  /**
   * Verify and throw PolicyDeniedError if not allowed.
   * Convenient for "check then act" patterns.
   */
  async assertAllowed(action: string, resource: string): Promise<void> {
    const result = await this.verify(action, resource);
    if (!result.allowed) {
      throw new PolicyDeniedError(action, resource, result.reason);
    }
  }

  // ── Agent info ────────────────────────────────────────────────────────────

  /** Get this agent's registration details. */
  async getInfo(): Promise<AgentInfo> {
    const raw = await this.request<Record<string, unknown>>(
      "GET",
      `/v1/agents/${this.config.agentId}`
    );
    return {
      id: raw.id as string,
      name: raw.name as string,
      ownerId: raw.owner_id as string,
      status: raw.status as AgentInfo["status"],
      framework: raw.framework as string | undefined,
      description: raw.description as string | undefined,
      createdAt: raw.created_at as string,
      lastActiveAt: raw.last_active_at as string | undefined,
    };
  }

  // ── Helpers ───────────────────────────────────────────────────────────────

  /** Returns Authorization header for use in external API calls. */
  async authHeaders(): Promise<Record<string, string>> {
    const token = await this.getToken();
    return {
      Authorization: `Bearer ${token}`,
      "X-Agent-ID": this.config.agentId,
    };
  }

  /** Returns current credential without refreshing (may be null). */
  currentCredential(): Credential | null {
    return this.credential;
  }

  private async request<T>(
    method: string,
    path: string,
    body?: unknown,
    extraHeaders?: Record<string, string>
  ): Promise<T> {
    const url = `${this.config.baseUrl}${path}`;
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "User-Agent": "@agentid/sdk/1.0.0",
      "X-API-Key": this.config.apiKey,
      ...extraHeaders,
    };

    const response = await fetch(url, {
      method,
      headers,
      body: body != null ? JSON.stringify(body) : undefined,
    });

    if (!response.ok) {
      let detail = response.statusText;
      try {
        const err = (await response.json()) as { detail?: string };
        detail = err.detail ?? detail;
      } catch {
        // ignore parse error
      }

      if (response.status === 401) throw new AuthError(detail);
      if (response.status === 429) throw new RateLimitError();
      throw new AgentIDError(detail, response.status);
    }

    return response.json() as Promise<T>;
  }
}
