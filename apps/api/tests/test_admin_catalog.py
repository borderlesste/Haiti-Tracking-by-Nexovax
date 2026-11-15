import pytest

from app.core import Settings
from app.models import Territory


@pytest.mark.parametrize("url", ["https://u:fixture@example.org", "https://example.org?code=fixture", "https://example.org#token", "javascript:example", "https://example.org:0"])
def test_web_base_cannot_embed_credentials_or_tokens(url):
    with pytest.raises(RuntimeError, match="WEB_BASE_URL"):
        Settings(env="test", web_base_url=url)


def test_catalog_update_is_admin_only_versioned_and_audited(api, signed_user, staff_user):
    with api.app.state.Session() as session:
        row = session.get(Territory, "HT0112")
        old_version, parent = row.source_version, row.parent_id
    payload = {"name": "Delmas", "aliases": ["Dèlma"], "source_version": "synthetic-review-v2", "expected_source_version": old_version, "source_url": "https://data.humdata.org/dataset/cod-ab-hti", "license": "Synthetic test only; CC BY-IGO source"}
    assert api.patch("/v1/admin/territories/HT0112", json=payload).status_code == 403
    api.cookies.set("ht_session", "test-staff-session")
    assert api.patch("/v1/admin/territories/HT0112", json={**payload, "parent_id": "HT02"}).status_code == 422
    assert api.patch("/v1/admin/territories/HT0112", json={**payload, "source_url": "https://u:fixture@example.org"}).status_code == 422
    assert api.patch("/v1/admin/territories/HT0112", json={**payload, "source_version": old_version}).status_code == 422
    changed = api.patch("/v1/admin/territories/HT0112", json=payload)
    assert changed.status_code == 200 and changed.json()["data"]["parent_id"] == parent
    assert api.patch("/v1/admin/territories/HT0112", json=payload).status_code == 409
    with api.app.state.Session() as session:
        row = session.get(Territory, "HT0112")
        assert row.aliases == ["Dèlma"] and row.parent_id == parent and row.level == "commune"
    events = api.get("/v1/admin/audit", params={"actor_id": staff_user.id, "subject_id": "HT0112", "action": "territory.updated"}).json()["data"]
    assert len(events) == 1 and events[0]["metadata"]["before"]["source_version"] == old_version
    assert events[0]["metadata"]["after"]["aliases"] == ["Dèlma"]
    assert api.get("/v1/admin/audit", params={"action": "' OR 1=1;--"}).json()["data"] == []
    assert api.get("/v1/admin/summary").json()["data"]["pending_suggestions"] == 0


def test_documented_contracts_and_unknown_routes_are_normalized(api):
    unknown = api.get("/v1/not-a-real-endpoint")
    assert unknown.status_code == 404 and unknown.json()["error"]["code"] == "NOT_FOUND"
    unsupported = api.get("/v1/auth/login")
    assert unsupported.status_code == 405 and unsupported.json()["error"]["code"] == "METHOD_NOT_ALLOWED"
    section = api.get("/v1/territories", params={"level": "section", "parent_id": "HT0112", "limit": 1}).json()["data"][0]
    assert api.get("/v1/territories/" + section["id"]).json()["data"] == section
    schema = api.get("/openapi.json").json()["components"]["schemas"]
    assert {"Territory", "ContributionCreate", "ContributionResponse", "DuplicateCandidate", "ApiError"} <= set(schema)
