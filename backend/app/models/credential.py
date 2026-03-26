from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.agent import Agent


class CredentialStatus(str, Enum):
    active = "active"
    expired = "expired"
    revoked = "revoked"


class CredentialBase(SQLModel):
    agent_id: str = Field(foreign_key="agents.id", index=True)
    jti: str = Field(unique=True, index=True, max_length=64)  # JWT ID for revocation
    scope_json: str = Field(default="{}")  # JSON policy snapshot baked into this token
    ttl_minutes: int = Field(default=15)
    status: CredentialStatus = Field(default=CredentialStatus.active)
    issued_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime


class Credential(CredentialBase, table=True):
    __tablename__ = "credentials"

    id: str = Field(primary_key=True, max_length=36)
    revoked_at: datetime | None = Field(default=None)
    revoke_reason: str | None = Field(default=None, max_length=256)

    agent: "Agent" = Relationship(back_populates="credentials")


class CredentialRead(SQLModel):
    id: str
    agent_id: str
    jti: str
    scope_json: str
    ttl_minutes: int
    status: CredentialStatus
    issued_at: datetime
    expires_at: datetime


class CredentialIssueRequest(SQLModel):
    agent_id: str
    ttl_minutes: int | None = None  # defaults to agent default or global default
    scope_override: dict | None = None  # override policies for this token


class CredentialIssueResponse(SQLModel):
    token: str
    credential_id: str
    jti: str
    expires_at: datetime
    scope: dict
