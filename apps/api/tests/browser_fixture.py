"""Synthetic browser QA data, strictly isolated from the normal local database."""
from pathlib import Path
import os
from uuid import UUID
from sqlalchemy import select
from app.core import Settings, database, migrate, passwords, seed_territories
from app.models import Contribution, Location, User

root = Path(__file__).resolve().parents[1]
run_id = os.getenv("E2E_RUN_ID", "")
if run_id:
    if str(UUID(run_id)) != run_id:
        raise RuntimeError("E2E_RUN_ID must be a canonical UUID")
    runtime = root / ".runtime" / ("e2e-" + run_id)
    target = runtime / "test.db"
    if target.exists():
        raise RuntimeError("E2E setup requires a fresh database; existing state was not changed")
else:
    runtime = root / ".runtime" / "browser-qa"
    target = root / ".runtime" / "browser-qa.db"
target = target.resolve()
settings = Settings(env="test", database_url=f"sqlite:///{target.as_posix()}", runtime_dir=runtime)
engine, Session = database(settings)
migrate(engine)
with Session() as session:
    seed_territories(session)
    for email, role in [("qa-contributor@example.org", "user"), ("qa-moderator@example.org", "admin")]:
        if not session.scalar(select(User).where(User.email == email)):
            session.add(User(email=email, display_name="Browser QA " + role, role=role, profile="collaborator", email_verified=True, password_hash=passwords.hash("Synthetic-browser-test-only-2026!"), mfa_secret=settings.cipher.encrypt(b"JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP").decode() if role == "admin" else None))
    if run_id:
        author = session.scalar(select(User).where(User.email == "qa-contributor@example.org"))
        session.add(Location(public_code="HT-NXV-PRIVATEFIX", name="E2E private residence", normalized_name="e2e private residence", type="residence", territory_id="HT0112", latitude=18.58, longitude=-72.28, address={"reference": "Hidden synthetic fixture"}, public_visibility="private"))
        for decision in ("reject", "merge"):
            session.add(Contribution(author_user_id=author.id, status="needs_review", payload={
                "mode": "remote", "type": "public", "name": "E2E fixture " + decision,
                "territory_id": "HT0112", "selected_point": {"latitude": 18.6, "longitude": -72.4},
                "address": {"reference": "Remote synthetic proposal for moderation tests"},
                "description": "Fiche de démonstration fictive; scénario de test.",
                "knowledge_source": "community_reference", "source_declaration_accepted": True,
            }))
    session.commit()
engine.dispose()
print("Synthetic QA users prepared in a separate test database; normal app data unchanged.")
