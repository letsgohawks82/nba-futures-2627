"""Bet Card robustness filter: a bet on a bottom-10-projected team must keep positive EV under kappa=0 AND kappa=1.57, and under sigma_team -10%/+10%.
ev_by_scenario: dict scenario -> EV per $1 for the same bet (computed from sim_robust_summary / wins hist)."""
import json, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
META = json.load(open(os.path.join(ROOT, "data/clean/sim_robust_meta.json")))
REQUIRED = ("kappa_0", "kappa_hi", "sigma_lo", "sigma_hi")

def passes(team, ev_by_scenario, apply_sigma_to_all=False):
    """Returns (ok, reason). Base EV condition is checked separately by the Bet Card."""
    bottom = team in META["bottom10_projected"]
    need = []
    if bottom:
        need = list(REQUIRED)
    elif apply_sigma_to_all:
        need = ["sigma_lo", "sigma_hi"]
    for s in need:
        if ev_by_scenario.get(s, -1.0) <= 0:
            return False, f"EV<=0 under {s}"
    return True, "ok"
