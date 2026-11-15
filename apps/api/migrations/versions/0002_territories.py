"""Import checksum-pinned CNIGS/OCHA COD-AB catalog, preserving existing records."""
from alembic import op
from sqlalchemy.orm import Session
from app.core import seed_territories

revision = "0002_territories"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    with Session(bind=op.get_bind()) as session:
        seed_territories(session)


def downgrade():
    # Catalog rows may be referenced by contributions; a schema rollback never deletes them.
    pass
