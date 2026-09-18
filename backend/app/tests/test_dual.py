import os
import tempfile

os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="ladderbill-test-"))

import pytest

from app import seed
from app.engines.dual_compare import dual_bill
from app.services.billing_service import BillingService, DualInputError

TIERS = [{"up_to": 180, "price": 0.52}, {"up_to": 260, "price": 0.62}, {"up_to": None, "price": 0.82}]


class Side:
    """Attribute stand-in for the DualSide schema (service is duck-typed)."""

    def __init__(self, account_id, kwh, peak=False):
        self.account_id = account_id
        self.kwh = kwh
        self.peak = peak


@pytest.fixture()
def svc():
    seed.init_db()
    with BillingService() as s:
        yield s


def test_dual_engine_delta_is_right_minus_left():
    r = dual_bill(120, False, 400, True, TIERS, 1.2)
    assert r["left"]["total"] == 62.40
    assert r["right"]["total"] == 309.60
    assert r["delta"] == 247.20


def test_dual_engine_peak_switch_is_per_side():
    r = dual_bill(400, True, 400, False, TIERS, 1.2)
    assert r["left"]["peak_factor"] == 1.2
    assert r["right"]["peak_factor"] == 1.0
    assert r["delta"] == -51.60


def test_dual_service_returns_both_sides_and_delta(svc):
    r = svc.run_dual(Side(1, 120), Side(2, 400, True), persist=False)
    assert r["run_ids"] is None
    assert r["left"]["account_id"] == 1
    assert r["left"]["total"] == 62.40
    assert len(r["left"]["segments"]) == 1
    assert r["right"]["account_id"] == 2
    assert r["right"]["total"] == 309.60
    assert len(r["right"]["segments"]) == 3
    assert r["delta"] == 247.20


def test_dual_service_trial_writes_nothing(svc):
    before = len(svc.list_history(1000))
    svc.run_dual(Side(1, 120), Side(2, 400), persist=False)
    assert len(svc.list_history(1000)) == before


def test_dual_service_unknown_account_names_side(svc):
    with pytest.raises(DualInputError) as ei:
        svc.run_dual(Side(1, 100), Side(999, 100), persist=False)
    assert ei.value.status_code == 404
    assert "right" in ei.value.detail


def test_dual_service_invalid_kwh_names_side(svc):
    with pytest.raises(DualInputError) as ei:
        svc.run_dual(Side(1, -5), Side(2, 100), persist=False)
    assert ei.value.status_code == 400
    assert "left" in ei.value.detail


def test_dual_service_failed_request_writes_nothing(svc):
    before = len(svc.list_history(1000))
    with pytest.raises(DualInputError):
        svc.run_dual(Side(1, 100), Side(999, 100), persist=True)
    assert len(svc.list_history(1000)) == before


def test_dual_service_persist_writes_two_runs(svc):
    before = len(svc.list_history(1000))
    r = svc.run_dual(Side(1, 120), Side(2, 400, True), persist=True)
    ids = r["run_ids"]
    assert ids["left"] != ids["right"]
    rows = svc.list_history(1000)
    assert len(rows) == before + 2
    by_id = {row["id"]: row for row in rows}
    assert by_id[ids["left"]]["kind"] == "dual"
    assert by_id[ids["left"]]["account_id"] == 1
    assert by_id[ids["right"]]["kind"] == "dual"
    assert by_id[ids["right"]]["account_id"] == 2
