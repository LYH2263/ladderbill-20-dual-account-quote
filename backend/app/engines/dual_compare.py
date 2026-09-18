"""Dual-account parallel trial: two independent bills plus their delta."""

from app.engines.tier_progressive import calc_bill


def dual_bill(
    left_kwh: float,
    left_peak: bool,
    right_kwh: float,
    right_peak: bool,
    tiers: list[dict],
    peak_factor: float,
) -> dict:
    """Run two independent tier bills; delta = right total - left total."""
    left = calc_bill(left_kwh, tiers, peak_factor if left_peak else 1.0)
    right = calc_bill(right_kwh, tiers, peak_factor if right_peak else 1.0)
    return {
        "left": left,
        "right": right,
        "delta": round(right["total"] - left["total"], 2),
    }
