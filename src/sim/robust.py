"""Robustness scenarios for the Bet Card filter: base, kappa=0, kappa=1.57 (upper CI), sigma_team -10% / +10%.
Writes data/clean/sim_robust_summary.csv (team x scenario probabilities incl. confrank/seed dist) and sim_robust_wins_hist.csv (pmf of wins)."""
import json, os, sys
import numpy as np, pandas as pd
from .inputs import build, lottery_tables
from .runner import simulate, FLAGS
from .run_sim import summarize
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
KAPPA_HI = 1.57

def run(N=100_000, seed=2026):
    lt = lottery_tables(16, 200_000)
    base = build({"_lottery_tables": lt}); sig = base["par_dict"]["sigma_team"]
    scen = {"base": {}, "kappa_0": {"tank_kappa": 0.0}, "kappa_hi": {"tank_kappa": KAPPA_HI}, "sigma_lo": {"sigma_team": sig * 0.9}, "sigma_hi": {"sigma_team": sig * 1.1}}
    S_all, H_all = [], []
    for name, ov in scen.items():
        o = dict(ov); o["_lottery_tables"] = lt
        inp = build(o); r = simulate(inp, N, seed, verbose=False)      # common random numbers across scenarios
        S = summarize(r, inp); S.insert(0, "scenario", name); S_all.append(S)
        for i, t in enumerate(r["teams"]):
            c = np.bincount(r["wins"][:, i], minlength=83) / N
            H_all.append(pd.DataFrame({"scenario": name, "team": t, "wins": np.arange(83), "p": c}))
    S = pd.concat(S_all); H = pd.concat(H_all)
    base_w = S[S.scenario == "base"].set_index("team").wins_mean; bottom10 = base_w.sort_values().head(10).index.tolist()
    S["bottom10_projected"] = S.team.isin(bottom10)
    S.to_csv(os.path.join(ROOT, "data/clean/sim_robust_summary.csv"), index=False); H.to_csv(os.path.join(ROOT, "data/clean/sim_robust_wins_hist.csv"), index=False)
    json.dump(dict(bottom10_projected=bottom10, kappa_hi=KAPPA_HI, sigma_base=sig, sigma_lo=sig * 0.9, sigma_hi=sig * 1.1, N=N), open(os.path.join(ROOT, "data/clean/sim_robust_meta.json"), "w"), indent=1)
    return S, bottom10

if __name__ == "__main__":
    S, b10 = run(); print("bottom-10 projected:", b10)
    P = S.pivot(index="team", columns="scenario", values="p_playoffs"); print((P.loc[b10]).round(3).to_string())
