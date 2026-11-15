import base64
import io
import json
from datetime import datetime, timedelta
from pathlib import Path

import pyotp
from PIL import Image
from sqlalchemy import select

from app.core import normalize, passwords
from app.models import ApiKey, AuthToken, Contribution, Location, LocationReport, User, UserSession, now


def test_body_limits_and_early_errors_keep_security_headers(api):
    large = api.post("/v1/public-suggestions", content=b"x" * 64_001, headers={"Content-Type": "application/json"})
    assert large.status_code == 413
    assert large.headers["cache-control"] == "no-store"
    assert large.headers["x-content-type-options"] == "nosniff"
    assert api.post("/v1/me/contributions/not-an-id/photos", json={"content_base64": "ignored-before-parsing"}).status_code == 401
    csrf = api.post("/v1/auth/logout", headers={"X-CSRF-Token": "wrong"})
    assert csrf.status_code == 403 and csrf.headers["cache-control"] == "no-store"


def test_security_rejections_are_observable_without_sensitive_input(api, caplog):
    result = api.post("/v1/auth/login", json={"email": "not-a-user@example.org", "password": "Do-not-log-this-password"})
    assert result.status_code == 401
    assert "security_rejection status=401 route=/v1/auth/login" in caplog.text
    assert "not-a-user@example.org" not in caplog.text and "Do-not-log-this-password" not in caplog.text


def test_unknown_environment_is_rejected():
    import pytest
    from app.core import Settings
    with pytest.raises(RuntimeError, match="APP_ENV"):
        Settings(env="prod")


def test_moving_access_preserves_observation_and_requires_explanation(api, signed_user, proposal):
    shifted = {**proposal, "selected_point": {"latitude": 18.54054, "longitude": -72.3}, "gps_observation": {**proposal["gps_observation"], "latitude": 18.54, "longitude": -72.3, "source": "browser_geolocation"}}
    denied = api.post("/v1/contributions", json=shifted, headers={"Idempotency-Key": "shifted-without-reason"})
    assert denied.status_code == 422 and denied.json()["error"]["code"] == "PIN_ADJUSTMENT_REASON_REQUIRED"
    accepted = api.post("/v1/contributions", json={**shifted, "pin_adjustment_reason": "The public entrance is across the square"}, headers={"Idempotency-Key": "shifted-with-reason"})
    assert accepted.status_code == 201
    data = accepted.json()["data"]["payload"]
    assert data["selected_point"] == shifted["selected_point"]
    assert {k: v for k, v in data["gps_observation"].items() if k != "captured_at"} == {k: v for k, v in shifted["gps_observation"].items() if k != "captured_at"}
    assert datetime.fromisoformat(data["gps_observation"]["captured_at"]) == datetime.fromisoformat(shifted["gps_observation"]["captured_at"])
    assert 59 < data["pin_distance_m"] < 61 and "pin_adjustment_review" in data["quality_flags"]


def test_public_suggestion_requires_staff_review_and_is_never_auto_published(api, signed_user, staff_user):
    response = api.post("/v1/public-suggestions", json={"name": "Suggested public place", "type": "public", "territory_id": "HT0112", "reference": "In front of a public square", "source_declaration_accepted": True})
    assert response.status_code == 202
    assert api.get("/v1/admin/suggestions").status_code == 403
    api.cookies.set("ht_session", "test-staff-session")
    suggestions = api.get("/v1/admin/suggestions").json()["data"]
    assert len(suggestions) == 1
    identifier = suggestions[0]["id"]
    result = api.post(f"/v1/admin/suggestions/{identifier}/decision", json={"decision": "reviewed", "reason": "Needs independent on-site capture"})
    assert result.status_code == 200 and result.json()["data"]["published"] is False
    assert api.get("/v1/locations/search?q=Suggested").json()["data"] == []
    assert api.post(f"/v1/admin/suggestions/{identifier}/decision", json={"decision": "reviewed", "reason": "Replay of review is not allowed"}).status_code == 409


def test_anonymous_search_needs_no_gps_and_never_exposes_private(api):
    with api.app.state.Session() as db:
        db.add_all([
            Location(public_code="HT-NXV-000101", name="Commerce Démo", normalized_name="commerce demo", type="business", territory_id="HT0112", latitude=18.54, longitude=-72.3, address={"reference": "Public entrance", "owner_email": "private@example.org", "gps_observation": {"accuracy_m": 10}}),
            Location(public_code="HT-NXV-SECRET", name="Private residence", normalized_name="private residence", type="residence", territory_id="HT0112", latitude=18.54, longitude=-72.3, address={}, public_visibility="private"),
            Location(public_code="HT-NXV-HIDDEN", name="Hidden commerce", normalized_name="hidden commerce", type="business", territory_id="HT0112", latitude=18.54, longitude=-72.3, address={}, public_visibility="hidden"),
        ])
        db.commit()
    result = api.get("/v1/locations/search").json()
    assert [item["code"] for item in result["data"]] == ["HT-NXV-000101"]
    assert result["data"][0]["last_verified_at"].endswith("Z")
    assert "gps_observation" not in json.dumps(result)
    assert "private@example.org" not in json.dumps(result)
    detail = api.get("/v1/locations/HT-NXV-000101").json()["data"]
    assert "owner_email" not in detail["address"] and detail["address"]["commune"] == "Delmas"
    import zxingcpp
    qr = api.get("/v1/locations/HT-NXV-000101/qr", headers={"Host": "untrusted.example.org"})
    assert qr.status_code == 200 and qr.headers["content-type"] == "image/png"
    decoded = zxingcpp.read_barcode(Image.open(io.BytesIO(qr.content)))
    assert decoded and decoded.text == api.app.state.settings.web_base_url + "/ubicaciones/HT-NXV-000101"
    schema = api.get("/openapi.json").json()
    assert schema["paths"]["/v1/locations/search"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("LocationListResponse")
    assert api.get("/v1/locations/HT-NXV-SECRET").status_code == 404
    assert api.get("/v1/locations/HT-NXV-HIDDEN").status_code == 404
    assert api.get("/v1/locations/HT-NXV-SECRET/qr").status_code == 404
    assert api.get("/v1/locations/HT-NXV-HIDDEN/qr").status_code == 404
    assert api.get("/v1/locations/search", params={"q": "%' OR 1=1;--"}).json()["data"] == []
    assert api.get("/v1/locations/search?limit=1000").status_code == 422


def test_csrf_role_mass_assignment_and_gps(api, signed_user, proposal):
    token = api.headers.pop("X-CSRF-Token")
    assert api.post("/v1/contributions", json=proposal).status_code == 403
    api.headers["X-CSRF-Token"] = token
    assert api.get("/v1/admin/contributions").status_code == 403
    invalid = {**proposal, "verified": True}
    response = api.post("/v1/contributions", json=invalid, headers={"Idempotency-Key": "bad-mass-assignment"})
    assert response.status_code == 422
    missing = {**proposal, "gps_observation": None}
    response = api.post("/v1/contributions", json=missing, headers={"Idempotency-Key": "missing-gps-test"})
    assert response.json()["error"]["code"] == "GPS_REQUIRED_FOR_ON_SITE"
    expired = {**proposal, "gps_observation": {**proposal["gps_observation"], "captured_at": (now()-timedelta(hours=1)).isoformat()}}
    assert api.post("/v1/contributions", json=expired, headers={"Idempotency-Key": "expired-gps-test"}).status_code == 422
    outside = {**proposal, "selected_point": {"latitude": -23.55, "longitude": -46.63}}
    assert api.post("/v1/contributions", json=outside, headers={"Idempotency-Key": "outside-haiti-test"}).json()["error"]["code"] == "POINT_OUTSIDE_HAITI"


def test_idempotency_review_publish_and_stable_code(api, signed_user, staff_user, proposal):
    headers = {"Idempotency-Key": "test-idempotent-proposal"}
    first = api.post("/v1/contributions", json=proposal, headers=headers)
    assert first.status_code == 201, first.text
    identifier = first.json()["data"]["id"]
    assert api.post("/v1/contributions", json=proposal, headers=headers).json()["data"]["id"] == identifier
    assert api.post("/v1/contributions", json={**proposal, "name": "Different name"}, headers=headers).status_code == 409
    assert api.get("/v1/locations/search").json()["data"] == []
    decision = {"decision": "approve", "reason": "Verified independently during test", "version": 1}
    api.cookies.set("ht_session", "test-staff-session")
    result = api.post(f"/v1/admin/contributions/{identifier}/decision", json=decision)
    assert result.status_code == 200, result.text
    code = result.json()["data"]["published_code"]
    assert code == "HT-NXV-000001"
    record = api.get(f"/v1/locations/{code}").json()["data"]
    assert record["name"] == proposal["name"] and record["was_redirected"] is False
    assert "author_user_id" not in record and "gps_observation" not in record
    assert api.post(f"/v1/admin/contributions/{identifier}/decision", json=decision).status_code == 409
    audit = api.get("/v1/admin/audit").json()["data"]
    assert "moderation.approve" in [event["action"] for event in audit]


def test_ownership_draft_changes_and_self_review(api, signed_user, proposal):
    draft = {**proposal, "mode": "draft", "gps_observation": None, "source_declaration_accepted": False}
    result = api.post("/v1/contributions", json=draft, headers={"Idempotency-Key": "draft-proposal-key"}).json()["data"]
    identifier = result["id"]
    assert api.patch(f"/v1/me/contributions/{identifier}", json={**draft, "name": "Updated draft", "version": 1}).status_code == 200
    assert api.patch(f"/v1/me/contributions/{identifier}", json={**draft, "version": 1}).status_code == 409
    with api.app.state.Session() as db:
        row = db.get(User, signed_user.id)
        row.role = "admin"
        entry = db.scalar(select(UserSession).where(UserSession.user_id == row.id))
        entry.mfa_verified = True
        db.commit()
    assert api.get("/v1/admin/contributions").json()["data"] == []
    submitted = api.post("/v1/contributions", json=proposal, headers={"Idempotency-Key": "self-review-submitted"}).json()["data"]
    response = api.post(f"/v1/admin/contributions/{submitted['id']}/decision", json={"decision": "approve", "reason": "Trying to approve my own record", "version": 1})
    assert response.status_code == 403 and response.json()["error"]["code"] == "SELF_REVIEW_FORBIDDEN"


def test_registration_verification_reset_are_single_use_and_revoke_sessions(api):
    payload = {"display_name": "Jean Test", "email": "jean@example.org", "password": "a-secure-test-password", "phone": "+509 37 12 34 56", "profile": "collaborator", "terms_accepted": True, "privacy_accepted": True}
    result = api.post("/v1/auth/register", json=payload)
    assert result.status_code == 202, result.text
    assert "token" not in result.text and "password" not in result.text
    with api.app.state.Session() as db:
        user = db.scalar(select(User).where(User.email == payload["email"]))
        assert user.password_hash.startswith("$argon2id$")
        assert user.phone_encrypted and "509" not in user.phone_encrypted
        assert not user.email_verified
    files = list((api.app.state.settings.runtime_dir / "outbox").glob("*.json"))
    body = json.loads(files[0].read_text(encoding="utf-8"))["text"]
    token = body.split("/verificar#token=")[1].split("\n")[0]
    assert api.post("/v1/auth/verify-email", json={"token": token}).status_code == 200
    assert api.post("/v1/auth/verify-email", json={"token": token}).status_code == 400
    login = api.post("/v1/auth/login", json={"email": payload["email"], "password": payload["password"]})
    assert login.status_code == 200 and "HttpOnly" in login.headers["set-cookie"]
    assert api.get("/v1/auth/me").status_code == 200
    assert api.post("/v1/auth/forgot-password", json={"email": payload["email"]}).status_code == 202
    reset_files = list((api.app.state.settings.runtime_dir / "outbox").glob("*.json"))
    body = next(json.loads(p.read_text(encoding="utf-8"))["text"] for p in reset_files if "/restablecer#token=" in p.read_text(encoding="utf-8"))
    token = body.split("/restablecer#token=")[1].split("\n")[0]
    reset = {"token": token, "password": "a-new-secure-test-password"}
    assert api.post("/v1/auth/reset-password", json=reset).status_code == 200
    assert api.get("/v1/auth/me").status_code == 401
    assert api.post("/v1/auth/reset-password", json=reset).status_code == 400


def test_key_is_one_time_hashed_revocable_and_cannot_access_private(api, signed_user):
    app = api.post("/v1/developer/apps", json={"name": "Integration test", "environment": "test"}).json()["data"]
    path = f"/v1/developer/apps/{app['id']}/keys"
    key = api.post(path, json={"password": "correct-horse-battery"}).json()["data"]
    assert key["secret"].startswith("ht_test_")
    serialized = api.get("/v1/developer/apps").text
    assert key["secret"] not in serialized
    with api.app.state.Session() as db:
        row = db.get(ApiKey, key["id"])
        assert row.secret_hash != key["secret"] and len(row.secret_hash) == 64
    headers = {"Authorization": f"Bearer {key['secret']}"}
    assert api.get("/v1/locations/nearby?lat=18.54&lon=-72.3", headers=headers).status_code == 200
    assert api.get("/v1/locations/nearby?lat=18.54&lon=-72.3").status_code == 401
    assert api.post(path+f"/{key['id']}/revoke").status_code == 200
    assert api.get("/v1/locations/search", headers=headers).status_code == 401


def test_photos_reencoded_private_and_owner_controlled(api, signed_user, proposal):
    row = api.post("/v1/contributions", json=proposal, headers={"Idempotency-Key": "photo-test-proposal"}).json()["data"]
    path = f"/v1/me/contributions/{row['id']}/photos"
    malicious = base64.b64encode(b"<svg onload=alert(1)></svg>").decode()
    assert api.post(path, json={"content_base64": malicious}).status_code == 422
    image = io.BytesIO()
    Image.new("RGB", (24, 24)).save(image, format="PNG")
    upload = api.post(path, json={"content_base64": base64.b64encode(image.getvalue()).decode()})
    assert upload.status_code == 201, upload.text
    photo_id = upload.json()["data"]["id"]
    replay = api.post(path, json={"content_base64": base64.b64encode(image.getvalue()).decode()})
    assert replay.json()["data"]["id"] == photo_id
    assert len(api.get(path).json()["data"]) == 1
    content = api.get(f"/v1/evidence/{photo_id}")
    assert content.status_code == 200 and content.headers["content-type"] == "image/jpeg"
    assert not Image.open(io.BytesIO(content.content)).getexif()
    api.cookies.delete("ht_session")
    assert api.get(f"/v1/evidence/{photo_id}").status_code == 401


def test_merged_codes_redirect_and_hidden_target_stays_private(api, signed_user, staff_user):
    with api.app.state.Session() as db:
        first = Location(public_code="HT-NXV-101101", name="Same business old", normalized_name="same business old", type="business", territory_id="HT0112", latitude=18.54, longitude=-72.3, address={})
        second = Location(public_code="HT-NXV-101102", name="Same business", normalized_name="same business", type="business", territory_id="HT0112", latitude=18.54, longitude=-72.3, address={})
        db.add_all([first, second])
        db.commit()
    api.cookies.set("ht_session", "test-staff-session")
    merged = api.post(f"/v1/admin/locations/{first.id}/merge", json={"canonical_code": second.public_code, "reason": "Confirmed duplicate of the same business"})
    assert merged.status_code == 200, merged.text
    record = api.get(f"/v1/locations/{first.public_code}").json()["data"]
    assert record["canonical_code"] == second.public_code and record["was_redirected"] is True
    import zxingcpp
    qr = api.get(f"/v1/locations/{first.public_code}/qr")
    assert zxingcpp.read_barcode(Image.open(io.BytesIO(qr.content))).text.endswith("/ubicaciones/" + second.public_code)
    assert api.post(f"/v1/admin/locations/{second.id}/hide", json={"category": "privacy", "description": "Withdraw publication after privacy review"}).status_code == 200
    assert api.get(f"/v1/locations/{first.public_code}").status_code == 404
    assert api.get(f"/v1/locations/{second.public_code}").status_code == 404
    assert api.get(f"/v1/locations/{first.public_code}/qr").status_code == 404


def test_high_gps_uncertainty_and_explicit_duplicate_resolution(api, signed_user, proposal):
    with api.app.state.Session() as db:
        db.add(Location(public_code="HT-NXV-000201", name=proposal["name"], normalized_name=normalize(proposal["name"]), type="business", territory_id="HT0112", latitude=18.54, longitude=-72.3, address={}))
        db.commit()
    matches = api.post("/v1/contributions/check-duplicates", json={key: proposal[key] for key in ["name", "type", "territory_id", "selected_point"]})
    assert matches.status_code == 200 and len(matches.json()["data"]["candidates"]) == 1
    assert api.post("/v1/contributions", json=proposal, headers={"Idempotency-Key": "unresolved-duplicates"}).status_code == 409
    uncertain = {**proposal, "gps_observation": {**proposal["gps_observation"], "accuracy_m": 150}, "duplicate_resolution": {"choice": "distinct_place", "justification": "Separate shop with its own entrance"}}
    result = api.post("/v1/contributions", json=uncertain, headers={"Idempotency-Key": "uncertain-gps-example"})
    assert result.status_code == 201, result.text
    assert result.json()["data"]["payload"]["quality_flags"] == ["low_gps_accuracy"]
    assert result.json()["data"]["eligible_for_automatic_payment"] is False
