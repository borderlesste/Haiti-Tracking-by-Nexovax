"""Synthetic browser QA data, strictly isolated from the normal local database."""
from pathlib import Path
import os
from sqlalchemy import select
from app.core import Settings, database, migrate, passwords, seed_territories
from app.models import User

root = Path(__file__).resolve().parents[1]
target = (root / ".runtime" / "browser-qa.db").resolve()
settings = Settings(env="test", database_url=f"sqlite:///{target}", runtime_dir=root / ".runtime" / "browser-qa")
engine, Session = database(settings)
migrate(engine)
with Session() as session:
    seed_territories(session)
    for email, role in [("qa-contributor@example.org", "user"), ("qa-moderator@example.org", "admin")]:
        if not session.scalar(select(User).where(User.email == email)):
            session.add(User(email=email, display_name="Browser QA " + role, role=role, profile="collaborator", email_verified=True, password_hash=passwords.hash("Synthetic-browser-test-only-2026!"), mfa_secret=settings.cipher.encrypt(b"JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP").decode() if role == "admin" else None))
    session.commit()
engine.dispose()
print("Synthetic QA users prepared in the explicitly separate browser-qa.db; normal app data unchanged.")
