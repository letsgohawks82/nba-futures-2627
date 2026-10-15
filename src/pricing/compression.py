"""Compression test: regress (model - market fair median) on market median across 30 teams. Writes data/clean/compression_test.json."""
import json, os, sys
import numpy as np, pandas as pd
from .diagnostics import wins_table
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
C = lambda f: os.path.join(ROOT, "data", "clean", f)

def slope_ci(x, y, B=4000, seed=1):
    X = np.column_stack([np.ones(len(x)), x]); b = np.linalg.lstsq(X, y, rcond=None)[0]; res = y - X @ b
    se = np.sqrt(np.diag(np.linalg.inv(X.T @ X) * res.var(ddof=2)))[1]; rng = np.random.default_rng(seed); bs = []
    for _ in range(B):
        i = rng.integers(0, len(x), len(x)); bs.append(np.polyfit(x[i], y[i], 1)[0])
    return float(b[1]), float(se), [float(np.percentile(bs, 10)), float(np.percentile(bs, 90))], [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]

def run(table="pricing_table.csv", write=True):
    o = pd.read_csv(C(table)); S = pd.read_csv(C("sim_team_summary.csv")).set_index("team")
    W, st = wins_table(o, S); W.round(3).to_csv(C("model_vs_market_wins_table.csv"))
    d = (W.model - W.mkt_median).values; x = W.mkt_median.values
    b, se, ci80, ci95 = slope_ci(x, d)
    out = dict(slope_diff_on_market=b, se=se, ci80=ci80, ci95=ci95, significant_negative_95=bool(ci95[1] < 0), significant_negative_80=bool(ci80[1] < 0), apply_rule=bool(ci95[1] < 0), **st)
    if write: json.dump(out, open(C("compression_test.json"), "w"), indent=1)
    return out, W

if __name__ == "__main__":
    out, W = run(sys.argv[1] if len(sys.argv) > 1 else "pricing_table.csv", write=len(sys.argv) <= 2); print(json.dumps(out, indent=1))
