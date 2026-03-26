/**
 * @agentid/sdk — Verifiable identity for every AI agent
 *
 * @example
 * ```typescript
 * import { AgentIDClient } from "@agentid/sdk";
 *
 * const client = new AgentIDClient({
 *   baseUrl: "http://localhost:8000",
 *   agentId: process.env.AGENTID_AGENT_ID!,
 *   apiKey: process.env.AGENTID_API_KEY!,
 * });
 *
 * const token = await client.getToken();
 * await client.logAction({ action: "email:send", resource: "user@example.com" });
 * const { allowed } = await client.verify("email:send", "user@example.com");
 * ```
 */

export { AgentIDClient } from "./client.js";
export type {
  AgentIDConfig,
  AgentInfo,
  AuditEntry,
  Credential,
  LogActionInput,
  VerifyResult,
  PolicyDocument,
  PolicyScope,
  PolicyConditions,
} from "./types.js";
export {
  AgentIDError,
  AuthError,
  PolicyDeniedError,
  RateLimitError,
} from "./types.js";
