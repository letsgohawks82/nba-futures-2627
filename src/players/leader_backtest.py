"""Calibration of the stat-leader probability engine on 2019-2026: leave-one-season-out calibration, previous-season minutes, ACTUAL games for qualification.
Pools the six stats; reports reliability by probability bucket and the log score of the actual leader. Players outside the top-30 predicted get probability 0 (can win -> 'missed')."""
import json
import numpy as np, pandas as pd
from .rates import table, STATS, C
from . import leaders as L

def run(n=20000, seed=5, sd_scale=1.0):
    R = pd.read_csv(C("g4_rate_backtest.csv")); ps = table(); rng = np.random.default_rng(seed); rows = []
    for s in sorted(R.season.unique()):
        cal = L.calib_from_backtest(R[R.season != s])
        act = ps[ps.season == s].set_index("bbref_id")
        for sn, st in STATS.items():
            g = R[(R.season == s) & (R.stat == sn)].reset_index(drop=True)
            mu = L.calibrated_pred(g.pred.values, cal[sn]); sd = cal[sn]["sd"] * sd_scale
            v = mu[None, :] * np.exp(sd * rng.standard_normal((n, len(g))) - 0.5 * sd * sd)
            gp = np.repeat(g.games.values[None, :], n, 0)
            pw = L.leader_credit(v, gp, total_alt=L.TOTAL_ALT[sn])
            # actual leader among the whole league (qualified): by actual per-game
            a = act[(act.games >= 58) | (act[st] >= L.TOTAL_ALT[sn])].copy(); a["pg"] = a[st] / a.games; top = a.pg.round(1).max()
            leaders = set(a[a.pg.round(1) == top].index)
            for b, p in zip(g.bbref_id, pw): rows.append(dict(season=s, stat=sn, bbref_id=b, p=p, win=(1.0 / len(leaders)) if b in leaders else 0.0))
            rows.append(dict(season=s, stat=sn, bbref_id="_missed", p=0.0, win=1.0 - sum(1.0 / len(leaders) for b in g.bbref_id if b in leaders)))
    D = pd.DataFrame(rows); P = D[D.bbref_id != "_missed"]
    bins = [0, .02, .05, .15, .35, 1.01]; P = P.assign(bk=pd.cut(P.p, bins, right=False))
    rel = P.groupby("bk", observed=True).agg(n=("p", "size"), mean_p=("p", "mean"), freq=("win", "mean")).reset_index().astype({"bk": str})
    ll = []
    for (s, sn), g in P.groupby(["season", "stat"]): ll.append(np.log(max(float((g.p * g.win).sum()), 1e-4)))
    out = dict(reliability=rel.round(4).to_dict("records"), mean_logscore_actual_leader=float(np.mean(ll)), top_pick_hit=float(np.mean([g.loc[g.p.idxmax(), "win"] > 0 for _, g in P.groupby(["season", "stat"])])),
               mean_p_top_pick=float(np.mean([g.p.max() for _, g in P.groupby(["season", "stat"])])), missed_mass=float(D[D.bbref_id == "_missed"].win.mean()))
    return out

if __name__ == "__main__":
    o = run(); print(json.dumps(o, indent=1)); json.dump(o, open(C("g4_leader_backtest.json"), "w"), indent=1)
