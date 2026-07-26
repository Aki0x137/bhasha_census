import pytest

from kyc_bot.flow.record import CensusRecord, Household, Person
from kyc_bot.storage import census_db


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    monkeypatch.setenv("CENSUS_DB_PATH", str(tmp_path / "census.db"))
    census_db.init_db()
    yield


def _rec(name="Aa Bb", match=1.0):
    return CensusRecord(
        consent=True,
        household=Household(size=2, ownership="Owned", assets=["TV", "Car"]),
        head=Person(
            name=name, age=30, sex="Male", marital="Married",
            id_masked="•••• •••• 1234", id_name=name, id_name_match=match, liveness="completed",
        ),
    )


def test_insert_and_list(tmp_db):
    rid = census_db.insert_record(_rec(), user_id="u1")
    rows = census_db.list_records()
    assert len(rows) == 1
    r = rows[0]
    assert r["id"] == rid
    assert r["head_name"] == "Aa Bb"
    assert r["assets"] == ["TV", "Car"]
    assert r["status"] == "pending"
    assert r["id_masked"].endswith("1234")


def test_status_and_counts(tmp_db):
    rid = census_db.insert_record(_rec())
    assert census_db.set_status(rid, "approved") is True
    assert census_db.counts() == {"pending": 0, "approved": 1, "rejected": 0}
    assert census_db.list_records(status="approved")[0]["id"] == rid


def test_needs_review_flag_persisted(tmp_db):
    census_db.insert_record(_rec(name="Typed Name", match=0.3))  # low match -> needs review
    assert census_db.list_records()[0]["needs_review"] == 1


def test_invalid_status_rejected(tmp_db):
    rid = census_db.insert_record(_rec())
    with pytest.raises(ValueError):
        census_db.set_status(rid, "bogus")
