"""G4 per-game stat projections (PTS/REB/AST/STL/BLK/TOV) and their season-level residual spread.
Per-minute rate = decayed 3-season minutes-weighted rate shrunk to a position prior with reliability mp/(mp+M0);
per-game = rate x projected mpg. M0 and the residual SD (relative, among the top-candidate players) are fit by backtest.
Only information before the target season is used in the backtest."""
import json, os
import numpy as np, pandas as pd
from ..ratings.prep import player_seasons

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
C = lambda f: os.path.join(ROOT, "data", "clean", f)
STATS = {"PPG": "pts", "RPG": "trb", "APG": "ast", "SPG": "stl", "BPG": "blk", "TPG": "fg3"}   # TPG = three-pointers made per game (book market), NOT turnovers
DECAY = (1.0, 0.55, 0.30)
PCLS = {"PG": "G", "SG": "G", "SF": "W", "PF": "B", "C": "B"}


def table():
    ps, _ = player_seasons()
    ps = ps[ps.bbref_id.notna()].drop_duplicates(["season", "bbref_id"]).copy()
    if "fg3" not in ps:
        import pandas as _pd
        from ..ratings.prep import FIX, num
        t = _pd.read_parquet(C("player_rs_totals.parquet")); t["season"] = t.season.astype(int); t["team"] = t.team_name_abbr.replace(FIX); t["fg3"] = num(t.fg3)
        t = t.sort_values("team", key=lambda x: ~x.str.endswith("TM")).drop_duplicates(["season", "bbref_id"])      # prefer the multi-team total row
        ps = ps.merge(t[["season", "bbref_id", "fg3"]], on=["season", "bbref_id"], how="left")
    ps["cls"] = ps.pos.map(PCLS).fillna("W"); ps["mpg"] = ps.mp / ps.games.clip(lower=1)
    return ps


def project(ps, season, M0, hist_ids=None):
    """Per-minute rates for each player seen in the 3 seasons before `season` (vectorized). Returns DataFrame indexed by bbref_id."""
    cols = list(STATS.values())
    h = pd.concat([ps[ps.season == season - k].assign(w=DECAY[k - 1], k=k) for k in (1, 2, 3)])
    if hist_ids is not None: h = h[h.bbref_id.isin(hist_ids)]
    big = h[h.mp >= 500]
    prior = {c: big.groupby("cls")[c].sum() / big.groupby("cls").mp.sum() for c in cols}
    g = h.copy(); g["wmp"] = g.w * g.mp
    for c in cols: g["w_" + c] = g.w * g[c].fillna(0.0)
    agg = g.groupby("bbref_id")[["wmp"] + ["w_" + c for c in cols]].sum()
    cls = g.sort_values("k").groupby("bbref_id").cls.first()
    out = pd.DataFrame(index=agg.index); out["cls"] = cls; out["S"] = agg.wmp
    for c in cols:
        pr = out.cls.map(prior[c]).fillna(float(prior[c].mean()))
        out[c] = (agg["w_" + c] + M0[c] * pr) / (agg.wmp + M0[c])
    return out


def backtest(seasons=range(2019, 2027), grid=(150, 300, 600, 1000, 1600, 2500, 4000)):
    ps = table(); err = {sn: {} for sn in STATS}
    for M in grid:
        Ms = {s: M for s in STATS.values()}; acc = {sn: [] for sn in STATS}
        for s in seasons:
            tgt = ps[(ps.season == s) & (ps.mp >= 600)].set_index("bbref_id"); pr = project(ps, s, Ms, tgt.index)
            j = tgt.join(pr, rsuffix="_p", how="inner")
            for sn, st in STATS.items(): acc[sn].append((((j[st] / j.mp) - j[st + "_p"]) ** 2 * j.mp).values)
        for sn in STATS: err[sn][M] = float(np.sqrt(np.concatenate(acc[sn]).mean()))
    best = {sn: min(err[sn], key=err[sn].get) for sn in STATS}
    return err, best


def residuals(M0, seasons=range(2019, 2027), top_n=30):
    """Season-level per-game prediction residuals among each season's top-N predicted players (the leader contenders).
    Projected mpg proxy = previous-season mpg (the production run uses the minutes model, whose error is smaller or comparable)."""
    ps = table(); rows = []
    for s in seasons:
        tgt = ps[ps.season == s].set_index("bbref_id"); prv = ps[ps.season == s - 1].set_index("bbref_id")
        pr = project(ps, s, M0, tgt.index)
        j = tgt.join(pr, rsuffix="_p", how="inner").join(prv.mpg.rename("mpg_prev"), how="left")
        j = j[(j.games >= 40) & j.mpg_prev.notna()].copy()
        j["mpg_p"] = j.mpg_prev          # no minutes regression: stars keep their minutes
        for sname, st in STATS.items():
            j["pred_" + sname] = j[st + "_p"] * j.mpg_p; j["act_" + sname] = j[st] / j.games
        for sname in STATS:
            top = j.nlargest(top_n, "pred_" + sname)
            for b, r in top.iterrows(): rows.append(dict(season=s, stat=sname, bbref_id=b, pred=r["pred_" + sname], act=r["act_" + sname], games=r.games))
    R = pd.DataFrame(rows)
    out = {}
    for sname, g in R.groupby("stat"):
        lr = np.log(g.act.clip(lower=0.05) / g.pred.clip(lower=0.05))
        b = np.polyfit(g.pred, g.act, 1)
        out[sname] = dict(n=int(len(g)), rel_sd=float(lr.std()), log_bias=float(lr.mean()), slope=float(b[0]), intercept=float(b[1]), rmse=float(np.sqrt(((g.act - g.pred) ** 2).mean())),
                          abs_sd_over_pred=float(((g.act - g.pred) / g.pred).std()))
    return R, out


if __name__ == "__main__":
    res, best = backtest()
    print(json.dumps(res, indent=1)); print("best M0", best)
    M0 = {STATS[k]: v for k, v in best.items()}
    R, out = residuals(M0)
    print(json.dumps(out, indent=1))
    R.to_csv(C("g4_rate_backtest.csv"), index=False)
    json.dump(dict(M0=best, residuals=out, grid_rmse=res, note="per-minute RMSE grid (mp>=600 targets, 2019-2026 first-time out-of-sample projection); residuals among top-30 predicted per stat"), open(C("g4_rate_fit.json"), "w"), indent=1)
