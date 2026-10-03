"""MCP API keys belong to the user account instead of one workspace

Revision ID: 0007_account_mcp_keys
Revises: 0006_report_widget_layout
Create Date: 2026-10-03
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0007_account_mcp_keys"
down_revision = "0006_report_widget_layout"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Keys now reach every workspace their creator belongs to; the role is checked per tool call.
    op.drop_index("ix_mcp_api_keys_business_created", table_name="mcp_api_keys")
    op.drop_index("ix_mcp_api_keys_business_id", table_name="mcp_api_keys")
    op.drop_column("mcp_api_keys", "business_id")  # also drops fk_mcp_api_keys_business_id
    op.create_index("ix_mcp_api_keys_owner_created", "mcp_api_keys", ["created_by", "created_at"])


def downgrade() -> None:
    # Keys can't be re-attached to a workspace automatically, so the column comes back empty.
    op.drop_index("ix_mcp_api_keys_owner_created", table_name="mcp_api_keys")
    op.add_column("mcp_api_keys", sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_mcp_api_keys_business_id", "mcp_api_keys", "business_entities", ["business_id"], ["id"], ondelete="CASCADE"
    )
    op.create_index("ix_mcp_api_keys_business_id", "mcp_api_keys", ["business_id"])
    op.create_index("ix_mcp_api_keys_business_created", "mcp_api_keys", ["business_id", "created_at"])
