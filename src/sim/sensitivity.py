import sys, numpy as np, pandas as pd
from .inputs import build, lottery_tables
from .runner import simulate, prob
lt = lottery_tables(16, 100_000); base = build({"_lottery_tables": lt, "_calibrate": False})["par_dict"]
cases = {"base": {}, "sigma_team 3.15 (-10%)": {"sigma_team": base["sigma_team"] * 0.9}, "sigma_team 3.85 (+10%)": {"sigma_team": base["sigma_team"] * 1.1}, "HCA -0.5": {"HCA": base["HCA"] - 0.5}, "HCA +0.5": {"HCA": base["HCA"] + 0.5},
         "tank kappa 0": {"tank_kappa": 0.0}, "tank kappa 1.57 (upper CI)": {"tank_kappa": 1.57}, "playoff adj lambda 0": {"po_lambda": 0.0}, "playoff adj lambda 1.0": {"po_lambda": 1.0},
         "playoff adj lambda 0.32": {"po_lambda": 0.32}, "playoff adj lambda 0.80": {"po_lambda": 0.80}, "playoff inj off": {"po_inj_prob": 0.0}, "cup semis neutral (user spec)": {"cup_semis_neutral": 1.0},
         "cup 0 cross-conf (user spec)": {"cup_cross_games": 0.0}, "availability draws off": {"avail_on": 0.0}, "LAC+TOR own-pick toggle": {"rules_override": {"LAC": (-1, -1.0), "TOR": (-1, -1.0)}}}
rows = []
for k, ov in cases.items():
    o = dict(ov); o["_lottery_tables"] = lt; o["_cal_n"] = 12_000; o["_cal_iters"] = 5
    inp = build(o); r = simulate(inp, 60000, 31, verbose=False)
    for i, t in enumerate(r["teams"]):
        rows.append(dict(case=k, team=t, wins=r["wins"][:, i].mean(), p_po=prob(r, "playoffs")[i], p_title=prob(r, "title")[i], p_div=prob(r, "division")[i], p_cup=prob(r, "cup")[i], pick=r["pick"][:, i].mean()))
    print(k, flush=True)
pd.DataFrame(rows).to_csv("data/clean/sim_sensitivity.csv", index=False)
