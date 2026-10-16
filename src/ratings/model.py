"""Player impact (BPM-based, per 100 poss), minutes/availability, team rating, wins projection + expanding-window backtest.
Seasons are bbref end-years (2026 = 2025-26). Everything for season s is fit only on seasons < s."""
import itertools
import numpy as np, pandas as pd
from .prep import player_seasons, team_seasons, draft
from ..data.namemap import norm

TEAM_MIN = 240.0 * 82           # team-minutes in an 82-game season
MPG_CAP = 38.0
MIN_PRIOR_SEASON = 2014
LAMBDA_GRID = [0.4, 0.55, 0.7, 0.85, 1.0]
M0_GRID = [300, 600, 1000, 1500, 2500]


class Data:
    def __init__(self):
        self.ps, self.st = player_seasons(); self.ts = team_seasons(); self.dr = draft()
        ps = self.ps
        ps["gp_season"] = ps.season.map(self.ts.groupby("season").gp.max())
        ps["gfrac"] = (ps.games / ps.gp_season).clip(0, 1)
        ps["mpg"] = ps.mp / ps.games.replace(0, np.nan)
        ps["k"] = ps.name_display.map(norm)
        dr = self.dr.copy(); dr["k"] = dr.player.map(norm); dr["rookie_season"] = dr.draft_year + 1
        m = dr.merge(ps[["season", "k", "bbref_id"]], left_on=["rookie_season", "k"], right_on=["season", "k"], how="left")
        self.draft_ids = m.dropna(subset=["bbref_id"])[["bbref_id", "draft_year", "pick"]].drop_duplicates("bbref_id")
        self.pick_of = self.draft_ids.set_index("bbref_id").pick.to_dict()
        self._prior_cache = {}


def apply_role_override(D, path):
    """Replace tank-mode 2025-26 totals for players of the bottom-8 teams with their PRE-deadline role (games = pre-deadline availability x 82,
    minutes = pre-deadline mpg x games). Applied after model fits, only for projecting 2026-27 (the sim uses healthy pre-deadline roles)."""
    import os
    if not os.path.exists(path):
        return 0
    ov = pd.read_csv(path); ps = D.ps; n = 0
    for r in ov.itertuples():
        m = (ps.season == 2026) & (ps.bbref_id == r.bbref_id)
        if m.any():
            idx = ps.index[m][0]
            ps.loc[idx, "games"] = r.games_adj; ps.loc[idx, "mp"] = r.mp_adj
            ps.loc[idx, "gfrac"] = min(r.games_adj / ps.loc[idx, "gp_season"], 1.0); ps.loc[idx, "mpg"] = r.mp_adj / max(r.games_adj, 1)
            n += 1
    D._prior_cache.clear()
    return n


def _wols(X, y, w, ridge=0.0):
    W = np.sqrt(w)[:, None]
    A = X * W; b = y * W[:, 0]
    if ridge:
        A = np.vstack([A, np.sqrt(ridge) * np.eye(X.shape[1])]); b = np.concatenate([b, np.zeros(X.shape[1])])
    beta, *_ = np.linalg.lstsq(A, b, rcond=None)
    return beta


def prior_table(D, s, lam, metric="bpm", ncol=3):
    """Per player weighted prior metric over seasons s-1..s-3 (only seasons < s)."""
    key = (s, lam, metric, ncol)
    if key in D._prior_cache:
        return D._prior_cache[key]
    ps = D.ps
    sub = ps[(ps.season < s) & (ps.season >= s - ncol) & ps[metric].notna() & (ps.mp > 0)].copy()
    sub["w"] = (lam ** (s - 1 - sub.season)) * sub.mp
    sub["wm"] = sub.w * sub[metric]
    g = sub.groupby("bbref_id")
    out = pd.DataFrame({"S": g.w.sum(), "wprior": g.wm.sum() / g.w.sum(), "mp_prior": g.mp.sum()})
    D._prior_cache[key] = out
    return out


def fit_player_model(D, max_season, metric="bpm"):
    """Fit metric_s ~ age terms + reliability*(weighted prior), target seasons <= max_season; also rookie + availability models."""
    ps = D.ps; best = None
    tgt = list(range(MIN_PRIOR_SEASON + 1, max_season + 1))
    for lam, M0 in itertools.product(LAMBDA_GRID, M0_GRID):
        X, Y, Wt = [], [], []
        for s in tgt:
            pr = prior_table(D, s, lam, metric)
            t = ps[(ps.season == s) & (ps.mp >= 250) & ps.age.notna()].set_index("bbref_id")
            j = t.join(pr, how="inner"); j = j[j.S > 0]
            r = j.S / (j.S + M0); a = (j.age - 27) / 5
            X.append(np.column_stack([np.ones(len(j)), a, a ** 2, r * j.wprior, r])); Y.append(j[metric].values); Wt.append(j.mp.values)
        X = np.vstack(X); Y = np.concatenate(Y); Wt = np.concatenate(Wt)
        b = _wols(X, Y, Wt)
        rmse = float(np.sqrt(np.average((Y - X @ b) ** 2, weights=Wt)))
        if best is None or rmse < best["rmse"]:
            best = dict(lam=lam, M0=M0, beta=b.tolist(), rmse=rmse, n=int(len(Y)), max_season=max_season)
    rk = D.draft_ids[D.draft_ids.draft_year + 1 <= max_season]
    rs = ps.merge(rk, on="bbref_id"); rs = rs[(rs.season == rs.draft_year + 1)].copy()
    rs["lp"] = np.log(rs.pick)
    rb = rs[rs.mp >= 100]
    best["rookie_bpm"] = _wols(np.column_stack([np.ones(len(rb)), rb.lp]), rb[metric].values, rb.mp.values).tolist()
    rm = rs[rs.games >= 10]
    best["rookie_mpg"] = _wols(np.column_stack([np.ones(len(rm)), rm.lp]), rm.mpg.values, rm.games.values.astype(float)).tolist()
    best["rookie_gfrac"] = _wols(np.column_stack([np.ones(len(rs)), rs.lp]), rs.gfrac.values, np.ones(len(rs))).tolist()
    best["rookie_n"] = int(len(rb))
    rows = []
    for s in range(MIN_PRIOR_SEASON + 1, max_season + 1):
        cur = ps[(ps.season == s) & (ps.mp >= 200)].set_index("bbref_id")
        p1 = ps[ps.season == s - 1].set_index("bbref_id").gfrac.rename("g1"); p2 = ps[ps.season == s - 2].set_index("bbref_id").gfrac.rename("g2")
        j = cur.join(p1, how="inner").join(p2, how="left"); j["g2"] = j.g2.fillna(j.g1)
        rows.append(j[["gfrac", "g1", "g2", "age"]])
    A = pd.concat(rows); a = (A.age - 27) / 5
    XA = np.column_stack([np.ones(len(A)), A.g1, A.g2, a, a ** 2]); bA = _wols(XA, A.gfrac.values, np.ones(len(A)))
    best["avail_beta"] = bA.tolist(); best["avail_resid_sd"] = float((A.gfrac.values - XA @ bA).std()); best["avail_n"] = int(len(A))
    return best


def predict_players(D, s, P, metric="bpm", roster_ids=None, ages=None):
    ps = D.ps
    pr = prior_table(D, s, P["lam"], metric)
    ids = {i for i in (set(ps[ps.season == s].bbref_id) if roster_ids is None else set(roster_ids)) if isinstance(i, str)}
    df = pd.DataFrame(index=pd.Index(sorted(ids), name="bbref_id"))
    last = ps[ps.season < s].sort_values("season").groupby("bbref_id").last()
    df["age"] = ps[ps.season == s].set_index("bbref_id").age.reindex(df.index)
    if ages is not None:
        df["age"] = pd.Series(ages).reindex(df.index).fillna(df.age)
    df["age"] = df.age.fillna(last.age.reindex(df.index) + (s - last.season.reindex(df.index)))
    df["age"] = df.age.fillna(22.0)
    df = df.join(pr)
    b = np.array(P["beta"]); a = (df.age - 27) / 5
    r = df.S / (df.S + P["M0"])
    pred = b[0] + b[1] * a + b[2] * a ** 2 + b[3] * r * df.wprior + b[4] * r
    pick = pd.Series(D.pick_of).reindex(df.index).fillna(61.0)
    rook = P["rookie_bpm"][0] + P["rookie_bpm"][1] * np.log(pick)
    has = df.S.fillna(0) > 0
    df["rating"] = np.where(has, pred, rook)
    df["no_history"] = ~has
    lm = 0.6
    sub = ps[(ps.season < s) & (ps.season >= s - 3)].copy(); sub["w"] = lm ** (s - 1 - sub.season)
    sub["wmp"] = sub.w * sub.mp; sub["wg"] = sub.w * sub.games
    g = sub.groupby("bbref_id")
    mpg_prior = (g.wmp.sum() / g.wg.sum().clip(lower=1)).reindex(df.index)
    gc = g.games.sum().reindex(df.index).fillna(0)
    shr = gc / (gc + 15)
    mpg_r = P["rookie_mpg"][0] + P["rookie_mpg"][1] * np.log(pick)
    df["mpg_hat"] = np.where(has, shr * mpg_prior.fillna(0) + (1 - shr) * 12.0, np.clip(mpg_r, 3, 30))
    bA = np.array(P["avail_beta"])
    g1 = ps[ps.season == s - 1].set_index("bbref_id").gfrac.reindex(df.index); g2 = ps[ps.season == s - 2].set_index("bbref_id").gfrac.reindex(df.index)
    g1f = g1.fillna(0.5); g2f = g2.fillna(g1f)
    gh = bA[0] + bA[1] * g1f + bA[2] * g2f + bA[3] * a + bA[4] * a ** 2
    rg = P["rookie_gfrac"][0] + P["rookie_gfrac"][1] * np.log(pick)
    df["gfrac_hat"] = np.clip(np.where(g1.notna(), gh, rg), 0.15, 0.97)
    return df


STAR_PROTECT = True; STAR_K = 3          # K = 3 minimises minutes RMSE on the 2022-26 backtest (src/ratings/minutes_backtest.py): stars bias -0.4 mpg vs -1.8 normalised
_MPG_CAL = dict(a=6.638110739949375, b=0.8343405725166403)       # actual mpg ~ a + b mpg_hat on the top-40 mpg_hat players, 2022-26 (src/players/mpg_calib.py -> data/clean/g4_mpg_calib.json)


def allocate_minutes_normalised(d):
    """Original G2 allocation: every player's expected minutes scaled proportionally to team minutes (deflates stars 6-12%)."""
    raw = (d.mpg_hat * d.gfrac_hat * 82 * d.w_team).values.astype(float)
    cap = np.maximum(MPG_CAP * 82 * d.gfrac_hat.values * d.w_team.values, 1e-6)
    m = raw.copy()
    for _ in range(60):
        tot = m.sum()
        if tot <= 0: break
        m = np.minimum(m * (TEAM_MIN / tot), cap)
        if abs(m.sum() - TEAM_MIN) < 1: break
    return m


def allocate_minutes(d):
    """Star-protected allocation (G8 fix): the top-5 by mpg_hat keep their per-game minutes (veteran mpg_hat calibrated by a + b x mpg_hat, capped at MPG_CAP; players without history keep mpg_hat);
    the remaining players absorb the scaling to team minutes. Coaches protect starters' minutes; proportional scaling deflated stars 6-12%."""
    if not STAR_PROTECT: return allocate_minutes_normalised(d)
    g = (d.gfrac_hat * 82 * d.w_team).values.astype(float); mh = d.mpg_hat.values.astype(float); n = len(d)
    nh = d.no_history.fillna(False).values.astype(bool) if "no_history" in d else np.zeros(n, bool)
    order = np.argsort(-np.where(g > 0, mh, -1)); top = [i for i in order[:STAR_K] if g[i] > 0]
    adj = np.where(nh, mh, _MPG_CAL["a"] + _MPG_CAL["b"] * mh)
    m = np.zeros(n); prot = {i: min(adj[i], MPG_CAP) * g[i] for i in top}
    for i, v in prot.items(): m[i] = v
    rest = [i for i in range(n) if i not in prot]; room = TEAM_MIN - sum(prot.values())
    if room <= 0:
        sc = TEAM_MIN / sum(prot.values()); return m * sc
    raw = np.array([mh[i] * g[i] for i in rest]); cap = np.array([MPG_CAP * g[i] for i in rest]); x = raw.copy()
    for _ in range(60):
        tot = x.sum()
        if tot <= 0: break
        x = np.minimum(x * (room / tot), cap)
        if abs(x.sum() - room) < 1: break
    for k, i in enumerate(rest): m[i] = x[k]
    return m


def actual_roster(D, s):
    st = D.st[(D.st.season == s) & D.st.bbref_id.notna()].copy()
    tot_g = D.ps[D.ps.season == s].set_index("bbref_id").games
    st["w_team"] = (st.g_team / st.bbref_id.map(tot_g).replace(0, np.nan)).clip(0, 1).fillna(1.0)
    return st.rename(columns={"team": "abbr"})[["abbr", "bbref_id", "w_team"]]


def team_features(D, s, P, metric="bpm", roster=None, rating_adj=None, pl=None):
    """roster: DataFrame[abbr, bbref_id, w_team]; None => actual season-s membership proxy (backtest)."""
    if roster is None:
        roster = actual_roster(D, s)
    if pl is None:
        pl = predict_players(D, s, P, metric, roster_ids=roster.bbref_id.unique())
    out = []
    for abbr, d in roster.groupby("abbr"):
        d = d.merge(pl, left_on="bbref_id", right_index=True, how="left")
        d["min"] = allocate_minutes(d)
        rat = d.rating + (d.bbref_id.map(rating_adj).fillna(0) if rating_adj else 0)
        share = d["min"] / (TEAM_MIN / 5)
        prev = set(D.st[(D.st.season == s - 1) & (D.st.team == abbr)].bbref_id)
        out.append(dict(abbr=abbr, season=s, teamsum=float((share * rat).sum()),
                        continuity=float(d.loc[d.bbref_id.isin(prev), "min"].sum() / d["min"].sum()),
                        top8_share=float(d["min"].nlargest(8).sum() / TEAM_MIN)))
    return pd.DataFrame(out), pl


def prev_roster(D, s):
    """Pessimistic point-in-time proxy: every player who ended season s-1 with the team (no offseason moves known)."""
    st = D.st[(D.st.season == s - 1) & D.st.bbref_id.notna()]
    r = st.rename(columns={"team": "abbr"})[["abbr", "bbref_id"]].drop_duplicates()
    return r.assign(w_team=1.0)


def first_roster(D, s):
    """Start-of-season proxy: each player on the FIRST team listed for him in season s (bbref lists stints chronologically);
    no in-season trade leakage. Late-season signings still appear (small residual leakage)."""
    st = D.st[(D.st.season == s) & D.st.bbref_id.notna()]
    r = st.drop_duplicates("bbref_id", keep="first").rename(columns={"team": "abbr"})[["abbr", "bbref_id"]]
    return r.assign(w_team=1.0)


def season_frame(D, s, P, metric="bpm", roster_mode="actual"):
    ro = {"prev": prev_roster, "first": first_roster}.get(roster_mode)
    f, _ = team_features(D, s, P, metric, roster=(ro(D, s) if ro else None))
    ts = D.ts
    prev = ts[ts.season == s - 1][["abbr", "srs", "wins"]].rename(columns={"srs": "prev_srs", "wins": "prev_wins"})
    cur = ts[ts.season == s][["abbr", "srs", "wins", "conf", "gp", "playoffs"]]
    return f.merge(prev, on="abbr", how="left").merge(cur, on="abbr", how="left")


def fit_team_layer(frames):
    F = pd.concat(frames).dropna(subset=["prev_srs", "srs", "teamsum"]).copy()
    F["ts_c"] = F.teamsum - F.groupby("season").teamsum.transform("mean")
    X = np.column_stack([np.ones(len(F)), F.ts_c, F.prev_srs, F.continuity * F.prev_srs]); y = F.srs.values
    beta = _wols(X, y, np.ones(len(F)), ridge=1e-6)
    res = y - X @ beta
    kw = float(((F.wins - 41) * F.srs).sum() / (F.srs ** 2).sum())
    pred = X @ beta
    wres = F.wins - 41 - kw * (pred - pred.mean())
    return dict(beta=beta.tolist(), srs_resid_sd=float(res.std(ddof=4)), k_wins=kw, wins_resid_sd=float(wres.std(ddof=2)), n=int(len(F)))


def predict_wins(frame, L):
    f = frame.copy()
    f["ts_c"] = f.teamsum - f.teamsum.mean()
    b = L["beta"]; ps_ = f.prev_srs.fillna(0)
    f["pred_srs"] = b[0] + b[1] * f.ts_c + b[2] * ps_ + b[3] * f.continuity * ps_
    f["pred_srs"] -= f.pred_srs.mean()
    f["pred_wins"] = 41 + L["k_wins"] * f.pred_srs        # sums to 1230 exactly
    return f
