"""
AgentID Python SDK — async and sync clients.

Async client (recommended):
    async with AgentIDClient(...) as client:
        token = await client.get_token()

Sync client:
    with AgentIDClientSync(...) as client:
        token = client.get_token()
"""

import asyncio
import threading
from datetime import datetime, timezone
from typing import Any

import httpx

from agentid.exceptions import (
    AgentIDError,
    AuthError,
    PolicyDeniedError,
    RateLimitError,
    ServerError,
    TokenExpiredError,
)
from agentid.models import AgentInfo, AuditEntry, Credential


class AgentIDClient:
    """
    Async AgentID client with automatic token refresh.

    Args:
        base_url: AgentID server URL (e.g. "https://api.agentid.dev")
        agent_id: Your registered agent's ID
        api_key: Your agent's API key (agid_...)
        ttl_minutes: Token TTL in minutes (default: 15)
        auto_refresh: Auto-refresh token before expiry (default: True)
        refresh_buffer_seconds: Seconds before expiry to refresh (default: 60)
    """

    def __init__(
        self,
        base_url: str,
        agent_id: str,
        api_key: str,
        ttl_minutes: int = 15,
        auto_refresh: bool = True,
        refresh_buffer_seconds: int = 60,
    ):
        self.base_url = base_url.rstrip("/")
        self.agent_id = agent_id
        self.api_key = api_key
        self.ttl_minutes = ttl_minutes
        self.auto_refresh = auto_refresh
        self.refresh_buffer_seconds = refresh_buffer_seconds

        self._credential: Credential | None = None
        self._lock = asyncio.Lock()
        self._http: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "AgentIDClient":
        self._http = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0,
            headers={"User-Agent": f"agentid-python/1.0.0"},
        )
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._http:
            await self._http.aclose()

    @property
    def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            raise AgentIDError("Client not started. Use 'async with AgentIDClient(...) as client:'")
        return self._http

    def _should_refresh(self) -> bool:
        if self._credential is None:
            return True
        if self._credential.is_expired():
            return True
        if self.auto_refresh:
            from datetime import timedelta
            refresh_at = self._credential.expires_at - timedelta(seconds=self.refresh_buffer_seconds)
            return datetime.now(timezone.utc) >= refresh_at
        return False

    async def get_token(self) -> str:
        """Get a valid JWT token, refreshing if needed."""
        async with self._lock:
            if self._should_refresh():
                await self._refresh_token()
        return self._credential.token  # type: ignore

    async def _refresh_token(self) -> None:
        resp = await self._client.post(
            "/v1/credentials/issue",
            json={"agent_id": self.agent_id, "ttl_minutes": self.ttl_minutes},
            headers={"X-API-Key": self.api_key},
        )
        self._handle_error(resp)
        data = resp.json()
        self._credential = Credential(
            token=data["token"],
            credential_id=data["credential_id"],
            jti=data["jti"],
            expires_at=datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00")),
            scope=data.get("scope", {}),
        )

    async def log_action(
        self,
        action: str,
        resource: str | None = None,
        result: str = "allowed",
        prompt_snippet: str | None = None,
        tool_called: str | None = None,
        result_summary: str | None = None,
        cost_usd: float | None = None,
        duration_ms: int | None = None,
    ) -> AuditEntry:
        """Log an action performed by this agent."""
        token = await self.get_token()
        payload: dict[str, Any] = {
            "action": action,
            "result": result,
        }
        if resource:
            payload["resource"] = resource
        if prompt_snippet:
            payload["prompt_snippet"] = prompt_snippet[:1024]
        if tool_called:
            payload["tool_called"] = tool_called
        if result_summary:
            payload["result_summary"] = result_summary
        if cost_usd is not None:
            payload["cost_usd"] = cost_usd
        if duration_ms is not None:
            payload["duration_ms"] = duration_ms

        resp = await self._client.post(
            "/v1/audit/log",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        self._handle_error(resp)
        data = resp.json()
        return AuditEntry(
            id=data["log_id"],
            agent_id=self.agent_id,
            action=action,
            result=result,
            resource=resource,
        )

    async def verify(self, action: str, resource: str) -> tuple[bool, str]:
        """Check if this agent is allowed to perform an action."""
        token = await self.get_token()
        resp = await self._client.post(
            "/v1/verify",
            json={"action": action, "resource": resource},
            headers={"Authorization": f"Bearer {token}"},
        )
        self._handle_error(resp)
        data = resp.json()
        return data["allowed"], data["reason"]

    async def get_info(self) -> AgentInfo:
        """Get this agent's registration info."""
        resp = await self._client.get(f"/v1/agents/{self.agent_id}")
        self._handle_error(resp)
        data = resp.json()
        return AgentInfo(
            id=data["id"],
            name=data["name"],
            owner_id=data["owner_id"],
            status=data["status"],
            framework=data.get("framework"),
            description=data.get("description"),
        )

    @staticmethod
    def _handle_error(resp: httpx.Response) -> None:
        if resp.status_code == 200 or resp.status_code == 201:
            return
        if resp.status_code == 401:
            raise AuthError(resp.json().get("detail", "Unauthorized"))
        if resp.status_code == 403:
            detail = resp.json().get("detail", "Forbidden")
            raise PolicyDeniedError("unknown", "unknown", detail)
        if resp.status_code == 429:
            raise RateLimitError("Rate limit exceeded")
        if resp.status_code >= 500:
            raise ServerError(f"Server error {resp.status_code}: {resp.text}")
        raise AgentIDError(f"HTTP {resp.status_code}: {resp.text}")

    # ---- Convenience: LangChain tool auth header ----

    async def auth_headers(self) -> dict[str, str]:
        """Return headers to attach to any API call as this agent."""
        token = await self.get_token()
        return {"Authorization": f"Bearer {token}", "X-Agent-ID": self.agent_id}


class AgentIDClientSync:
    """
    Synchronous wrapper around AgentIDClient.
    Runs async operations in a background thread's event loop.

    Usage:
        with AgentIDClientSync(...) as client:
            token = client.get_token()
            client.log_action("email:send", resource="user@example.com")
    """

    def __init__(self, *args: Any, **kwargs: Any):
        self._async_client = AgentIDClient(*args, **kwargs)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
            self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
            self._thread.start()
        return self._loop

    def _run(self, coro: Any) -> Any:
        loop = self._get_loop()
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result(timeout=60)

    def __enter__(self) -> "AgentIDClientSync":
        self._run(self._async_client.__aenter__())
        return self

    def __exit__(self, *args: Any) -> None:
        self._run(self._async_client.__aexit__(*args))
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)

    def get_token(self) -> str:
        return self._run(self._async_client.get_token())

    def log_action(self, **kwargs: Any) -> AuditEntry:
        return self._run(self._async_client.log_action(**kwargs))

    def verify(self, action: str, resource: str) -> tuple[bool, str]:
        return self._run(self._async_client.verify(action, resource))

    def auth_headers(self) -> dict[str, str]:
        return self._run(self._async_client.auth_headers())
