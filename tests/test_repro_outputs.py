"""End-to-end tests for a completed clean-room run (`run.py repro`). They FAIL (never skip) when the run is missing, incomplete, or its outputs disagree with the committed ones."""
import json, os
import pandas as pd
import pytest
from conftest import ROOT
from src.release import repro as R, checks as K

pytestmark = pytest.mark.e2e
STATUS = os.path.join(ROOT, "repro", "run_status.json")
REQUIRED = ["verify_inputs", "ratings_project", "sim", "price_teams", "price_tier1", "players_sim", "price_players", "joint_kelly", "write_card"]


@pytest.fixture(scope="module")
def status():
    assert os.path.exists(STATUS), "no repro/run_status.json: `run.py repro` has not completed - the reproduction is incomplete (fail closed)"
    return json.load(open(STATUS))


def test_every_stage_ran_and_exited_zero(status):
    done = {s["name"]: s for s in status["stages"]}
    for name in REQUIRED:
        assert name in done, f"stage {name} did not run"
        assert done[name]["exit"] == 0, f"stage {name} exited {done[name]['exit']} (see {done[name]['log']})"


def test_ratings_and_pricing_ran_from_the_frozen_inputs_only(status):
    import subprocess, sys
    assert subprocess.call([sys.executable, os.path.join(ROOT, "scripts", "verify_inputs.py")], cwd=ROOT) == 0


def test_rebuilt_outputs_agree_with_committed_outputs_within_monte_carlo_error(status):
    res = R.compare(status["n"], status["seed"])
    assert not res["problems"], "reproduction differs from the committed outputs: " + "; ".join(res["problems"][:5])
    assert res["ratings_max_abs_diff_wins"] <= 1e-6


def test_rebuilt_final_card_equals_committed_card(status):
    base = pd.read_csv(os.path.join(ROOT, "release", "final_card.csv")); new = pd.read_csv(os.path.join(ROOT, "repro", "rebuilt_card.csv"))
    kb = set(zip(base.market, base.selection, base.side)); kn = set(zip(new.market, new.selection, new.side))
    if status["n"] == R_N0() and status["seed"] == R_SEED0():
        assert kb == kn, f"rebuilt card differs at identical N/seed: {kb ^ kn}"
        m = base.merge(new, on=["market", "selection", "side"], suffixes=("_0", "_1"))
        assert (abs(m.stake_frac_0 - m.stake_frac_1) < 1e-6).all(), "stakes differ at identical N/seed"
    else:   # reduced N: membership may differ only for bets whose shrunk edge sits within Monte Carlo error of the 3% bar (reported in repro_check.md)
        res = R.compare(status["n"], status["seed"])
        assert not [p for p in res["problems"] if "card" in p or "stake" in p], res["problems"]


def test_repro_report_says_pass(status):
    txt = open(os.path.join(ROOT, "reports", "repro_check.md"), encoding="utf-8").read()
    assert "**Result: PASS" in txt and f"N = {status['n']:,}" in txt and f"seed {status['seed']}" in txt


def R_N0():
    return int(pd.read_csv(os.path.join(ROOT, "repro", "baseline", "data__clean__sim_team_summary.csv")).n_sims.iloc[0])


def R_SEED0():
    return json.load(open(os.path.join(ROOT, "repro", "baseline", "data__clean__sim_run_meta.json")))["seed"]
