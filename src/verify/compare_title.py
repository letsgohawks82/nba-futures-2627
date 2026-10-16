"""Run the engine in its stripped configuration and compare to the independent check (src/verify/title_check.py)."""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
import numpy as np, pandas as pd
from src.sim.inputs import build, lottery_tables
from src.sim.runner import simulate, prob

C = lambda f: os.path.join(os.path.dirname(__file__), "..", "..", "data", "clean", f)
ind = json.load(open(C("verify_title_independent.json"))); N2 = ind["N"]
lt = lottery_tables(16, 40_000)
inp = build({"_lottery_tables": lt, "_calibrate": False, "avail_on": 0.0, "tank_on": 0.0, "po_lambda": 0.0, "po_inj_prob": 0.0, "cup_on": 0.0})
r = simulate(inp, 200_000, 123, verbose=False)
teams = inp["teams"]; assert teams == ind["teams"]
rows = []
for name, key in [("title", "title"), ("conference", "conf"), ("playoffs(top10)", "po"), ("top6", "top6"), ("division", "div")]:
    pe = prob(r, {"title": "title", "conference": "conference", "playoffs(top10)": "playoffs", "top6": "top6", "division": "division"}[name]); pi = np.array(ind[key])
    se = np.sqrt(pe * (1 - pe) / 200_000 + pi * (1 - pi) / N2)
    z = (pe - pi) / np.maximum(se, 1e-9)
    rows.append(dict(market=name, max_abs_diff_pp=float(np.abs(pe - pi).max() * 100), mean_abs_diff_pp=float(np.abs(pe - pi).mean() * 100), max_abs_z=float(np.abs(z).max()),
                     sum_engine=float(pe.sum()), sum_indep=float(pi.sum()), worst_team=teams[int(np.argmax(np.abs(z)))]))
w_e = r["wins"].mean(0); w_i = np.array(ind["wins"])
rows.append(dict(market="mean wins (80-game schedule)", max_abs_diff_pp=float(np.abs(w_e - w_i).max()), mean_abs_diff_pp=float(np.abs(w_e - w_i).mean()), max_abs_z=float("nan"), sum_engine=float(w_e.sum()), sum_indep=float(w_i.sum()), worst_team=teams[int(np.argmax(np.abs(w_e - w_i)))]))
d = pd.DataFrame(rows); print(d.round(3).to_string()); d.to_csv(C("verify_title_compare.csv"), index=False)
t = pd.DataFrame({"team": teams, "engine_title": prob(r, "title"), "indep_title": ind["title"]}); t["diff_pp"] = (t.engine_title - t.indep_title) * 100
print(t.sort_values("engine_title", ascending=False).head(8).round(4).to_string())
