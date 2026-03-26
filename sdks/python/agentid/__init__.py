"""
AgentID Python SDK
==================
Verifiable identity for every AI agent.

Quick start:
    from agentid import AgentIDClient

    client = AgentIDClient(
        base_url="http://localhost:8000",
        agent_id="your-agent-id",
        api_key="agid_your_api_key",
    )

    # Get a short-lived token
    token = await client.get_token()

    # Log an action
    await client.log_action(action="email:send", resource="user@example.com")
"""

from agentid.client import AgentIDClient, AgentIDClientSync
from agentid.exceptions import AgentIDError, AuthError, PolicyDeniedError, TokenExpiredError
from agentid.models import AgentInfo, Credential, AuditEntry

__version__ = "1.0.0"
__all__ = [
    "AgentIDClient",
    "AgentIDClientSync",
    "AgentIDError",
    "AuthError",
    "PolicyDeniedError",
    "TokenExpiredError",
    "AgentInfo",
    "Credential",
    "AuditEntry",
]
