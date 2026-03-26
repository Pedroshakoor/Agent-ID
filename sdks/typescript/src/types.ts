export interface AgentIDConfig {
  /** AgentID server base URL, e.g. "https://api.agentid.dev" */
  baseUrl: string;
  /** Your registered agent's ID */
  agentId: string;
  /** Your agent's API key (agid_...) */
  apiKey: string;
  /** Token TTL in minutes (default: 15) */
  ttlMinutes?: number;
  /** Auto-refresh token before expiry (default: true) */
  autoRefresh?: boolean;
  /** Seconds before expiry to proactively refresh (default: 60) */
  refreshBufferSeconds?: number;
}

export interface Credential {
  token: string;
  credentialId: string;
  jti: string;
  expiresAt: Date;
  scope: PolicyScope;
}

export interface PolicyScope {
  policies: PolicyDocument[];
  agentName?: string;
  ownerId?: string;
}

export interface PolicyDocument {
  effect: "allow" | "deny";
  resources: string[];
  actions: string[];
  conditions?: PolicyConditions;
}

export interface PolicyConditions {
  maxDaily?: number;
  timeWindow?: { start: string; end: string };
  ipAllowlist?: string[];
}

export interface AgentInfo {
  id: string;
  name: string;
  ownerId: string;
  status: "active" | "suspended" | "revoked";
  framework?: string;
  description?: string;
  createdAt: string;
  lastActiveAt?: string;
}

export interface AuditEntry {
  id: string;
  agentId: string;
  action: string;
  resource?: string;
  result: "allowed" | "denied" | "error";
  createdAt: string;
}

export interface LogActionInput {
  action: string;
  resource?: string;
  result?: "allowed" | "denied" | "error";
  promptSnippet?: string;
  toolCalled?: string;
  resultSummary?: string;
  costUsd?: number;
  durationMs?: number;
}

export interface VerifyResult {
  allowed: boolean;
  reason: string;
  agentId?: string;
  ownerId?: string;
  jti?: string;
  scopeSummary?: object;
}

export class AgentIDError extends Error {
  constructor(
    message: string,
    public readonly statusCode?: number
  ) {
    super(message);
    this.name = "AgentIDError";
  }
}

export class AuthError extends AgentIDError {
  constructor(message = "Authentication failed") {
    super(message, 401);
    this.name = "AuthError";
  }
}

export class PolicyDeniedError extends AgentIDError {
  constructor(
    public readonly action: string,
    public readonly resource: string,
    public readonly reason: string
  ) {
    super(`Action '${action}' on '${resource}' denied: ${reason}`, 403);
    this.name = "PolicyDeniedError";
  }
}

export class RateLimitError extends AgentIDError {
  constructor() {
    super("Rate limit exceeded", 429);
    this.name = "RateLimitError";
  }
}
