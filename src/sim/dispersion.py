"""G3 conditional checks: leave-one-season-out CV of sigma_team (availability draws ON), predictive-SD vs backtest RMSE, variance ratio vs
self-consistency ceiling, out-of-sample reliability for P(over projection +/-5/10 wins) and P(top-6 seed)."""
import json, os, time
import numpy as np, pandas as pd
from ..ratings.model import Data
from .calibrate import hist_inputs
from .fit_game_model import games_frame, add_rest
from .inputs import build, lottery_tables, TEAM_LIST, PAR_NAMES
from .runner import simulate

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
C = lambda f: os.path.join(ROOT, "data", "clean", f)
SEASONS = [2019, 2022, 2023, 2024, 2025, 2026]       # full 82-game seasons (2020/2021 shortened)
GRID = [2.25, 2.5, 2.75, 3.0, 3.25, 3.5, 3.75]
N = 30_000


def run():
    D = Data(); g = add_rest(games_frame()); bt = pd.read_csv(C("backtest_predictions_firstroster.csv"))
    ts = D.ts.set_index(["season", "abbr"]); base = build({"_lottery_tables": lottery_tables(16, 30_000), "_calibrate": False})
    inputs = {s: hist_inputs(D, g, bt, s, base, cal=False) for s in SEASONS}
    from .meanmatch import calibrate_ratings
    targets = {s: bt[bt.test_season == s].set_index("abbr").loc[TEAM_LIST].pred_wins.values.astype(float) for s in SEASONS}
    actual = {s: np.array([ts.loc[(s, t)].wins for t in TEAM_LIST], float) for s in SEASONS}
    res = {}
    for sg in GRID:
        for s in SEASONS:
            inp = {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in inputs[s].items()}
            inp["par"][PAR_NAMES.index("sigma_team")] = sg                         # availability draws stay ON (avail_on=1)
            inp["rating"], _ = calibrate_ratings(inp, targets[s], n=12_000, iters=5)   # moment-match E[wins] to the calibrated projection for THIS sigma
            r = simulate(inp, N, 100 + s, verbose=False)
            res[(sg, s)] = (r["wins"].copy(), r["conf_rank"].copy())
    # log score of actual wins under the simulated pmf (smoothed)
    def logscore(sg, s):
        W = res[(sg, s)][0]; a = actual[s].astype(int); ls = []
        for i in range(30):
            c = np.bincount(W[:, i], minlength=84).astype(float) + 0.2
            ls.append(np.log(c[a[i]] / c.sum()))
        return np.array(ls)
    LS = {(sg, s): logscore(sg, s) for sg in GRID for s in SEASONS}
    tot = {sg: float(np.mean([LS[(sg, s)].mean() for s in SEASONS])) for sg in GRID}
    cv = []
    for hold in SEASONS:
        tr = {sg: np.mean([LS[(sg, s)].mean() for s in SEASONS if s != hold]) for sg in GRID}
        best = max(tr, key=tr.get)
        cv.append(dict(held_out=hold, sigma_selected=best, heldout_logscore_at_selected=float(LS[(best, hold)].mean()), heldout_logscore_at_3_5=float(LS[(3.5, hold)].mean())))
    cv = pd.DataFrame(cv)
    sg_all = max(tot, key=tot.get)
    # predictive SD vs realized RMSE
    rows = []
    for sg in GRID:
        sd = np.mean([res[(sg, s)][0].std(0).mean() for s in SEASONS])
        rmse = np.sqrt(np.mean([((actual[s] - res[(sg, s)][0].mean(0)) ** 2).mean() for s in SEASONS]))
        rows.append(dict(sigma_team=sg, mean_sim_sd=float(sd), realized_rmse=float(rmse), sd_over_rmse=float(sd / rmse), logscore=tot[sg]))
    disp = pd.DataFrame(rows)
    # variance ratio vs self-consistency ceiling at the CV-chosen sigma (all-season optimum)
    def vr(sg):
        mu = {s: res[(sg, s)][0].mean(0) for s in SEASONS}; va = {s: res[(sg, s)][0].var(0).mean() for s in SEASONS}
        o = np.mean([((actual[s] - mu[s]) ** 2).mean() / va[s] for s in SEASONS])
        rng = np.random.default_rng(7); ce = []
        idx = {s: rng.integers(0, N, 3000) for s in SEASONS}
        for k in range(3000):
            v = []
            for s in SEASONS:
                w = res[(sg, s)][0][idx[s][k]].astype(float)
                v.append(((w - mu[s]) ** 2).mean() / va[s])
            ce.append(np.mean(v))
        ce = np.array(ce); return dict(obs=float(o), ceil_mean=float(ce.mean()), ceil_p05=float(np.percentile(ce, 5)), ceil_p95=float(np.percentile(ce, 95)), p_ge=float((ce >= o).mean()))
    vrs = {sg: vr(sg) for sg in GRID}
    # out-of-sample reliability: each season uses the sigma selected without it
    sel = dict(zip(cv.held_out, cv.sigma_selected)); recs = []
    for s in SEASONS:
        W, CR = res[(sel[s], s)]; mu = W.mean(0)
        for i, t in enumerate(TEAM_LIST):
            a = actual[s][i]
            rec = dict(season=s, team=t, mu=mu[i], actual=a, sigma=sel[s], top6=float((CR[:, i] <= 6).mean()),
                       act_top6=float(pd.Series(actual[s]).rank(ascending=False, method="first").values[i] <= 6) if False else np.nan)
            for dlt in (-10, -5, 5, 10):
                rec[f"p_over_{dlt:+d}"] = float((W[:, i] > mu[i] + dlt).mean()); rec[f"y_over_{dlt:+d}"] = float(a > mu[i] + dlt)
            recs.append(rec)
    R = pd.DataFrame(recs)
    # actual conference rank by wins
    cf = {t: ("E" if t in {"ATL","BOS","BKN","CHA","CHI","CLE","DET","IND","MIA","MIL","NYK","ORL","PHI","TOR","WAS"} else "W") for t in TEAM_LIST}
    R["conf"] = R.team.map(cf); R["rk"] = R.groupby(["season", "conf"]).actual.rank(ascending=False, method="first"); R["act_top6"] = (R.rk <= 6).astype(float)
    def rel(p, y, edges=(0, .1, .25, .4, .6, .75, .9, 1.0001)):
        b = np.digitize(p, edges) - 1; out = []
        for k in range(len(edges) - 1):
            m = b == k
            if m.sum(): out.append(dict(bin=f"{edges[k]:.2f}-{min(edges[k+1],1):.2f}", n=int(m.sum()), mean_pred=float(p[m].mean()), freq=float(y[m].mean())))
        return out
    relo = {}
    for name, pc, yc in [(f"P(wins > proj {d:+d})", f"p_over_{d:+d}", f"y_over_{d:+d}") for d in (-10, -5, 5, 10)] + [("P(top-6 seed)", "top6", "act_top6")]:
        p = R[pc].values; y = R[yc].values
        relo[name] = dict(brier=float(np.mean((p - y) ** 2)), brier_ref=float(np.mean((y.mean() - y) ** 2)), reliability=rel(p, y))
    out = dict(seasons=SEASONS, n_team_seasons=int(len(R)), grid_table=disp.to_dict("records"), cv=cv.to_dict("records"), sigma_all_season_optimum=sg_all,
               variance_ratio_by_sigma={str(k): v for k, v in vrs.items()}, reliability_oos=relo)
    json.dump(out, open(C("sigma_team_cv_meanmatched.json"), "w"), indent=1); R.to_csv(C("sigma_team_cv_oos_predictions_meanmatched.csv"), index=False)
    return out, disp, cv, vrs, relo


if __name__ == "__main__":
    t = time.time(); out, disp, cv, vrs, relo = run()
    print(disp.round(3).to_string()); print(cv.round(3).to_string()); print("all-season optimum sigma:", out["sigma_all_season_optimum"], "time", round(time.time() - t))
    for k, v in vrs.items(): print("sigma", k, {a: round(b, 3) for a, b in v.items()})
    for k, v in relo.items():
        print(k, "Brier", round(v["brier"], 4), "ref", round(v["brier_ref"], 4)); [print("   ", r["bin"], r["n"], round(r["mean_pred"], 3), round(r["freq"], 3)) for r in v["reliability"]]
