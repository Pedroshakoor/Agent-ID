from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.agent import Agent


class AuditResult(str, Enum):
    allowed = "allowed"
    denied = "denied"
    error = "error"


class AuditLogBase(SQLModel):
    agent_id: str = Field(foreign_key="agents.id", index=True)
    credential_id: str | None = Field(default=None, index=True, max_length=36)
    jti: str | None = Field(default=None, index=True, max_length=64)

    # What happened
    action: str = Field(index=True, max_length=256)  # e.g. "email:send", "file:read"
    resource: str | None = Field(default=None, max_length=512)  # target resource
    result: AuditResult = Field(index=True)

    # Context
    prompt_snippet: str | None = Field(default=None, max_length=1024)
    tool_called: str | None = Field(default=None, max_length=256)
    result_summary: str | None = Field(default=None, max_length=1024)
    cost_usd: float | None = Field(default=None)

    # Technical
    ip_address: str | None = Field(default=None, max_length=64)
    user_agent: str | None = Field(default=None, max_length=512)
    duration_ms: int | None = Field(default=None)
    metadata_json: str | None = Field(default=None)


class AuditLog(AuditLogBase, table=True):
    __tablename__ = "audit_logs"

    id: str = Field(primary_key=True, max_length=36)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), index=True
    )

    agent: "Agent" = Relationship(back_populates="audit_logs")


class AuditLogCreate(SQLModel):
    action: str
    resource: str | None = None
    result: AuditResult = AuditResult.allowed
    prompt_snippet: str | None = None
    tool_called: str | None = None
    result_summary: str | None = None
    cost_usd: float | None = None
    duration_ms: int | None = None
    metadata_json: str | None = None


class AuditLogRead(AuditLogBase):
    id: str
    created_at: datetime
