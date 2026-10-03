"""reports and report widgets

Revision ID: 0005_reports
Revises: 0004_mcp_api_key_encrypted
Create Date: 2026-10-03
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_reports"
down_revision = "0004_mcp_api_key_encrypted"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["business_entities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reports_business_id", "reports", ["business_id"])
    op.create_index("ix_reports_created_by", "reports", ["created_by"])
    op.create_index("ix_reports_business_created", "reports", ["business_id", "created_at"])

    op.create_table(
        "report_widgets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("chart_type", sa.String(), nullable=False),
        sa.Column("config", postgresql.JSONB(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("width", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_report_widgets_report_id", "report_widgets", ["report_id"])
    op.create_index("ix_report_widgets_report_position", "report_widgets", ["report_id", "position"])


def downgrade() -> None:
    op.drop_index("ix_report_widgets_report_position", table_name="report_widgets")
    op.drop_index("ix_report_widgets_report_id", table_name="report_widgets")
    op.drop_table("report_widgets")
    op.drop_index("ix_reports_business_created", table_name="reports")
    op.drop_index("ix_reports_created_by", table_name="reports")
    op.drop_index("ix_reports_business_id", table_name="reports")
    op.drop_table("reports")
