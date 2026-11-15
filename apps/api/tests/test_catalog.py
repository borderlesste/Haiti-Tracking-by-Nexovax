from collections import Counter
from sqlalchemy import select
from app.catalog import catalog
from app.models import Territory


def test_pinned_catalog_is_versioned_complete_and_parent_linked(api):
    records = catalog()
    assert Counter(row["level"] for row in records) == {"country": 1, "department": 10, "commune": 140, "section": 570}
    by_id = {row["id"]: row for row in records}
    assert by_id["HT0112"]["name"] == "Delmas"
    assert by_id["HT0112"]["parent_id"] == "HT01"
    assert by_id["HT01"]["name"] == "Ouest"
    assert all("2018-11-29" in row["source_version"] and "creativecommons.org" in row["license"] for row in records)
    with api.app.state.Session() as session:
        assert len(session.scalars(select(Territory).where(Territory.active == True)).all()) == 721
    cursor = None
    identifiers = []
    while True:
        params = {"level": "commune", "limit": 50}
        if cursor:
            params["cursor"] = cursor
        result = api.get("/v1/territories", params=params).json()
        assert len(result["data"]) <= 50
        identifiers.extend(row["id"] for row in result["data"])
        cursor = result["pagination"]["next_cursor"]
        if not cursor:
            break
    assert len(set(identifiers)) == len(identifiers) == 140
    children = api.get("/v1/territories/HT01/children").json()["data"]
    assert {r["id"] for r in children} >= {"HT0111", "HT0112", "HT0114"}
    assert api.get("/v1/territories?limit=100").status_code == 422
