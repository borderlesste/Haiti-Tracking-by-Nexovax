import base64
import hashlib
import hmac
import json
import logging
import math
import os
import re
import secrets
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from cryptography.fernet import Fernet
from fastapi import HTTPException, Request
from sqlalchemy import create_engine, delete, event, func, inspect, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import sessionmaker

from .models import ApiKey, ApiUsage, AuditEvent, AuthToken, Base, CodeCounter, Contribution, DeveloperApp, Location, MailJob, RateLimit, Territory, User, UserSession, now

log = logging.getLogger("haititracking.security")
passwords = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)
DUMMY_PASSWORD_HASH = passwords.hash(secrets.token_urlsafe(32))


@dataclass
class Settings:
    env: str = field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./.runtime/haiti-tracking.db"))
    web_base_url: str = field(default_factory=lambda: os.getenv("WEB_BASE_URL", "http://127.0.0.1:3000").rstrip("/"))
    origins: list[str] = field(default_factory=lambda: [x.strip() for x in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000").split(",") if x.strip()])
    secret: str = field(default_factory=lambda: os.getenv("SESSION_SECRET", "local-development-only-never-use-in-production"))
    pepper: str = field(default_factory=lambda: os.getenv("API_KEY_PEPPER", "local-development-api-pepper-change-in-production"))
    resend_key: str = field(default_factory=lambda: os.getenv("RESEND_API_KEY", ""))
    email_from: str = field(default_factory=lambda: os.getenv("EMAIL_FROM", "Haiti Tracking <onboarding@resend.dev>"))
    runtime_dir: Path = field(default_factory=lambda: Path(os.getenv("RUNTIME_DIR", ".runtime")))

    def __post_init__(self):
        try:
            base = urlsplit(self.web_base_url)
            if base.scheme not in {"http", "https"} or not base.hostname or base.username or base.password or base.query or base.fragment or any(c.isspace() for c in self.web_base_url) or len(self.web_base_url) > 1000 or base.port == 0:
                raise ValueError()
        except ValueError:
            raise RuntimeError("WEB_BASE_URL must be an HTTP(S) URL without credentials, query or fragment")
        if self.env not in {"development", "test", "production"}:
            raise RuntimeError("APP_ENV must be development, test or production")
        if self.database_url.startswith("postgres://"):
            self.database_url = self.database_url.replace("postgres://", "postgresql+psycopg://", 1)
        elif self.database_url.startswith("postgresql://"):
            self.database_url = self.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        if os.getenv("REWARDS_CASH_ENABLED", "false").lower() == "true":
            raise RuntimeError("Monetary rewards are not enabled for this pilot")
        if self.production:
            bad = lambda value: any(marker in value.lower() for marker in ("development", "change_me", "changeme", "placeholder", "example"))
            if len(self.secret) < 32 or bad(self.secret) or len(self.pepper) < 32 or bad(self.pepper):
                raise RuntimeError("Production requires distinct random SESSION_SECRET and API_KEY_PEPPER (32+ characters)")
            if self.secret == self.pepper or not self.web_base_url.startswith("https://") or "*" in self.origins:
                raise RuntimeError("Production requires HTTPS, exact allowed origins and separate secrets")
            if not self.database_url.startswith("postgresql+") or not self.resend_key:
                raise RuntimeError("Production requires PostgreSQL/PostGIS and a configured transactional email provider")
            if any(not origin.startswith("https://") for origin in self.origins):
                raise RuntimeError("Production CORS origins must use HTTPS")

    @property
    def production(self):
        return self.env == "production"

    def digest(self, value: str):
        return hmac.new(self.pepper.encode(), value.encode(), hashlib.sha256).hexdigest()

    @property
    def cipher(self):
        return Fernet(base64.urlsafe_b64encode(hashlib.sha256(self.secret.encode()).digest()))


def database(settings: Settings):
    if settings.database_url.startswith("sqlite"):
        if ":memory:" not in settings.database_url:
            Path(settings.database_url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine(settings.database_url, connect_args={"check_same_thread": False, "timeout": 30})
        @event.listens_for(engine, "connect")
        def pragmas(conn, _):
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA journal_mode=WAL")
    else:
        engine = create_engine(settings.database_url, pool_pre_ping=True)
    return engine, sessionmaker(engine, expire_on_commit=False)


def ensure_location_relationships(connection):
    columns = {column["name"]: column for column in inspect(connection).get_columns("locations")}
    definitions = {
        "parent_location_id": "VARCHAR(36) REFERENCES locations(id) ON DELETE RESTRICT CONSTRAINT location_parent_not_self CHECK (parent_location_id IS NULL OR parent_location_id <> id)",
        "access_point_id": "VARCHAR(36) REFERENCES locations(id) ON DELETE RESTRICT CONSTRAINT location_access_not_self CHECK (access_point_id IS NULL OR access_point_id <> id)",
        "aliases": "JSON NOT NULL DEFAULT '[]'",
        "normalized_aliases": "TEXT NOT NULL DEFAULT ''",
    }
    for name, definition in definitions.items():
        if name not in columns:
            connection.execute(text(f"ALTER TABLE locations ADD COLUMN {name} {definition}"))
    for name in ("parent_location_id", "access_point_id"):
        connection.execute(text(f"CREATE INDEX IF NOT EXISTS ix_locations_{name} ON locations ({name})"))
    if connection.dialect.name == "postgresql":
        if getattr(columns["normalized_name"]["type"], "length", None):
            connection.execute(text("ALTER TABLE locations ALTER COLUMN normalized_name TYPE TEXT"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_locations_aliases_trgm ON locations USING gin(normalized_aliases gin_trgm_ops)"))
        connection.execute(text("""CREATE OR REPLACE FUNCTION prevent_location_parent_cycles() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
              PERFORM pg_advisory_xact_lock(684172031);
              IF NEW.parent_location_id IS NOT NULL AND EXISTS (
                WITH RECURSIVE ancestors AS (
                  SELECT id,parent_location_id FROM locations WHERE id=NEW.parent_location_id
                  UNION SELECT p.id,p.parent_location_id FROM locations p JOIN ancestors a ON p.id=a.parent_location_id
                ) SELECT 1 FROM ancestors WHERE id=NEW.id
              ) THEN RAISE EXCEPTION 'Location parent cycle'; END IF;
              RETURN NEW;
            END $$"""))
        connection.execute(text("DROP TRIGGER IF EXISTS location_parent_cycles ON locations"))
        connection.execute(text("CREATE TRIGGER location_parent_cycles BEFORE INSERT OR UPDATE OF parent_location_id ON locations FOR EACH ROW EXECUTE FUNCTION prevent_location_parent_cycles()"))
    else:
        for suffix, event_name in (("insert", "INSERT"), ("update", "UPDATE OF parent_location_id")):
            # Identifiers and events come only from the two literal tuples above.
            connection.execute(text(f"""CREATE TRIGGER IF NOT EXISTS location_parent_cycles_{suffix}
                BEFORE {event_name} ON locations WHEN NEW.parent_location_id IS NOT NULL BEGIN
                SELECT RAISE(ABORT,'Location parent cycle') WHERE EXISTS (
                  WITH RECURSIVE ancestors AS (
                    SELECT id,parent_location_id FROM locations WHERE id=NEW.parent_location_id
                    UNION SELECT p.id,p.parent_location_id FROM locations p JOIN ancestors a ON p.id=a.parent_location_id
                  ) SELECT 1 FROM ancestors WHERE id=NEW.id
                ); END"""))  # nosec B608


def migrate(engine):
    if engine.dialect.name == "postgresql":
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        ensure_location_relationships(conn)
        insert = pg_insert if engine.dialect.name == "postgresql" else sqlite_insert
        conn.execute(insert(CodeCounter).values(id=1, value=0).on_conflict_do_nothing(index_elements=["id"]))
        if engine.dialect.name == "postgresql":
            conn.execute(text("ALTER TABLE locations ADD COLUMN IF NOT EXISTS point geography(Point,4326) GENERATED ALWAYS AS (ST_SetSRID(ST_MakePoint(longitude, latitude),4326)::geography) STORED"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_locations_point_gist ON locations USING gist(point)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_locations_name_trgm ON locations USING gin(normalized_name gin_trgm_ops)"))
            conn.execute(text("CREATE OR REPLACE FUNCTION prevent_audit_changes() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Audit events are append only'; END $$"))
            conn.execute(text("DROP TRIGGER IF EXISTS audit_append_only ON audit_events"))
            conn.execute(text("CREATE TRIGGER audit_append_only BEFORE UPDATE OR DELETE ON audit_events FOR EACH ROW EXECUTE FUNCTION prevent_audit_changes()"))
            # Supabase API roles get no table policies or grants; only the dedicated backend role reads these tables.
            for table in Base.metadata.sorted_tables:
                conn.execute(text(f'ALTER TABLE "{table.name}" ENABLE ROW LEVEL SECURITY'))
                conn.execute(text(f'REVOKE ALL ON TABLE "{table.name}" FROM PUBLIC'))
                for role in ("anon", "authenticated"):
                    if conn.execute(text("SELECT 1 FROM pg_roles WHERE rolname=:name"), {"name": role}).scalar():
                        conn.execute(text(f'REVOKE ALL ON TABLE "{table.name}" FROM "{role}"'))
            runtime_role = os.getenv("BACKEND_DB_ROLE", "")
            if runtime_role:
                if not re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]{0,62}", runtime_role):
                    raise RuntimeError("Invalid BACKEND_DB_ROLE identifier")
                flags = conn.execute(text("SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=:role"), {"role": runtime_role}).one_or_none()
                if not flags or flags.rolsuper or flags.rolbypassrls:
                    raise RuntimeError("Backend runtime role must exist without SUPERUSER or BYPASSRLS")
                conn.execute(text(f'GRANT USAGE ON SCHEMA public TO "{runtime_role}"'))
                for table in Base.metadata.sorted_tables:
                    privileges = "SELECT, INSERT" if table.name == "audit_events" else "SELECT, INSERT, UPDATE, DELETE"
                    conn.execute(text(f'GRANT {privileges} ON TABLE "{table.name}" TO "{runtime_role}"'))
                    conn.execute(text(f'DROP POLICY IF EXISTS backend_access ON "{table.name}"'))
                    conn.execute(text(f'CREATE POLICY backend_access ON "{table.name}" TO "{runtime_role}" USING (true) WITH CHECK (true)'))


def normalize(value):
    return " ".join("".join(c for c in unicodedata.normalize("NFKD", value.lower()) if not unicodedata.combining(c)).split())


def utc_iso(value):
    return value.replace(tzinfo=value.tzinfo or timezone.utc).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def distance(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (a["latitude"], a["longitude"], b["latitude"], b["longitude"]))
    v = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 6_371_008.8 * 2 * math.asin(min(1, math.sqrt(v)))


def public_filter():
    return (Location.status == "active", Location.public_visibility == "public", Location.type.in_(["business", "public", "landmark", "road", "access"]))


def administrative_area(session, latitude, longitude):
    if session.bind.dialect.name != "postgresql":
        return None
    from .catalog import boundary_for
    result = {}
    parent = None
    for level in ("country", "department", "commune", "section"):
        rows = session.scalars(select(Territory).where(Territory.active == True, Territory.level == level, Territory.parent_id == parent).order_by(Territory.id))
        for row in rows:
            boundary = boundary_for(row.id)
            if boundary and session.execute(text("SELECT ST_Covers(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:shape),4326)),ST_SetSRID(ST_MakePoint(:lon,:lat),4326))"), {"shape": json.dumps(boundary), "lon": longitude, "lat": latitude}).scalar_one():
                result[level] = {"id": row.id, "name": row.name, "source_version": row.source_version}
                parent = row.id
                break
        else:
            break
    # shortcut: the small pilot walks pinned boundaries; materialize/index them when measured reverse traffic warrants it.
    return result or None


def public_location(location, session):
    from .schemas import PublicAddress
    territory = session.get(Territory, location.territory_id)
    ancestors = {}
    current = territory
    for _ in range(4):
        if not current or current.level in ancestors:
            break
        ancestors[current.level] = current
        current = session.get(Territory, current.parent_id) if current.parent_id else None
    is_demo = location.description.startswith("Fiche de démonstration fictive")
    def linked_code(identifier):
        return session.scalar(select(Location.public_code).where(Location.id == identifier, *public_filter())) if identifier else None
    return {
        "id": location.id, "code": location.public_code, "name": location.name, "type": location.type,
        "address": PublicAddress.model_validate({**location.address, "country_code": "HT", "commune": ancestors["commune"].name if "commune" in ancestors else "", "department": ancestors["department"].name if "department" in ancestors else "", "communal_section": ancestors["section"].name if "section" in ancestors else None}).model_dump(),
        "territory_id": location.territory_id,
        "coordinates": {"latitude": location.latitude, "longitude": location.longitude},
        "description": location.description, "aliases": location.aliases,
        "parent_location_code": linked_code(location.parent_location_id), "access_point_code": linked_code(location.access_point_id),
        "verification_status": "demonstration" if is_demo else "verified", "is_demo": is_demo, "confidence_score": location.confidence_score,
        "last_verified_at": utc_iso(location.last_verified_at), "version": location.version,
    }


def duplicates(session, payload, exclude_id=None):
    point = payload["selected_point"]
    stmt = select(Location).where(*public_filter(), Location.id != exclude_id if exclude_id else True)
    if session.bind.dialect.name == "postgresql":
        stmt = stmt.where(text("ST_DWithin(point, ST_SetSRID(ST_MakePoint(:lon,:lat),4326)::geography,200)")).params(lon=point["longitude"], lat=point["latitude"])
        query_name = normalize(payload["name"])
        stmt = stmt.order_by(func.greatest(func.similarity(Location.normalized_name, query_name), func.word_similarity(query_name, Location.normalized_aliases)).desc(), Location.id)
    else:
        # shortcut: SQLite is local development only; production uses the indexed PostGIS radius predicate.
        stmt = stmt.where(Location.latitude.between(point["latitude"]-.003, point["latitude"]+.003), Location.longitude.between(point["longitude"]-.003, point["longitude"]+.003))
    result = []
    for location in session.scalars(stmt.limit(100)):
        meters = distance(point, {"latitude": location.latitude, "longitude": location.longitude})
        similarity = max(SequenceMatcher(None, normalize(payload["name"]), name).ratio() for name in [location.normalized_name, *(normalize(alias) for alias in location.aliases)])
        if meters <= 200 and (similarity >= .45 or meters <= 30):
            reasons = ["nearby"]
            if similarity >= .7:
                reasons.append("similar_name")
            if location.type == payload["type"]:
                reasons.append("same_category")
            result.append({"code": location.public_code, "name": location.name, "type": location.type, "distance_m": round(meters, 1), "similarity_score": round(similarity, 3), "reasons": reasons})
    return sorted(result, key=lambda x: (-x["similarity_score"], x["distance_m"]))[:10]


def rate_limit(session, settings, key, count=60, seconds=60):
    stamp = int(time.time())
    bucket = stamp // seconds
    identifier = settings.digest(f"{key}:{bucket}")
    insert = pg_insert if session.bind.dialect.name == "postgresql" else sqlite_insert
    statement = insert(RateLimit).values(key=identifier, count=1, expires_at=(bucket+1)*seconds).on_conflict_do_update(index_elements=["key"], set_={"count": RateLimit.count + 1}).returning(RateLimit.count)
    used = session.execute(statement).scalar_one()
    session.commit()
    if used > count:
        raise HTTPException(429, "RATE_LIMITED", headers={"Retry-After": str(seconds-stamp % seconds)})


def audit(session, actor, action, subject, metadata=None):
    session.add(AuditEvent(actor_id=actor.id if actor else None, action=action, subject_id=str(subject), metadata_sanitized=metadata or {}))


def require_user(request, session, verified=False, staff=False, admin=False):
    token = request.cookies.get("ht_session", "")
    entry = session.scalar(select(UserSession).where(UserSession.token_hash == request.app.state.settings.digest(token), UserSession.expires_at > now())) if token else None
    user = session.get(User, entry.user_id) if entry else None
    if not user or not user.active:
        raise HTTPException(401, "UNAUTHENTICATED")
    if verified and not user.email_verified:
        raise HTTPException(403, "EMAIL_VERIFICATION_REQUIRED")
    if staff or admin:
        allowed = ["admin"] if admin else ["admin", "moderator"]
        if user.role not in allowed or not entry.mfa_verified:
            raise HTTPException(403, "FORBIDDEN")
    return user


def verify_password(password, stored):
    try:
        return passwords.verify(stored, password)
    except VerificationError:
        return False


def issue_email(session, settings, user, purpose):
    token = secrets.token_urlsafe(40)
    session.execute(update(AuthToken).where(AuthToken.user_id == user.id, AuthToken.purpose == purpose, AuthToken.used == False).values(used=True))
    session.add(AuthToken(user_id=user.id, token_hash=settings.digest(token), purpose=purpose, expires_at=now()+timedelta(minutes=30 if purpose == "reset" else 60)))
    path = "/restablecer#token=" if purpose == "reset" else "/verificar#token="
    link = settings.web_base_url + path + token
    title = "Réinitialiser votre mot de passe" if purpose == "reset" else "Vérifiez votre adresse e-mail"
    body = {"from": settings.email_from, "to": [user.email], "subject": f"Haiti Tracking — {title}", "text": f"{title}\n\n{link}\n\nCe lien est à usage unique et expire bientôt. Si vous n'êtes pas à l'origine de cette demande, ignorez ce message."}
    session.add(MailJob(payload_encrypted=settings.cipher.encrypt(json.dumps(body, ensure_ascii=False).encode()).decode()))


def deliver_mail(settings, Session, limit=10):
    """Lease durable encrypted jobs; provider failures never change a recovery response."""
    for _ in range(limit):
        with Session() as session:
            job = session.scalar(select(MailJob).where(MailJob.status.in_(["pending", "sending"]), MailJob.attempts < 5, MailJob.next_attempt_at <= now()).order_by(MailJob.created_at).with_for_update(skip_locked=True).limit(1))
            if not job:
                return
            attempts = job.attempts
            claimed = session.execute(update(MailJob).where(MailJob.id == job.id, MailJob.attempts == attempts, MailJob.next_attempt_at <= now()).values(status="sending", attempts=attempts+1, next_attempt_at=now()+timedelta(minutes=1)).execution_options(synchronize_session=False)).rowcount
            if not claimed:
                session.rollback()
                continue
            identifier, encrypted = job.id, job.payload_encrypted
            session.commit()
        delivered = False
        try:
            body = json.loads(settings.cipher.decrypt(encrypted.encode()))
            if settings.resend_key:
                result = httpx.post("https://api.resend.com/emails", headers={"Authorization": f"Bearer {settings.resend_key}", "Idempotency-Key": "mail-job-"+identifier}, json=body, timeout=15)
                result.raise_for_status()
            elif settings.production:
                raise RuntimeError("Email provider not configured")
            else:
                outbox = settings.runtime_dir / "outbox"
                outbox.mkdir(parents=True, exist_ok=True)
                # Development mail is a private local file; no tokens enter HTTP responses or logs.
                (outbox / f"{identifier}.json").write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
            delivered = True
        except Exception:
            log.warning("mail_delivery_deferred job_id=%s", identifier)
        with Session() as session:
            session.execute(update(MailJob).where(MailJob.id == identifier).values(status="delivered" if delivered else "pending", next_attempt_at=now()+timedelta(minutes=5), payload_encrypted="" if delivered else encrypted))
            session.commit()


def public_api_access(request, session, required=False):
    settings = request.app.state.settings
    authorization = request.headers.get("authorization")
    if not authorization:
        if required:
            raise HTTPException(401, "UNAUTHENTICATED")
        return
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "UNAUTHENTICATED")
    key = session.scalar(select(ApiKey).where(ApiKey.secret_hash == settings.digest(authorization[7:]), ApiKey.revoked == False, ApiKey.expires_at > now()))
    app = session.get(DeveloperApp, key.app_id) if key else None
    owner = session.get(User, app.owner_id) if app else None
    if not app or app.status != "active" or not owner or not owner.active or not owner.email_verified:
        raise HTTPException(401, "UNAUTHENTICATED")
    rate_limit(session, settings, f"api-key:{key.id}", count=60)
    day = now().date().isoformat()
    insert = pg_insert if session.bind.dialect.name == "postgresql" else sqlite_insert
    statement = insert(ApiUsage).values(key=f"{app.id}:{day}", app_id=app.id, day=day, count=1).on_conflict_do_update(index_elements=["key"], set_={"count": ApiUsage.count+1}).returning(ApiUsage.count)
    count = session.execute(statement).scalar_one()
    session.commit()
    if count > app.daily_quota:
        raise HTTPException(429, "QUOTA_EXCEEDED", headers={"Retry-After": "86400"})


def seed_territories(session):
    """Idempotently import the checksum-pinned CNIGS/OCHA catalog without deleting records."""
    from .catalog import catalog
    for record in catalog():
        if not session.get(Territory, record["id"]):
            session.add(Territory(**record))
        # Parents must exist before their children on databases enforcing foreign keys.
        session.flush()
    session.execute(update(Territory).where(Territory.source_version.like("illustrative-catalog-%")).values(active=False))
    session.commit()
