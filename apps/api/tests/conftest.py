from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.core import Settings, passwords
from app.main import create_app
from app.models import User, UserSession, now


@pytest.fixture
def api(tmp_path):
    settings = Settings(env="test", database_url=f"sqlite:///{tmp_path / 'test.db'}", runtime_dir=tmp_path)
    app = create_app(settings)
    with TestClient(app) as client:
        client.headers["X-CSRF-Token"] = client.get("/v1/auth/csrf").json()["data"]["csrf_token"]
        yield client


@pytest.fixture
def signed_user(api):
    with api.app.state.Session() as session:
        user = User(email="contributor@example.org", display_name="Contributor", password_hash=passwords.hash("correct-horse-battery"), email_verified=True)
        session.add(user)
        session.flush()
        session.add(UserSession(user_id=user.id, token_hash=api.app.state.settings.digest("test-user-session"), expires_at=now()+timedelta(hours=1)))
        session.commit()
    api.cookies.set("ht_session", "test-user-session")
    return user


@pytest.fixture
def staff_user(api, signed_user):
    with api.app.state.Session() as session:
        staff = User(email="staff@example.org", display_name="Moderator", password_hash=passwords.hash("correct-horse-battery"), email_verified=True, role="admin")
        session.add(staff)
        session.flush()
        session.add(UserSession(user_id=staff.id, token_hash=api.app.state.settings.digest("test-staff-session"), expires_at=now()+timedelta(hours=1), mfa_verified=True))
        session.commit()
    return staff


@pytest.fixture
def proposal():
    return {"mode": "on_site", "type": "business", "name": "Commerce test", "territory_id": "HT0112", "address": {"neighborhood": "Delmas", "reference": "A public reference"}, "selected_point": {"latitude": 18.54, "longitude": -72.3}, "gps_observation": {"latitude": 18.54002, "longitude": -72.30001, "accuracy_m": 18.5, "captured_at": now().isoformat()}, "source_declaration_accepted": True}
