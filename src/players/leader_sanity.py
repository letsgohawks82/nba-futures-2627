"""Leader-level sanity check: simulated top-5 qualified values per stat (mean over sims) vs the actual top-5 qualified per-game values 2022-2026 (58 games or NBA totals path).
Also the simulated mpg / games of the sim's top 5. data/clean/g4_leader_sanity.json"""
import json, os
import numpy as np, pandas as pd
from . import leaders as L, run_g4 as G, simgp
from .rates import table, STATS, C, STATS as ST

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def hist():
    ps = table(); out = {}
    for sn, st in ST.items():
        rows = []
        for s in range(2022, 2027):
            a = ps[ps.season == s].copy(); a["pg"] = a[st] / a.games.clip(lower=1); a = a[(a.games >= 58) | (a[st] >= L.TOTAL_ALT[sn])]
            t = a.nlargest(5, "pg"); rows.append(dict(season=s, top1=t.pg.iloc[0], top5=t.pg.mean(), mpg5=t.mpg.mean(), gp5=t.games.mean()))
        out[sn] = pd.DataFrame(rows)
    return out

def simulated(n=20000, seed=3):
    pool = G.prep_pool(); Z = np.load(os.path.join(ROOT, "sims/season_sims.npz")); rng = np.random.default_rng(seed)
    gp, ti = simgp.sim_gp(pool, {"gp": Z["gp"][:n], "teams": Z["teams"]}, rng=rng)
    R = pd.read_csv(C("g4_rate_backtest.csv")); cal = L.calib_from_backtest(R); st = L.draw_stats(pool, cal, n, rng); out = {}
    for sn in L.SN:
        ok = (gp >= L.QUAL_GAMES) | (st[sn] * gp >= L.TOTAL_ALT[sn]); v = np.where(ok, np.round(st[sn], 1), -1.0)
        idx = np.argsort(-v, 1)[:, :5]; top = np.take_along_axis(v, idx, 1); mp = pool.proj_mpg.values[idx]; g = np.take_along_axis(gp, idx, 1)
        out[sn] = dict(top1=float(top[:, 0].mean()), top5=float(top.mean()), mpg5=float(mp.mean()), gp5=float(g.mean()))
    return out

if __name__ == "__main__":
    h = hist(); s = simulated(); rows = []
    for sn in L.SN:
        rows.append(dict(stat=sn, hist_top1=h[sn].top1.mean(), sim_top1=s[sn]["top1"], hist_top5=h[sn].top5.mean(), sim_top5=s[sn]["top5"], top5_gap_pct=100 * (s[sn]["top5"] / h[sn].top5.mean() - 1), hist_mpg5=h[sn].mpg5.mean(), sim_mpg5=s[sn]["mpg5"], hist_gp5=h[sn].gp5.mean(), sim_gp5=s[sn]["gp5"]))
    D = pd.DataFrame(rows); print(D.round(2).to_string()); json.dump(dict(table=D.round(4).to_dict("records"), hist_by_season={k: v.round(3).to_dict("records") for k, v in h.items()}), open(C("g4_leader_sanity.json"), "w"), indent=1)
