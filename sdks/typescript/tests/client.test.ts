import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { AgentIDClient } from "../src/client.js";
import { AuthError, PolicyDeniedError } from "../src/types.js";

const BASE_URL = "http://test.agentid.local";
const AGENT_ID = "test-agent-123";
const API_KEY = "agid_testkey";

const futureDate = new Date(Date.now() + 15 * 60 * 1000).toISOString();

const FAKE_ISSUE_RESPONSE = {
  token: "eyJhbGciOiJSUzI1NiJ9.fake.sig",
  credential_id: "cred-abc",
  jti: "jti-xyz",
  expires_at: futureDate,
  scope: { policies: [{ effect: "allow", resources: ["*"], actions: ["*"] }] },
};

function makeClient() {
  return new AgentIDClient({ baseUrl: BASE_URL, agentId: AGENT_ID, apiKey: API_KEY });
}

function mockFetch(responses: Array<{ status: number; body: unknown }>) {
  let callIdx = 0;
  return vi.fn().mockImplementation(async () => {
    const res = responses[Math.min(callIdx++, responses.length - 1)];
    return {
      ok: res.status >= 200 && res.status < 300,
      status: res.status,
      statusText: res.status === 200 ? "OK" : "Error",
      json: async () => res.body,
    };
  });
}

describe("AgentIDClient", () => {
  let globalFetch: typeof fetch;

  beforeEach(() => {
    globalFetch = global.fetch;
  });

  afterEach(() => {
    global.fetch = globalFetch;
    vi.restoreAllMocks();
  });

  it("issues a token on first getToken()", async () => {
    const fetchMock = mockFetch([{ status: 200, body: FAKE_ISSUE_RESPONSE }]);
    global.fetch = fetchMock as unknown as typeof fetch;

    const client = makeClient();
    const token = await client.getToken();

    expect(token).toBe(FAKE_ISSUE_RESPONSE.token);
    expect(fetchMock).toHaveBeenCalledOnce();
  });

  it("caches token on subsequent calls", async () => {
    const fetchMock = mockFetch([{ status: 200, body: FAKE_ISSUE_RESPONSE }]);
    global.fetch = fetchMock as unknown as typeof fetch;

    const client = makeClient();
    await client.getToken();
    await client.getToken();
    await client.getToken();

    expect(fetchMock).toHaveBeenCalledOnce();
  });

  it("throws AuthError on 401", async () => {
    const fetchMock = mockFetch([{ status: 401, body: { detail: "Invalid API key" } }]);
    global.fetch = fetchMock as unknown as typeof fetch;

    const client = makeClient();
    await expect(client.getToken()).rejects.toThrow(AuthError);
  });

  it("logs an action", async () => {
    const logResponse = {
      logged: true,
      log_id: "log-123",
      created_at: new Date().toISOString(),
    };
    const fetchMock = mockFetch([
      { status: 200, body: FAKE_ISSUE_RESPONSE },
      { status: 200, body: logResponse },
    ]);
    global.fetch = fetchMock as unknown as typeof fetch;

    const client = makeClient();
    const entry = await client.logAction({
      action: "email:send",
      resource: "user@example.com",
      toolCalled: "send_email",
    });

    expect(entry.id).toBe("log-123");
    expect(entry.action).toBe("email:send");
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("verifies allowed action", async () => {
    const verifyResponse = { allowed: true, reason: "allowed", agent_id: AGENT_ID };
    const fetchMock = mockFetch([
      { status: 200, body: FAKE_ISSUE_RESPONSE },
      { status: 200, body: verifyResponse },
    ]);
    global.fetch = fetchMock as unknown as typeof fetch;

    const client = makeClient();
    const result = await client.verify("read", "file:report.pdf");

    expect(result.allowed).toBe(true);
  });

  it("verifies denied action", async () => {
    const verifyResponse = { allowed: false, reason: "No matching policy", agent_id: AGENT_ID };
    const fetchMock = mockFetch([
      { status: 200, body: FAKE_ISSUE_RESPONSE },
      { status: 200, body: verifyResponse },
    ]);
    global.fetch = fetchMock as unknown as typeof fetch;

    const client = makeClient();
    const result = await client.verify("delete", "system:root");

    expect(result.allowed).toBe(false);
    expect(result.reason).toContain("policy");
  });

  it("assertAllowed throws PolicyDeniedError when denied", async () => {
    const fetchMock = mockFetch([
      { status: 200, body: FAKE_ISSUE_RESPONSE },
      { status: 200, body: { allowed: false, reason: "Explicit deny" } },
    ]);
    global.fetch = fetchMock as unknown as typeof fetch;

    const client = makeClient();
    await expect(client.assertAllowed("delete", "admin:users")).rejects.toThrow(PolicyDeniedError);
  });

  it("returns auth headers", async () => {
    const fetchMock = mockFetch([{ status: 200, body: FAKE_ISSUE_RESPONSE }]);
    global.fetch = fetchMock as unknown as typeof fetch;

    const client = makeClient();
    const headers = await client.authHeaders();

    expect(headers.Authorization).toMatch(/^Bearer /);
    expect(headers["X-Agent-ID"]).toBe(AGENT_ID);
  });

  it("gets agent info", async () => {
    const agentData = {
      id: AGENT_ID,
      name: "test-agent",
      owner_id: "owner-1",
      status: "active",
      framework: "openai",
      created_at: new Date().toISOString(),
    };
    const fetchMock = mockFetch([{ status: 200, body: agentData }]);
    global.fetch = fetchMock as unknown as typeof fetch;

    const client = makeClient();
    const info = await client.getInfo();

    expect(info.id).toBe(AGENT_ID);
    expect(info.ownerId).toBe("owner-1");
    expect(info.framework).toBe("openai");
  });
});
