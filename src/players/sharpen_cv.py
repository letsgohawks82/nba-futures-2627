"""Leave-one-season-out fit of the leader sharpening exponent gamma (p^gamma renormalised per stat-season). Reports gamma per fold, pooled gamma with a season-block bootstrap CI,
and out-of-sample reliability / Brier / log score before vs after. Output data/clean/g4_leader_sharpen.json."""
import json
import numpy as np, pandas as pd
from .leader_backtest import frame
from .rates import C

GRID = np.round(np.arange(0.8, 2.41, 0.05), 2)

def sharpen(g, gam):
    q = g.p ** gam; return q / q.sum() if q.sum() > 0 else q

def score(D, gam, seasons=None):
    P = D[(D.bbref_id != "_missed")]
    if seasons is not None: P = P[P.season.isin(seasons)]
    return float(np.mean([np.log(max(float((sharpen(g, gam) * g.win).sum()), 1e-4)) for _, g in P.groupby(["season", "stat"])]))

def fit_gamma(D, seasons):
    sc = [score(D, g, seasons) for g in GRID]; return float(GRID[int(np.argmax(sc))])

def reliability(P, col):
    P = P.assign(bk=pd.cut(P[col], [0, .02, .05, .15, .35, 1.01], right=False))
    return P.groupby("bk", observed=True).agg(n=(col, "size"), mean_p=(col, "mean"), freq=("win", "mean")).reset_index().astype({"bk": str}).round(4).to_dict("records")

def main(seed=5):
    D = frame(seed=seed); P = D[D.bbref_id != "_missed"].copy(); seasons = sorted(P.season.unique()); folds = {}
    P["q_oos"] = np.nan
    for s in seasons:
        gam = fit_gamma(D, [x for x in seasons if x != s]); folds[int(s)] = gam
        m = P.season == s; P.loc[m, "q_oos"] = P[m].groupby("stat").p.transform(lambda x: (x ** gam) / (x ** gam).sum())
    pooled = fit_gamma(D, seasons)
    rng = np.random.default_rng(1); boots = []
    for _ in range(200):
        bs = list(rng.choice(seasons, len(seasons), replace=True)); sc = []
        for g in GRID:
            ls = []
            for s in bs: ls.append(score(D, g, [s]))
            sc.append(np.mean(ls))
        boots.append(float(GRID[int(np.argmax(sc))]))
    lo, hi = np.percentile(boots, [10, 90])
    brier = lambda col: float(np.mean((P[col] - P.win) ** 2))
    ls = lambda col: float(np.mean([np.log(max(float((g[col] * g.win).sum()), 1e-4)) for _, g in P.groupby(["season", "stat"])]))
    out = dict(gamma=pooled, gamma_ci80=[float(lo), float(hi)], fold_gammas=folds, boot_sd=float(np.std(boots)), oos=dict(
        brier_before=brier("p"), brier_after=brier("q_oos"), logscore_before=ls("p"), logscore_after=ls("q_oos"),
        reliability_before=reliability(P, "p"), reliability_after=reliability(P, "q_oos")))
    json.dump(out, open(C("g4_leader_sharpen.json"), "w"), indent=1); return out

if __name__ == "__main__":
    print(json.dumps(main(), indent=1))
