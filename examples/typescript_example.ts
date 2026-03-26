/**
 * TypeScript + AgentID Example
 * =============================
 * Shows how to use @agentid/sdk with any Node.js AI agent.
 *
 * Run:
 *   npm install @agentid/sdk
 *   npx ts-node examples/typescript_example.ts
 */

import { AgentIDClient, PolicyDeniedError } from "@agentid/sdk";

const client = new AgentIDClient({
  baseUrl: process.env.AGENTID_URL ?? "http://localhost:8000",
  agentId: process.env.AGENTID_AGENT_ID ?? "your-agent-id",
  apiKey: process.env.AGENTID_API_KEY ?? "agid_your_key",
  ttlMinutes: 15,
});

// ── Example: Middleware for any async function ─────────────────────────────

async function withAgentID<T>(
  action: string,
  resource: string,
  fn: () => Promise<T>
): Promise<T> {
  // 1. Verify policy before acting
  await client.assertAllowed(action, resource);

  // 2. Execute
  const start = Date.now();
  let result: T;
  try {
    result = await fn();
  } catch (err) {
    await client.logAction({
      action,
      resource,
      result: "error",
      resultSummary: String(err),
      durationMs: Date.now() - start,
    });
    throw err;
  }

  // 3. Audit log
  await client.logAction({
    action,
    resource,
    result: "allowed",
    resultSummary: JSON.stringify(result).slice(0, 256),
    durationMs: Date.now() - start,
  });

  return result;
}

// ── Example: Fake external tool that checks the token ─────────────────────

async function fakeStripeCharge(
  amount: number,
  currency: string,
  agentToken: string
): Promise<{ chargeId: string }> {
  // A real Stripe integration would verify the token with AgentID
  const verifyResponse = await fetch(
    `${process.env.AGENTID_URL ?? "http://localhost:8000"}/v1/verify`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${agentToken}`,
      },
      body: JSON.stringify({
        action: "payment:charge",
        resource: `stripe:${currency}:${amount}`,
      }),
    }
  );

  const verification = (await verifyResponse.json()) as {
    allowed: boolean;
    reason: string;
  };

  if (!verification.allowed) {
    throw new Error(`AgentID denied payment: ${verification.reason}`);
  }

  return { chargeId: `ch_${Date.now()}` };
}

// ── Main ───────────────────────────────────────────────────────────────────

async function main() {
  console.log("AgentID TypeScript SDK Example\n");

  // Get a token
  const token = await client.getToken();
  console.log(`Token issued: ${token.slice(0, 50)}...`);

  // Check agent info
  try {
    const info = await client.getInfo();
    console.log(`Agent: ${info.name} (${info.status})`);
  } catch (e) {
    console.log("Could not fetch agent info — is the server running?");
  }

  // Use the middleware wrapper
  try {
    const result = await withAgentID("email:send", "user@example.com", async () => {
      console.log("Sending email...");
      return { sent: true, to: "user@example.com" };
    });
    console.log("Email result:", result);
  } catch (err) {
    if (err instanceof PolicyDeniedError) {
      console.log(`Policy denied: ${err.reason}`);
    }
  }

  // Attach auth headers to outbound requests
  const headers = await client.authHeaders();
  console.log("\nAuth headers for outbound API calls:");
  console.log(JSON.stringify(headers, null, 2));

  console.log("\nAll actions logged to AgentID audit trail.");
}

main().catch(console.error);
