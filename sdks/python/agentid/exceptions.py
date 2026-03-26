class AgentIDError(Exception):
    """Base exception for AgentID SDK errors."""


class AuthError(AgentIDError):
    """Authentication failed — invalid or missing API key."""


class PolicyDeniedError(AgentIDError):
    """Action denied by policy engine."""

    def __init__(self, action: str, resource: str, reason: str):
        self.action = action
        self.resource = resource
        self.reason = reason
        super().__init__(f"Action '{action}' on '{resource}' denied: {reason}")


class TokenExpiredError(AgentIDError):
    """JWT token has expired."""


class RateLimitError(AgentIDError):
    """Rate limit exceeded."""


class ServerError(AgentIDError):
    """AgentID server returned an unexpected error."""
