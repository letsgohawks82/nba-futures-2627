"""G4 award models (MVP / DPOY / ROY): conditional (multinomial) logit fit on 2014-2026 winners against each season's candidate pool, ridge-penalised.
Per sim: candidate features are drawn from that sim's team record (win%), the player's games, and sampled box/impact lines; winner = argmax(utility + Gumbel),
which is exactly the multinomial-logit choice. 65-game rule is a toggle (games >= 65 and projected mpg >= 20).
Parameter uncertainty = season-block bootstrap of the fit (coefficients) and of the BPM/DBPM prediction-error SD."""
import json, os
import numpy as np, pandas as pd
from scipy.optimize import minimize
from ..data.namemap import norm
from .rates import table, STATS, C

DECAY = (1.0, 0.55, 0.30)
FEATS = {"MVP": ["bpm", "ppg", "win", "gp", "prev_mvp"], "DPOY": ["dbpm", "stocks", "blkpg", "win", "tdef", "big", "gp", "prev_dpoy"], "ROY": ["ppg", "rebast", "gp", "lnpick"]}
SCALE = dict(prev_mvp=0.5, prev_dpoy=0.5, blkpg=1.0, tdef=1.0, bpm=5.0, dbpm=2.0, ppg=10.0, win=0.15, gp=15.0, stocks=1.5, big=1.0, rebast=5.0, lnpick=1.0)
CENTER = dict(prev_mvp=0.0, prev_dpoy=0.0, blkpg=0.8, tdef=0.0, bpm=0.0, dbpm=0.0, ppg=15.0, win=0.5, gp=65.0, stocks=2.0, big=0.0, rebast=5.0, lnpick=1.5)


def zf(name, x):
    return (x - CENTER[name]) / SCALE[name]


def hist_frame():
    ps = table(); a = pd.read_parquet(C("award_voting.parquet"))
    for c in ["season", "rank", "award_share"]: a[c] = pd.to_numeric(a[c], errors="coerce")
    from ..ratings.prep import team_seasons
    t = team_seasons(); t["win"] = t.wins / (t.wins + t.losses); t["defz"] = (t.def_rtg - t.groupby("season").def_rtg.transform("mean")) / 3.0
    tw = t.set_index(["season", "abbr"]).win; td = t.set_index(["season", "abbr"]).defz
    d = ps[ps.season >= 2014].copy()
    # multi-team players: use the team with the most games would need splits; use league .500 for TOT rows (rare among candidates)
    d["win"] = [tw.get((s, tm), 0.5) for s, tm in zip(d.season, d.team)]; d["tdef"] = [td.get((s, tm), 0.0) for s, tm in zip(d.season, d.team)]
    # previous-season voting share (voter inertia)
    for aw in ("mvp", "dpoy"):
        sh = a[a.award == aw].set_index(["season", "bbref_id"]).award_share; sh = sh[~sh.index.duplicated()]
        d["prev_" + aw] = [sh.get((s - 1, b), 0.0) for s, b in zip(d.season, d.bbref_id)]
    d["blkpg"] = d.blk / d.games.clip(lower=1)
    d["ppg"] = d.pts / d.games.clip(lower=1); d["rpg"] = d.trb / d.games.clip(lower=1); d["apg"] = d.ast / d.games.clip(lower=1)
    d["stocks"] = (d.stl + d.blk) / d.games.clip(lower=1); d["big"] = (d.cls == "B").astype(float); d["gp"] = d.games; d["rebast"] = d.rpg + d.apg
    # rookies: draft_year + 1 == season
    dr = pd.read_parquet(C("draft_picks.parquet")); dr["k"] = dr.player.map(norm); dr["pick"] = pd.to_numeric(dr.pick_overall, errors="coerce"); dr["dy"] = pd.to_numeric(dr.draft_year)
    d["k"] = d.name_display.map(norm)
    m = d.merge(dr[["k", "pick", "dy"]].drop_duplicates("k"), on="k", how="left")
    m["rookie"] = (m.dy + 1 == m.season); m["lnpick"] = np.log(m.pick.clip(lower=1).fillna(61))
    w = a[(a["rank"] == 1)][["season", "award", "bbref_id"]]
    return m, w


def pools(m, w):
    out = {}
    for aw, key in (("mvp", "MVP"), ("dpoy", "DPOY"), ("roy", "ROY")):
        rows = []
        for s in range(2014, 2027):
            g = m[m.season == s]
            if key == "ROY": g = g[g.rookie & (g.mp >= 300)]
            else: g = g[(g.mp >= 1000) & (g.games >= 40)]
            win = w[(w.season == s) & (w.award == aw)].bbref_id.tolist()
            if not len(win) or win[0] not in set(g.bbref_id): continue
            g = g.copy(); g["is_win"] = (g.bbref_id == win[0]).astype(int); rows.append(g)
        out[key] = pd.concat(rows)
    return out


def design(df, key):
    return np.column_stack([zf(f, df[f].fillna(CENTER[f]).values) for f in FEATS[key]])


def fit_clogit(df, key, ridge=0.5, seasons=None):
    X = design(df, key); y = df.is_win.values; sid = df.season.values
    ss = sorted(set(sid)) if seasons is None else seasons
    # season-block bootstrap: repeat seasons by their multiplicities
    cnt = pd.Series(ss).value_counts(); idx = {s: np.where(sid == s)[0] for s in cnt.index}
    def f(b):
        nll = 0.0; g = np.zeros_like(b)
        for s, c in cnt.items():
            ix = idx[s]; u = X[ix] @ b; mx = u.max(); e = np.exp(u - mx); Z = e.sum(); wi = ix[y[ix] == 1][0] - ix[0]
            nll += c * (-(u[wi] - mx - np.log(Z))); g += c * (-(X[ix][wi] - (e[:, None] * X[ix]).sum(0) / Z))
        return nll + 0.5 * ridge * (b @ b), g + ridge * b
    r = minimize(f, np.zeros(X.shape[1]), jac=True, method="L-BFGS-B")
    return r.x


def loo(df, key, ridge=0.5):
    """Leave-one-season-out: probability the model gives the actual winner and rank of the winner."""
    ss = sorted(df.season.unique()); res = []
    for s in ss:
        b = fit_clogit(df[df.season != s], key, ridge); g = df[df.season == s]; u = design(g, key) @ b; p = np.exp(u - u.max()); p /= p.sum()
        i = int(np.where(g.is_win.values == 1)[0][0]); res.append(dict(season=s, p_winner=float(p[i]), rank=int((p > p[i]).sum() + 1), winner=g.name_display.iloc[i], top=g.name_display.iloc[int(p.argmax())], p_top=float(p.max())))
    r = pd.DataFrame(res); return r


def bpm_error(col="bpm", seasons=range(2019, 2027), grid=(300, 600, 1000, 1500, 2500), top_n=30):
    """Residual SD of season BPM/DBPM around a decayed shrunk 3-year projection among the top-N predicted (MVP/DPOY contenders). Conservative: baseline, not the production ensemble."""
    ps = table(); ps = ps[ps[col].notna()]; best = None
    for M in grid:
        rows = []
        for s in seasons:
            h = pd.concat([ps[ps.season == s - k].assign(w=w) for k, w in zip((1, 2, 3), DECAY)])
            big = h[h.mp >= 500]; prior = float((big[col] * big.mp).sum() / big.mp.sum())
            g = h.assign(wm=h.w * h.mp, wb=h.w * h.mp * h[col]).groupby("bbref_id")[["wm", "wb"]].sum(); pred = (g.wb + M * prior) / (g.wm + M)
            t = ps[(ps.season == s) & (ps.mp >= 1000)].set_index("bbref_id"); j = t.join(pred.rename("pred"), how="inner")
            top = j.nlargest(top_n, "pred"); rows.append(top[["pred", col]].assign(season=s))
        R = pd.concat(rows); b = np.polyfit(R.pred, R[col], 1); res = R[col] - np.polyval(b, R.pred)
        sd = float(np.sqrt((res ** 2).mean()))
        if best is None or sd < best["sd"]: best = dict(M=M, sd=sd, slope=float(b[0]), intercept=float(b[1]), n=len(R), rmse_raw=float(np.sqrt(((R[col] - R.pred) ** 2).mean())))
    return best


if __name__ == "__main__":
    m, w = hist_frame(); P = pools(m, w); out = {}
    for key, df in P.items():
        print(key, "seasons", df.season.nunique(), "pool", len(df))
        for rg in (0.1, 0.5, 2.0):
            r = loo(df, key, rg); print(" ridge", rg, "LOO mean p_winner", round(r.p_winner.mean(), 3), "winner ranked 1 in", int((r["rank"] == 1).sum()), "of", len(r), "log-score", round(float(np.log(r.p_winner).mean()), 3), "uniform", round(float(np.mean(-np.log(df.groupby("season").size()))), 3))
        b = fit_clogit(df, key, 0.5); print(" coefficients", dict(zip(FEATS[key], np.round(b, 2))))
        print(loo(df, key, 0.5).round(3).to_string())
        out[key] = dict(coef=dict(zip(FEATS[key], map(float, b))))
    out["bpm_error"] = bpm_error("bpm"); out["dbpm_error"] = bpm_error("dbpm"); print(out["bpm_error"], out["dbpm_error"])
    json.dump(out, open(C("g4_award_fit.json"), "w"), indent=1)
