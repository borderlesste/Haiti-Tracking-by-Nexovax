"""One transactional data model; private proposal payloads never feed public serializers."""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def now():
    return datetime.now(timezone.utc)


def uid():
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    display_name: Mapped[str] = mapped_column(String(100))
    phone_encrypted: Mapped[str | None] = mapped_column(Text)
    password_hash: Mapped[str] = mapped_column(Text)
    profile: Mapped[str] = mapped_column(String(20), default="collaborator")
    role: Mapped[str] = mapped_column(String(20), default="user")
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    mfa_secret: Mapped[str | None] = mapped_column(Text)
    consent_version: Mapped[str] = mapped_column(String(40), default="pilot-2026-11")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class UserSession(Base):
    __tablename__ = "user_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    mfa_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AuthToken(Base):
    __tablename__ = "auth_tokens"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    purpose: Mapped[str] = mapped_column(String(20))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used: Mapped[bool] = mapped_column(Boolean, default=False)


class MailJob(Base):
    __tablename__ = "mail_jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    payload_encrypted: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Territory(Base):
    __tablename__ = "territories"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("territories.id", ondelete="RESTRICT"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    level: Mapped[str] = mapped_column(String(30))
    aliases: Mapped[list] = mapped_column(JSON, default=list)
    country_code: Mapped[str] = mapped_column(String(2), default="HT")
    source_version: Mapped[str] = mapped_column(String(200))
    source_url: Mapped[str] = mapped_column(Text)
    license: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Location(Base):
    __tablename__ = "locations"
    __table_args__ = (
        CheckConstraint("latitude >= -90 AND latitude <= 90", name="location_latitude"),
        CheckConstraint("longitude >= -180 AND longitude <= 180", name="location_longitude"),
        CheckConstraint("confidence_score >= 0 AND confidence_score <= 1", name="location_confidence"),
        CheckConstraint("parent_location_id IS NULL OR parent_location_id <> id", name="location_parent_not_self"),
        CheckConstraint("access_point_id IS NULL OR access_point_id <> id", name="location_access_not_self"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    public_code: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    normalized_name: Mapped[str] = mapped_column(Text, index=True)
    aliases: Mapped[list] = mapped_column(JSON, default=list, server_default="[]")
    normalized_aliases: Mapped[str] = mapped_column(Text, default="", server_default="")
    parent_location_id: Mapped[str | None] = mapped_column(ForeignKey("locations.id", ondelete="RESTRICT"), index=True)
    access_point_id: Mapped[str | None] = mapped_column(ForeignKey("locations.id", ondelete="RESTRICT"), index=True)
    type: Mapped[str] = mapped_column(String(30), index=True)
    territory_id: Mapped[str] = mapped_column(ForeignKey("territories.id", ondelete="RESTRICT"), index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    address: Mapped[dict] = mapped_column(JSON)
    description: Mapped[str] = mapped_column(String(1000), default="")
    public_visibility: Mapped[str] = mapped_column(String(20), default="public", index=True)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.7)
    version: Mapped[int] = mapped_column(Integer, default=1)
    last_verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class LocationVersion(Base):
    __tablename__ = "location_versions"
    __table_args__ = (UniqueConstraint("location_id", "version"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.id", ondelete="RESTRICT"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[dict] = mapped_column(JSON)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    reason: Mapped[str] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CodeRedirect(Base):
    __tablename__ = "public_code_redirects"
    old_code: Mapped[str] = mapped_column(String(30), primary_key=True)
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.id", ondelete="RESTRICT"), index=True)


class CodeCounter(Base):
    __tablename__ = "public_code_counter"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    value: Mapped[int] = mapped_column(Integer, default=0)


class Contribution(Base):
    __tablename__ = "contributions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    author_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    target_location_id: Mapped[str | None] = mapped_column(ForeignKey("locations.id", ondelete="RESTRICT"))
    payload: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(30), default="submitted", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    review_reason: Mapped[str | None] = mapped_column(String(1000))
    published_code: Mapped[str | None] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Review(Base):
    __tablename__ = "reviews"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    contribution_id: Mapped[str] = mapped_column(ForeignKey("contributions.id", ondelete="RESTRICT"), index=True)
    reviewer_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    decision: Mapped[str] = mapped_column(String(30))
    reason: Mapped[str] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PublicSuggestion(Base):
    __tablename__ = "public_suggestions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    payload: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="unverified")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class LocationReport(Base):
    __tablename__ = "location_reports"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.id", ondelete="RESTRICT"), index=True)
    category: Mapped[str] = mapped_column(String(30))
    description: Mapped[str] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(20), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    subject_id: Mapped[str] = mapped_column(String(100))
    metadata_sanitized: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DeveloperApp(Base):
    __tablename__ = "developer_apps"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    environment: Mapped[str] = mapped_column(String(10), default="test")
    status: Mapped[str] = mapped_column(String(20), default="active")
    daily_quota: Mapped[int] = mapped_column(Integer, default=1000)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ApiKey(Base):
    __tablename__ = "api_keys"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    app_id: Mapped[str] = mapped_column(ForeignKey("developer_apps.id", ondelete="RESTRICT"), index=True)
    prefix: Mapped[str] = mapped_column(String(30))
    secret_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ApiUsage(Base):
    __tablename__ = "api_usage_daily"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    app_id: Mapped[str] = mapped_column(ForeignKey("developer_apps.id", ondelete="RESTRICT"), index=True)
    day: Mapped[str] = mapped_column(String(10))
    count: Mapped[int] = mapped_column(Integer, default=0)


class RateLimit(Base):
    __tablename__ = "rate_limits"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[int] = mapped_column(Integer, index=True)


class Idempotency(Base):
    __tablename__ = "idempotency_keys"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    payload_hash: Mapped[str] = mapped_column(String(64))
    contribution_id: Mapped[str] = mapped_column(ForeignKey("contributions.id", ondelete="RESTRICT"))


class Evidence(Base):
    __tablename__ = "verification_evidence"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    contribution_id: Mapped[str] = mapped_column(ForeignKey("contributions.id", ondelete="RESTRICT"), index=True)
    storage_key: Mapped[str] = mapped_column(String(100))
    content_type: Mapped[str] = mapped_column(String(30), default="image/jpeg")
    moderation_status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
