"""add_indexes_for_budget_and_created_at

Revision ID: a10bd25799ac
Revises: 148875d256b5
Create Date: 2026-10-21
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a10bd25799ac"
down_revision: str | None = "148875d256b5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_leads_budget_inr",
        "leads",
        ["budget_inr"],
        unique=False,
    )
    op.create_index(
        "ix_leads_status_budget",
        "leads",
        ["status", "budget_inr"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_leads_status_budget", table_name="leads", if_exists=True)
    op.drop_index("ix_leads_budget_inr", table_name="leads", if_exists=True)
