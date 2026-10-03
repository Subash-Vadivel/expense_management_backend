"""store report widget grid layout ({x, y, w, h}) instead of position/width

Revision ID: 0006_report_widget_layout
Revises: 0005_reports
Create Date: 2026-10-03
"""
from __future__ import annotations

import json

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006_report_widget_layout"
down_revision = "0005_reports"
branch_labels = None
depends_on = None

COLUMNS = 12
DEFAULT_HEIGHT = 8


def upgrade() -> None:
    op.add_column("report_widgets", sa.Column("layout", postgresql.JSONB(), nullable=True))

    # Recreate the previous two-column flow: half widgets fill left then right, full ones take a row.
    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, report_id, width FROM report_widgets ORDER BY report_id, position, created_at")
    ).all()
    cursor: dict = {}
    for widget_id, report_id, width in rows:
        y, column = cursor.get(report_id, (0, 0))
        if width == "full":
            if column:
                y, column = y + DEFAULT_HEIGHT, 0
            layout = {"x": 0, "y": y, "w": COLUMNS, "h": DEFAULT_HEIGHT}
            y += DEFAULT_HEIGHT
        else:
            layout = {"x": column * (COLUMNS // 2), "y": y, "w": COLUMNS // 2, "h": DEFAULT_HEIGHT}
            column += 1
            if column == 2:
                y, column = y + DEFAULT_HEIGHT, 0
        cursor[report_id] = (y, column)
        bind.execute(
            sa.text("UPDATE report_widgets SET layout = CAST(:layout AS JSONB) WHERE id = :id"),
            {"layout": json.dumps(layout), "id": widget_id},
        )

    op.alter_column("report_widgets", "layout", nullable=False)
    op.drop_index("ix_report_widgets_report_position", table_name="report_widgets")
    op.drop_column("report_widgets", "position")
    op.drop_column("report_widgets", "width")


def downgrade() -> None:
    op.add_column("report_widgets", sa.Column("width", sa.String(), nullable=False, server_default="half"))
    op.add_column("report_widgets", sa.Column("position", sa.Integer(), nullable=False, server_default="0"))
    op.execute(
        "UPDATE report_widgets SET "
        "width = CASE WHEN (layout->>'w')::int >= 12 THEN 'full' ELSE 'half' END, "
        "position = (layout->>'y')::int * 100 + (layout->>'x')::int"
    )
    op.create_index("ix_report_widgets_report_position", "report_widgets", ["report_id", "position"])
    op.drop_column("report_widgets", "layout")
