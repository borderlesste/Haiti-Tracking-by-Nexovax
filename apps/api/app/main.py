import base64
import hashlib
import hmac
import io
import json
import logging
import os
import re
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
from urllib.parse import quote

import pyotp
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import delete, func, or_, select, text, update
from sqlalchemy.exc import IntegrityError
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import schemas as S
from .core import DUMMY_PASSWORD_HASH, Settings, administrative_area, audit, database, deliver_mail, distance, duplicates, issue_email, migrate, normalize, passwords, public_api_access, public_filter, public_location, rate_limit, require_user, seed_territories, utc_iso, verify_password
from .models import ApiKey, ApiUsage, AuditEvent, AuthToken, CodeCounter, CodeRedirect, Contribution, DeveloperApp, Evidence, Idempotency, Location, LocationReport, LocationVersion, PublicSuggestion, Review, Territory, User, UserSession, now


def create_app(settings=None):
    settings = settings or Settings()
    engine, Session = database(settings)

    @asynccontextmanager
    async def lifespan(app):
        if settings.env != "production" and os.getenv("DATABASE_AUTO_CREATE", "true").lower() == "true":
            migrate(engine)
            with Session() as session:
                seed_territories(session)
        if settings.production:
            with engine.connect() as conn:
                flags = conn.execute(text("SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user")).one()
                owner = conn.execute(text("SELECT 1 FROM pg_tables WHERE schemaname='public' AND tablename='users' AND pg_has_role(current_user,tableowner,'MEMBER')")).scalar()
                if flags.rolsuper or flags.rolbypassrls or owner:
                    raise RuntimeError("Production backend must use a non-owner role without SUPERUSER/BYPASSRLS; migrate with BACKEND_DB_ROLE grants first")
        yield
        engine.dispose()

    app = FastAPI(title="Haiti Tracking by Nexovax", version="1.0.0", lifespan=lifespan, description="Verified public places only. Monetary rewards and residential sharing are disabled.", responses={status: {"model": S.ApiErrorResponse} for status in (400, 401, 403, 404, 405, 409, 413, 422, 429, 500, 503)})
    app.state.settings, app.state.engine, app.state.Session = settings, engine, Session
    app.add_middleware(CORSMiddleware, allow_origins=settings.origins, allow_credentials=True, allow_methods=["GET", "POST", "PATCH", "OPTIONS"], allow_headers=["Content-Type", "Authorization", "X-CSRF-Token", "Idempotency-Key"])
    if settings.production:
        hosts = [x.strip() for x in os.getenv("TRUSTED_HOSTS", "").split(",") if x.strip()]
        if not hosts or "*" in hosts:
            raise RuntimeError("Production requires explicit TRUSTED_HOSTS")
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts)

    def envelope(request, data, **extra):
        return {"success": True, "data": data, **extra, "request_id": request.state.request_id}

    def failure(request, status, code, details=None, headers=None):
        return JSONResponse({"success": False, "error": {"code": code, "message": code.replace("_", " ").capitalize(), "details": details or {}}, "request_id": getattr(request.state, "request_id", "unavailable")}, status_code=status, headers=headers)

    @app.middleware("http")
    async def security(request, call_next):
        request.state.request_id = "req_" + uuid4().hex
        try:
            if settings.production and request.url.scheme != "https" and request.url.path != "/v1/health":
                raise HTTPException(400, "HTTPS_REQUIRED")
            if request.url.path.startswith("/v1/") and request.url.path != "/v1/health":
                with Session() as session:
                    rate_limit(session, settings, "ip:" + (request.client.host if request.client else "unknown"), count=180)
            if request.method not in {"GET", "HEAD", "OPTIONS"}:
                origin = request.headers.get("origin")
                csrf = request.headers.get("x-csrf-token", "")
                cookie = request.cookies.get("ht_csrf", "")
                if origin and origin not in settings.origins:
                    raise HTTPException(403, "ORIGIN_NOT_ALLOWED")
                if not csrf or not cookie or not hmac.compare_digest(csrf, cookie):
                    raise HTTPException(403, "CSRF_REJECTED")
                photo_upload = request.url.path.startswith("/v1/me/contributions/") and request.url.path.endswith("/photos")
                if photo_upload:
                    with Session() as session:
                        require_user(request, session, verified=True)
                maximum = 7_100_000 if photo_upload else 64_000
                body = bytearray()
                async for chunk in request.stream():
                    if len(body) + len(chunk) > maximum:
                        raise HTTPException(413, "REQUEST_TOO_LARGE")
                    body.extend(chunk)
                request._body = bytes(body)
            response = await call_next(request)
        except HTTPException as exc:
            response = failure(request, exc.status_code, str(exc.detail), headers=exc.headers)
        except Exception:
            # No exception payload, URL query, credentials or GPS enters the operational log.
            logging.getLogger("haititracking").error("request_failed request_id=%s", request.state.request_id)
            response = failure(request, 500, "INTERNAL_ERROR")
        response.headers.update({"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer", "X-Frame-Options": "DENY", "X-Request-ID": request.state.request_id, "Permissions-Policy": "geolocation=(self), camera=(), microphone=()", "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"})
        if request.url.path in {"/docs", "/redoc"}:
            response.headers["Content-Security-Policy"] = "default-src 'none'; script-src https://cdn.jsdelivr.net 'unsafe-inline'; style-src https://cdn.jsdelivr.net 'unsafe-inline'; img-src data: https://fastapi.tiangolo.com; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"
        if settings.production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        if response.status_code in {401, 403, 429}:
            route = getattr(request.scope.get("route"), "path", "unmatched")
            logging.getLogger("haititracking.security").warning("security_rejection status=%s route=%s request_id=%s", response.status_code, route, request.state.request_id)
        return response

    @app.exception_handler(StarletteHTTPException)
    async def handle_http(request, exc):
        code = str(exc.detail)
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", code):
            code = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}.get(exc.status_code, "REQUEST_REJECTED")
        return failure(request, exc.status_code, code, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request, exc):
        return failure(request, 422, "VALIDATION_ERROR", {"fields": [{"field": ".".join(map(str, error["loc"])), "message": error["msg"]} for error in exc.errors()]})

    def db():
        with Session() as session:
            try:
                yield session
            except Exception:
                session.rollback()
                raise

    def client_key(request):
        return request.client.host if request.client else "unknown"

    def user_json(user):
        return {"id": user.id, "display_name": user.display_name, "email": user.email, "profile": user.profile, "role": user.role, "email_verified": user.email_verified, "mfa_enabled": bool(user.mfa_secret), "created_at": utc_iso(user.created_at)}

    def own_contribution(request, session, identifier):
        user = require_user(request, session)
        item = session.get(Contribution, identifier)
        if not item or item.author_user_id != user.id:
            raise HTTPException(404, "CONTRIBUTION_NOT_FOUND")
        return user, item

    def contribution_json(item):
        return {"id": item.id, "contribution_id": item.id, "status": item.status, "version": item.version, "payload": item.payload, "review_reason": item.review_reason, "published_code": item.published_code, "created_at": utc_iso(item.created_at), "eligible_for_automatic_payment": False}

    def find_location(session, code):
        location = session.scalar(select(Location).where(Location.public_code == code, *public_filter()))
        if not location:
            redirect = session.get(CodeRedirect, code)
            location = session.scalar(select(Location).where(Location.id == redirect.location_id, *public_filter())) if redirect else None
        if not location:
            raise HTTPException(404, "LOCATION_NOT_FOUND")
        return location

    def own_app(request, session, identifier):
        user = require_user(request, session, verified=True)
        item = session.get(DeveloperApp, identifier)
        if not item or item.owner_id != user.id:
            raise HTTPException(404, "APP_NOT_FOUND")
        return user, item

    def app_json(item, session):
        return {"id": item.id, "name": item.name, "environment": item.environment, "daily_quota": item.daily_quota, "status": item.status, "keys": [{"id": key.id, "prefix": key.prefix, "revoked": key.revoked, "expires_at": utc_iso(key.expires_at)} for key in session.scalars(select(ApiKey).where(ApiKey.app_id == item.id))]}

    @app.get("/v1/health")
    def health(request: Request):
        return envelope(request, {"status": "ok", "environment": settings.env, "cash_rewards_enabled": False, "private_sharing_enabled": False})

    @app.get("/v1/auth/csrf")
    def csrf(request: Request, response: Response):
        token = secrets.token_urlsafe(32)
        response.set_cookie("ht_csrf", token, httponly=True, secure=settings.production, samesite="lax", max_age=3600, path="/")
        return envelope(request, {"csrf_token": token})

    @app.post("/v1/auth/register", status_code=202)
    def register(payload: S.Register, request: Request, background_tasks: BackgroundTasks, session=Depends(db)):
        rate_limit(session, settings, "register:" + client_key(request), 5, 3600)
        email = str(payload.email).lower()
        stored = passwords.hash(payload.password)
        if not session.scalar(select(User.id).where(User.email == email)):
            user = User(email=email, display_name=payload.display_name, password_hash=stored, profile=payload.profile, phone_encrypted=settings.cipher.encrypt(payload.phone.encode()).decode() if payload.phone else None)
            session.add(user)
            try:
                session.flush()
                issue_email(session, settings, user, "verify")
                audit(session, user, "account.created", user.id)
                session.commit()
            except IntegrityError:
                session.rollback()
            except HTTPException:
                session.rollback()
                logging.getLogger("haititracking").warning("registration_delivery_deferred request_id=%s", request.state.request_id)
        background_tasks.add_task(deliver_mail, settings, Session)
        return envelope(request, {"message": "If this address can be registered, a verification email will arrive shortly.", "email_verification_required": True, "email_delivery": "provider" if settings.resend_key else "local_outbox"})

    @app.post("/v1/auth/login")
    def login(payload: S.Login, request: Request, response: Response, session=Depends(db)):
        email = str(payload.email).lower()
        rate_limit(session, settings, "login-ip:" + client_key(request), 10, 900)
        rate_limit(session, settings, "login-account:" + email, 10, 900)
        user = session.scalar(select(User).where(User.email == email))
        valid = verify_password(payload.password, user.password_hash if user else DUMMY_PASSWORD_HASH)
        if not user or not valid or not user.active:
            audit(session, None, "auth.login_failed", "anonymous")
            session.commit()
            raise HTTPException(401, "INVALID_CREDENTIALS")
        mfa = False
        if user.role in {"admin", "moderator"}:
            if not user.mfa_secret or not payload.otp:
                raise HTTPException(403, "MFA_REQUIRED")
            secret = settings.cipher.decrypt(user.mfa_secret.encode()).decode()
            if not pyotp.TOTP(secret).verify(payload.otp, valid_window=1):
                raise HTTPException(401, "INVALID_CREDENTIALS")
            mfa = True
        raw = secrets.token_urlsafe(40)
        expires = timedelta(minutes=30) if mfa else timedelta(hours=8)
        session.add(UserSession(user_id=user.id, token_hash=settings.digest(raw), expires_at=now()+expires, mfa_verified=mfa))
        audit(session, user, "auth.login", user.id)
        session.commit()
        response.set_cookie("ht_session", raw, httponly=True, secure=settings.production, samesite="lax", max_age=int(expires.total_seconds()), path="/")
        return envelope(request, user_json(user))

    @app.post("/v1/auth/logout")
    def logout(request: Request, response: Response, session=Depends(db)):
        token = request.cookies.get("ht_session", "")
        session.execute(delete(UserSession).where(UserSession.token_hash == settings.digest(token)))
        session.commit()
        response.delete_cookie("ht_session", path="/", secure=settings.production, httponly=True, samesite="lax")
        return envelope(request, {"message": "Signed out"})

    @app.get("/v1/auth/me")
    @app.get("/v1/me")
    def me(request: Request, session=Depends(db)):
        return envelope(request, user_json(require_user(request, session)))

    @app.post("/v1/auth/verify-email")
    def verify_email(payload: S.TokenRequest, request: Request, session=Depends(db)):
        result = session.execute(update(AuthToken).where(AuthToken.token_hash == settings.digest(payload.token), AuthToken.purpose == "verify", AuthToken.used == False, AuthToken.expires_at > now()).values(used=True).returning(AuthToken.user_id)).scalar_one_or_none()
        if not result:
            raise HTTPException(400, "TOKEN_INVALID_OR_EXPIRED")
        user = session.get(User, result)
        user.email_verified = True
        audit(session, user, "auth.email_verified", user.id)
        session.commit()
        return envelope(request, {"message": "Email verified"})

    @app.post("/v1/auth/resend-verification", status_code=202)
    def resend_verification(payload: S.EmailRequest, request: Request, background_tasks: BackgroundTasks, session=Depends(db)):
        rate_limit(session, settings, "verification:" + client_key(request), 3, 3600)
        user = session.scalar(select(User).where(User.email == str(payload.email).lower(), User.active == True))
        if user and not user.email_verified:
            try:
                issue_email(session, settings, user, "verify")
                session.commit()
            except HTTPException:
                session.rollback()
                logging.getLogger("haititracking").warning("verification_delivery_deferred request_id=%s", request.state.request_id)
        background_tasks.add_task(deliver_mail, settings, Session)
        return envelope(request, {"message": "If the account needs verification, an email will arrive shortly."})

    @app.post("/v1/auth/forgot-password", status_code=202)
    def forgot_password(payload: S.EmailRequest, request: Request, background_tasks: BackgroundTasks, session=Depends(db)):
        rate_limit(session, settings, "reset:" + client_key(request), 3, 3600)
        user = session.scalar(select(User).where(User.email == str(payload.email).lower(), User.active == True))
        if user:
            try:
                issue_email(session, settings, user, "reset")
                session.commit()
            except HTTPException:
                session.rollback()
                logging.getLogger("haititracking").warning("recovery_delivery_deferred request_id=%s", request.state.request_id)
        background_tasks.add_task(deliver_mail, settings, Session)
        return envelope(request, {"message": "If the account exists, a recovery email will arrive shortly."})

    @app.post("/v1/auth/reset-password")
    def reset_password(payload: S.ResetPassword, request: Request, session=Depends(db)):
        identifier = session.execute(update(AuthToken).where(AuthToken.token_hash == settings.digest(payload.token), AuthToken.purpose == "reset", AuthToken.used == False, AuthToken.expires_at > now()).values(used=True).returning(AuthToken.user_id)).scalar_one_or_none()
        if not identifier:
            raise HTTPException(400, "TOKEN_INVALID_OR_EXPIRED")
        user = session.get(User, identifier)
        user.password_hash = passwords.hash(payload.password)
        session.execute(delete(UserSession).where(UserSession.user_id == user.id))
        audit(session, user, "auth.password_reset", user.id)
        session.commit()
        return envelope(request, {"message": "Password changed. Sign in again."})

    @app.patch("/v1/me")
    def profile(payload: S.ProfileInput, request: Request, session=Depends(db)):
        user = require_user(request, session)
        user.display_name = payload.display_name
        session.commit()
        return envelope(request, user_json(user))

    @app.get("/v1/me/sessions")
    def sessions(request: Request, session=Depends(db)):
        user = require_user(request, session)
        return envelope(request, [{"id": row.id, "created_at": utc_iso(row.created_at), "expires_at": utc_iso(row.expires_at), "current": row.token_hash == settings.digest(request.cookies.get("ht_session", ""))} for row in session.scalars(select(UserSession).where(UserSession.user_id == user.id, UserSession.expires_at > now()))])

    @app.post("/v1/me/sessions/{identifier}/revoke")
    def revoke_session(identifier: str, request: Request, session=Depends(db)):
        user = require_user(request, session)
        row = session.get(UserSession, identifier)
        if not row or row.user_id != user.id:
            raise HTTPException(404, "SESSION_NOT_FOUND")
        session.delete(row)
        audit(session, user, "auth.session_revoked", identifier)
        session.commit()
        return envelope(request, {"revoked": True})

    @app.get("/v1/me/export")
    def export(request: Request, session=Depends(db)):
        user = require_user(request, session)
        return envelope(request, {"profile": user_json(user), "contributions": [contribution_json(c) for c in session.scalars(select(Contribution).where(Contribution.author_user_id == user.id))], "consent_version": user.consent_version})

    @app.post("/v1/me/deletion-request", status_code=202)
    def deletion_request(request: Request, session=Depends(db)):
        user = require_user(request, session)
        audit(session, user, "privacy.deletion_requested", user.id)
        session.commit()
        return envelope(request, {"message": "Request received for controlled review; no records have been silently deleted."})

    @app.get("/v1/public/stats")
    def stats(request: Request, session=Depends(db)):
        count = session.scalar(select(func.count()).select_from(Location).where(*public_filter(), ~Location.description.startswith("Fiche de démonstration fictive")))
        contributors = session.scalar(select(func.count(func.distinct(Contribution.author_user_id))).join(User, User.id == Contribution.author_user_id).where(User.email_verified == True, User.active == True, Contribution.status != "draft"))
        calls = session.scalar(select(func.coalesce(func.sum(ApiUsage.count), 0)))
        return envelope(request, {"locations": count, "verified_locations": count, "contributors": contributors, "api_requests": calls, "pilot": True})

    def territory_json(row):
        return {"id": row.id, "parent_id": row.parent_id, "name": row.name, "level": row.level, "aliases": row.aliases, "country_code": row.country_code, "source_version": row.source_version, "source_url": row.source_url, "license": row.license}

    @app.get("/v1/territories", response_model=S.TerritoryListResponse)
    def territories(request: Request, parent_id: str | None = Query(default=None, max_length=40), q: str = Query(default="", max_length=100), level: str | None = Query(default=None, pattern="^(country|department|commune|section)$"), limit: int = Query(default=50, ge=1, le=50), cursor: str | None = Query(default=None, max_length=1000), session=Depends(db)):
        public_api_access(request, session)
        stmt = select(Territory).where(Territory.active == True)
        if parent_id:
            stmt = stmt.where(Territory.parent_id == parent_id)
        if level:
            stmt = stmt.where(Territory.level == level)
        if q:
            stmt = stmt.where(func.lower(Territory.name).contains(q.lower(), autoescape=True))
        filters = settings.digest(json.dumps([parent_id, q, level, limit]))
        offset = cursor_offset(cursor, filters)
        rows = session.scalars(stmt.order_by(Territory.name, Territory.id).offset(offset).limit(limit+1)).all()
        return envelope(request, [territory_json(row) for row in rows[:limit]], pagination={"limit": limit, "next_cursor": cursor_value(offset+limit, filters) if len(rows)>limit else None})

    @app.get("/v1/territories/{identifier}", response_model=S.TerritoryResponse)
    def territory_detail(identifier: str, request: Request, session=Depends(db)):
        public_api_access(request, session)
        row = session.get(Territory, identifier)
        if not row or not row.active:
            raise HTTPException(404, "TERRITORY_NOT_FOUND")
        return envelope(request, territory_json(row))

    @app.get("/v1/territories/{identifier}/children")
    def territory_children(identifier: str, request: Request, session=Depends(db)):
        return territories(request, parent_id=identifier, q="", level=None, limit=50, cursor=None, session=session)

    def cursor_value(offset, filters):
        body = base64.urlsafe_b64encode(json.dumps({"offset": offset, "filter": filters}, separators=(",", ":")).encode()).decode().rstrip("=")
        return body + "." + settings.digest(body)

    def cursor_offset(cursor, filters):
        if not cursor:
            return 0
        try:
            body, signature = cursor.split(".")
            if not hmac.compare_digest(signature, settings.digest(body)):
                raise ValueError()
            parsed = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
            if parsed["filter"] != filters or not isinstance(parsed["offset"], int) or not 0 <= parsed["offset"] <= 100000:
                raise ValueError()
            return parsed["offset"]
        except (ValueError, KeyError, TypeError):
            raise HTTPException(400, "INVALID_CURSOR")

    @app.get("/v1/locations/search", response_model=S.LocationListResponse, response_model_exclude_unset=True)
    def search(request: Request, q: str = Query(default="", max_length=160), type: S.PlaceType | None = None, territory_id: str | None = Query(default=None, max_length=40), limit: int = Query(default=20, ge=1, le=50), cursor: str | None = Query(default=None, max_length=1000), session=Depends(db)):
        public_api_access(request, session)
        filters = settings.digest(json.dumps([q, type, territory_id, limit]))
        offset = cursor_offset(cursor, filters)
        stmt = select(Location).where(*public_filter())
        if q:
            escaped = normalize(q).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            stmt = stmt.where(or_(Location.normalized_name.like("%"+escaped+"%", escape="\\"), Location.normalized_aliases.like("%"+escaped+"%", escape="\\"), Location.public_code == q.upper(), func.lower(Location.address["reference"].as_string()).contains(q.lower(), autoescape=True), func.lower(Location.address["neighborhood"].as_string()).contains(q.lower(), autoescape=True)))
        if type:
            stmt = stmt.where(Location.type == type)
        if territory_id:
            children = select(Territory.id).where(Territory.id == territory_id).cte(recursive=True)
            children = children.union_all(select(Territory.id).where(Territory.parent_id == children.c.id))
            stmt = stmt.where(Location.territory_id.in_(select(children.c.id)))
        rows = session.scalars(stmt.order_by(Location.normalized_name, Location.id).offset(offset).limit(limit+1)).all()
        return envelope(request, [public_location(row, session) for row in rows[:limit]], pagination={"limit": limit, "next_cursor": cursor_value(offset+limit, filters) if len(rows) > limit else None})

    @app.get("/v1/locations/nearby", response_model=S.LocationListResponse, response_model_exclude_unset=True)
    def nearby(request: Request, lat: float = Query(ge=-90, le=90, allow_inf_nan=False), lon: float = Query(ge=-180, le=180, allow_inf_nan=False), radius_m: int = Query(default=500, ge=1, le=5000), limit: int = Query(default=20, ge=1, le=50), session=Depends(db)):
        public_api_access(request, session, required=True)
        point = {"latitude": lat, "longitude": lon}
        if engine.dialect.name == "postgresql":
            ids = session.execute(text("SELECT id, ST_Distance(point,ST_SetSRID(ST_MakePoint(:lon,:lat),4326)::geography) AS distance_m FROM locations WHERE status='active' AND public_visibility='public' AND type IN ('business','public','landmark','road','access') AND ST_DWithin(point,ST_SetSRID(ST_MakePoint(:lon,:lat),4326)::geography,:radius) ORDER BY distance_m,id LIMIT :limit"), {"lat": lat, "lon": lon, "radius": radius_m, "limit": limit}).all()
            result = [{**public_location(session.get(Location, row.id), session), "distance_m": round(row.distance_m, 1)} for row in ids]
        else:
            rows = session.scalars(select(Location).where(*public_filter(), Location.latitude.between(lat-.06, lat+.06), Location.longitude.between(lon-.06, lon+.06)).limit(1000))
            result = [{**public_location(row, session), "distance_m": round(distance(point, {"latitude": row.latitude, "longitude": row.longitude}), 1)} for row in rows]
            result = sorted([row for row in result if row["distance_m"] <= radius_m], key=lambda row: (row["distance_m"], row["code"]))[:limit]
        return envelope(request, result, pagination={"limit": limit, "next_cursor": None})

    @app.get("/v1/geocode")
    def geocode(request: Request, q: str = Query(min_length=2, max_length=160), commune_id: str | None = Query(default=None, max_length=40), session=Depends(db)):
        public_api_access(request, session, required=True)
        query = select(Location).where(*public_filter(), or_(Location.normalized_name.contains(normalize(q), autoescape=True), Location.normalized_aliases.contains(normalize(q), autoescape=True)))
        if commune_id:
            commune = session.get(Territory, commune_id)
            if not commune or not commune.active or commune.level != "commune":
                raise HTTPException(422, "TERRITORY_NOT_FOUND")
            sections = select(Territory.id).where(Territory.parent_id == commune_id)
            query = query.where(or_(Location.territory_id == commune_id, Location.territory_id.in_(sections)))
        rows = session.scalars(query.order_by(Location.normalized_name).limit(20))
        return envelope(request, [{**public_location(row, session), "match_type": "text_candidate"} for row in rows])

    @app.get("/v1/reverse")
    def reverse(request: Request, lat: float = Query(ge=-90, le=90, allow_inf_nan=False), lon: float = Query(ge=-180, le=180, allow_inf_nan=False), session=Depends(db)):
        result = nearby(request, lat, lon, 5000, 10, session)
        result["data"] = {"administrative_area": administrative_area(session, lat, lon), "territory_boundary_available": engine.dialect.name == "postgresql", "public_places": result["data"]}
        return result

    @app.get("/v1/locations/{code}", response_model=S.LocationResponse, response_model_exclude_unset=True)
    def location(code: str, request: Request, session=Depends(db)):
        public_api_access(request, session)
        row = find_location(session, code)
        return envelope(request, {**public_location(row, session), "requested_code": code, "canonical_code": row.public_code, "was_redirected": code != row.public_code})

    @app.post("/v1/locations/{code}/reports", status_code=202)
    def report(code: str, payload: S.Report, request: Request, session=Depends(db)):
        rate_limit(session, settings, "reports:" + client_key(request), 5, 3600)
        row = find_location(session, code)
        report = LocationReport(location_id=row.id, category=payload.category, description=payload.description)
        session.add(report)
        session.flush()
        audit(session, None, "location.report_received", report.id, {"category": payload.category})
        session.commit()
        return envelope(request, {"report_id": report.id, "status": "open"})

    @app.get("/v1/locations/{code}/qr", response_class=Response, responses={200: {"content": {"image/png": {}}}})
    def location_qr(code: str, request: Request, session=Depends(db)):
        import qrcode
        public_api_access(request, session)
        row = find_location(session, code)
        url = settings.web_base_url + "/ubicaciones/" + quote(row.public_code, safe="")
        output = io.BytesIO()
        qrcode.make(url).save(output, format="PNG")
        return Response(output.getvalue(), media_type="image/png", headers={"Content-Disposition": "inline; filename=haiti-location-qr.png"})

    @app.post("/v1/public-suggestions", status_code=202)
    def suggestion(payload: S.Suggestion, request: Request, session=Depends(db)):
        rate_limit(session, settings, "suggestions:" + client_key(request), 3, 3600)
        if not session.get(Territory, payload.territory_id):
            raise HTTPException(422, "TERRITORY_NOT_FOUND")
        row = PublicSuggestion(payload=payload.model_dump(exclude={"website"}))
        session.add(row)
        session.commit()
        return envelope(request, {"suggestion_id": row.id, "status": "unverified", "eligible_for_automatic_payment": False})

    @app.post("/v1/contributions/check-duplicates", response_model=S.DuplicateEnvelope)
    def check_duplicates(payload: S.DuplicateRequest, request: Request, session=Depends(db)):
        require_user(request, session, verified=True)
        matches = duplicates(session, payload.model_dump())
        return envelope(request, {"decision": "manual_review_recommended" if matches else "no_match", "candidates": matches})

    def location_links(data, session, target_id=None):
        links = {}
        for field in ("parent_location", "access_point"):
            code = data.get(field + "_code")
            linked = find_location(session, code) if code else None
            if linked and (linked.id == target_id or field == "access_point" and linked.type != "access"):
                raise HTTPException(422, "INVALID_LOCATION_RELATION")
            links[field + "_id"] = linked.id if linked else None
        current = links["parent_location_id"]
        seen = set()
        while current:
            if current == target_id or current in seen:
                raise HTTPException(422, "LOCATION_PARENT_CYCLE")
            seen.add(current)
            current = session.get(Location, current).parent_location_id
        if target_id and data["type"] != "access" and session.scalar(select(Location.id).where(Location.access_point_id == target_id).limit(1)):
            raise HTTPException(422, "ACCESS_POINT_IN_USE")
        return links

    def contribution_status(data):
        return "draft" if data["mode"] == "draft" else "needs_review" if data.get("quality_flags") or data["mode"] == "remote" else "submitted"

    def validate_contribution(payload, session, target_id=None):
        data = payload.model_dump(mode="json", exclude={"version"})
        if payload.gps_observation:
            data["gps_received_at"] = utc_iso(now())
        location_links(data, session, target_id)
        territory = session.get(Territory, payload.territory_id)
        if not territory or not territory.active or territory.level not in {"commune", "section"}:
            raise HTTPException(422, "TERRITORY_NOT_FOUND")
        if not (17.9 <= payload.selected_point.latitude <= 20.2 and -74.6 <= payload.selected_point.longitude <= -71.5):
            raise HTTPException(422, "POINT_OUTSIDE_HAITI")
        if payload.mode != "draft" and not payload.source_declaration_accepted:
            raise HTTPException(422, "SOURCE_DECLARATION_REQUIRED")
        if payload.mode == "on_site":
            gps = payload.gps_observation
            if not gps:
                raise HTTPException(422, "GPS_REQUIRED_FOR_ON_SITE")
            if not gps.captured_at.tzinfo or not -60 <= (now()-gps.captured_at).total_seconds() <= 300:
                raise HTTPException(422, "GPS_OBSERVATION_EXPIRED")
            meters = distance(payload.selected_point.model_dump(), gps.model_dump())
            if meters > min(1000, max(100, gps.accuracy_m*2)):
                raise HTTPException(422, "PIN_TOO_FAR_FROM_GPS")
            if meters > 50 and len(payload.pin_adjustment_reason) < 10:
                raise HTTPException(422, "PIN_ADJUSTMENT_REASON_REQUIRED")
            data["pin_distance_m"] = round(meters, 1)
            data["quality_flags"] = ["low_gps_accuracy"] if gps.accuracy_m > 100 else ["gps_accuracy_review"] if gps.accuracy_m > 30 else []
            if meters > 50:
                data["quality_flags"].append("pin_adjustment_review")
        if payload.mode != "draft":
            if engine.dialect.name == "postgresql":
                from .catalog import boundary_for
                boundary = boundary_for(territory.id)
                if boundary:
                    covered = session.execute(text("SELECT ST_Covers(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:shape),4326)),ST_SetSRID(ST_MakePoint(:lon,:lat),4326))"), {"shape": json.dumps(boundary), "lon": payload.selected_point.longitude, "lat": payload.selected_point.latitude}).scalar_one()
                    if not covered:
                        data.setdefault("quality_flags", []).append("territory_boundary_mismatch")
            matches = duplicates(session, data)
            resolution = payload.duplicate_resolution
            if matches and not (resolution and resolution.choice in {"distinct_place", "update_existing"} and len(resolution.justification) >= 10):
                raise HTTPException(409, "DUPLICATE_REVIEW_REQUIRED")
            data["duplicate_candidates"] = matches
        return data

    @app.post("/v1/contributions", status_code=201, response_model=S.ContributionEnvelope)
    def create_contribution(payload: S.ContributionInput, request: Request, session=Depends(db)):
        user = require_user(request, session, verified=payload.mode != "draft")
        rate_limit(session, settings, "contribute:"+user.id, 30, 3600)
        raw_key = request.headers.get("idempotency-key", "")
        if not 8 <= len(raw_key) <= 100:
            raise HTTPException(400, "IDEMPOTENCY_KEY_REQUIRED")
        identifier = settings.digest(user.id+":"+raw_key)
        payload_hash = settings.digest(payload.model_dump_json())
        prior = session.get(Idempotency, identifier)
        if prior:
            if prior.payload_hash != payload_hash:
                raise HTTPException(409, "IDEMPOTENCY_CONFLICT")
            return envelope(request, contribution_json(session.get(Contribution, prior.contribution_id)))
        target = find_location(session, payload.target_location_code) if payload.target_location_code else None
        data = validate_contribution(payload, session, target.id if target else None)
        row = Contribution(author_user_id=user.id, target_location_id=target.id if target else None, payload=data, status=contribution_status(data))
        session.add(row)
        session.flush()
        session.add(Idempotency(key=identifier, owner_id=user.id, payload_hash=payload_hash, contribution_id=row.id))
        audit(session, user, "contribution.created", row.id, {"mode": payload.mode})
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            prior = session.get(Idempotency, identifier)
            if not prior or prior.payload_hash != payload_hash:
                raise HTTPException(409, "IDEMPOTENCY_CONFLICT")
            row = session.get(Contribution, prior.contribution_id)
        return envelope(request, contribution_json(row))

    @app.get("/v1/me/contributions", response_model=S.ContributionListEnvelope)
    def my_contributions(request: Request, limit: int = Query(default=20, ge=1, le=50), offset: int = Query(default=0, ge=0, le=100000), session=Depends(db)):
        user = require_user(request, session)
        rows = session.scalars(select(Contribution).where(Contribution.author_user_id == user.id).order_by(Contribution.created_at.desc()).offset(offset).limit(limit))
        return envelope(request, [contribution_json(row) for row in rows])

    @app.get("/v1/me/contributions/{identifier}", response_model=S.ContributionEnvelope)
    def my_contribution(identifier: str, request: Request, session=Depends(db)):
        _, row = own_contribution(request, session, identifier)
        return envelope(request, contribution_json(row))

    @app.patch("/v1/me/contributions/{identifier}", response_model=S.ContributionEnvelope)
    def edit_contribution(identifier: str, payload: S.ContributionInput, request: Request, session=Depends(db)):
        user, row = own_contribution(request, session, identifier)
        if row.status not in {"draft", "changes_requested"}:
            raise HTTPException(409, "CONTRIBUTION_NOT_EDITABLE")
        if payload.version != row.version:
            raise HTTPException(409, "VERSION_CONFLICT")
        if payload.mode != "draft" and not user.email_verified:
            raise HTTPException(403, "EMAIL_VERIFICATION_REQUIRED")
        target = find_location(session, payload.target_location_code) if payload.target_location_code else None
        if target and target.id != row.target_location_id:
            raise HTTPException(422, "TARGET_LOCATION_IMMUTABLE")
        data = validate_contribution(payload, session, row.target_location_id)
        data["target_location_code"] = session.get(Location, row.target_location_id).public_code if row.target_location_id else None
        affected = session.execute(update(Contribution).where(Contribution.id == row.id, Contribution.version == payload.version, Contribution.status.in_(["draft", "changes_requested"])).values(payload=data, version=payload.version+1, status=contribution_status(data), updated_at=now())).rowcount
        if not affected:
            raise HTTPException(409, "VERSION_CONFLICT")
        audit(session, user, "contribution.updated", row.id)
        session.commit()
        session.refresh(row)
        return envelope(request, contribution_json(row))

    @app.post("/v1/me/contributions/{identifier}/withdraw", response_model=S.ContributionEnvelope)
    def withdraw_contribution(identifier: str, payload: S.ContributionVersion, request: Request, session=Depends(db)):
        user, row = own_contribution(request, session, identifier)
        affected = session.execute(update(Contribution).where(Contribution.id == row.id, Contribution.version == payload.version, Contribution.status.in_(["draft", "submitted", "needs_review", "changes_requested"])).values(status="withdrawn", version=payload.version+1, updated_at=now())).rowcount
        if not affected:
            raise HTTPException(409, "VERSION_CONFLICT_OR_DECIDED")
        audit(session, user, "contribution.withdrawn", row.id)
        session.commit()
        session.refresh(row)
        return envelope(request, contribution_json(row))

    @app.get("/v1/developer/apps")
    def apps(request: Request, session=Depends(db)):
        user = require_user(request, session, verified=True)
        return envelope(request, [app_json(row, session) for row in session.scalars(select(DeveloperApp).where(DeveloperApp.owner_id == user.id).order_by(DeveloperApp.created_at).limit(20))])

    @app.post("/v1/developer/apps", status_code=201)
    def create_developer_app(payload: S.AppInput, request: Request, session=Depends(db)):
        user = require_user(request, session, verified=True)
        if session.scalar(select(func.count()).select_from(DeveloperApp).where(DeveloperApp.owner_id == user.id)) >= 10:
            raise HTTPException(409, "APP_LIMIT_REACHED")
        row = DeveloperApp(owner_id=user.id, name=payload.name, environment=payload.environment)
        session.add(row)
        session.flush()
        audit(session, user, "developer.app_created", row.id)
        session.commit()
        return envelope(request, app_json(row, session))

    @app.post("/v1/developer/apps/{identifier}/keys", status_code=201)
    def create_key(identifier: str, payload: S.NewKey, request: Request, session=Depends(db)):
        user, developer_app = own_app(request, session, identifier)
        rate_limit(session, settings, "key-create:"+user.id, 10, 900)
        if not verify_password(payload.password, user.password_hash):
            raise HTTPException(401, "INVALID_CREDENTIALS")
        if session.scalar(select(func.count()).select_from(ApiKey).where(ApiKey.app_id == identifier, ApiKey.revoked == False)) >= 5:
            raise HTTPException(409, "KEY_LIMIT_REACHED")
        raw = "ht_"+developer_app.environment+"_"+secrets.token_urlsafe(32)
        row = ApiKey(app_id=identifier, prefix=raw[:16], secret_hash=settings.digest(raw), expires_at=now()+timedelta(days=90))
        session.add(row)
        session.flush()
        audit(session, user, "developer.key_created", row.id)
        session.commit()
        return envelope(request, {"id": row.id, "secret": raw, "prefix": row.prefix, "expires_at": utc_iso(row.expires_at), "message": "Save this server-side secret now. It cannot be retrieved again."})

    @app.post("/v1/developer/apps/{identifier}/keys/{key_id}/revoke")
    def revoke_key(identifier: str, key_id: str, request: Request, session=Depends(db)):
        user, _ = own_app(request, session, identifier)
        row = session.get(ApiKey, key_id)
        if not row or row.app_id != identifier:
            raise HTTPException(404, "KEY_NOT_FOUND")
        row.revoked = True
        audit(session, user, "developer.key_revoked", row.id)
        session.commit()
        return envelope(request, {"revoked": True})

    @app.get("/v1/developer/apps/{identifier}/usage")
    def usage(identifier: str, request: Request, session=Depends(db)):
        _, row = own_app(request, session, identifier)
        return envelope(request, {"daily_quota": row.daily_quota, "days": [{"day": record.day, "count": record.count} for record in session.scalars(select(ApiUsage).where(ApiUsage.app_id == identifier).order_by(ApiUsage.day.desc()).limit(30))]})

    @app.get("/v1/admin/summary")
    def admin_summary(request: Request, session=Depends(db)):
        require_user(request, session, verified=True, staff=True)
        counts = dict(session.execute(select(Contribution.status, func.count()).group_by(Contribution.status)).all())
        coverage = session.execute(select(Territory.id, Territory.name, func.count(Location.id).label("published_count")).join(Location, Location.territory_id == Territory.id).where(*public_filter()).group_by(Territory.id, Territory.name).order_by(Territory.name)).all()
        return envelope(request, {"contributions": counts, "open_reports": session.scalar(select(func.count()).select_from(LocationReport).where(LocationReport.status == "open")), "pending_suggestions": session.scalar(select(func.count()).select_from(PublicSuggestion).where(PublicSuggestion.status == "unverified")), "public_locations": session.scalar(select(func.count()).select_from(Location).where(*public_filter())), "territory_counts": [{"id": row.id, "name": row.name, "count": row.published_count} for row in coverage], "cash_rewards_enabled": False})

    @app.get("/v1/admin/contributions")
    def admin_contributions(request: Request, status: str | None = Query(default=None, max_length=30), limit: int = Query(default=20, ge=1, le=50), offset: int = Query(default=0, ge=0, le=100000), session=Depends(db)):
        require_user(request, session, verified=True, staff=True)
        stmt = select(Contribution).where(Contribution.status != "draft")
        if status:
            stmt = stmt.where(Contribution.status == status)
        return envelope(request, [contribution_json(row) for row in session.scalars(stmt.order_by(Contribution.created_at).offset(offset).limit(limit))])

    @app.post("/v1/admin/contributions/{identifier}/decision")
    def decide(identifier: str, payload: S.Decision, request: Request, session=Depends(db)):
        actor = require_user(request, session, verified=True, staff=True)
        row = session.scalar(select(Contribution).where(Contribution.id == identifier).with_for_update())
        if not row or row.status == "draft":
            raise HTTPException(404, "CONTRIBUTION_NOT_FOUND")
        if row.author_user_id == actor.id:
            raise HTTPException(403, "SELF_REVIEW_FORBIDDEN")
        if row.version != payload.version:
            raise HTTPException(409, "VERSION_CONFLICT")
        if row.status not in {"submitted", "needs_review"}:
            raise HTTPException(409, "INVALID_STATE_TRANSITION")
        data = row.payload
        if payload.decision == "approve":
            if data["type"] not in {"public", "business", "landmark", "road", "access"}:
                raise HTTPException(422, "PRIVATE_PUBLICATION_FORBIDDEN")
            if engine.dialect.name == "postgresql":
                # Serialize publication in the small pilot to recheck concurrent proposals consistently.
                session.execute(text("SELECT pg_advisory_xact_lock(684172031)"))
            links = location_links(data, session, row.target_location_id)
            if data.get("gps_retention_expired") or (data.get("gps_observation") or {}).get("accuracy_m", 0) > 100 or data["mode"] == "remote":
                if len(payload.corroboration) < 20:
                    raise HTTPException(422, "INDEPENDENT_CORROBORATION_REQUIRED")
            matches = duplicates(session, data, exclude_id=row.target_location_id)
            if matches and not ((data.get("duplicate_resolution") or {}).get("choice") == "distinct_place" and len((data.get("duplicate_resolution") or {}).get("justification", "")) >= 10):
                raise HTTPException(409, "DUPLICATE_REVIEW_REQUIRED")
            if row.target_location_id:
                location_row = session.scalar(select(Location).where(Location.id == row.target_location_id, *public_filter()).with_for_update())
                if not location_row:
                    raise HTTPException(404, "LOCATION_NOT_FOUND")
                location_row.version += 1
            else:
                number = session.execute(update(CodeCounter).where(CodeCounter.id == 1).values(value=CodeCounter.value+1).returning(CodeCounter.value)).scalar_one()
                location_row = Location(public_code=f"HT-NXV-{number:06d}", version=1)
                session.add(location_row)
            location_row.name, location_row.normalized_name, location_row.type = data["name"], normalize(data["name"]), data["type"]
            location_row.aliases = data.get("aliases", [])
            location_row.normalized_aliases = "\n".join(normalize(alias) for alias in location_row.aliases)
            location_row.parent_location_id, location_row.access_point_id = links["parent_location_id"], links["access_point_id"]
            location_row.territory_id, location_row.latitude, location_row.longitude = data["territory_id"], data["selected_point"]["latitude"], data["selected_point"]["longitude"]
            location_row.address, location_row.description, location_row.last_verified_at = data["address"], data.get("description", ""), now()
            location_row.confidence_score = .65 if data.get("quality_flags") else .8
            session.flush()
            session.add(LocationVersion(location_id=location_row.id, version=location_row.version, snapshot=public_location(location_row, session), actor_id=actor.id, reason=payload.reason))
            row.published_code, row.status = location_row.public_code, "approved"
        elif payload.decision == "merge":
            canonical = find_location(session, payload.canonical_code or "")
            row.published_code, row.status = canonical.public_code, "merged"
        else:
            row.status = "rejected" if payload.decision == "reject" else "changes_requested"
        row.review_reason, row.updated_at, row.version = payload.reason, now(), row.version+1
        session.add(Review(contribution_id=row.id, reviewer_user_id=actor.id, decision=payload.decision, reason=payload.reason + ("\nCorroboration: " + payload.corroboration if payload.corroboration else "")))
        audit(session, actor, "moderation."+payload.decision, row.id)
        session.commit()
        return envelope(request, contribution_json(row))

    @app.post("/v1/admin/locations/{identifier}/merge")
    def merge_locations(identifier: str, payload: S.Merge, request: Request, session=Depends(db)):
        actor = require_user(request, session, verified=True, staff=True)
        if engine.dialect.name == "postgresql":
            # Serialize canonical changes with publication to prevent reciprocal merge cycles.
            session.execute(text("SELECT pg_advisory_xact_lock(684172031)"))
        source = session.scalar(select(Location).where(Location.id == identifier, *public_filter()).with_for_update())
        target = find_location(session, payload.canonical_code)
        if not source or source.id == target.id:
            raise HTTPException(422, "INVALID_MERGE")
        current = target
        while current:
            if current.id == source.id:
                raise HTTPException(422, "LOCATION_PARENT_CYCLE")
            current = session.get(Location, current.parent_location_id) if current.parent_location_id else None
        if target.type != "access" and session.scalar(select(Location.id).where(Location.access_point_id == source.id).limit(1)):
            raise HTTPException(422, "ACCESS_POINT_IN_USE")
        if target.access_point_id == source.id:
            raise HTTPException(422, "INVALID_LOCATION_RELATION")
        merged_aliases = list(dict.fromkeys([*target.aliases, source.name, *source.aliases]))
        if len(merged_aliases) > 10:
            raise HTTPException(409, "ALIAS_LIMIT_REVIEW_REQUIRED")
        dependents = session.scalars(select(Location).where(or_(Location.parent_location_id == source.id, Location.access_point_id == source.id), Location.id != source.id)).all()
        for linked in dependents:
            if linked.parent_location_id == source.id:
                linked.parent_location_id = target.id
            if linked.access_point_id == source.id:
                linked.access_point_id = target.id
            linked.version += 1
        target.aliases = merged_aliases
        target.normalized_aliases = "\n".join(normalize(alias) for alias in target.aliases)
        target.version += 1
        session.flush()
        for changed in [target, *dependents]:
            session.add(LocationVersion(location_id=changed.id, version=changed.version, snapshot=public_location(changed, session), actor_id=actor.id, reason=payload.reason))
        session.execute(update(CodeRedirect).where(CodeRedirect.location_id == source.id).values(location_id=target.id))
        session.add(CodeRedirect(old_code=source.public_code, location_id=target.id))
        source.status = "merged"
        audit(session, actor, "location.merged", source.id, {"canonical_location_id": target.id, "reason": payload.reason})
        session.commit()
        return envelope(request, {"old_code": source.public_code, "canonical_code": target.public_code})

    @app.get("/v1/admin/audit")
    def audit_events(request: Request, limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0, le=100000), actor_id: str | None = Query(default=None, max_length=36), subject_id: str | None = Query(default=None, max_length=200), action: str | None = Query(default=None, max_length=100), session=Depends(db)):
        require_user(request, session, verified=True, admin=True)
        query = select(AuditEvent)
        for column, value in ((AuditEvent.actor_id, actor_id), (AuditEvent.subject_id, subject_id), (AuditEvent.action, action)):
            if value:
                query = query.where(column == value)
        return envelope(request, [{"id": row.id, "action": row.action, "subject_id": row.subject_id, "actor_id": row.actor_id, "metadata": row.metadata_sanitized, "created_at": utc_iso(row.created_at)} for row in session.scalars(query.order_by(AuditEvent.created_at.desc(), AuditEvent.id).offset(offset).limit(limit))])

    @app.get("/v1/admin/reports")
    def admin_reports(request: Request, offset: int = Query(default=0, ge=0, le=100000), session=Depends(db)):
        require_user(request, session, verified=True, staff=True)
        result = []
        for row in session.scalars(select(LocationReport).where(LocationReport.status == "open").order_by((LocationReport.category == "privacy").desc(), LocationReport.created_at).offset(offset).limit(50)):
            location = session.get(Location, row.location_id)
            result.append({"id": row.id, "location_id": row.location_id, "location_code": location.public_code, "location_name": location.name, "category": row.category, "description": row.description, "status": row.status})
        return envelope(request, result)

    @app.get("/v1/admin/suggestions")
    def admin_suggestions(request: Request, offset: int = Query(default=0, ge=0, le=100000), session=Depends(db)):
        require_user(request, session, verified=True, staff=True)
        return envelope(request, [{"id": row.id, "payload": row.payload, "status": row.status, "created_at": utc_iso(row.created_at)} for row in session.scalars(select(PublicSuggestion).where(PublicSuggestion.status == "unverified").order_by(PublicSuggestion.created_at).offset(offset).limit(50))])

    @app.post("/v1/admin/suggestions/{identifier}/decision")
    def review_suggestion(identifier: str, payload: S.SuggestionDecision, request: Request, session=Depends(db)):
        actor = require_user(request, session, verified=True, staff=True)
        row = session.scalar(select(PublicSuggestion).where(PublicSuggestion.id == identifier).with_for_update())
        if not row:
            raise HTTPException(404, "SUGGESTION_NOT_FOUND")
        if row.status != "unverified":
            raise HTTPException(409, "INVALID_STATE_TRANSITION")
        row.status = payload.decision
        audit(session, actor, "suggestion." + payload.decision, row.id, {"reason": payload.reason})
        session.commit()
        return envelope(request, {"id": row.id, "status": row.status, "published": False})

    @app.get("/v1/admin/contributions/{identifier}/photos")
    def review_photos(identifier: str, request: Request, session=Depends(db)):
        actor = require_user(request, session, verified=True, staff=True)
        row = session.get(Contribution, identifier)
        if not row or row.status == "draft":
            raise HTTPException(404, "CONTRIBUTION_NOT_FOUND")
        audit(session, actor, "evidence.list_viewed", row.id)
        session.commit()
        return envelope(request, [{"id": item.id, "moderation_status": item.moderation_status} for item in session.scalars(select(Evidence).where(Evidence.contribution_id == identifier))])

    @app.post("/v1/admin/locations/{identifier}/hide")
    def hide_location(identifier: str, payload: S.Report, request: Request, session=Depends(db)):
        actor = require_user(request, session, verified=True, staff=True)
        row = session.get(Location, identifier)
        if not row:
            raise HTTPException(404, "LOCATION_NOT_FOUND")
        row.public_visibility = "hidden"
        session.execute(update(LocationReport).where(LocationReport.location_id == row.id, LocationReport.status == "open").values(status="hidden"))
        audit(session, actor, "location.hidden", row.id, {"category": payload.category, "reason": payload.description})
        session.commit()
        return envelope(request, {"hidden": True})

    @app.post("/v1/admin/territories", status_code=201)
    def create_territory(payload: S.TerritoryInput, request: Request, session=Depends(db)):
        actor = require_user(request, session, verified=True, admin=True)
        if session.get(Territory, payload.id):
            raise HTTPException(409, "TERRITORY_EXISTS")
        parent = session.get(Territory, payload.parent_id) if payload.parent_id else None
        if payload.parent_id and not parent:
            raise HTTPException(422, "TERRITORY_NOT_FOUND")
        required_parent = {"department": "country", "commune": "department", "section": "commune"}
        if payload.level in required_parent and (not parent or parent.level != required_parent[payload.level]):
            raise HTTPException(422, "INVALID_TERRITORY_HIERARCHY")
        if payload.level == "country" and (parent or payload.id != "HT") or parent and not parent.active:
            raise HTTPException(422, "INVALID_TERRITORY_HIERARCHY")
        row = Territory(**payload.model_dump())
        session.add(row)
        audit(session, actor, "territory.created", row.id)
        session.commit()
        return envelope(request, payload.model_dump())

    @app.patch("/v1/admin/territories/{identifier}")
    def update_territory(identifier: str, payload: S.TerritoryUpdate, request: Request, session=Depends(db)):
        actor = require_user(request, session, verified=True, admin=True)
        row = session.get(Territory, identifier)
        if not row or not row.active:
            raise HTTPException(404, "TERRITORY_NOT_FOUND")
        if payload.source_version == payload.expected_source_version:
            raise HTTPException(422, "NEW_SOURCE_VERSION_REQUIRED")
        fields = payload.model_dump(exclude={"expected_source_version"})
        before = {key: getattr(row, key) for key in fields}
        changed = session.execute(update(Territory).where(Territory.id == identifier, Territory.source_version == payload.expected_source_version).values(**fields))
        if changed.rowcount != 1:
            raise HTTPException(409, "VERSION_CONFLICT")
        audit(session, actor, "territory.updated", row.id, {"before": before, "after": fields})
        session.commit()
        return envelope(request, {"id": row.id, "parent_id": row.parent_id, "level": row.level, **fields})

    def evidence_storage():
        bucket = os.getenv("S3_BUCKET", "")
        if bucket:
            import boto3
            client = boto3.client("s3", endpoint_url=os.getenv("S3_ENDPOINT_URL") or None, aws_access_key_id=os.getenv("S3_ACCESS_KEY_ID"), aws_secret_access_key=os.getenv("S3_SECRET_ACCESS_KEY"), region_name=os.getenv("S3_REGION", "us-east-1"))
            return client, bucket
        if settings.production:
            raise HTTPException(503, "PRIVATE_STORAGE_NOT_CONFIGURED")
        return None, None

    @app.post("/v1/me/contributions/{identifier}/photos", status_code=201)
    def upload_photo(identifier: str, payload: S.PhotoInput, request: Request, session=Depends(db)):
        user, row = own_contribution(request, session, identifier)
        if engine.dialect.name == "postgresql":
            session.refresh(row, with_for_update=True)
        if row.status not in {"draft", "submitted", "changes_requested"}:
            raise HTTPException(409, "CONTRIBUTION_NOT_EDITABLE")
        try:
            raw = base64.b64decode(payload.content_base64, validate=True)
            if len(raw) > 5_000_000:
                raise ValueError()
            Image.MAX_IMAGE_PIXELS = 20_000_000
            image = Image.open(io.BytesIO(raw))
            if image.format not in {"JPEG", "PNG", "WEBP"} or image.width*image.height > 20_000_000:
                raise ValueError()
            image.load()
            image = ImageOps.exif_transpose(image).convert("RGB")
            image.thumbnail((2048, 2048))
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=85)
        except (ValueError, UnidentifiedImageError, OSError, Image.DecompressionBombError):
            raise HTTPException(422, "INVALID_IMAGE")
        key = "evidence/" + identifier.replace("-", "") + "/" + hashlib.sha256(output.getvalue()).hexdigest()[:32] + ".jpg"
        prior = session.scalar(select(Evidence).where(Evidence.contribution_id == identifier, Evidence.storage_key == key))
        if prior:
            return envelope(request, {"id": prior.id, "moderation_status": prior.moderation_status, "visibility": "private"})
        if session.scalar(select(func.count()).select_from(Evidence).where(Evidence.contribution_id == identifier)) >= 5:
            raise HTTPException(422, "PHOTO_LIMIT_REACHED")
        client, bucket = evidence_storage()
        if client:
            try:
                client.put_object(Bucket=bucket, Key=key, Body=output.getvalue(), ContentType="image/jpeg", ServerSideEncryption="AES256")
            except Exception:
                raise HTTPException(503, "PRIVATE_STORAGE_UNAVAILABLE")
        else:
            folder = Path(os.getenv("EVIDENCE_DIR", str(settings.runtime_dir / "private-evidence")))
            folder.mkdir(parents=True, exist_ok=True)
            (folder/key.split("/")[-1]).write_bytes(output.getvalue())
        photo = Evidence(contribution_id=identifier, storage_key=key)
        session.add(photo)
        session.flush()
        audit(session, user, "evidence.uploaded", photo.id)
        session.commit()
        return envelope(request, {"id": photo.id, "moderation_status": "pending", "visibility": "private"})

    @app.get("/v1/me/contributions/{identifier}/photos")
    def photos(identifier: str, request: Request, session=Depends(db)):
        own_contribution(request, session, identifier)
        return envelope(request, [{"id": item.id, "moderation_status": item.moderation_status} for item in session.scalars(select(Evidence).where(Evidence.contribution_id == identifier))])

    @app.get("/v1/evidence/{identifier}")
    def photo_content(identifier: str, request: Request, session=Depends(db)):
        user = require_user(request, session, verified=True)
        item = session.get(Evidence, identifier)
        proposal = session.get(Contribution, item.contribution_id) if item else None
        if not proposal:
            raise HTTPException(404, "EVIDENCE_NOT_FOUND")
        if proposal.author_user_id != user.id:
            require_user(request, session, verified=True, staff=True)
            if proposal.status == "draft":
                raise HTTPException(404, "EVIDENCE_NOT_FOUND")
            audit(session, user, "evidence.staff_viewed", item.id)
            session.commit()
        client, bucket = evidence_storage()
        if client:
            try:
                content = client.get_object(Bucket=bucket, Key=item.storage_key)["Body"].read()
            except Exception:
                raise HTTPException(503, "PRIVATE_STORAGE_UNAVAILABLE")
        else:
            folder = Path(os.getenv("EVIDENCE_DIR", str(settings.runtime_dir / "private-evidence")))
            try:
                content = (folder/item.storage_key.split("/")[-1]).read_bytes()
            except OSError:
                raise HTTPException(404, "EVIDENCE_NOT_FOUND")
        return Response(content, media_type="image/jpeg", headers={"Content-Disposition": "inline; filename=evidence.jpg"})

    return app


app = create_app()
