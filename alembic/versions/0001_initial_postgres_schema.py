"""initial postgres schema

Revision ID: 0001_initial_postgres_schema
Revises:
Create Date: 2026-07-15
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial_postgres_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("normalized_name", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("custom_fields", sa.JSON(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("created_by", "type", "normalized_name", name="uq_categories_owner_type_name"),
    )
    op.create_index("ix_categories_created_by", "categories", ["created_by"])
    op.create_index("ix_categories_normalized_name", "categories", ["normalized_name"])
    op.create_index("ix_categories_type", "categories", ["type"])
    op.create_index("ix_categories_owner_type_name", "categories", ["created_by", "type", "name"])

    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("custom_field_values", sa.JSON(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transactions_category_id", "transactions", ["category_id"])
    op.create_index("ix_transactions_created_by", "transactions", ["created_by"])
    op.create_index("ix_transactions_date", "transactions", ["date"])
    op.create_index("ix_transactions_type", "transactions", ["type"])
    op.create_index("ix_transactions_owner_type_date", "transactions", ["created_by", "type", "date"])
    op.create_index("ix_transactions_owner_category", "transactions", ["created_by", "category_id"])

    op.create_table(
        "mcp_api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("key_hash", sa.String(), nullable=False),
        sa.Column("key_prefix", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("disabled_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_hash"),
    )
    op.create_index("ix_mcp_api_keys_created_by", "mcp_api_keys", ["created_by"])
    op.create_index("ix_mcp_api_keys_enabled", "mcp_api_keys", ["enabled"])
    op.create_index("ix_mcp_api_keys_key_hash", "mcp_api_keys", ["key_hash"])
    op.create_index("ix_mcp_api_keys_owner_created", "mcp_api_keys", ["created_by", "created_at"])


def downgrade() -> None:
    op.drop_table("mcp_api_keys")
    op.drop_table("transactions")
    op.drop_table("categories")
    op.drop_table("users")
