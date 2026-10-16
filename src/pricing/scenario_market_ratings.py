"""Scenario for the Toronto Atlantic / East bets: set NYK and PHI to their MARKET-IMPLIED expected wins (book line + fair-prob median), zero-sum rebalance the other 28 teams, re-simulate
(100k sims, mean-matched) and re-draw parameter uncertainty. The question: does the TOR edge survive when TOR's two division rivals are no longer 6-7 wins below the book,
i.e. with the Kawhi / Dick roster change as the only remaining driver. Outputs data/clean/scenario_nyk_phi_market.json (+ param draws npz)."""
import json, os, sys
import numpy as np, pandas as pd
from ..sim.inputs import build, lottery_tables, TEAM_LIST, IDX
from ..sim.runner import simulate, FLAGS
from . import param_draws as PD

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
C = lambda f: os.path.join(ROOT, "data", "clean", f)
TEAMS_SET = {"NYK": None, "PHI": None}


def shift_vector():
    W = pd.read_csv(C("model_vs_market_wins_table.csv"), index_col=0); tp = pd.read_csv(C("team_projection_2027.csv")).set_index("abbr").loc[TEAM_LIST]
    k = json.load(open(os.path.join(ROOT, "params/provenance.json")))["k_wins_per_srs"]["value"]; dw = np.zeros(30)
    for t in TEAMS_SET: dw[IDX[t]] = W.loc[t, "mkt_median"] - tp.pred_wins[t]
    others = [i for i in range(30) if TEAM_LIST[i] not in TEAMS_SET]; dw[others] = -dw.sum() / len(others)
    return dw / k, dw


def main(M=40, N=15_000):
    sh, dw = shift_vector(); lt = lottery_tables(16, 150_000)
    inp = build({"_lottery_tables": lt, "srs_shift": sh}); r = simulate(inp, 100_000, 4242, verbose=False)
    p = dict(div_TOR=float(((r["flags"][:, IDX["TOR"]] & 4) > 0).mean()), conf_TOR=float(((r["flags"][:, IDX["TOR"]] & 8) > 0).mean()), wins_TOR=float(r["wins"][:, IDX["TOR"]].mean()),
             wins_NYK=float(r["wins"][:, IDX["NYK"]].mean()), wins_PHI=float(r["wins"][:, IDX["PHI"]].mean()), div_NYK=float(((r["flags"][:, IDX["NYK"]] & 4) > 0).mean()), div_PHI=float(((r["flags"][:, IDX["PHI"]] & 4) > 0).mean()),
             div_BOS=float(((r["flags"][:, IDX["BOS"]] & 4) > 0).mean()), div_BKN=float(((r["flags"][:, IDX["BKN"]] & 4) > 0).mean()))
    PD.run(M, N, 123, srs_shift=sh, out_name="param_draws_nyk_phi.npz")
    D = np.load(C("param_draws_nyk_phi.npz")); t = IDX["TOR"]
    ci = dict(div_lo=float(np.percentile(D["division"][:, t], 10)), div_hi=float(np.percentile(D["division"][:, t], 90)), conf_lo=float(np.percentile(D["conference"][:, t], 10)), conf_hi=float(np.percentile(D["conference"][:, t], 90)))
    out = dict(win_shift_by_team={TEAM_LIST[i]: float(dw[i]) for i in range(30)}, point=p, ci=ci)
    json.dump(out, open(C("scenario_nyk_phi_market.json"), "w"), indent=1); return out


if __name__ == "__main__":
    print(json.dumps(main(), indent=1))
