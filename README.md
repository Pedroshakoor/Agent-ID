# AgentID

**Verifiable identity for every AI agent.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Twitter](https://img.shields.io/twitter/follow/pedroshakoor?style=social)](https://x.com/pedroshakoor)

> Built by [@pedroshakoor](https://x.com/pedroshakoor)

---

> Every production AI agent today either shares human credentials (dangerous) or runs with no identity, no audit trail, and no scoped permissions. AgentID fixes this.

AgentID is a **lightweight, open-source identity provider + audit service + SDKs** that gives every AI agent its own verifiable identity, short-lived scoped credentials, and automatic action logging — without ever using human credentials.

Works with **LangChain, LangGraph, CrewAI, AutoGen, OpenAI Agents, LlamaIndex** — or any custom agent.

---

## Why AgentID

Research from Strata, Teleport, and Cisco (March 2026) consistently identifies **"unmanaged agent identities"** as the #1 enterprise blocker for AI adoption:

- Agents share human OAuth tokens → impossible to audit, impossible to revoke
- No scoped permissions → an agent with email access can send anything to anyone
- No audit trail → no way to know what an agent did or why
- No standard → every team invents their own (insecure) solution

**AgentID solves this in 5 lines of code.**

---

## Quickstart

### 1. Start the server

```bash
git clone https://github.com/Pedroshakoor/Agent-ID
cd Agent-ID
make dev   # starts backend + frontend + postgres + redis via Docker Compose
```

Dashboard: http://localhost:3000 · API docs: http://localhost:8000/docs

### 2. Register your agent

```bash
curl -X POST http://localhost:8000/v1/agents \
  -H "Content-Type: application/json" \
  -d '{"name": "my-agent", "owner_id": "user-123"}'
# → { "id": "...", "api_key": "agid_..." }
```

### 3. Use the SDK

**Python:**
```python
pip install agentid
```

```python
from agentid import AgentIDClient

async with AgentIDClient(
    base_url="http://localhost:8000",
    agent_id="your-agent-id",
    api_key="agid_your_key",
) as client:
    token = await client.get_token()           # short-lived RS256 JWT
    await client.log_action(                   # audit every action
        action="email:send",
        resource="user@example.com",
        result="allowed",
    )
    allowed, reason = await client.verify(     # check policy before acting
        "email:send", "user@example.com"
    )
```

**TypeScript:**
```bash
npm install @agentid/sdk
```

```typescript
import { AgentIDClient } from "@agentid/sdk";

const client = new AgentIDClient({
  baseUrl: "http://localhost:8000",
  agentId: process.env.AGENTID_AGENT_ID!,
  apiKey: process.env.AGENTID_API_KEY!,
});

const token = await client.getToken();
await client.logAction({ action: "stripe:charge", resource: "usd:99" });
await client.assertAllowed("stripe:charge", "usd:99"); // throws if denied
```

**LangChain (2 lines):**
```python
from agentid.middleware.langchain import agentid_langchain_middleware

tools = agentid_langchain_middleware(tools=my_tools, client=client)
# Every tool call is now verified + audited automatically
```

---

## Architecture

```mermaid
graph TB
    subgraph "Your Agent"
        A[Agent Code] -->|1. get_token()| SDK[AgentID SDK]
        A -->|3. use token| EXT[External APIs]
        A -->|4. log_action()| SDK
    end

    subgraph "AgentID Server"
        SDK -->|2. issue JWT| CRED[Credential Service\nRS256 JWT]
        CRED --> DB[(PostgreSQL)]
        CRED --> POLICY[Policy Engine\nAllow/Deny Rules]
        SDK --> AUDIT[Audit Service\nImmutable Logs]
        AUDIT --> DB
    end

    subgraph "External Service (e.g. Gmail)"
        EXT -->|5. verify token| VER[/v1/verify/]
        VER --> POLICY
        VER -->|allowed/denied| EXT
    end

    subgraph "Dashboard"
        DASH[Next.js 15 UI] --> DB
    end
```

**Flow:**
1. Agent requests a short-lived JWT from AgentID (authenticated with its API key)
2. AgentID issues a signed RS256 token with the agent's scoped policies baked in
3. Agent uses the token to call external services (Gmail, Stripe, internal APIs)
4. External services call `/v1/verify` to confirm the token is valid + action is allowed
5. Agent logs every action to the immutable audit trail

---

## Core Concepts

### Agent Registration

Every agent gets a unique `agent_id` and an `api_key` (shown only once). The `api_key` is used to request short-lived credentials. It never appears in the JWT.

### Scoped Credentials (JWTs)

JWTs contain:
- `agent_id`, `owner_id` — identity
- `scope.policies` — what this agent is allowed to do
- `exp`, `iat`, `jti` — expiry, issued-at, unique ID (for revocation)
- Signed with RS256 — verifiable by any service with the public key

Default TTL: **15 minutes**. Configurable per-agent or per-request.

### Policy Language

Policies are simple JSON documents. Multiple policies can be attached to an agent:

```json
{
  "effect": "allow",
  "resources": ["email:*", "calendar:read:*"],
  "actions": ["read", "send"],
  "conditions": {
    "max_daily": 100,
    "time_window": { "start": "09:00", "end": "17:00" },
    "ip_allowlist": ["10.0.0.0/8"]
  }
}
```

**Effect:** `allow` or `deny`. Explicit deny always wins.

**Resources:** Glob patterns matching `namespace:subresource:...`
- `email:*` — all email resources
- `file:read:*` — any read on any file
- `stripe:charge:usd:*` — any USD charge
- `*` — everything

**Actions:** What the agent can do
- `read`, `write`, `send`, `delete`, `*`

**Conditions:**
| Condition | Type | Description |
|---|---|---|
| `max_daily` | int | Max actions per day (resets at UTC midnight) |
| `time_window` | `{start, end}` | UTC time range (HH:MM format) |
| `ip_allowlist` | string[] | CIDR ranges the agent may call from |

**Evaluation order:** Policies evaluated by priority (highest first). First match wins. If no policy matches → **default deny**.

### Audit Logs

Every call to `/v1/audit/log` records:
- `agent_id`, `jti` — which agent, which credential
- `action`, `resource` — what happened
- `result` — `allowed | denied | error`
- `prompt_snippet` — the prompt that triggered the action (truncated at 1024 chars)
- `tool_called`, `result_summary` — what tool ran and what it returned
- `cost_usd`, `duration_ms` — performance + cost tracking
- `ip_address`, `user_agent` — network context

---

## API Reference

### Agents

| Method | Path | Description |
|---|---|---|
| `POST` | `/v1/agents` | Register a new agent |
| `GET` | `/v1/agents` | List agents (filter by `owner_id`) |
| `GET` | `/v1/agents/{id}` | Get agent details |
| `PATCH` | `/v1/agents/{id}` | Update agent |
| `DELETE` | `/v1/agents/{id}` | Delete agent |
| `POST` | `/v1/agents/{id}/policies` | Add a policy |
| `GET` | `/v1/agents/{id}/policies` | List policies |

### Credentials

| Method | Path | Description |
|---|---|---|
| `POST` | `/v1/credentials/issue` | Issue a JWT (requires `X-API-Key` header) |
| `POST` | `/v1/credentials/{id}/revoke` | Revoke a credential |
| `GET` | `/v1/credentials/{agent_id}/list` | List credentials |

### Audit

| Method | Path | Description |
|---|---|---|
| `POST` | `/v1/audit/log` | Log an action (requires `Authorization: Bearer <token>`) |
| `GET` | `/v1/audit/logs` | Query audit logs |
| `GET` | `/v1/audit/logs/{agent_id}/stats` | Aggregate stats |

### Verify

| Method | Path | Description |
|---|---|---|
| `POST` | `/v1/verify` | Verify token + policy for an action |
| `GET` | `/v1/verify/public-key` | Get RS256 public key |

---

## Integration Examples

### LangChain / LangGraph

```python
from agentid import AgentIDClient
from agentid.middleware.langchain import agentid_langchain_middleware
from langchain.tools import BaseTool

async with AgentIDClient(...) as client:
    safe_tools = agentid_langchain_middleware(
        tools=[email_tool, search_tool, file_tool],
        client=client,
        enforce_policy=True,
    )
    agent = create_react_agent(llm=llm, tools=safe_tools)
```

### CrewAI

```python
from crewai import Task
from agentid.middleware.crewai import agentid_task_callback

task = Task(
    description="Research competitors",
    agent=researcher,
    callback=agentid_task_callback(client, action="research:web"),
)
```

### External service verification (any language)

```python
import httpx

async def verify_agent_token(token: str, action: str, resource: str) -> bool:
    async with httpx.AsyncClient() as http:
        resp = await http.post(
            "http://agentid-server/v1/verify",
            json={"action": action, "resource": resource},
            headers={"Authorization": f"Bearer {token}"},
        )
    result = resp.json()
    return result["allowed"]
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./agentid.db` | PostgreSQL or SQLite |
| `REDIS_URL` | `redis://localhost:6379` | Redis for rate limiting |
| `SECRET_KEY` | — | App secret (32+ chars) |
| `ENVIRONMENT` | `development` | `development` or `production` |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed origins |
| `DEFAULT_TOKEN_TTL_MINUTES` | `15` | Default JWT lifetime |
| `MAX_TOKEN_TTL_MINUTES` | `1440` | Maximum allowed JWT lifetime |
| `LOG_LEVEL` | `info` | Logging verbosity |

---

## Deployment

### Railway (one click)

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template)

### Fly.io

```bash
fly launch --name agentid-backend --dockerfile backend/Dockerfile
fly postgres create --name agentid-db
fly secrets set DATABASE_URL=... SECRET_KEY=$(openssl rand -hex 32)
fly deploy
```

### Docker Compose (self-hosted)

```bash
cp .env.example .env
docker compose up -d
```

---

## Security

- **Private keys never stored in DB** — RS256 key pair lives on disk at `keys/`. Back this up.
- **API keys are hashed** — SHA-256 one-way hash. Original never stored.
- **Short-lived tokens** — 15-minute default TTL limits blast radius of a leaked token.
- **Token revocation** — JTI tracked in DB; revoked JTIs checked on every verify call.
- **Rate limiting** — 60 req/min per IP via slowapi + Redis.
- **Input sanitization** — All inputs validated via Pydantic v2.
- **CORS** — Configurable allowed origins; defaults to localhost only.
- **Structured logging** — All requests logged with structlog (JSON, no sensitive data).
- **Never log secrets** — API keys, tokens, and private keys are never written to logs.

### Key Rotation

```bash
make keygen
docker compose restart backend
```

---

## Roadmap

- [ ] **On-chain identity** — Anchor agent identities to a blockchain for immutable provenance
- [ ] **Multi-org support** — Teams, orgs, hierarchical ownership
- [ ] **AgentID Cloud** — Hosted version (waitlist open)
- [ ] **OIDC/OAuth2 bridge** — Let agents authenticate to any OAuth2-compatible service
- [ ] **Agent-to-agent delegation** — Agent A grants limited access to Agent B
- [ ] **OpenTelemetry traces** — Full distributed tracing for multi-agent workflows
- [ ] **MCP server** — AgentID as a Model Context Protocol server
- [ ] **Helm chart** — Production Kubernetes deployment

---

## Development

```bash
git clone https://github.com/Pedroshakoor/Agent-ID
cd Agent-ID

make dev          # start everything with Docker Compose
make test         # run all tests
make lint         # lint all code
make migrate      # run DB migrations
```

### Project Structure

```
Agent-ID/
├── backend/              # FastAPI server (Python 3.12)
│   ├── app/
│   │   ├── main.py       # FastAPI app entry point
│   │   ├── config.py     # Settings (pydantic-settings)
│   │   ├── database.py   # SQLAlchemy async engine
│   │   ├── models/       # SQLModel table definitions
│   │   ├── routers/      # API route handlers
│   │   ├── services/     # JWT, policy engine, audit
│   │   └── middleware/   # Rate limiting
│   ├── migrations/       # Alembic migrations
│   └── tests/            # pytest test suite
├── frontend/             # Next.js 15 dashboard
│   ├── app/              # App Router pages
│   └── components/       # shadcn/ui + custom components
├── sdks/
│   ├── python/           # agentid (PyPI)
│   └── typescript/       # @agentid/sdk (npm)
├── examples/             # Integration examples
│   ├── langchain_example.py
│   ├── crewai_example.py
│   ├── openai_example.py
│   └── typescript_example.ts
└── .github/workflows/    # CI/CD
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). PRs welcome.

## License

MIT — see [LICENSE](LICENSE).

---

*Built for the agent infrastructure era.*

---

Made by [@pedroshakoor](https://x.com/pedroshakoor) — follow for updates.
