"""Tests for the AgentID Python SDK client."""

import pytest
import respx
import httpx
from datetime import datetime, timezone, timedelta

from agentid import AgentIDClient
from agentid.exceptions import AuthError, AgentIDError, PolicyDeniedError


BASE_URL = "http://test.agentid.local"
AGENT_ID = "test-agent-123"
API_KEY = "agid_testkey123"

FAKE_TOKEN_RESPONSE = {
    "token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.fake.sig",
    "credential_id": "cred-abc",
    "jti": "jti-xyz",
    "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat(),
    "scope": {"policies": [{"effect": "allow", "resources": ["*"], "actions": ["*"]}]},
}


@pytest.fixture
def client():
    return AgentIDClient(
        base_url=BASE_URL,
        agent_id=AGENT_ID,
        api_key=API_KEY,
        ttl_minutes=15,
    )


@pytest.mark.asyncio
async def test_get_token_issues_credential(client):
    with respx.mock:
        respx.post(f"{BASE_URL}/v1/credentials/issue").mock(
            return_value=httpx.Response(200, json=FAKE_TOKEN_RESPONSE)
        )
        async with client:
            token = await client.get_token()
            assert token == FAKE_TOKEN_RESPONSE["token"]


@pytest.mark.asyncio
async def test_get_token_cached(client):
    """Second call should not re-issue if token still valid."""
    call_count = 0

    with respx.mock:
        def handler(request):
            nonlocal call_count
            call_count += 1
            return httpx.Response(200, json=FAKE_TOKEN_RESPONSE)

        respx.post(f"{BASE_URL}/v1/credentials/issue").mock(side_effect=handler)

        async with client:
            await client.get_token()
            await client.get_token()
            assert call_count == 1  # Only issued once


@pytest.mark.asyncio
async def test_get_token_auth_error(client):
    with respx.mock:
        respx.post(f"{BASE_URL}/v1/credentials/issue").mock(
            return_value=httpx.Response(401, json={"detail": "Invalid API key"})
        )
        async with client:
            with pytest.raises(AuthError):
                await client.get_token()


@pytest.mark.asyncio
async def test_log_action(client):
    with respx.mock:
        respx.post(f"{BASE_URL}/v1/credentials/issue").mock(
            return_value=httpx.Response(200, json=FAKE_TOKEN_RESPONSE)
        )
        respx.post(f"{BASE_URL}/v1/audit/log").mock(
            return_value=httpx.Response(200, json={
                "logged": True,
                "log_id": "log-abc",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
        )
        async with client:
            entry = await client.log_action(
                action="email:send",
                resource="user@example.com",
                result="allowed",
                tool_called="send_email",
            )
            assert entry.id == "log-abc"
            assert entry.action == "email:send"


@pytest.mark.asyncio
async def test_verify_allowed(client):
    with respx.mock:
        respx.post(f"{BASE_URL}/v1/credentials/issue").mock(
            return_value=httpx.Response(200, json=FAKE_TOKEN_RESPONSE)
        )
        respx.post(f"{BASE_URL}/v1/verify").mock(
            return_value=httpx.Response(200, json={
                "allowed": True,
                "reason": "allowed",
                "agent_id": AGENT_ID,
            })
        )
        async with client:
            allowed, reason = await client.verify("read", "file:report.pdf")
            assert allowed is True
            assert reason == "allowed"


@pytest.mark.asyncio
async def test_verify_denied(client):
    with respx.mock:
        respx.post(f"{BASE_URL}/v1/credentials/issue").mock(
            return_value=httpx.Response(200, json=FAKE_TOKEN_RESPONSE)
        )
        respx.post(f"{BASE_URL}/v1/verify").mock(
            return_value=httpx.Response(200, json={
                "allowed": False,
                "reason": "No matching policy found",
                "agent_id": AGENT_ID,
            })
        )
        async with client:
            allowed, reason = await client.verify("delete", "system:root")
            assert allowed is False
            assert "policy" in reason.lower()


@pytest.mark.asyncio
async def test_auth_headers(client):
    with respx.mock:
        respx.post(f"{BASE_URL}/v1/credentials/issue").mock(
            return_value=httpx.Response(200, json=FAKE_TOKEN_RESPONSE)
        )
        async with client:
            headers = await client.auth_headers()
            assert headers["Authorization"].startswith("Bearer ")
            assert headers["X-Agent-ID"] == AGENT_ID


@pytest.mark.asyncio
async def test_get_info(client):
    with respx.mock:
        respx.get(f"{BASE_URL}/v1/agents/{AGENT_ID}").mock(
            return_value=httpx.Response(200, json={
                "id": AGENT_ID,
                "name": "test-agent",
                "owner_id": "owner-1",
                "status": "active",
                "framework": "langchain",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
        )
        async with client:
            info = await client.get_info()
            assert info.id == AGENT_ID
            assert info.name == "test-agent"
            assert info.framework == "langchain"


def test_credential_expired():
    from agentid.models import Credential
    expired = Credential(
        token="tok",
        credential_id="cid",
        jti="jti",
        expires_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
    )
    assert expired.is_expired() is True

    valid = Credential(
        token="tok",
        credential_id="cid",
        jti="jti",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    assert valid.is_expired() is False
