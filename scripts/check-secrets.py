"""Fail CI on unreviewed detector findings without printing credential values."""
import json
from pathlib import Path
import subprocess
import sys


def fingerprint(filename, finding):
    return filename.replace("\\", "/"), finding["type"], finding["hashed_secret"]


def new_findings(current, baseline):
    reviewed = {fingerprint(name, item) for name, items in baseline["results"].items() for item in items if item.get("is_secret") is False}
    return [(name, item["line_number"]) for name, items in current["results"].items() for item in items if fingerprint(name, item) not in reviewed]


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    scan = subprocess.run([sys.executable, "-m", "detect_secrets", "scan", "--no-verify", "--exclude-files", r"(^|[\\/])secrets-scan\.json$"], cwd=root, capture_output=True, text=True, check=False)
    if scan.returncode:
        raise SystemExit("Secret detector failed; no scan contents were printed.")
    findings = new_findings(json.loads(scan.stdout), json.loads((root / "docs/secrets-scan.json").read_text(encoding="utf-8")))
    for name, line in findings:
        print(f"Unreviewed secret candidate: {name}:{line}")
    print(f"Secret scan: {len(findings)} unreviewed candidates. Values remain redacted.")
    raise SystemExit(bool(findings))
