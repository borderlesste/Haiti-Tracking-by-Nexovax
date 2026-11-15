"""Pinned CNIGS/OCHA catalog; the source archive is never edited in place."""
import hashlib
import json
import zipfile
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def catalog():
    folder = Path(__file__).resolve().parent.parent / "data"
    source = json.loads((folder / "SOURCE.json").read_text(encoding="utf-8"))
    archive = folder / "hti-cod-ab.geojson.zip"
    if hashlib.sha256(archive.read_bytes()).hexdigest() != source["resource_sha256"]:
        raise RuntimeError("Territory source checksum does not match its manifest")
    records = []
    with zipfile.ZipFile(archive) as package:
        for level, kind, expected in [(0, "country", 1), (1, "department", 10), (2, "commune", 140), (3, "section", 570)]:
            features = json.loads(package.read(f"hti_admin{level}.geojson"))["features"]
            if len(features) != expected:
                raise RuntimeError("Unexpected territory catalog feature count")
            for feature in features:
                props = feature["properties"]
                name = props.get(f"adm{level}_name1") or props[f"adm{level}_name"]
                aliases = sorted({props[f"adm{level}_pcode"], *(props.get(f"adm{level}_name{suffix}") for suffix in ("", "1", "2", "3"))} - {None, name})
                records.append({"id": props[f"adm{level}_pcode"], "parent_id": props[f"adm{level-1}_pcode"] if level else None, "name": name, "level": kind, "aliases": aliases, "country_code": "HT", "source_version": f"CNIGS-OCHA-COD-AB-{props['version']}-valid-{props['valid_on']}", "source_url": source["dataset"], "license": source["license_url"]})
    identifiers = {record["id"] for record in records}
    if len(identifiers) != len(records) or any(record["parent_id"] and record["parent_id"] not in identifiers for record in records):
        raise RuntimeError("Duplicate or orphan territory identifier")
    return tuple(records)


@lru_cache(maxsize=32)
def boundary_for(identifier):
    record = next((row for row in catalog() if row["id"] == identifier), None)
    if not record:
        return None
    level = {"country": 0, "department": 1, "commune": 2, "section": 3}[record["level"]]
    with zipfile.ZipFile(Path(__file__).resolve().parent.parent / "data" / "hti-cod-ab.geojson.zip") as package:
        features = json.loads(package.read(f"hti_admin{level}.geojson"))["features"]
        return next(feature["geometry"] for feature in features if feature["properties"][f"adm{level}_pcode"] == identifier)
