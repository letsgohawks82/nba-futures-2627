"""Bet-card anatomy, model-vs-market wins, zero-sum (1,241) filter. python -m src.pricing.diagnostics [pricing_table.csv]"""
import sys, json, math, os
import numpy as np, pandas as pd
from scipy.stats import norm
from .price import wins_prob_shift
from ..sim.inputs import TEAM_LIST

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
C = lambda f: os.path.join(ROOT, "data", "clean", f)

def anatomy(o, qual_col="qualifies"):
    Q = o[o[qual_col]].copy(); out = {}
    Q["edge_pp"] = (Q.model_prob - Q.fair) * 100
    g = Q.groupby("market").agg(n=("ev", "size"), stake=("kelly_portfolio", "sum"), med_ev=("ev", "median"), med_edge_pp=("edge_pp", "median")).round(4)
    out["by_market"] = g.sort_values("stake", ascending=False)
    w = Q[Q.market == "WINS"]
    out["wins_split"] = w.groupby("side").agg(n=("ev", "size"), stake=("kelly_portfolio", "sum"), med_ev=("ev", "median")).round(4)
    fam = Q[Q.market.isin(["TITLE", "CUP"]) | Q.market.str.startswith(("CONF", "DIV", "CUP_"))].copy()
    fam["family"] = np.where(fam.market == "TITLE", "TITLE", np.where(fam.market.str.startswith("CONF"), "CONF", np.where(fam.market.str.startswith("DIV"), "DIV", np.where(fam.market == "CUP", "CUP", "CUP_GROUP"))))
    fam["type"] = np.where(fam.fair >= 0.10, "favorite (fair>=10%)", "longshot (fair<10%)")
    out["fav_long"] = fam.groupby(["family", "type"]).agg(n=("ev", "size"), stake=("kelly_portfolio", "sum"), med_ev=("ev", "median")).round(4)
    out["overall"] = dict(n=int(len(Q)), stake=float(Q.kelly_portfolio.sum()), median_ev=float(Q.ev.median()), median_edge_pp=float(Q.edge_pp.median()), median_ev_lo=float(Q.ev_lo.median()))
    return Q, out

def wins_table(o, S):
    w = o[(o.market == "WINS") & (o.side == "OVER")].copy().set_index("team"); sd = S.wins_sd.mean()
    w["mkt_median"] = w.line + sd * norm.ppf(w.fair); w["model"] = S.wins_mean.reindex(w.index); w["diff"] = w.model - w.mkt_median
    stats = dict(rmse=float(np.sqrt((w["diff"] ** 2).mean())), mean_signed=float(w["diff"].mean()), mae=float(w["diff"].abs().mean()), corr=float(np.corrcoef(w.model, w.mkt_median)[0, 1]),
                 sd_model=float(w.model.std()), sd_market=float(w.mkt_median.std()), slope_model_on_market=float(np.polyfit(w.mkt_median, w.model, 1)[0]), sum_market_lines=float(w.line.sum()))
    return w[["line", "mkt_median", "model", "diff"]], stats

if __name__ == "__main__":
    f = sys.argv[1] if len(sys.argv) > 1 else "pricing_table.csv"
    o = pd.read_csv(C(f)); S = pd.read_csv(C("sim_team_summary.csv")).set_index("team")
    Q, a = anatomy(o)
    pd.set_option("display.width", 200)
    print("OVERALL", a["overall"]); print(a["by_market"].to_string()); print(a["wins_split"].to_string()); print(a["fav_long"].to_string())
    W, st = wins_table(o, S); print(json.dumps(st, indent=1)); W.round(3).to_csv(C("model_vs_market_wins_table.csv"))
