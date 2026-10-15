"""Fit game-level parameters on 2021-22 -> 2025-26: HCA, back-to-back effects, sigma_game (RS) and playoff HCA / sigma. Margin model:
   margin_home = HCA + c*(srs_h - srs_a) + beta_h*b2b_h + beta_a*b2b_a + eps,  eps ~ N(0, sigma_game)  (srs = end-of-season bbref SRS)"""
import json, os, datetime
import numpy as np, pandas as pd
from ..ratings.prep import team_seasons
from ..data.teams import NAME2ABBR
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def games_frame():
    g = pd.read_parquet(os.path.join(ROOT, "data/clean/games_hist.parquet"))
    g["season"] = g.season.astype(int)
    g["date"] = pd.to_datetime(g.date_game, format="%a, %b %d, %Y")
    g["hp"] = pd.to_numeric(g.home_pts, errors="coerce"); g["ap"] = pd.to_numeric(g.visitor_pts, errors="coerce")
    g["home"] = g.home_team_name.replace({"Charlotte Bobcats": "Charlotte Hornets"}).map(NAME2ABBR); g["away"] = g.visitor_team_name.replace({"Charlotte Bobcats": "Charlotte Hornets"}).map(NAME2ABBR)
    g = g.dropna(subset=["hp", "ap", "home", "away"]).sort_values(["season", "date"]).reset_index(drop=True)
    g["margin"] = g.hp - g.ap; g["total"] = g.hp + g.ap
    g["ot"] = g.overtimes.fillna("").str.len() > 0
    out = []
    for s, d in g.groupby("season"):
        n_rs = 1230 if s not in (2020, 2021) else (1080 if s == 2021 else None)
        if s == 2020: n_rs = 1059
        cut = d.date.iloc[n_rs - 1]
        d = d.assign(post=d.date > cut); out.append(d)
    return pd.concat(out, ignore_index=True)

def add_rest(g):
    rows = []
    for t in ("home", "away"):
        rows.append(g[["season", "date", t]].rename(columns={t: "team"}).assign(idx=g.index, side=t))
    L = pd.concat(rows).sort_values(["team", "season", "date", "idx"])
    L["prev"] = L.groupby(["team", "season"]).date.shift(1)
    L["b2b"] = ((L.date - L.prev).dt.days == 1).astype(int)
    for t in ("home", "away"):
        g["b2b_" + t[0]] = L[L.side == t].set_index("idx").b2b
    return g

def fit(save=True):
    g = add_rest(games_frame()); ts = team_seasons().set_index(["season", "abbr"]).srs
    g["srs_d"] = [ts.get((s, h), np.nan) - ts.get((s, a), np.nan) for s, h, a in zip(g.season, g.home, g.away)]
    d = g[(g.season >= 2022) & g.srs_d.notna()]
    rs = d[~d.post]; po = d[d.post]
    X = np.column_stack([np.ones(len(rs)), rs.srs_d, rs.b2b_h, rs.b2b_a]); y = rs.margin.values
    b, *_ = np.linalg.lstsq(X, y, rcond=None); res = y - X @ b
    # SEs
    cov = np.linalg.inv(X.T @ X) * res.var(ddof=4); se = np.sqrt(np.diag(cov))
    # sigma with slope fixed at 1 (the simulator's ratings are on the SRS scale)
    y1 = y - rs.srs_d.values
    X1 = np.column_stack([np.ones(len(rs)), rs.b2b_h, rs.b2b_a]); b1, *_ = np.linalg.lstsq(X1, y1, rcond=None); res1 = y1 - X1 @ b1
    cov1 = np.linalg.inv(X1.T @ X1) * res1.var(ddof=3); se1 = np.sqrt(np.diag(cov1))
    # playoff / post-season games
    yp = po.margin.values - po.srs_d.values; hca_po = float(yp.mean()); sd_po = float(yp.std(ddof=1)); se_po = sd_po / np.sqrt(len(yp))
    tot = rs.total.values
    P = dict(n_rs=int(len(rs)), seasons="2021-22..2025-26", slope_on_srs=float(b[1]), slope_se=float(se[1]),
             hca=float(b1[0]), hca_se=float(se1[0]), b2b_home=float(b1[1]), b2b_home_se=float(se1[1]), b2b_away=float(b1[2]), b2b_away_se=float(se1[2]),
             sigma_game=float(res1.std(ddof=3)), n_post=int(len(po)), hca_post=hca_po, hca_post_se=float(se_po), sigma_post=sd_po,
             mean_total=float(tot.mean()), sd_total=float(tot.std()), ot_rate=float(rs.ot.mean()), mean_abs_srs_d=float(rs.srs_d.abs().mean()))
    if save:
        json.dump(P, open(os.path.join(ROOT, "data/clean/game_model_fit.json"), "w"), indent=1)
        pv = json.load(open(os.path.join(ROOT, "params/provenance.json"))); now = datetime.date.today().isoformat()
        for k, m in [("hca", "OLS: margin - srs_diff ~ 1 + b2b_h + b2b_a (home margin pts)"), ("sigma_game", "sd of residual margin"), ("b2b_home", "OLS"), ("b2b_away", "OLS"), ("hca_post", "mean of (margin - srs_diff) in post-RS games (play-in+playoffs)"), ("sigma_post", "sd, post-RS games")]:
            pv[f"game_{k}"] = dict(value=P[k], method=m, data_window="2021-22..2025-26 (end-of-season SRS as strength)", n=P["n_rs"] if "post" not in k else P["n_post"], fit_date=now, code_path="src/sim/fit_game_model.py")
        json.dump(pv, open(os.path.join(ROOT, "params/provenance.json"), "w"), indent=1)
    return P, g

if __name__ == "__main__":
    P, g = fit(); print(json.dumps(P, indent=1))
