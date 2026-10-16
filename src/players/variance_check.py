"""G6 root-cause check on stat-leader variance: per-sim SD of the season average for the model's top-5 in each market vs (a) those players' own historical year-over-year SD and
(b) the backtest residual SD of the top-5 / ranks 6-30 predicted players. Output data/clean/g4_variance_check.json."""
import json
import numpy as np, pandas as pd
from .rates import table, STATS, C
from . import leaders as L

def main():
    R = pd.read_csv(C("g4_rate_backtest.csv")); cal = L.calib_from_backtest(R); ps = table()
    pm = pd.read_csv(C("player_market_probs.csv")); out = {}; rows = []
    ps["games"] = ps.games.astype(float)
    for sn, st in STATS.items():
        mk = pm[pm.market == "LDR_" + sn].sort_values("p", ascending=False).head(5)
        pool = pd.read_csv(C("g4_pool.csv")).set_index("key")
        for r in mk.itertuples():
            mu = float(L.calibrated_pred(np.array([pool.loc[r.key, "pg_" + sn]]), cal[sn])[0]); sim_sd = cal[sn]["sd"] * mu
            h = ps[(ps.bbref_id == pool.loc[r.key, "bbref_id"]) & (ps.games >= 40) & (ps.season >= 2019)].sort_values("season")
            v = (h[st] / h.games).values
            rows.append(dict(stat=sn, player=r.player, sim_mean=mu, sim_sd=sim_sd, hist_n=len(v), hist_sd_levels=float(np.std(v, ddof=1)) if len(v) > 2 else np.nan, hist_yoy_sd=float(np.std(np.diff(v), ddof=1)) if len(v) > 2 else np.nan))
    T = pd.DataFrame(rows)
    # pooled historical YoY SD of the top-10 producers in each stat (consecutive seasons, >= 40 games)
    pooled = {}
    for sn, st in STATS.items():
        d = []
        for s in range(2020, 2027):
            a = ps[(ps.season == s - 1) & (ps.games >= 40)].set_index("bbref_id"); b = ps[(ps.season == s) & (ps.games >= 40)].set_index("bbref_id")
            top = (a[st] / a.games).nlargest(10).index.intersection(b.index)
            d += list(((b.loc[top, st] / b.loc[top, "games"]) - (a.loc[top, st] / a.loc[top, "games"])).values)
        d = np.array(d); mean_lvl = float((ps[(ps.season >= 2019) & (ps.games >= 40)].assign(v=lambda x: x[st] / x.games).groupby("season").v.apply(lambda x: x.nlargest(10).mean())).mean())
        pooled[sn] = dict(yoy_sd=float(d.std(ddof=1)), implied_idio_sd=float(d.std(ddof=1) / np.sqrt(2)), n=len(d), top10_mean_level=mean_lvl)
    # backtest residual SD by predicted rank group
    grp = {}
    for sn in STATS:
        g = R[R.stat == sn].copy(); g["cal"] = L.calibrated_pred(g.pred.values, cal[sn]); g["rank"] = g.groupby("season").pred.rank(ascending=False)
        g["lr"] = np.log(g.act.clip(lower=0.05) / g.cal); g["ar"] = g.act - g.cal
        grp[sn] = {f"{a}-{b}": dict(n=int(len(x)), log_sd=float(x.lr.std()), abs_sd=float(x.ar.std()), bias=float(x.lr.mean())) for (a, b), x in ((k, g[(g["rank"] >= k[0]) & (g["rank"] <= k[1])]) for k in ((1, 5), (6, 15), (16, 30)))}
    res = dict(per_player=T.round(3).to_dict("records"), pooled_top10_yoy=pooled, resid_by_rank=grp, sim_log_sd=cal)
    json.dump(res, open(C("g4_variance_check.json"), "w"), indent=1, default=float)
    return T, pooled, grp

if __name__ == "__main__":
    T, pooled, grp = main(); pd.set_option("display.width", 200)
    print(T.round(2).to_string()); print(json.dumps(pooled, indent=1)); print(json.dumps(grp, indent=1))
