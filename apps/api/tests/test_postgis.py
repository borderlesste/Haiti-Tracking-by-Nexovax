"""Spatial and database permissions checks, on a disposable CI database only."""
import os
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker

from app.core import Settings, migrate, normalize, public_location, seed_territories
from app.models import AuditEvent, Location, User


def test_database_rejects_parent_cycles_and_indexes_aliases(postgis):
    with sessionmaker(postgis)() as db:
        first = Location(public_code="HT-NXV-PARENT", name="Parent", normalized_name="parent", type="public", territory_id="HT0112", latitude=18.54, longitude=-72.3, address={})
        db.add(first)
        db.flush()
        second = Location(public_code="HT-NXV-CHILD", name="Child", normalized_name="child", type="business", territory_id="HT0112", latitude=18.54, longitude=-72.3, address={}, parent_location_id=first.id)
        db.add(second)
        db.commit()
        with pytest.raises(DBAPIError):
            db.execute(text("UPDATE locations SET parent_location_id=:child WHERE id=:parent"), {"child": second.id, "parent": first.id})
        db.rollback()
        assert db.execute(text("SELECT count(*) FROM pg_indexes WHERE schemaname=current_schema() AND indexname='ix_locations_aliases_trgm'")).scalar_one() == 1


def test_runtime_role_has_explicit_rls_and_append_only_access(postgis, monkeypatch):
    role = "test_haiti_runtime_" + uuid4().hex[:12]
    denied = "test_haiti_denied_" + uuid4().hex[:12]
    with postgis.begin() as connection:
        schema = connection.execute(text("SELECT current_schema()")).scalar_one()
        connection.execute(text(f'CREATE ROLE "{role}" NOLOGIN NOSUPERUSER NOBYPASSRLS'))
        connection.execute(text(f'CREATE ROLE "{denied}" NOLOGIN NOSUPERUSER NOBYPASSRLS'))
        connection.execute(text(f'GRANT USAGE ON SCHEMA "{schema}" TO "{role}", "{denied}"'))
    try:
        monkeypatch.setenv("BACKEND_DB_ROLE", role)
        migrate(postgis)
        with postgis.begin() as connection:
            connection.execute(text(f'SET LOCAL ROLE "{role}"'))
            assert connection.execute(text("SELECT count(*) FROM territories")).scalar_one() > 0
            assert connection.execute(text("SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname=current_user")).scalar_one() is False
            connection.execute(text("INSERT INTO audit_events (id,action,subject_id,metadata_sanitized,created_at) VALUES ('runtime-test','test.runtime','test','{}',now())"))
        with postgis.begin() as connection:
            connection.execute(text(f'SET LOCAL ROLE "{role}"'))
            with pytest.raises(DBAPIError):
                connection.execute(text("UPDATE audit_events SET action='tampered' WHERE id='runtime-test'"))
        with postgis.begin() as connection:
            connection.execute(text(f'SET LOCAL ROLE "{denied}"'))
            with pytest.raises(DBAPIError):
                connection.execute(text("SELECT count(*) FROM users"))
    finally:
        # These roles were created by this test, and never belong to a production database.
        with postgis.begin() as connection:
            connection.execute(text(f'DROP OWNED BY "{role}", "{denied}"'))
            connection.execute(text(f'DROP ROLE "{role}", "{denied}"'))


def test_concurrent_publication_rechecks_duplicates(postgis, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from fastapi.testclient import TestClient
    from app.core import passwords
    from app.main import create_app
    from app.models import Contribution, UserSession, now

    monkeypatch.setenv("DATABASE_AUTO_CREATE", "false")
    with postgis.connect() as connection:
        schema = connection.execute(text("SELECT current_schema()")).scalar_one()
    url = postgis.url.update_query_dict({"options": f"-csearch_path={schema},public"})
    settings = Settings(env="test", database_url=url.render_as_string(hide_password=False))
    app = create_app(settings)
    with sessionmaker(postgis, expire_on_commit=False)() as session:
        author = User(email="author@concurrency.invalid", display_name="Test author", password_hash=passwords.hash("concurrency-test-password"), email_verified=True)
        staff = User(email="staff@concurrency.invalid", display_name="Test staff", password_hash=passwords.hash("concurrency-test-password"), email_verified=True, role="moderator")
        session.add_all([author, staff])
        session.flush()
        payload = {"mode": "on_site", "name": "Same public test place", "type": "business", "territory_id": "HT0112", "selected_point": {"latitude": 18.54, "longitude": -72.3}, "address": {"reference": "Synthetic concurrency test"}, "source_declaration_accepted": True}
        proposals = [Contribution(author_user_id=author.id, payload=payload, status="submitted") for _ in range(2)]
        session.add_all(proposals)
        session.add(UserSession(user_id=staff.id, token_hash=settings.digest("concurrency-staff"), expires_at=now()+timedelta(hours=1), mfa_verified=True))
        session.commit()
        identifiers = [p.id for p in proposals]
    with TestClient(app) as client:
        client.cookies.set("ht_session", "concurrency-staff")
        client.headers["X-CSRF-Token"] = client.get("/v1/auth/csrf").json()["data"]["csrf_token"]
        mismatch = {**payload, "selected_point": {"latitude": 19.75, "longitude": -72.2}, "gps_observation": {"latitude": 19.75, "longitude": -72.2, "accuracy_m": 15, "captured_at": now().isoformat()}}
        result = client.post("/v1/contributions", json=mismatch, headers={"Idempotency-Key": "boundary-mismatch-test"})
        assert result.status_code == 201
        assert "territory_boundary_mismatch" in result.json()["data"]["payload"]["quality_flags"]
        def approve(identifier):
            return client.post(f"/v1/admin/contributions/{identifier}/decision", json={"decision": "approve", "reason": "Reviewed synthetic concurrency test", "version": 1}).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            codes = list(pool.map(approve, identifiers))
        with sessionmaker(postgis, expire_on_commit=False)() as session:
            places = [Location(public_code=f"HT-NXV-MERGE{i}", name=f"Merge test {i}", normalized_name=f"merge test {i}", type="business", territory_id="HT0112", latitude=18.54, longitude=-72.3, address={}) for i in range(2)]
            session.add_all(places)
            session.commit()
            merges = [(places[0].id, places[1].public_code), (places[1].id, places[0].public_code)]
        def merge(pair):
            return client.post(f"/v1/admin/locations/{pair[0]}/merge", json={"canonical_code": pair[1], "reason": "Synthetic reciprocal merge concurrency check"}).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            merge_codes = list(pool.map(merge, merges))
        assert sorted(merge_codes) == [200, 422]
        resolved = [client.get(f"/v1/locations/HT-NXV-MERGE{i}").json()["data"]["code"] for i in range(2)]
        assert resolved[0] == resolved[1]
    assert sorted(codes) == [200, 409]
    with sessionmaker(postgis)() as session:
        assert session.query(Location).filter(Location.normalized_name == "same public test place").count() == 1


@pytest.fixture
def postgis(monkeypatch):
    raw = os.getenv("TEST_DATABASE_URL")
    if not raw:
        pytest.skip("TEST_DATABASE_URL not configured; PostGIS checks run in dedicated CI database")
    url = make_url(raw)
    if url.get_backend_name() != "postgresql" or "test" not in (url.database or "").lower():
        pytest.fail("PostGIS tests require an explicitly named disposable test database")
    schema = "test_haiti_" + uuid4().hex
    admin_engine = create_engine(raw)
    with admin_engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    scoped = create_engine(raw, connect_args={"options": f"-csearch_path={schema},public"})
    monkeypatch.delenv("BACKEND_DB_ROLE", raising=False)
    try:
        migrate(scoped)
        with sessionmaker(scoped, expire_on_commit=False)() as session:
            seed_territories(session)
        yield scoped
    finally:
        scoped.dispose()
        with admin_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin_engine.dispose()


def test_postgis_generated_geography_and_meter_query(postgis):
    with sessionmaker(postgis, expire_on_commit=False)() as session:
        session.add_all([
            Location(public_code="HT-NXV-TEST1", name="Public sample", normalized_name="public sample", type="business", territory_id="HT0112", latitude=18.54, longitude=-72.3, address={}),
            Location(public_code="HT-NXV-TEST2", name="Private sample", normalized_name="private sample", type="residence", territory_id="HT0112", latitude=18.54001, longitude=-72.3, address={}, public_visibility="private"),
        ])
        session.commit()
        rows = session.execute(text("SELECT public_code,ST_Distance(point,ST_SetSRID(ST_MakePoint(:lon,:lat),4326)::geography) AS meters FROM locations WHERE status='active' AND public_visibility='public' AND type IN ('public','business','landmark','road','access') AND ST_DWithin(point,ST_SetSRID(ST_MakePoint(:lon,:lat),4326)::geography,:radius) ORDER BY meters"), {"lat": 18.54, "lon": -72.3, "radius": 200}).all()
        assert len(rows) == 1 and rows[0].public_code == "HT-NXV-TEST1" and rows[0].meters < .01
        definition = session.execute(text("SELECT indexdef FROM pg_indexes WHERE schemaname=current_schema() AND indexname='ix_locations_point_gist'")).scalar_one()
        assert "gist" in definition.lower()
        assert session.execute(text("SELECT relrowsecurity FROM pg_class WHERE oid='locations'::regclass")).scalar_one() is True


def test_postgres_audit_is_append_only(postgis):
    with sessionmaker(postgis, expire_on_commit=False)() as session:
        row = AuditEvent(action="test.event", subject_id="test")
        session.add(row)
        session.commit()
        with pytest.raises(DBAPIError):
            session.execute(text("UPDATE audit_events SET action='modified' WHERE id=:id"), {"id": row.id})
            session.commit()
        session.rollback()
        assert session.get(AuditEvent, row.id).action == "test.event"


def test_geocode_commune_filter_and_reverse_boundaries(postgis, monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import create_app
    from app.models import ApiKey, DeveloperApp, now
    monkeypatch.setenv("DATABASE_AUTO_CREATE", "false")
    with postgis.connect() as connection:
        schema = connection.execute(text("SELECT current_schema()")).scalar_one()
    url = postgis.url.update_query_dict({"options": f"-csearch_path={schema},public"})
    settings = Settings(env="test", database_url=url.render_as_string(hide_password=False))
    app = create_app(settings)
    with sessionmaker(postgis)() as session:
        owner = User(email="reverse-test@example.invalid", display_name="Reverse test", password_hash="not-a-login-fixture", email_verified=True)
        session.add(owner)
        session.flush()
        developer_app = DeveloperApp(owner_id=owner.id, name="Boundary test")
        session.add(developer_app)
        session.flush()
        session.add(ApiKey(app_id=developer_app.id, prefix="synthetic-reverse", secret_hash=settings.digest("synthetic-reverse-key"), expires_at=now()+timedelta(hours=1)))
        for code, territory in [("HT-NXV-TESTA", "HT0112"), ("HT-NXV-TESTB", "HT0111")]:
            session.add(Location(public_code=code, name="Named place", normalized_name="named place", type="public", territory_id=territory, latitude=18.54, longitude=-72.3, address={}))
        session.commit()
    with TestClient(app) as client:
        client.headers["Authorization"] = "Bearer synthetic-reverse-key"
        filtered = client.get("/v1/geocode?q=named&commune_id=HT0112").json()["data"]
        assert [row["code"] for row in filtered] == ["HT-NXV-TESTA"]
        assert client.get("/v1/geocode?q=named&commune_id=HT01").status_code == 422
        result = client.get("/v1/reverse?lat=18.54&lon=-72.3")
        assert result.status_code == 200, result.text
        data = result.json()["data"]
        assert data["territory_boundary_available"] is True
        assert data["administrative_area"]["country"]["id"] == "HT"
        assert data["administrative_area"]["department"]["name"] == "Ouest"
        assert data["administrative_area"].get("commune")
        assert "gps_observation" not in result.text
        outside = client.get("/v1/reverse?lat=0&lon=0").json()["data"]
        assert outside["administrative_area"] is None and outside["public_places"] == []
