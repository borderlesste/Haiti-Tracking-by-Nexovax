"""Explicit local/staging maintenance; never runs on import."""
import argparse
import getpass
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pyotp
from sqlalchemy import select, update

from .core import Settings, audit, database, deliver_mail, migrate, normalize, passwords, seed_territories
from .models import CodeCounter, Contribution, Location, User, now


def purge_gps(session, days=30, apply=False):
    if not 1 <= days <= 365:
        raise ValueError("Retention must be 1–365 days")
    cutoff = now() - timedelta(days=days)
    count = 0
    query = select(Contribution)
    for row in session.scalars(query.with_for_update() if apply else query):
        if not row.payload.get("gps_observation"):
            continue
        received = datetime.fromisoformat(row.payload["gps_received_at"]) if row.payload.get("gps_received_at") else row.updated_at
        if received.replace(tzinfo=received.tzinfo or timezone.utc) >= cutoff:
            continue
        count += 1
        if apply:
            data = {key: value for key, value in row.payload.items() if key not in {"gps_observation", "pin_distance_m", "gps_received_at"}}
            data["gps_retention_expired"] = True
            row.payload, row.version = data, row.version + 1
            if row.status in {"submitted", "needs_review"}:
                row.status = "needs_review"
            audit(session, None, "privacy.gps_purged", row.id, {"retention_days": days})
    if apply:
        session.commit()
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["migrate", "seed-territories", "seed-demo", "create-user", "export-openapi", "deliver-mail", "purge-gps"])
    parser.add_argument("--retention-days", type=int, default=30)
    parser.add_argument("--apply", action="store_true", help="Apply the reviewed GPS retention policy; default is dry-run")
    args = parser.parse_args()
    settings = Settings()
    engine, Session = database(settings)
    if args.command == "purge-gps":
        with Session() as session:
            count = purge_gps(session, args.retention_days, args.apply)
        print(json.dumps({"mode": "applied" if args.apply else "dry-run", "eligible_records": count, "retention_days": args.retention_days}))
    elif args.command == "migrate":
        from alembic import command
        from alembic.config import Config
        command.upgrade(Config(str(Path(__file__).resolve().parent.parent / "alembic.ini")), "head")
        print("Schema prepared. No existing production records were removed.")
    elif args.command == "export-openapi":
        from .main import create_app
        destination = Path("openapi.json")
        destination.write_text(json.dumps(create_app(settings).openapi(), ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"OpenAPI written to {destination.resolve()}")
    elif args.command == "seed-territories":
        if settings.production:
            raise SystemExit("Catalog import in production requires an explicit reviewed migration; use the pinned catalog with the migration owner")
        with Session() as session:
            seed_territories(session)
        print("Pinned CNIGS/OCHA territory catalog imported. Review its validity date before pilot use.")
    elif args.command == "deliver-mail":
        deliver_mail(settings, Session, limit=100)
        print("Due email jobs processed; delivery outcomes remain private.")
    elif args.command == "seed-demo":
        if settings.production:
            raise SystemExit("Demo data cannot be seeded in production")
        with Session() as session:
            seed_territories(session)
            samples = [
                ("Pharmacie Démo — Delmas", "business", 18.548, -72.299, "HT0112"),
                ("Marché Démo — Port-au-Prince", "public", 18.547, -72.337, "HT0111"),
                ("Point de repère Démo — Pétion-Ville", "landmark", 18.513, -72.286, "HT0114"),
            ]
            for name, kind, lat, lon, territory in samples:
                if session.scalar(select(Location.id).where(Location.name == name)):
                    continue
                value = session.execute(update(CodeCounter).where(CodeCounter.id == 1).values(value=CodeCounter.value+1).returning(CodeCounter.value)).scalar_one()
                session.add(Location(public_code=f"HT-NXV-{value:06d}", name=name, normalized_name=normalize(name), type=kind, latitude=lat, longitude=lon, territory_id=territory, address={"neighborhood": "Démonstration", "reference": "Donnée fictive — ne pas utiliser pour se déplacer"}, description="Fiche de démonstration fictive, non vérifiée sur le terrain.", confidence_score=0))
            session.commit()
        print("Explicitly labeled fictitious demo places inserted; never use them for navigation.")
    else:
        email = input("Email: ").strip().lower()
        name = input("Display name: ").strip()
        role = input("Role [user/moderator/admin]: ").strip()
        if role not in {"user", "moderator", "admin"}:
            raise SystemExit("Unknown role")
        password = getpass.getpass("Password (12+ characters): ")
        if len(password) < 12 or len(password) > 128:
            raise SystemExit("Password must contain 12–128 characters")
        secret = None
        if role in {"admin", "moderator"}:
            otp_secret = getpass.getpass("Authenticator base32 secret (stored encrypted; no spaces): ").strip()
            if not re.fullmatch("[A-Z2-7]{32,64}", otp_secret):
                raise SystemExit("A 32+ character base32 authenticator secret is required")
            otp = getpass.getpass("Current authenticator code: ")
            if not pyotp.TOTP(otp_secret).verify(otp, valid_window=1):
                raise SystemExit("Authenticator verification failed")
            secret = settings.cipher.encrypt(otp_secret.encode()).decode()
        with Session() as session:
            if session.scalar(select(User.id).where(User.email == email)):
                raise SystemExit("Account exists; no permissions were changed")
            user = User(email=email, display_name=name, role=role, password_hash=passwords.hash(password), email_verified=True, mfa_secret=secret)
            session.add(user)
            session.flush()
            audit(session, user, "account.provisioned_cli", user.id, {"role": role})
            session.commit()
        print("Account created with audited role assignment. No credentials were printed.")
    engine.dispose()


if __name__ == "__main__":
    main()
