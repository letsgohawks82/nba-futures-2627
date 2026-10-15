"""Out-of-sample preseason backtest 2018-19 -> 2025-26 (test seasons 2019..2026). Fit on seasons < t only."""
import json, os, sys
import numpy as np, pandas as pd
from scipy.stats import norm as N, spearmanr
from .model import *

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TEST = list(range(2019, 2027))
FIRST_TRAIN = 2016
LINES = [30.5, 35.5, 41.5, 47.5, 52.5]


def wins82(ts):
    ts = ts.copy(); ts["w82"] = ts.wins / ts.gp * 82
    return ts


def conf_rank_probs(mu, sigma, conf, nsim=4000, seed=0):
    rng = np.random.default_rng(seed)
    W = mu[None, :] + sigma * rng.standard_normal((nsim, len(mu)))
    out10 = np.zeros(len(mu)); out6 = np.zeros(len(mu))
    for c in np.unique(conf):
        ix = np.where(conf == c)[0]
        r = (-W[:, ix]).argsort(1).argsort(1) + 1
        out10[ix] = (r <= 10).mean(0); out6[ix] = (r <= 6).mean(0)
    return out10, out6


def run():
    D = Data(); ts = wins82(D.ts)
    player_fits, frames = {}, {}
    def pfit(m):
        if m not in player_fits: player_fits[m] = fit_player_model(D, m)
        return player_fits[m]
    def frame(s):
        if s not in frames:
            f = season_frame(D, s, pfit(s - 1)); f = f.merge(ts[ts.season == s][["abbr", "w82"]], on="abbr"); frames[s] = f
        return frames[s]
    rows, fitlog = [], []
    for t in TEST:
        L = fit_team_layer([frame(s) for s in range(FIRST_TRAIN, t)])
        f = predict_wins(frame(t), L)
        # baselines trained on seasons < t
        hist = ts[(ts.season >= 2015) & (ts.season < t)].merge(ts.assign(season=ts.season + 1)[["season", "abbr", "w82", "srs"]].rename(columns={"w82": "pw", "srs": "psrs"}), on=["season", "abbr"])
        b1 = np.polyfit(hist.pw, hist.w82, 1); b2 = np.polyfit(hist.psrs, hist.srs, 1)
        prev = ts[ts.season == t - 1].set_index("abbr")
        f["pw"] = f.abbr.map(prev.w82); f["psrs"] = f.abbr.map(prev.srs)
        f["b1_wins"] = np.polyval(b1, f.pw); f["b1_wins"] += 41 - f.b1_wins.mean()
        f["b2_wins"] = 41 + L["k_wins"] * (np.polyval(b2, f.psrs) - np.polyval(b2, f.psrs).mean())
        f["b3_wins"] = f.pw + (41 - f.pw.mean())
        f["sigma"] = L["wins_resid_sd"]; f["test_season"] = t
        f["pred_srs_resid_sd"] = L["srs_resid_sd"]
        rows.append(f); fitlog.append(dict(test_season=t, n_train=L["n"], k_wins=L["k_wins"], wins_resid_sd=L["wins_resid_sd"], beta=L["beta"], player_lam=pfit(t - 1)["lam"], player_M0=pfit(t - 1)["M0"], player_rmse=pfit(t - 1)["rmse"]))
    R = pd.concat(rows, ignore_index=True)
    # probabilities (per test season, using that season's sigma)
    p10 = np.zeros(len(R)); p6 = np.zeros(len(R))
    for t, g in R.groupby("test_season"):
        a, b = conf_rank_probs(g.pred_wins.values, g.sigma.iloc[0], g.conf.values, seed=t)
        p10[g.index] = a; p6[g.index] = b
    R["p_top10"] = p10; R["p_top6"] = p6
    R["act_top10"] = R.groupby(["test_season", "conf"]).w82.rank(ascending=False, method="first") <= 10
    R["act_top6"] = R.groupby(["test_season", "conf"]).w82.rank(ascending=False, method="first") <= 6
    R.to_csv(os.path.join(ROOT, "data/clean/backtest_predictions.csv"), index=False)
    pd.DataFrame(fitlog).to_csv(os.path.join(ROOT, "data/clean/backtest_fitlog.csv"), index=False)
    return R


def metrics(R, rng=np.random.default_rng(42), B=2000):
    n = len(R); idx = np.arange(n)
    def rm(e): return float(np.sqrt(np.mean(e ** 2)))
    def stat(sub, col):
        e = sub[col].values - sub.w82.values
        return dict(rmse=rm(e), mae=float(np.mean(np.abs(e))),
                    rho=float(np.mean([spearmanr(g[col], g.w82)[0] for _, g in sub.groupby("test_season")])))
    out = {}
    cols = {"model": "pred_wins", "B1_prev_wins_regress": "b1_wins", "B2_prev_srs": "b2_wins", "B3_naive_prev_wins": "b3_wins"}
    boots = {k: [] for k in cols}; diffs = {k: [] for k in cols}
    for _ in range(B):
        s = R.iloc[rng.integers(0, n, n)]
        for k, c in cols.items():
            e = s[c].values - s.w82.values; boots[k].append((rm(e), float(np.mean(np.abs(e)))))
    for k, c in cols.items():
        st = stat(R, c); b = np.array(boots[k])
        out[k] = dict(**st, rmse_ci=[float(np.percentile(b[:, 0], 10)), float(np.percentile(b[:, 0], 90))], mae_ci=[float(np.percentile(b[:, 1], 10)), float(np.percentile(b[:, 1], 90))])
    # paired RMSE difference model - baseline (negative = model better)
    for k in list(cols)[1:]:
        d = []
        for _ in range(B):
            s = R.iloc[rng.integers(0, n, n)]
            d.append(rm(s.pred_wins.values - s.w82.values) - rm(s[cols[k]].values - s.w82.values))
        out[k]["paired_rmse_diff_model_minus_this"] = dict(mean=float(np.mean(d)), ci80=[float(np.percentile(d, 10)), float(np.percentile(d, 90))])
    # probabilistic: P(top10 conf), P(top6 conf), P(over line)
    def brier(p, y): return float(np.mean((p - y) ** 2))
    def ll(p, y): p = np.clip(p, 1e-4, 1 - 1e-4); return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
    prob = {}
    for name, pc, ac in [("top10_conf", "p_top10", "act_top10"), ("top6_conf", "p_top6", "act_top6")]:
        y = R[ac].values.astype(float); p = R[pc].values
        base = np.full(n, y.mean())
        bs = [brier(R.iloc[i][pc].values, R.iloc[i][ac].values.astype(float)) for i in [rng.integers(0, n, n) for _ in range(500)]]
        prob[name] = dict(brier=brier(p, y), logloss=ll(p, y), brier_climatology=brier(base, y), brier_ci80=[float(np.percentile(bs, 10)), float(np.percentile(bs, 90))])
    pr, ac_ = [], []
    for X in LINES:
        pr.append(1 - N.cdf((X - R.pred_wins.values) / R.sigma.values)); ac_.append((R.w82.values > X).astype(float))
    pr = np.concatenate(pr); ac_ = np.concatenate(ac_)
    prob["over_lines"] = dict(brier=brier(pr, ac_), logloss=ll(pr, ac_), brier_climatology=brier(np.full(len(pr), ac_.mean()), ac_))
    out["probabilistic"] = prob
    # calibration tables
    cal = []
    for name, p, y in [("top10_conf", R.p_top10.values, R.act_top10.values.astype(float)), ("top6_conf", R.p_top6.values, R.act_top6.values.astype(float)), ("over_lines", pr, ac_)]:
        bins = np.array([0, .05, .15, .3, .5, .7, .85, .95, 1.0001])
        b = np.digitize(p, bins) - 1
        for i in range(len(bins) - 1):
            m = b == i
            if m.sum() > 0: cal.append(dict(market=name, bin=f"{bins[i]:.2f}-{min(bins[i+1],1):.2f}", n=int(m.sum()), mean_pred=float(p[m].mean()), freq=float(y[m].mean())))
    out["calibration"] = cal
    # per-season rmse
    out["by_season"] = {int(t): dict(model=rm(g.pred_wins - g.w82), B1=rm(g.b1_wins - g.w82), B2=rm(g.b2_wins - g.w82)) for t, g in R.groupby("test_season")}
    out["mean_bias_wins"] = float((R.pred_wins - R.w82).mean())
    out["sum_pred_wins_per_season"] = {int(t): float(g.pred_wins.sum()) for t, g in R.groupby("test_season")}
    return out


if __name__ == "__main__":
    R = run(); m = metrics(R)
    json.dump(m, open(os.path.join(ROOT, "data/clean/backtest_metrics.json"), "w"), indent=1)
    for k in ["model", "B1_prev_wins_regress", "B2_prev_srs", "B3_naive_prev_wins"]:
        v = m[k]; print(f"{k:24s} RMSE {v['rmse']:.2f} {v['rmse_ci']}  MAE {v['mae']:.2f}  rho {v['rho']:.3f}", v.get("paired_rmse_diff_model_minus_this", ""))
    print(json.dumps(m["probabilistic"], indent=0)); print(m["by_season"]); print("bias", m["mean_bias_wins"])
