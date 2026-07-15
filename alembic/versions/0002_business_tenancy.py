"""business tenancy

Revision ID: 0002_business_tenancy
Revises: 0001_initial_postgres_schema
Create Date: 2026-07-15
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_business_tenancy"
down_revision = "0001_initial_postgres_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "business_entities",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("legal_name", sa.String(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_business_entities_created_by", "business_entities", ["created_by"])

    op.create_table(
        "business_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("invited_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["business_entities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invited_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("business_id", "user_id", name="uq_business_membership_business_user"),
    )
    op.create_index("ix_business_memberships_business_id", "business_memberships", ["business_id"])
    op.create_index("ix_business_memberships_role", "business_memberships", ["role"])
    op.create_index("ix_business_memberships_status", "business_memberships", ["status"])
    op.create_index("ix_business_memberships_user_id", "business_memberships", ["user_id"])
    op.create_index("ix_business_memberships_user_status", "business_memberships", ["user_id", "status"])

    op.create_table(
        "business_invitations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("invited_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("accepted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["accepted_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["business_id"], ["business_entities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invited_by"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_business_invitations_business_id", "business_invitations", ["business_id"])
    op.create_index("ix_business_invitations_business_status", "business_invitations", ["business_id", "status"])
    op.create_index("ix_business_invitations_email", "business_invitations", ["email"])
    op.create_index("ix_business_invitations_email_status", "business_invitations", ["email", "status"])
    op.create_index("ix_business_invitations_invited_by", "business_invitations", ["invited_by"])
    op.create_index("ix_business_invitations_role", "business_invitations", ["role"])
    op.create_index("ix_business_invitations_status", "business_invitations", ["status"])
    op.create_index("ix_business_invitations_token_hash", "business_invitations", ["token_hash"])

    op.add_column("categories", sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("transactions", sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("mcp_api_keys", sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=True))

    op.create_foreign_key("fk_categories_business_id", "categories", "business_entities", ["business_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("fk_transactions_business_id", "transactions", "business_entities", ["business_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("fk_mcp_api_keys_business_id", "mcp_api_keys", "business_entities", ["business_id"], ["id"], ondelete="CASCADE")

    op.drop_index("ix_categories_owner_type_name", table_name="categories")
    op.drop_constraint("uq_categories_owner_type_name", "categories", type_="unique")
    op.create_index("ix_categories_business_id", "categories", ["business_id"])
    op.create_index("ix_categories_business_type_name", "categories", ["business_id", "type", "name"])
    op.create_unique_constraint("uq_categories_business_type_name", "categories", ["business_id", "type", "normalized_name"])

    op.drop_index("ix_transactions_owner_type_date", table_name="transactions")
    op.drop_index("ix_transactions_owner_category", table_name="transactions")
    op.create_index("ix_transactions_business_id", "transactions", ["business_id"])
    op.create_index("ix_transactions_business_type_date", "transactions", ["business_id", "type", "date"])
    op.create_index("ix_transactions_business_category", "transactions", ["business_id", "category_id"])

    op.drop_index("ix_mcp_api_keys_owner_created", table_name="mcp_api_keys")
    op.create_index("ix_mcp_api_keys_business_id", "mcp_api_keys", ["business_id"])
    op.create_index("ix_mcp_api_keys_business_created", "mcp_api_keys", ["business_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_mcp_api_keys_business_created", table_name="mcp_api_keys")
    op.drop_index("ix_mcp_api_keys_business_id", table_name="mcp_api_keys")
    op.create_index("ix_mcp_api_keys_owner_created", "mcp_api_keys", ["created_by", "created_at"])
    op.drop_constraint("fk_mcp_api_keys_business_id", "mcp_api_keys", type_="foreignkey")
    op.drop_column("mcp_api_keys", "business_id")

    op.drop_index("ix_transactions_business_category", table_name="transactions")
    op.drop_index("ix_transactions_business_type_date", table_name="transactions")
    op.drop_index("ix_transactions_business_id", table_name="transactions")
    op.create_index("ix_transactions_owner_category", "transactions", ["created_by", "category_id"])
    op.create_index("ix_transactions_owner_type_date", "transactions", ["created_by", "type", "date"])
    op.drop_constraint("fk_transactions_business_id", "transactions", type_="foreignkey")
    op.drop_column("transactions", "business_id")

    op.drop_constraint("uq_categories_business_type_name", "categories", type_="unique")
    op.drop_index("ix_categories_business_type_name", table_name="categories")
    op.drop_index("ix_categories_business_id", table_name="categories")
    op.create_unique_constraint("uq_categories_owner_type_name", "categories", ["created_by", "type", "normalized_name"])
    op.create_index("ix_categories_owner_type_name", "categories", ["created_by", "type", "name"])
    op.drop_constraint("fk_categories_business_id", "categories", type_="foreignkey")
    op.drop_column("categories", "business_id")

    op.drop_table("business_invitations")
    op.drop_table("business_memberships")
    op.drop_table("business_entities")
