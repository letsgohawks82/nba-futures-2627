"""Backtest of minutes allocation variants: predicted per-game-played minutes (allocated minutes / expected games) vs actual mpg, by within-team rank of mpg_hat, 2022-2026.
Variants: normalised (G2), star-protected top-K with the a + b x mpg_hat calibration (K = 3, 5, 8, 10)."""
import json
import numpy as np, pandas as pd
from . import model as M
from .model import Data, fit_player_model, predict_players, actual_roster

def run():
    D = Data(); rows = []
    for s in range(2022, 2027):
        P = fit_player_model(D, s - 1); ro = actual_roster(D, s); pl = predict_players(D, s, P, roster_ids=ro.bbref_id.unique())
        act = D.ps[D.ps.season == s].drop_duplicates("bbref_id").set_index("bbref_id")
        for ab, r in ro.groupby("abbr"):
            d = r.merge(pl, left_on="bbref_id", right_index=True, how="left"); d["w_team"] = d.w_team.clip(0, 1)
            d = d[d.mpg_hat.notna()].reset_index(drop=True)
            if len(d) < 8: continue
            d["rank"] = d.mpg_hat.rank(ascending=False, method="first")
            for name, (prot, K) in {"normalised": (False, 5), "K3": (True, 3), "K5": (True, 5), "K8": (True, 8), "K10": (True, 10)}.items():
                M.STAR_PROTECT = prot; M.STAR_K = K; m = M.allocate_minutes(d)
                g = (d.gfrac_hat * 82 * d.w_team).values; pred = m / np.maximum(g, 1e-6)
                for i in range(len(d)):
                    b = d.bbref_id[i]
                    if b in act.index and act.games[b] >= 25 and d["rank"][i] <= 12: rows.append(dict(season=s, team=ab, variant=name, rank=int(d["rank"][i]), pred=pred[i], act=act.mp[b] / act.games[b]))
    M.STAR_PROTECT = True; M.STAR_K = 5
    R = pd.DataFrame(rows); R["grp"] = pd.cut(R["rank"], [0, 5, 8, 12], labels=["1-5", "6-8", "9-12"])
    out = R.groupby(["variant", "grp"], observed=True).apply(lambda g: pd.Series(dict(n=len(g), bias=float((g.pred - g.act).mean()), rmse=float(np.sqrt(((g.pred - g.act) ** 2).mean())))), include_groups=False).round(2)
    allv = R.groupby("variant").apply(lambda g: float(np.sqrt(((g.pred - g.act) ** 2).mean())), include_groups=False).round(3)
    return out, allv, R

if __name__ == "__main__":
    out, allv, R = run(); print(out.to_string()); print(allv.to_string()); R.to_csv("data/clean/minutes_backtest_rows.csv", index=False)
