import runpy
from pathlib import Path


def test_secret_review_is_portable_and_never_accepts_a_changed_value():
    check = runpy.run_path(str(Path(__file__).resolve().parents[3] / "scripts/check-secrets.py"))["new_findings"]
    finding = {"type": "Secret Keyword", "hashed_secret": "synthetic-hash", "line_number": 10, "is_secret": False}
    baseline = {"results": {"apps\\api\\test.py": [finding]}}
    moved = {**finding, "line_number": 20}
    assert check({"results": {"apps/api/test.py": [moved]}}, baseline) == []
    assert check({"results": {"apps/api/test.py": [{**moved, "hashed_secret": "new-hash"}]}}, baseline) == [("apps/api/test.py", 20)]
