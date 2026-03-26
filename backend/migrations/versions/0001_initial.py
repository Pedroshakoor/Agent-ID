"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2026-03-26

"""
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agents",
        sa.Column("id", sqlmodel.AutoString(length=36), nullable=False),
        sa.Column("name", sqlmodel.AutoString(length=128), nullable=False),
        sa.Column("description", sqlmodel.AutoString(length=1024), nullable=True),
        sa.Column("owner_id", sqlmodel.AutoString(length=128), nullable=False),
        sa.Column("framework", sqlmodel.AutoString(length=64), nullable=True),
        sa.Column("tags", sqlmodel.AutoString(length=512), nullable=True),
        sa.Column("status", sqlmodel.AutoString(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("api_key_hash", sqlmodel.AutoString(length=256), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("last_active_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agents_name", "agents", ["name"])
    op.create_index("ix_agents_owner_id", "agents", ["owner_id"])

    op.create_table(
        "policies",
        sa.Column("id", sqlmodel.AutoString(length=36), nullable=False),
        sa.Column("agent_id", sqlmodel.AutoString(length=36), nullable=False),
        sa.Column("name", sqlmodel.AutoString(length=128), nullable=False),
        sa.Column("description", sqlmodel.AutoString(length=512), nullable=True),
        sa.Column("policy_json", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_policies_agent_id", "policies", ["agent_id"])

    op.create_table(
        "credentials",
        sa.Column("id", sqlmodel.AutoString(length=36), nullable=False),
        sa.Column("agent_id", sqlmodel.AutoString(length=36), nullable=False),
        sa.Column("jti", sqlmodel.AutoString(length=64), nullable=False),
        sa.Column("scope_json", sa.Text(), nullable=False),
        sa.Column("ttl_minutes", sa.Integer(), nullable=False),
        sa.Column("status", sqlmodel.AutoString(), nullable=False),
        sa.Column("issued_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("revoke_reason", sqlmodel.AutoString(length=256), nullable=True),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("jti"),
    )
    op.create_index("ix_credentials_agent_id", "credentials", ["agent_id"])
    op.create_index("ix_credentials_jti", "credentials", ["jti"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sqlmodel.AutoString(length=36), nullable=False),
        sa.Column("agent_id", sqlmodel.AutoString(length=36), nullable=False),
        sa.Column("credential_id", sqlmodel.AutoString(length=36), nullable=True),
        sa.Column("jti", sqlmodel.AutoString(length=64), nullable=True),
        sa.Column("action", sqlmodel.AutoString(length=256), nullable=False),
        sa.Column("resource", sqlmodel.AutoString(length=512), nullable=True),
        sa.Column("result", sqlmodel.AutoString(), nullable=False),
        sa.Column("prompt_snippet", sqlmodel.AutoString(length=1024), nullable=True),
        sa.Column("tool_called", sqlmodel.AutoString(length=256), nullable=True),
        sa.Column("result_summary", sqlmodel.AutoString(length=1024), nullable=True),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column("ip_address", sqlmodel.AutoString(length=64), nullable=True),
        sa.Column("user_agent", sqlmodel.AutoString(length=512), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_agent_id", "audit_logs", ["agent_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_result", "audit_logs", ["result"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("credentials")
    op.drop_table("policies")
    op.drop_table("agents")
