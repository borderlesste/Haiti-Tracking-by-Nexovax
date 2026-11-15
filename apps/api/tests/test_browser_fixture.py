import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4


def run_fixture(run_id):
    root = Path(__file__).resolve().parents[1]
    return subprocess.run([sys.executable, "-c", "import runpy; runpy.run_path('tests/browser_fixture.py', run_name='__main__')"], cwd=root, env={**os.environ, "APP_ENV": "test", "E2E_RUN_ID": run_id}, capture_output=True, text=True)


def test_e2e_fixture_rejects_path_traversal_before_database_access():
    result = run_fixture("../../outside-test-scope")
    assert result.returncode != 0 and "UUID" in result.stderr


def test_e2e_fixture_refuses_to_modify_an_existing_database():
    root = Path(__file__).resolve().parents[1]
    run_id = str(uuid4())
    folder = root / ".runtime" / ("e2e-" + run_id)
    assert folder.resolve().is_relative_to((root / ".runtime").resolve())
    folder.mkdir(exist_ok=False)
    target = folder / "test.db"
    try:
        target.write_bytes(b"preserve-existing-data")
        result = run_fixture(run_id)
        assert result.returncode != 0 and "fresh database" in result.stderr
        assert target.read_bytes() == b"preserve-existing-data"
    finally:
        target.unlink()
        folder.rmdir()
