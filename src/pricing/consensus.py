"""External-consensus layer for WINS bets (mirrors the live formulas in M_WinDist).
market fair median = line + (fair P(over) - 0.5) / p_per_win ; compression bias = comp_slope x (median - 41);
bias-adjusted gap = (projection - median) - bias, for our model and each STAT_MODEL source. A WINS bet PASSES when our gap and at least one STAT_MODEL gap
point the same direction as the bet (OVER +, UNDER -), each with magnitude >= cons_min. EXPERT sources are displayed only."""
import json, os
import numpy as np, pandas as pd
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
C = lambda f: os.path.join(ROOT, "data", "clean", f)


def params():
    return json.load(open(os.path.join(ROOT, "params/tier1_overrides.json")))


def table(o):
    """o: pricing_table (needs WINS OVER rows with fair, line). Returns per-team DataFrame."""
    pr = params(); src = json.load(open(os.path.join(ROOT, "data/consensus/sources.json")))["sources"]
    M = pd.read_csv(os.path.join(ROOT, "data/consensus/consensus_wins_2026-10-15.csv")).set_index("team")
    tp = pd.read_csv(C("team_projection_2027.csv")).set_index("abbr")
    w = o[(o.market == "WINS") & (o.side == "OVER")].set_index("team")
    T = pd.DataFrame(index=w.index); T["line"] = w.line; T["fair_over"] = w.fair
    T["median"] = T.line + (T.fair_over - 0.5) / pr["p_per_win"]; T["bias"] = pr["comp_slope"] * (T["median"] - 41.0)
    T["model"] = tp.pred_wins.reindex(T.index); T["gap_model"] = (T.model - T["median"]) - T.bias
    stat = [s["id"] for s in src if s["type"] == "STAT_MODEL"]; exp = [s["id"] for s in src if s["type"] == "EXPERT"]
    for s in stat + exp: T["gap_" + s] = (M[s].reindex(T.index) - T["median"]) - T.bias; T["proj_" + s] = M[s].reindex(T.index)
    m = pr["cons_min"]
    anyup = np.zeros(len(T), bool); anydn = np.zeros(len(T), bool)
    for s in stat: anyup |= (T["gap_" + s] >= m).values; anydn |= (T["gap_" + s] <= -m).values
    T["pass_over"] = (T.gap_model >= m) & anyup; T["pass_under"] = (T.gap_model <= -m) & anydn
    return T, stat, exp
