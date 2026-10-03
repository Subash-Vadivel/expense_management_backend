"""store MCP API keys encrypted so they can be copied again

Revision ID: 0004_mcp_api_key_encrypted
Revises: 0003_email_verification
Create Date: 2026-10-03
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0004_mcp_api_key_encrypted"
down_revision = "0003_email_verification"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Nullable: keys created before this migration only have a hash and can't be revealed.
    op.add_column("mcp_api_keys", sa.Column("encrypted_key", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("mcp_api_keys", "encrypted_key")
