"""Independent negative tests: trust boundaries, privacy and credential lifecycle."""
import base64
import io
import secrets
from datetime import timedelta

import pytest
import pyotp
import httpx
from fastapi.testclient import TestClient
from fastapi import HTTPException
from PIL import Image
from sqlalchemy import select

from app.core import Settings, passwords
from app.main import create_app
from app.models import ApiKey, AuthToken, Contribution, DeveloperApp, Location, MailJob, User, UserSession, now


@pytest.fixture
def reviewed_app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_AUTO_CREATE", "true")
    monkeypatch.delenv("BACKEND_DB_ROLE", raising=False)
    monkeypatch.delenv("REWARDS_CASH_ENABLED", raising=False)
    monkeypatch.delenv("EVIDENCE_DIR", raising=False)
    settings = Settings(env="test", database_url=f"sqlite:///{tmp_path}/review.sqlite", runtime_dir=tmp_path, origins=["http://testserver"])
    app = create_app(settings)
    with TestClient(app) as client:
        client.headers["X-CSRF-Token"] = client.get("/v1/auth/csrf").json()["data"]["csrf_token"]
        yield app, client, settings


def identity(app, settings, name="owner", *, role="user", mfa=False, expired=False):
    token = secrets.token_urlsafe(40)
    with app.state.Session() as session:
        user = User(email=f"{name}@example.com", display_name=name, password_hash=passwords.hash("Example-review-password-42"), email_verified=True, role=role)
        session.add(user)
        session.flush()
        session.add(UserSession(user_id=user.id, token_hash=settings.digest(token), expires_at=now()+timedelta(hours=-1 if expired else 1), mfa_verified=mfa))
        session.commit()
        return user.id, token


def draft(name="Review public place"):
    return {"name": name, "type": "business", "territory_id": "HT0112", "selected_point": {"latitude": 18.54, "longitude": -72.3}, "mode": "draft"}


def api_key(app, settings, owner, *, quota=1000):
    token = "ht_test_" + secrets.token_urlsafe(32)
    with app.state.Session() as session:
        application = DeveloperApp(owner_id=owner, name="Independent test app", daily_quota=quota)
        session.add(application)
        session.flush()
        key = ApiKey(app_id=application.id, prefix=token[:16], secret_hash=settings.digest(token), expires_at=now()+timedelta(days=1))
        session.add(key)
        session.commit()
        return application.id, key.id, token


def test_csrf_and_origin_enforced_on_mutations(reviewed_app):
    app, client, settings = reviewed_app
    _, token = identity(app, settings)
    client.cookies.set("ht_session", token)
    assert client.patch("/v1/me", json={"display_name": "Changed"}, headers={"Origin": "https://attacker.example"}).status_code == 403
    client.headers.pop("X-CSRF-Token")
    assert client.patch("/v1/me", json={"display_name": "Changed"}).status_code == 403
    assert client.get("/v1/me").json()["data"]["display_name"] == "owner"


def test_client_cannot_assign_role_or_verification(reviewed_app):
    app, client, settings = reviewed_app
    body = {"display_name": "Visitor", "email": "visitor@example.com", "password": "Example-review-password-42", "terms_accepted": True, "privacy_accepted": True, "role": "admin", "email_verified": True}
    response = client.post("/v1/auth/register", json=body)
    assert response.status_code == 422
    assert "Example-review-password-42" not in response.text
    with app.state.Session() as session:
        assert session.scalar(select(User).where(User.email == body["email"])) is None


def test_expired_session_and_staff_without_mfa_rejected(reviewed_app):
    app, client, settings = reviewed_app
    _, expired = identity(app, settings, "expired", expired=True)
    client.cookies.set("ht_session", expired)
    assert client.get("/v1/me").status_code == 401
    _, staff = identity(app, settings, "staff", role="admin", mfa=False)
    client.cookies.set("ht_session", staff)
    assert client.get("/v1/admin/audit").status_code == 403
    assert client.post("/v1/auth/login", json={"email": "staff@example.com", "password": "Example-review-password-42"}).json()["error"]["code"] == "MFA_REQUIRED"


def test_production_response_cookie_flags_without_external_services(reviewed_app):
    app, client, settings = reviewed_app
    identity(app, settings)
    # Only exercises response configuration; a real production DB/TLS deployment is a separate gate.
    settings.env = "production"
    assert client.post("/v1/auth/login", json={"email": "owner@example.com", "password": "Example-review-password-42"}).status_code == 400
    client.base_url = "https://testserver"
    response = client.post("/v1/auth/login", json={"email": "owner@example.com", "password": "Example-review-password-42"})
    assert response.status_code == 200
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "secure" in cookie and "samesite=lax" in cookie
    assert response.headers["strict-transport-security"].startswith("max-age=")
    assert "password_hash" not in response.text
    settings.env = "test"


def test_encrypted_authenticator_unlocks_staff_session(reviewed_app):
    app, client, settings = reviewed_app
    owner, _ = identity(app, settings, "admin", role="admin")
    authenticator = pyotp.random_base32()
    with app.state.Session() as session:
        session.get(User, owner).mfa_secret = settings.cipher.encrypt(authenticator.encode()).decode()
        session.commit()
    response = client.post("/v1/auth/login", json={"email": "admin@example.com", "password": "Example-review-password-42", "otp": pyotp.TOTP(authenticator).now()})
    assert response.status_code == 200
    assert client.get("/v1/admin/summary").status_code == 200
    assert authenticator not in response.text


def test_reset_token_is_purpose_bound_single_use_and_revokes_sessions(reviewed_app):
    app, client, settings = reviewed_app
    owner, token = identity(app, settings)
    reset = secrets.token_urlsafe(40)
    verify = secrets.token_urlsafe(40)
    expired = secrets.token_urlsafe(40)
    with app.state.Session() as session:
        session.add_all([AuthToken(user_id=owner, token_hash=settings.digest(reset), purpose="reset", expires_at=now()+timedelta(minutes=10)), AuthToken(user_id=owner, token_hash=settings.digest(verify), purpose="verify", expires_at=now()+timedelta(minutes=10)), AuthToken(user_id=owner, token_hash=settings.digest(expired), purpose="reset", expires_at=now()-timedelta(minutes=1))])
        session.commit()
    assert client.post("/v1/auth/reset-password", json={"token": verify, "password": "New-review-password-42"}).status_code == 400
    assert client.post("/v1/auth/reset-password", json={"token": expired, "password": "New-review-password-42"}).status_code == 400
    response = client.post("/v1/auth/reset-password", json={"token": reset, "password": "New-review-password-42"})
    assert response.status_code == 200
    assert client.post("/v1/auth/reset-password", json={"token": reset, "password": "Other-review-password-42"}).status_code == 400
    client.cookies.set("ht_session", token)
    assert client.get("/v1/me").status_code == 401


@pytest.mark.parametrize("route", ["forgot-password", "resend-verification", "register"])
def test_recovery_provider_failure_does_not_reveal_account(reviewed_app, monkeypatch, route):
    app, client, settings = reviewed_app
    owner, _ = identity(app, settings)
    if route == "resend-verification":
        with app.state.Session() as session:
            session.get(User, owner).email_verified = False
            session.commit()

    def unavailable(*args, **kwargs):
        raise HTTPException(503, "EMAIL_DELIVERY_UNAVAILABLE")

    monkeypatch.setattr("app.main.issue_email", unavailable)
    common = {"display_name": "Review account", "password": "Example-review-password-42", "terms_accepted": True, "privacy_accepted": True} if route == "register" else {}
    present = client.post(f"/v1/auth/{route}", json={**common, "email": "owner@example.com"})
    absent = client.post(f"/v1/auth/{route}", json={**common, "email": "missing@example.com"})
    assert present.status_code == absent.status_code == 202
    assert present.json()["data"] == absent.json()["data"]


def test_provider_failure_leaves_durable_encrypted_retry(reviewed_app, monkeypatch):
    app, client, settings = reviewed_app
    identity(app, settings)
    settings.resend_key = "test-only-provider-placeholder"

    def unavailable(*args, **kwargs):
        raise httpx.ConnectError("simulated offline provider")

    monkeypatch.setattr("app.core.httpx.post", unavailable)
    response = client.post("/v1/auth/forgot-password", json={"email": "owner@example.com"})
    assert response.status_code == 202
    with app.state.Session() as session:
        job = session.scalar(select(MailJob))
        assert job and job.status == "pending" and job.attempts == 1
        assert "owner@example.com" not in job.payload_encrypted
        assert b"owner@example.com" in settings.cipher.decrypt(job.payload_encrypted.encode())


def test_contribution_ownership_and_idempotency_scope(reviewed_app):
    app, client, settings = reviewed_app
    owner, token = identity(app, settings)
    client.cookies.set("ht_session", token)
    headers = {"Idempotency-Key": "independent-review-request"}
    response = client.post("/v1/contributions", json=draft(), headers=headers)
    assert response.status_code == 201
    identifier = response.json()["data"]["id"]
    assert client.post("/v1/contributions", json=draft(), headers=headers).json()["data"]["id"] == identifier
    assert client.post("/v1/contributions", json=draft("A different place"), headers=headers).status_code == 409
    _, other = identity(app, settings, "other")
    client.cookies.set("ht_session", other)
    assert client.get(f"/v1/me/contributions/{identifier}").status_code == 404
    assert client.patch(f"/v1/me/contributions/{identifier}", json={**draft(), "version": 1}).status_code == 404
    different = client.post("/v1/contributions", json=draft(), headers=headers)
    assert different.status_code == 201
    assert different.json()["data"]["id"] != identifier
    exported = client.get("/v1/me/export").json()["data"]
    assert identifier not in [row["id"] for row in exported["contributions"]]


def test_api_keys_are_owned_revocable_and_suspend_with_owner(reviewed_app):
    app, client, settings = reviewed_app
    owner, owner_session = identity(app, settings)
    application, key_id, secret = api_key(app, settings, owner)
    _, other = identity(app, settings, "other")
    client.cookies.set("ht_session", other)
    assert client.get(f"/v1/developer/apps/{application}/usage").status_code == 404
    assert client.post(f"/v1/developer/apps/{application}/keys/{key_id}/revoke").status_code == 404
    authorization = {"Authorization": f"Bearer {secret}"}
    assert client.get("/v1/locations/nearby?lat=18.54&lon=-72.3", headers=authorization).status_code == 200
    with app.state.Session() as session:
        session.get(User, owner).active = False
        session.commit()
    assert client.get("/v1/locations/nearby?lat=18.54&lon=-72.3", headers=authorization).status_code == 401
    with app.state.Session() as session:
        session.get(User, owner).active = True
        session.commit()
    client.cookies.set("ht_session", owner_session)
    assert secret not in client.get("/v1/developer/apps").text
    assert client.post(f"/v1/developer/apps/{application}/keys/{key_id}/revoke").status_code == 200
    assert client.get("/v1/locations/nearby?lat=18.54&lon=-72.3", headers=authorization).status_code == 401


def test_private_and_hidden_records_never_enter_public_routes(reviewed_app):
    app, client, settings = reviewed_app
    owner, _ = identity(app, settings)
    _, _, secret = api_key(app, settings, owner)
    with app.state.Session() as session:
        for code, place_type, visibility in [("HT-NXV-800001", "business", "public"), ("HT-NXV-800002", "private_address", "public"), ("HT-NXV-800003", "business", "hidden")]:
            session.add(Location(public_code=code, name="Privacy review place", normalized_name="privacy review place", type=place_type, territory_id="HT0112", latitude=18.54, longitude=-72.3, public_visibility=visibility, address={"reference": "Public business entrance"}))
        session.commit()
    authorization = {"Authorization": f"Bearer {secret}"}
    for path in ["/v1/locations/search?q=Privacy", "/v1/locations/nearby?lat=18.54&lon=-72.3", "/v1/geocode?q=Privacy"]:
        response = client.get(path, headers=authorization)
        assert response.status_code == 200
        assert [row["code"] for row in response.json()["data"]] == ["HT-NXV-800001"]
        assert "gps_observation" not in response.text
        assert "author_user_id" not in response.text
    reverse = client.get("/v1/reverse?lat=18.54&lon=-72.3", headers=authorization)
    assert [row["code"] for row in reverse.json()["data"]["public_places"]] == ["HT-NXV-800001"]
    for code in ["HT-NXV-800002", "HT-NXV-800003", "HT-NXV-999999"]:
        response = client.get(f"/v1/locations/{code}")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "LOCATION_NOT_FOUND"


def test_api_quota_validation_and_no_store(reviewed_app):
    app, client, settings = reviewed_app
    owner, _ = identity(app, settings)
    _, _, secret = api_key(app, settings, owner, quota=1)
    headers = {"Authorization": f"Bearer {secret}"}
    first = client.get("/v1/locations/nearby?lat=18.54&lon=-72.3", headers=headers)
    assert first.status_code == 200 and first.headers["cache-control"] == "no-store"
    blocked = client.get("/v1/locations/nearby?lat=18.54&lon=-72.3", headers=headers)
    assert blocked.status_code == 429 and int(blocked.headers["retry-after"]) > 0
    assert client.get("/v1/locations/search?limit=51").status_code == 422
    assert client.get("/v1/locations/nearby?lat=nan&lon=-72.3", headers=headers).status_code == 422
    assert client.get("/v1/locations/search?q=%27%20OR%201%3D1%20--").status_code == 200


def test_evidence_reencoded_private_and_cross_account_denied(reviewed_app):
    app, client, settings = reviewed_app
    _, token = identity(app, settings)
    client.cookies.set("ht_session", token)
    proposal = client.post("/v1/contributions", json=draft(), headers={"Idempotency-Key": "evidence-review-create"}).json()["data"]["id"]
    assert client.post(f"/v1/me/contributions/{proposal}/photos", json={"content_base64": base64.b64encode(b"<script>malicious()</script>").decode()}).status_code == 422
    source = io.BytesIO()
    exif = Image.Exif()
    exif[270] = "Private EXIF sentinel"
    Image.new("RGB", (4, 4), "white").save(source, format="JPEG", exif=exif)
    uploaded = client.post(f"/v1/me/contributions/{proposal}/photos", json={"content_base64": base64.b64encode(source.getvalue()).decode()})
    assert uploaded.status_code == 201
    assert uploaded.json()["data"]["visibility"] == "private"
    identifier = uploaded.json()["data"]["id"]
    content = client.get(f"/v1/evidence/{identifier}")
    assert content.status_code == 200
    assert not Image.open(io.BytesIO(content.content)).getexif()
    _, other = identity(app, settings, "other")
    client.cookies.set("ht_session", other)
    assert client.get(f"/v1/evidence/{identifier}").status_code in {403, 404}
    assert client.get(f"/v1/me/contributions/{proposal}/photos").status_code == 404
    client.cookies.delete("ht_session")
    assert client.get(f"/v1/evidence/{identifier}").status_code == 401


def test_staff_cannot_self_approve_or_mass_assign_canonical_fields(reviewed_app):
    app, client, settings = reviewed_app
    owner, token = identity(app, settings, "moderator", role="moderator", mfa=True)
    client.cookies.set("ht_session", token)
    payload = {**draft(), "mode": "remote", "source_declaration_accepted": True}
    assert client.post("/v1/contributions", json={**payload, "reward_amount": 50, "verified": True}, headers={"Idempotency-Key": "massassign-review-test"}).status_code == 422
    with app.state.Session() as session:
        row = Contribution(author_user_id=owner, payload=payload, status="submitted")
        session.add(row)
        session.commit()
        identifier = row.id
    response = client.post(f"/v1/admin/contributions/{identifier}/decision", json={"decision": "approve", "reason": "Independent review explanation", "version": 1})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "SELF_REVIEW_FORBIDDEN"
