"""Per-season Brier + pooled reliability with bootstrap CIs for the pricing-relevant probabilities."""
import json, os, sys
import numpy as np, pandas as pd
from scipy.stats import norm as N
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
rng = np.random.default_rng(11)
half = lambda x: np.floor(x) + 0.5

def brier(p, y): return float(np.mean((p - y) ** 2))

def boot_ci(p, y, B=2000):
    n = len(p); v = [brier(p[i], y[i]) for i in (rng.integers(0, n, n) for _ in range(B))]
    return [float(np.percentile(v, 10)), float(np.percentile(v, 90))]

def reliability(p, y, edges=(0, .1, .25, .4, .6, .75, .9, 1.0001)):
    b = np.digitize(p, edges) - 1; rows = []
    for i in range(len(edges) - 1):
        m = b == i
        if m.sum(): rows.append(dict(bin=f"{edges[i]:.2f}-{min(edges[i+1],1):.2f}", n=int(m.sum()), mean_pred=float(p[m].mean()), freq=float(y[m].mean()), se=float(np.sqrt(max(y[m].mean() * (1 - y[m].mean()), 1e-9) / m.sum()))))
    return rows

def run(path="data/clean/backtest_predictions.csv"):
    R = pd.read_csv(os.path.join(ROOT, path)); out = {}
    R["line_med"] = half(R.pred_wins); R["line_b4"] = half(R.b4_wins)
    tests = {
        "P(over median projection line)": (1 - N.cdf((R.line_med - R.pred_wins) / R.sigma), (R.w82 > R.line_med).astype(float)),
        "P(over B4 market-proxy line)": (1 - N.cdf((R.line_b4 - R.pred_wins) / R.sigma), (R.w82 > R.line_b4).astype(float)),
        "P(top-10 in conference)": (R.p_top10, R.act_top10.astype(float)),
        "P(top-6 in conference)": (R.p_top6, R.act_top6.astype(float))}
    for name, (p, y) in tests.items():
        p = np.asarray(p, float); y = np.asarray(y, float); rows = []
        for t in sorted(R.test_season.unique()):
            m = (R.test_season == t).values
            base = np.full(m.sum(), y[m].mean()) if "over" not in name else np.full(m.sum(), 0.5)
            rows.append(dict(season=int(t), n=int(m.sum()), brier=brier(p[m], y[m]), ci80=boot_ci(p[m], y[m], 800), brier_ref=brier(base, y[m])))
        out[name] = dict(by_season=rows, pooled=dict(brier=brier(p, y), ci80=boot_ci(p, y), ref=("0.5" if "over" in name else "season climatology"),
                         brier_ref=float(np.mean([r["brier_ref"] for r in rows]))), reliability=reliability(p, y))
    # does the model's disagreement with the B4 line carry information? slope of outcome on (model-B4 gap)
    gap = (R.pred_wins - R.b4_wins).values; yv = (R.w82 - R.b4_wins).values
    slope = float((gap * yv).sum() / (gap ** 2).sum()); 
    bs = [float((gap[i] * yv[i]).sum() / (gap[i] ** 2).sum()) for i in (rng.integers(0, len(gap), len(gap)) for _ in range(2000))]
    out["gap_vs_B4_information"] = dict(slope_actual_on_model_minus_B4=slope, ci80=[float(np.percentile(bs, 10)), float(np.percentile(bs, 90))], note="1.0 = the model's deviation from B4 is fully real; 0 = pure noise")
    return out

if __name__ == "__main__":
    o = run(sys.argv[1] if len(sys.argv) > 1 else "data/clean/backtest_predictions.csv")
    tag = sys.argv[2] if len(sys.argv) > 2 else ""
    json.dump(o, open(os.path.join(ROOT, f"data/clean/backtest_calibration{tag}.json"), "w"), indent=1)
    for k, v in o.items():
        if k.startswith("gap"): print(k, v); continue
        print(k, "pooled", round(v["pooled"]["brier"], 4), [round(x, 4) for x in v["pooled"]["ci80"]], "ref", round(v["pooled"]["brier_ref"], 4))
        print("   by season:", [(r["season"], round(r["brier"], 3)) for r in v["by_season"]])
