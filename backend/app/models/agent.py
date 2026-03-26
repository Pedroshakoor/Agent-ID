from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.credential import Credential
    from app.models.audit_log import AuditLog
    from app.models.policy import Policy


class AgentStatus(str, Enum):
    active = "active"
    suspended = "suspended"
    revoked = "revoked"


class AgentBase(SQLModel):
    name: str = Field(index=True, max_length=128)
    description: str | None = Field(default=None, max_length=1024)
    owner_id: str = Field(index=True, max_length=128)
    framework: str | None = Field(default=None, max_length=64)  # langchain, crewai, etc.
    tags: str | None = Field(default=None, max_length=512)  # JSON array stored as string
    status: AgentStatus = Field(default=AgentStatus.active)
    metadata_json: str | None = Field(default=None)  # arbitrary JSON


class Agent(AgentBase, table=True):
    __tablename__ = "agents"

    id: str = Field(primary_key=True, max_length=36)
    api_key_hash: str = Field(max_length=256)  # bcrypt hash of API key for dashboard auth
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_active_at: datetime | None = Field(default=None)

    credentials: list["Credential"] = Relationship(back_populates="agent")
    audit_logs: list["AuditLog"] = Relationship(back_populates="agent")
    policies: list["Policy"] = Relationship(back_populates="agent")


class AgentCreate(AgentBase):
    policies: list[dict] | None = None  # initial policy list


class AgentRead(AgentBase):
    id: str
    created_at: datetime
    updated_at: datetime
    last_active_at: datetime | None


class AgentReadWithKey(AgentRead):
    api_key: str  # only returned on creation


class AgentUpdate(SQLModel):
    name: str | None = None
    description: str | None = None
    framework: str | None = None
    tags: str | None = None
    status: AgentStatus | None = None
    metadata_json: str | None = None
