"""G3 calibration: re-run the engine on 2023-24 .. 2025-26 PRESEASON inputs (bbref seasons 2024..2026) and compare to realized outcomes."""
import json, os, sys, time
import numpy as np, pandas as pd
from ..ratings.model import Data, fit_player_model, predict_players, first_roster, allocate_minutes
from ..data.teams import TEAMS
from .inputs import TEAM_LIST, IDX, DIVS, PAR_NAMES, B_TEAM, R_REPL, K_TOP, build, lottery_tables
from .fit_game_model import games_frame, add_rest
from .runner import simulate, FLAGS

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
C = lambda f: os.path.join(ROOT, "data", "clean", f)


def hist_inputs(D, g_all, bt, s, base_inp):
    P = fit_player_model(D, s - 1)
    ro = first_roster(D, s)
    pl = predict_players(D, s, P, roster_ids=ro.bbref_id.unique())
    inp = {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in base_inp.items()}
    rating = np.zeros(30); pw = np.zeros((30, K_TOP)); pa = np.zeros((30, K_TOP)); pw_po = np.zeros((30, K_TOP)); po_delta = np.zeros(30)
    b = bt[bt.test_season == s].set_index("abbr")
    for abbr, d in ro.groupby("abbr"):
        if abbr not in IDX: continue
        i = IDX[abbr]; rating[i] = b.loc[abbr, "pred_srs"]
        x = d.merge(pl, left_on="bbref_id", right_index=True, how="left"); x["w_team"] = 1.0
        x["min"] = allocate_minutes(x); x = x.sort_values("min", ascending=False).reset_index(drop=True)
        healthy = x.mpg_hat.clip(upper=38.0).values
        norm_reg = healthy * (240.0 / healthy.sum())
        top = x.head(K_TOP)
        for k, r in top.iterrows():
            pw[i, k] = max(B_TEAM * (healthy[k] / 48.0) * (r.rating - R_REPL), 0.0); pa[i, k] = r.gfrac_hat
        o8 = np.argsort(-healthy)[:8]
        mp8 = healthy[o8] * (228.0 / healthy[o8].sum()); mp8 = np.minimum(mp8, 42.0); mp8 *= 228.0 / mp8.sum()
        rr = x.rating.values
        po_delta[i] = B_TEAM * ((mp8 / 48.0 * rr[o8]).sum() - (norm_reg / 48.0 * rr).sum())
        for kk, ix in enumerate(o8):
            if ix < K_TOP: pw_po[i, ix] = max(B_TEAM * (mp8[kk] / 48.0) * (rr[ix] - R_REPL), 0.0)
    # schedule: first 1230 games of the season
    g = g_all[g_all.season == s].sort_values(["date"]).head(1230).reset_index(drop=True)
    day0 = g.date.min()
    inp.update(rating=rating, pw=pw, pa=pa, pw_po=pw_po, po_delta=po_delta,
               gh=g.home.map(IDX).values.astype(np.int64), ga=g.away.map(IDX).values.astype(np.int64),
               gb2bh=g.b2b_h.fillna(0).values.astype(float), gb2ba=g.b2b_a.fillna(0).values.astype(float),
               gday=(g.date - day0).dt.days.values.astype(np.int64), gcup=np.zeros(len(g), np.bool_),
               deadline_day=10_000, cup_ko_day=10_000, kprot=-np.ones(30, np.int64), fover=-np.ones(30), nf_team=-1, nt5_team=-1)
    par = inp["par"].copy(); par[PAR_NAMES.index("cup_on")] = 0.0; par[PAR_NAMES.index("tank_on")] = 0.0
    inp["par"] = par
    return inp


def reliability(p, y, edges=(0, .1, .25, .4, .6, .75, .9, 1.0001)):
    b = np.digitize(p, edges) - 1; rows = []
    for i in range(len(edges) - 1):
        m = b == i
        if m.sum(): rows.append(dict(bin=f"{edges[i]:.2f}-{min(edges[i+1],1):.2f}", n=int(m.sum()), mean_pred=float(p[m].mean()), freq=float(y[m].mean()), se=float(np.sqrt(max(p[m].mean() * (1 - p[m].mean()), 1e-9) / m.sum()))))
    return rows


def run(n=40_000, seasons=(2024, 2025, 2026), seed=21):
    D = Data(); gh = games_frame(); gh = add_rest(gh)
    bt = pd.read_csv(C("backtest_predictions_firstroster.csv"))
    ts = D.ts.set_index(["season", "abbr"])
    lt = lottery_tables(16, 60_000)
    base = build({"_lottery_tables": lt})
    out = []; recs = []; sims = {}
    for s in seasons:
        inp = hist_inputs(D, gh, bt, s, base)
        r = simulate(inp, n, seed + s, verbose=False)
        sims[s] = r
        for i, t in enumerate(TEAM_LIST):
            w = r["wins"][:, i].astype(float)
            q = np.percentile(w, [5, 10, 25, 50, 75, 90, 95])
            actual = float(ts.loc[(s, t)].wins)
            rec = dict(season=s, team=t, conf=TEAMS[t][1], div=TEAMS[t][2], mu=w.mean(), var=w.var(), q05=q[0], q10=q[1], q25=q[2], q50=q[3], q75=q[4], q90=q[5], q95=q[6], actual=actual,
                       p_po=float(((r["flags"][:, i] & 1) > 0).mean()), p_div=float(((r["flags"][:, i] & 4) > 0).mean()), p_top6=float(((r["flags"][:, i] & 2) > 0).mean()),
                       p_title=float(((r["flags"][:, i] & 16) > 0).mean()),
                       pit=float((w < actual).mean() + 0.5 * (w == actual).mean()))
            recs.append(rec)
    R = pd.DataFrame(recs)
    # realized outcomes from standings: top-10 in conference by wins; division winner = best wins in division (ties -> shared fractional credit)
    R["act_po"] = 0.0; R["act_top6"] = 0.0; R["act_div"] = 0.0
    for (s, c), d in R.groupby(["season", "conf"]):
        rk = d.actual.rank(ascending=False, method="first")
        R.loc[d.index, "act_po"] = (rk <= 10).astype(float); R.loc[d.index, "act_top6"] = (rk <= 6).astype(float)
    for (s, dv), d in R.groupby(["season", "div"]):
        top = d.actual.max(); winners = d[d.actual == top]
        R.loc[winners.index, "act_div"] = 1.0 / len(winners)
    cal = {}
    for name, pc, ac in [("P(top-10 in conference = makes playoffs/play-in)", "p_po", "act_po"), ("P(top-6 in conference)", "p_top6", "act_top6"), ("P(division title)", "p_div", "act_div")]:
        p = R[pc].values; y = R[ac].values
        cal[name] = dict(brier=float(np.mean((p - y) ** 2)), brier_climatology=float(np.mean((y.mean() - y) ** 2)), reliability=reliability(p, y))
    cov = {}
    for lo, hi, lab in [("q25", "q75", "50%"), ("q10", "q90", "80%"), ("q05", "q95", "90%")]:
        cov[lab] = float(((R.actual >= R[lo]) & (R.actual <= R[hi])).mean())
    # variance ratio vs self-consistency ceiling
    vr_obs = float(((R.actual - R.mu) ** 2).mean() / R["var"].mean())
    rng = np.random.default_rng(5); ceil = []
    for _ in range(4000):          # pseudo-actual seasons drawn from the model's own simulations
        tot = 0.0; vv = 0.0
        for s in seasons:
            j = rng.integers(0, sims[s]["wins"].shape[0])
            w = sims[s]["wins"][j].astype(float)
            mus = R[R.season == s].set_index("team").loc[TEAM_LIST]
            tot += ((w - mus.mu.values) ** 2).sum(); vv += mus["var"].sum()
        ceil.append(tot / vv)
    ceil = np.array(ceil)
    # PIT uniformity: share of PITs in outer deciles, KS stat
    pit = np.sort(R.pit.values); ks = float(np.max(np.abs(pit - (np.arange(1, len(pit) + 1) / len(pit)))))
    res = dict(n_team_seasons=int(len(R)), seasons=list(seasons), interval_coverage=cov, variance_ratio_obs=vr_obs, variance_ratio_ceiling=dict(mean=float(ceil.mean()), p05=float(np.percentile(ceil, 5)), p95=float(np.percentile(ceil, 95)),
               p_obs_at_or_above=float((ceil >= vr_obs).mean())), pit_ks=ks, calibration=cal, wins_rmse=float(np.sqrt(((R.actual - R.mu) ** 2).mean())), mean_bias=float((R.mu - R.actual).mean()),
               note="HCA/sigma_game/sigma_team were fit on windows that include these seasons (mild in-sample); ratings and player inputs are preseason-only (first-team roster proxy)")
    R.to_csv(C("sim_calibration_team_seasons.csv"), index=False)
    json.dump(res, open(C("sim_calibration.json"), "w"), indent=1)
    return R, res


if __name__ == "__main__":
    R, res = run()
    print(json.dumps({k: v for k, v in res.items() if k != "calibration"}, indent=1))
    for k, v in res["calibration"].items():
        print(k, "Brier", round(v["brier"], 4), "vs clim", round(v["brier_climatology"], 4))
        for r in v["reliability"]: print("   ", r["bin"], r["n"], round(r["mean_pred"], 3), round(r["freq"], 3), "se", round(r["se"], 3))
