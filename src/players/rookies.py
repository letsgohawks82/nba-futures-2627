"""Rookie box-score model for ROY: per-36 PTS and REB+AST as a function of draft slot and age, plus a rookie minutes-error SD
(rookie mpg vs the slot/age expectation) used as an upper bound on the minutes-projection error. Fit on 2015-2026 rookies with >= 300 minutes."""
import json
import numpy as np, pandas as pd
from .awards import hist_frame
from .rates import C


def fit():
    m, _ = hist_frame(); r = m[m.rookie & (m.mp >= 300) & (m.season >= 2015)].copy()
    r["pts36"] = r.ppg * 36 / (r.mp / r.games); r["ra36"] = r.rebast * 36 / (r.mp / r.games); r["mpg"] = r.mp / r.games
    X = np.column_stack([np.ones(len(r)), r.lnpick.values, (r.age.values - 20.0)])
    out = {}
    for y in ("pts36", "ra36", "mpg"):
        yy = np.log(r[y].values); b, *_ = np.linalg.lstsq(X, yy, rcond=None); res = yy - X @ b
        H = X @ np.linalg.pinv(X.T @ X) @ X.T; loo = res / (1 - np.diag(H))          # leave-one-out residuals
        out[y] = dict(coef=b.tolist(), sd=float(res.std(ddof=3)), loo_sd=float(loo.std()), n=int(len(r)))
    return out, r


def predict(fit_, pick, age):
    x = np.array([1.0, np.log(max(pick, 1.0)), age - 20.0]); res = {}
    for y in ("pts36", "ra36", "mpg"): res[y] = float(np.exp(x @ np.array(fit_[y]["coef"])))
    return res


if __name__ == "__main__":
    f, r = fit(); print(json.dumps(f, indent=1)); json.dump(f, open(C("g4_rookie_fit.json"), "w"), indent=1)
    print(predict(f, 1, 19), predict(f, 5, 19), predict(f, 30, 21))
