from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.agent import Agent


class PolicyBase(SQLModel):
    agent_id: str = Field(foreign_key="agents.id", index=True)
    name: str = Field(max_length=128)
    description: str | None = Field(default=None, max_length=512)
    policy_json: str = Field()  # Full JSON policy document
    enabled: bool = Field(default=True)
    priority: int = Field(default=0)  # higher = evaluated first


class Policy(PolicyBase, table=True):
    __tablename__ = "policies"

    id: str = Field(primary_key=True, max_length=36)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    agent: "Agent" = Relationship(back_populates="policies")


class PolicyCreate(SQLModel):
    name: str
    description: str | None = None
    policy_json: str  # JSON string of PolicyDocument
    enabled: bool = True
    priority: int = 0


class PolicyRead(PolicyBase):
    id: str
    created_at: datetime
    updated_at: datetime


class PolicyUpdate(SQLModel):
    name: str | None = None
    description: str | None = None
    policy_json: str | None = None
    enabled: bool | None = None
    priority: int | None = None


# Policy document schema (validated in policy_engine.py)
# {
#   "effect": "allow" | "deny",
#   "resources": ["email:*", "file:read:*"],
#   "actions": ["read", "send", "*"],
#   "conditions": {
#     "max_daily": 100,
#     "time_window": {"start": "09:00", "end": "17:00"},
#     "ip_allowlist": ["10.0.0.0/8"],
#     "require_mfa": false
#   }
# }
