"""Synthetic encrypted dump/restore smoke test on the task's disposable local PostgreSQL."""
import json
import subprocess
from pathlib import Path
from uuid import uuid4
import psycopg
from cryptography.fernet import Fernet
from sqlalchemy import text
from app.core import Settings, database, migrate, normalize, seed_territories
from app.models import AuditEvent, Location

container = "haiti_tracking_pg_verify_20261114"
suffix = uuid4().hex[:10]
source, restored = f"haiti_backup_test_{suffix}", f"haiti_restore_test_{suffix}"
with psycopg.connect("host=127.0.0.1 port=55432 user=haiti_verify dbname=postgres client_encoding=UTF8", autocommit=True) as connection:
    for name in (source, restored):
        # Names are generated here, never supplied by an external caller.
        connection.execute(f'CREATE DATABASE "{name}" ENCODING \'UTF8\' TEMPLATE template0')
settings = Settings(env="test", database_url=f"postgresql+psycopg://haiti_verify@127.0.0.1:55432/{source}")
engine, Session = database(settings)
migrate(engine)
with Session() as session:
    seed_territories(session)
    session.add(Location(public_code="HT-NXV-RESTORE-TEST", name="Synthetic restore fixture", normalized_name=normalize("Synthetic restore fixture"), type="business", territory_id="HT0112", latitude=18.54, longitude=-72.3, address={"reference": "Test data only"}))
    session.add(AuditEvent(action="test.backup", subject_id="synthetic"))
    session.commit()
engine.dispose()
prefix = ["wsl", "-d", "Ubuntu", "--", "docker", "exec", container]
dump = subprocess.run([*prefix, "pg_dump", "-h", "127.0.0.1", "-U", "haiti_verify", "-d", source, "-Fc", "--no-owner"], capture_output=True, check=True).stdout
cipher = Fernet(Fernet.generate_key())
encrypted = cipher.encrypt(dump)
target = Path(".runtime/backups")
target.mkdir(parents=True, exist_ok=True)
(target / f"{source}.dump.enc").write_bytes(encrypted)
subprocess.run(["wsl", "-d", "Ubuntu", "--", "docker", "exec", "-i", container, "pg_restore", "-h", "127.0.0.1", "-U", "haiti_verify", "-d", restored, "--no-owner", "--exit-on-error"], input=cipher.decrypt(encrypted), capture_output=True, check=True)
restored_settings = Settings(env="test", database_url=f"postgresql+psycopg://haiti_verify@127.0.0.1:55432/{restored}")
engine, _ = database(restored_settings)
with engine.connect() as connection:
    assert connection.execute(text("SELECT count(*) FROM territories")).scalar_one() == 721
    assert connection.execute(text("SELECT public_code FROM locations")).scalar_one() == "HT-NXV-RESTORE-TEST"
    assert connection.execute(text("SELECT count(*) FROM audit_events WHERE action='test.backup'")).scalar_one() == 1
    assert connection.execute(text("SELECT ST_Distance(point,ST_SetSRID(ST_MakePoint(-72.3,18.54),4326)::geography) FROM locations")).scalar_one() < .01
    assert connection.execute(text("SELECT count(*) FROM pg_trigger WHERE tgname='audit_append_only'")).scalar_one() == 1
engine.dispose()
report = {"result": "passed", "data": "synthetic only", "catalog_records_restored": 721, "location_code_preserved": True, "audit_and_spatial_column_restored": True, "encrypted_archive": True, "test_key_retained": False, "limitation": "One-process test key only; production key custody, retention and scheduled off-site backups remain operational requirements."}
Path("../../docs/backup-roundtrip.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report))
