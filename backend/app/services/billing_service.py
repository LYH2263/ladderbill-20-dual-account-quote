import json
import math

from app.db import connect
from app.engines.dual_compare import dual_bill
from app.engines.peak_compare import compare_plain_vs_peak
from app.engines.tier_progressive import calc_bill
from app.repositories import accounts as accounts_repo
from app.repositories import readings as readings_repo
from app.repositories import runs as runs_repo
from app.repositories import settings as settings_repo
from app.repositories import tiers as tiers_repo


class DualInputError(Exception):
    """One side of a dual trial is invalid; detail names the failing side."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class BillingService:
    def __init__(self):
        self._conn = connect()

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def list_accounts(self):
        return accounts_repo.list_all(self._conn)

    def get_account(self, account_id: int):
        return accounts_repo.get(self._conn, account_id)

    def list_tiers(self):
        return tiers_repo.list_ordered(self._conn)

    def list_readings(self):
        return readings_repo.list_all(self._conn)

    def readings_for_account(self, account_id: int):
        return readings_repo.for_account(self._conn, account_id)

    def settings_map(self):
        return settings_repo.get_map(self._conn)

    def run_bill(self, kwh: float, peak: bool, account_id: int | None, persist: bool):
        tiers = tiers_repo.as_calc_rows(self._conn)
        pf = settings_repo.peak_factor(self._conn)
        factor = pf if peak else 1.0
        result = calc_bill(kwh, tiers, factor)
        run_id = None
        if persist:
            run_id = runs_repo.insert(
                self._conn,
                "bill",
                {"kwh": kwh, "peak": peak, "account_id": account_id},
                result,
                account_id,
            )
        return {"run_id": run_id, **result}

    def run_compare(self, kwh: float, persist: bool):
        tiers = tiers_repo.as_calc_rows(self._conn)
        pf = settings_repo.peak_factor(self._conn)
        result = compare_plain_vs_peak(kwh, tiers, pf)
        run_id = None
        if persist:
            run_id = runs_repo.insert(self._conn, "compare", {"kwh": kwh}, result, None)
        return {"run_id": run_id, **result}

    def run_dual(self, left, right, persist: bool):
        """Trial-run two accounts side by side. left/right carry account_id,
        kwh, peak. Both sides are validated before anything is calculated or
        written; the whole request fails naming the failing side."""
        for label, side in (("left", left), ("right", right)):
            zh = "左侧" if label == "left" else "右侧"
            if accounts_repo.get(self._conn, side.account_id) is None:
                raise DualInputError(404, f"{zh}({label}) 户号不存在: account_id={side.account_id}")
            if not math.isfinite(side.kwh) or side.kwh < 0:
                raise DualInputError(400, f"{zh}({label}) 电量非法: kwh={side.kwh}")
        tiers = tiers_repo.as_calc_rows(self._conn)
        pf = settings_repo.peak_factor(self._conn)
        calc = dual_bill(left.kwh, left.peak, right.kwh, right.peak, tiers, pf)
        out = {"run_ids": None, "delta": calc["delta"]}
        for label, side in (("left", left), ("right", right)):
            out[label] = {"account_id": side.account_id, "peak": side.peak, **calc[label]}
        if persist:
            run_ids = {}
            for label, side in (("left", left), ("right", right)):
                run_ids[label] = runs_repo.insert(
                    self._conn,
                    "dual",
                    {"side": label, "account_id": side.account_id, "kwh": side.kwh, "peak": side.peak},
                    out[label],
                    side.account_id,
                )
            out["run_ids"] = run_ids
        return out

    def list_history(self, limit: int = 50):
        return runs_repo.list_recent(self._conn, limit)

    def get_run(self, run_id: int):
        return runs_repo.get(self._conn, run_id)

    def dashboard_stats(self):
        accounts = accounts_repo.list_all(self._conn)
        readings = readings_repo.list_all(self._conn)
        clean = [a for a in accounts if "种子" not in a.get("name", "")]
        dirty = [a for a in accounts if "种子" in a.get("name", "")]
        return {
            "account_count": len(accounts),
            "reading_count": len(readings),
            "clean_accounts": len(clean),
            "dirty_accounts": len(dirty),
            "recent_runs": len(runs_repo.list_recent(self._conn, 5)),
        }
