from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class AgentInfo:
    id: str
    name: str
    owner_id: str
    status: str
    framework: str | None = None
    description: str | None = None
    created_at: datetime | None = None
    last_active_at: datetime | None = None


@dataclass
class Credential:
    token: str
    credential_id: str
    jti: str
    expires_at: datetime
    scope: dict = field(default_factory=dict)

    def is_expired(self) -> bool:
        from datetime import timezone
        return datetime.now(timezone.utc) >= self.expires_at


@dataclass
class AuditEntry:
    id: str
    agent_id: str
    action: str
    result: str
    resource: str | None = None
    created_at: datetime | None = None
