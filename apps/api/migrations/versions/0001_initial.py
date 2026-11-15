"""Initial isolated Haiti Tracking pilot schema, not RD Marketplace.

Revision ID: 0001_initial
Revises:
"""
from alembic import op
from app.core import migrate
from app.models import Base
from app.core import Settings
from sqlalchemy import text

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    migrate(op.get_bind().engine)


def downgrade():
    # Explicit Alembic downgrade is destructive and reserved for disposable databases.
    if Settings().production:
        raise RuntimeError("Destructive schema downgrade is disabled in production; use a reviewed restore plan")
    bind = op.get_bind()
    # Local disposable rollback only: clear self-references before dropping the table.
    bind.execute(text("UPDATE locations SET parent_location_id=NULL, access_point_id=NULL"))
    for table in reversed(Base.metadata.sorted_tables):
        if table.name == "territories" and bind.dialect.name == "sqlite":
            # SQLite also checks self-references on DROP; clear child levels after dependent tables are gone.
            for level in ("section", "commune", "department", "country"):
                bind.execute(text("DELETE FROM territories WHERE level=:level"), {"level": level})
        table.drop(bind)
