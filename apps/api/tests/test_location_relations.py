from datetime import timedelta

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import IntegrityError

from app.cli import purge_gps
from app.core import ensure_location_relationships, normalize
from app.models import AuditEvent, Contribution, Location, LocationVersion, Territory, now


def places(api):
    with api.app.state.Session() as db:
        parent = Location(public_code="HT-NXV-000100", name="Complexe public", normalized_name="complexe public", type="public", territory_id="HT0112", latitude=18.6, longitude=-72.3, address={})
        entrance = Location(public_code="HT-NXV-000101", name="Entrée nord", normalized_name="entree nord", type="access", territory_id="HT0112", latitude=18.6, longitude=-72.3, address={})
        db.add_all([parent, entrance])
        db.commit()
        return parent, entrance


def test_links_alias_search_and_hidden_link_redaction(api, signed_user, staff_user, proposal):
    parent, entrance = places(api)
    body = {**proposal, "parent_location_code": parent.public_code, "access_point_code": entrance.public_code, "aliases": ["Boutik Lakay", "Bótik Lokal"], "knowledge_source": "local_representative"}
    result = api.post("/v1/contributions", json=body, headers={"Idempotency-Key": "location-relations-test"})
    assert result.status_code == 201, result.text
    identifier = result.json()["data"]["id"]
    api.cookies.set("ht_session", "test-staff-session")
    approved = api.post(f"/v1/admin/contributions/{identifier}/decision", json={"decision": "approve", "reason": "Entrance and names independently checked", "version": 1})
    assert approved.status_code == 200, approved.text
    detail = api.get("/v1/locations/HT-NXV-000001").json()["data"]
    assert detail["parent_location_code"] == parent.public_code and detail["access_point_code"] == entrance.public_code
    assert detail["aliases"] == body["aliases"] and "knowledge_source" not in detail
    summary = api.get("/v1/admin/summary").json()["data"]
    assert summary["territory_counts"] == [{"id": "HT0112", "name": "Delmas", "count": 3}]
    assert api.get("/v1/locations/search?q=botik").json()["data"][0]["code"] == detail["code"]
    matches = api.post("/v1/contributions/check-duplicates", json={k: body[k] for k in ("name", "type", "territory_id", "selected_point")} | {"name": "Boutik Lakay"}).json()["data"]["candidates"]
    assert matches[0]["similarity_score"] == 1
    with api.app.state.Session() as db:
        db.get(Location, parent.id).public_visibility = "hidden"
        db.commit()
    assert api.get("/v1/locations/HT-NXV-000001").json()["data"]["parent_location_code"] is None


def test_department_and_commune_search_include_communal_sections(api):
    with api.app.state.Session() as db:
        section = db.scalar(select(Territory).where(Territory.level == "section"))
        commune = db.get(Territory, section.parent_id)
        item = Location(public_code="HT-NXV-000211", name="Section public place", normalized_name="section public place", type="public", territory_id=section.id, latitude=18.54, longitude=-72.3, address={})
        db.add(item)
        db.commit()
    for territory in (section.id, commune.id, commune.parent_id, "HT"):
        assert api.get("/v1/locations/search", params={"territory_id": territory}).json()["data"][0]["code"] == item.public_code


def test_invalid_private_self_and_cyclic_links(api, signed_user, proposal):
    parent, entrance = places(api)
    with api.app.state.Session() as db:
        child = Location(public_code="HT-NXV-000102", name="Child", normalized_name="child", type="business", territory_id="HT0112", latitude=18.6, longitude=-72.3, address={}, parent_location_id=parent.id)
        db.add(child)
        db.commit()
    for index, extra in enumerate([
        {"access_point_code": parent.public_code},
        {"target_location_code": parent.public_code, "parent_location_code": parent.public_code},
        {"target_location_code": parent.public_code, "parent_location_code": child.public_code},
        {"aliases": ["bad\u0000name"]},
    ]):
        result = api.post("/v1/contributions", json={**proposal, **extra}, headers={"Idempotency-Key": f"invalid-relations-{index}"})
        assert result.status_code == 422, result.text
    with api.app.state.Session() as db:
        db.get(Location, entrance.id).public_visibility = "hidden"
        db.commit()
    assert api.post("/v1/contributions", json={**proposal, "access_point_code": entrance.public_code}, headers={"Idempotency-Key": "hidden-relation-test"}).status_code == 404
    with api.app.state.Session() as db:
        with pytest.raises(IntegrityError):
            db.execute(text("UPDATE locations SET parent_location_id=:child WHERE id=:parent"), {"child": child.id, "parent": parent.id})
        db.rollback()


def test_edit_preserves_correction_target_and_rejects_retargeting(api, signed_user, proposal):
    original, other = places(api)
    body = {**proposal, "mode": "draft", "target_location_code": original.public_code}
    created = api.post("/v1/contributions", json=body, headers={"Idempotency-Key": "immutable-correction-target"}).json()["data"]
    path = f"/v1/me/contributions/{created['id']}"
    assert api.patch(path, json={**body, "version": 1, "target_location_code": other.public_code}).status_code == 422
    without_target = {key: value for key, value in body.items() if key != "target_location_code"}
    saved = api.patch(path, json={**without_target, "version": 1})
    assert saved.status_code == 200, saved.text
    assert saved.json()["data"]["payload"]["target_location_code"] == original.public_code
    with api.app.state.Session() as db:
        assert db.get(Contribution, created["id"]).target_location_id == original.id
    new_place = api.post("/v1/contributions", json=without_target, headers={"Idempotency-Key": "immutable-new-place-target"}).json()["data"]
    assert api.patch(f"/v1/me/contributions/{new_place['id']}", json={**body, "version": 1}).status_code == 422


def test_merge_preserves_child_links_names_codes_and_versions(api, signed_user, staff_user):
    source, target = places(api)
    with api.app.state.Session() as db:
        child = Location(public_code="HT-NXV-000102", name="Child", normalized_name="child", type="business", territory_id="HT0112", latitude=18.6, longitude=-72.3, address={}, parent_location_id=source.id)
        db.add(child)
        db.commit()
    api.cookies.set("ht_session", "test-staff-session")
    denied = api.post(f"/v1/admin/locations/{source.id}/merge", json={"canonical_code": child.public_code, "reason": "Cannot merge parent into descendant"})
    assert denied.status_code == 422
    result = api.post(f"/v1/admin/locations/{source.id}/merge", json={"canonical_code": target.public_code, "reason": "Both codes identify the same entrance"})
    assert result.status_code == 200, result.text
    assert api.get(f"/v1/locations/{source.public_code}").json()["data"]["canonical_code"] == target.public_code
    assert api.get(f"/v1/locations/{child.public_code}").json()["data"]["parent_location_code"] == target.public_code
    assert api.get("/v1/locations/search?q=complexe").json()["data"][0]["code"] == target.public_code
    with api.app.state.Session() as db:
        assert db.scalar(select(LocationVersion).where(LocationVersion.location_id == child.id)).version == 2


def test_withdraw_is_owned_versioned_audited_and_final(api, signed_user, staff_user, proposal):
    result = api.post("/v1/contributions", json=proposal, headers={"Idempotency-Key": "withdraw-proposal-key"}).json()["data"]
    path = f"/v1/me/contributions/{result['id']}/withdraw"
    api.cookies.set("ht_session", "test-staff-session")
    assert api.post(path, json={"version": 1}).status_code == 404
    api.cookies.set("ht_session", "test-user-session")
    assert api.post(path, json={"version": 2}).status_code == 409
    result = api.post(path, json={"version": 1}).json()["data"]
    assert result["status"] == "withdrawn" and result["version"] == 2
    assert api.post(path, json={"version": 2}).status_code == 409
    api.cookies.set("ht_session", "test-staff-session")
    assert api.post(f"/v1/admin/contributions/{result['id']}/decision", json={"decision": "approve", "reason": "Cannot approve a withdrawn proposal", "version": 2}).status_code == 409
    with api.app.state.Session() as db:
        assert db.scalar(select(AuditEvent.id).where(AuditEvent.action == "contribution.withdrawn"))


def test_retention_dry_run_purges_only_observation_and_requires_corroboration(api, signed_user, staff_user, proposal):
    result = api.post("/v1/contributions", json=proposal, headers={"Idempotency-Key": "gps-retention-test"}).json()["data"]
    with api.app.state.Session() as db:
        row = db.get(Contribution, result["id"])
        row.payload = {**row.payload, "gps_received_at": (now()-timedelta(days=31)).isoformat()}
        db.commit()
        assert purge_gps(db) == 1
        assert db.get(Contribution, row.id).payload.get("gps_observation")
        assert purge_gps(db, apply=True) == 1
        db.refresh(row)
        assert "gps_observation" not in row.payload and "pin_distance_m" not in row.payload
        assert row.payload["selected_point"] == proposal["selected_point"] and row.status == "needs_review" and row.version == 2
        assert purge_gps(db, apply=True) == 0
    api.cookies.set("ht_session", "test-staff-session")
    decision = {"decision": "approve", "reason": "An independent source must support publication", "version": 2}
    assert api.post(f"/v1/admin/contributions/{row.id}/decision", json=decision).status_code == 422
    assert api.post(f"/v1/admin/contributions/{row.id}/decision", json=decision | {"corroboration": "Verified the entrance in person using a separate field visit record"}).status_code == 200


def test_low_accuracy_always_needs_additional_human_evidence(api, signed_user, staff_user, proposal):
    body = {**proposal, "gps_observation": {**proposal["gps_observation"], "accuracy_m": 150}}
    result = api.post("/v1/contributions", json=body, headers={"Idempotency-Key": "low-accuracy-review"}).json()["data"]
    assert result["status"] == "needs_review"
    api.cookies.set("ht_session", "test-staff-session")
    assert api.post(f"/v1/admin/contributions/{result['id']}/decision", json={"decision": "approve", "reason": "GPS alone cannot prove this entrance", "version": 1}).json()["error"]["code"] == "INDEPENDENT_CORROBORATION_REQUIRED"


def test_additive_upgrade_preserves_legacy_records_and_references(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as connection:
        connection.execute(text("PRAGMA foreign_keys=ON"))
        connection.execute(text("CREATE TABLE locations (id VARCHAR(36) PRIMARY KEY, normalized_name VARCHAR(200) NOT NULL)"))
        connection.execute(text("INSERT INTO locations VALUES ('legacy', 'original name')"))
        ensure_location_relationships(connection)
        ensure_location_relationships(connection)
        row = connection.execute(text("SELECT normalized_name,aliases,normalized_aliases,parent_location_id,access_point_id FROM locations WHERE id='legacy'")).one()
        assert tuple(row) == ("original name", "[]", "", None, None)
        with pytest.raises(IntegrityError):
            connection.execute(text("UPDATE locations SET access_point_id='unknown' WHERE id='legacy'"))
    engine.dispose()
