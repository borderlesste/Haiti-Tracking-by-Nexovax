import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, text


def test_alembic_upgrade_and_downgrade_only_disposable_database(tmp_path):
    target = tmp_path / "migration-test.sqlite"
    env = {**os.environ, "APP_ENV": "test", "DATABASE_URL": f"sqlite:///{target}"}
    root = Path(__file__).resolve().parents[1]
    upgrade = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=root, env=env, capture_output=True, text=True)
    assert upgrade.returncode == 0, upgrade.stderr
    engine = create_engine(env["DATABASE_URL"])
    assert {"locations", "user_sessions", "api_keys", "audit_events"} <= set(inspect(engine).get_table_names())
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM territories")).scalar_one() == 721
    engine.dispose()
    downgrade = subprocess.run([sys.executable, "-m", "alembic", "downgrade", "base"], cwd=root, env=env, capture_output=True, text=True)
    assert downgrade.returncode == 0, downgrade.stderr
    engine = create_engine(env["DATABASE_URL"])
    assert "locations" not in inspect(engine).get_table_names()
    engine.dispose()
