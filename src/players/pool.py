"""G4 player pool for 2026-27: sim slots (top-12 per team, per-sim games from the season sims) + odds-named players outside the slots.
Per-game rate predictions (raw), BPM-scale rating, DBPM projection, class, rookies flagged. Stat-level calibration is applied in the draws (leaders.py)."""
import json, os
import numpy as np, pandas as pd
from ..data.namemap import norm
from .rates import table, project, STATS, C

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SEASON = 2027
DB_M = 1500.0          # minutes of shrinkage for the DBPM projection (see awards.fit_dbpm)


def odds_names():
    o = pd.read_csv(os.path.join(ROOT, "data/raw/odds/odds_2026-10-15.csv")); nm = pd.read_csv(C("name_map.csv")); nm = nm[nm.source == "odds_book"].set_index("source_name").canonical
    o = o[o.market.str.startswith("LDR_") | o.market.isin(["MVP", "DPOY", "ROY", "MIP", "SMOY", "CLUTCH", "CUP_MVP"])].copy()
    o["canon"] = [nm.get(s) if isinstance(nm.get(s), str) else s for s in o.selection]
    o["key"] = o.canon.map(norm)
    return o


def dbpm_hat(ps, season, M=DB_M):
    h = pd.concat([ps[ps.season == season - k].assign(w=w, k=k) for k, w in zip((1, 2, 3), (1.0, 0.55, 0.30))])
    h = h[h.dbpm.notna()]; big = h[h.mp >= 500]
    prior = (big.dbpm * big.mp).groupby(big.cls).sum() / big.groupby("cls").mp.sum()
    g = h.assign(wmp=h.w * h.mp, wd=h.w * h.mp * h.dbpm).groupby("bbref_id")[["wmp", "wd"]].sum()
    cls = h.sort_values("k").groupby("bbref_id").cls.first()
    return (g.wd + M * cls.reindex(g.index).map(prior).fillna(0.0)) / (g.wmp + M), prior


TEAM_MIN = 240.0 * 82; MPG_CAP = 38.0; PROTECT_K = 5


def star_protected_mpg(P):
    """Minutes per game PLAYED for the player markets. The team layer (G2) normalises every player's expected minutes proportionally to 240 x 82, which deflates stars by 6-12%
    (the sum of mpg_hat x availability exceeds team minutes because per-game-played mpg already includes teammates' absences). Coaches protect starters' minutes, so here the
    top-5 by mpg_hat per team keep mpg_hat (capped at 38) and the rest absorb the scaling. The team-strength layer is NOT changed (its coefficients were fit on the normalised minutes)."""
    out = P.proj_mpg.copy(); cal = json.load(open(C("g4_mpg_calib.json")))       # actual mpg ~ a + b mpg_hat on the top-40 mpg_hat players, 2022-26 (mpg_calib.py)
    for ab, d in P.groupby("abbr"):
        g = d.gfrac_hat.clip(lower=0.01); raw = d.mpg_hat * g * 82; top = d.mpg_hat.nlargest(PROTECT_K).index
        adj = np.where(d.no_history[top].astype(bool), d.mpg_hat[top], cal["a"] + cal["b"] * d.mpg_hat[top])      # calibration was fit on veterans; rookies keep mpg_hat
        prot = np.minimum(adj, MPG_CAP) * g[top] * 82; rest = [i for i in d.index if i not in top]
        room = TEAM_MIN - prot.sum(); sc = min(1.0, room / max(raw[rest].sum(), 1e-6))
        m = pd.Series(0.0, index=d.index); m[top] = prot; m[rest] = np.minimum(raw[rest] * sc, MPG_CAP * g[rest] * 82)
        out[d.index] = m / (82 * g)
    return out


def build():
    P = pd.read_csv(C("player_projection_2027.csv")); G = pd.read_csv(C("sim_player_games.csv"))
    ps = table(); M0 = json.load(open(C("g4_rate_fit.json")))["M0"]; M0 = {STATS[k]: v for k, v in M0.items()}
    pr = project(ps, SEASON, M0)
    dh, dprior = dbpm_hat(ps, SEASON)
    P["proj_mpg_team_layer"] = P.proj_mpg      # the team layer now allocates star-protected minutes itself (G8); no second adjustment here
    P["key"] = P.name.map(norm)
    P = P.merge(G[["team", "slot", "bbref_id"]].rename(columns={"team": "abbr", "bbref_id": "gid"}), left_on=["abbr", "bbref_id"], right_on=["abbr", "gid"], how="left")
    P["slotted"] = P.slot.notna()
    P = P.join(pr[["cls", "S"] + list(STATS.values())], on="bbref_id", rsuffix="_h")
    cls_prior = {c: g for c, g in ps[(ps.season == 2026) & (ps.mp >= 500)].groupby("cls")}
    pos_guess = ps.sort_values("season").groupby("bbref_id").pos.last()
    P["cls"] = P.cls.fillna(P.bbref_id.map(pos_guess).map({"PG": "G", "SG": "G", "SF": "W", "PF": "B", "C": "B"})).fillna("W")
    P["rookie"] = P.bbref_id.astype(str).str.startswith("rk_") | P.S.isna()
    # no-history players: class prior per-minute rates at 85% of the cohort mean (replacement-ish); only relevant for ROY / depth
    for sn, st in STATS.items():
        pri = ps[(ps.season == 2026) & (ps.mp >= 500)].groupby("cls").apply(lambda g: g[st].sum() / g.mp.sum(), include_groups=False)
        rate = P[st].copy(); miss = rate.isna(); rate[miss] = P.cls[miss].map(pri) * 0.85
        P["pg_" + sn] = rate * P.proj_mpg
    P["dbpm_hat"] = P.bbref_id.map(dh); P["dbpm_hat"] = P.dbpm_hat.fillna(P.cls.map(dprior) * 0.7)
    return P, ps


if __name__ == "__main__":
    P, ps = build(); pd.set_option("display.width", 220)
    print(P[P.slotted].shape, P.rookie.sum())
    print(P.sort_values("pg_PPG", ascending=False).head(12)[["name", "abbr", "proj_mpg", "proj_gp", "pg_PPG", "pg_RPG", "pg_APG", "pg_SPG", "pg_BPG", "pg_TPG", "rating", "dbpm_hat"]].round(2))
