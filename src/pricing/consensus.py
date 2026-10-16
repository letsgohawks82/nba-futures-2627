"""External-consensus layer for WINS bets (mirrors the live formulas in M_WinDist / Raw_Consensus).
For every source (ours included) regress its projected wins on the book's fair median across the 30 teams, and use the RESIDUALS (this removes each source's own compression / expansion
relative to the market, so no fixed slope is needed). market fair median = line + (fair P(over) - 0.5) / p_per_win.
A WINS bet PASSES when both roster-aware residuals (ours and PredictionEngine) point the bet's way, each >= cons_min. Results-based sources (Opta TRACR, Massey) only count for teams with
continuity >= rb_min_continuity and no top-3-minutes player who changed teams or missed most of 2025-26; when they count, they must not BOTH point the other way (interpretation: they can veto, not confirm).
MARKET_INFORMED (ESPN, TeamRankings) and EXPERT (Bleacher Report) sources are displayed only. Source tags come from the raw file."""
import json, os
import numpy as np, pandas as pd
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
C = lambda f: os.path.join(ROOT, "data", "clean", f)


def params():
    return json.load(open(os.path.join(ROOT, "params/tier1_overrides.json")))


def raw():
    d = pd.read_csv(os.path.join(ROOT, "data/consensus/raw_consensus_20261016.csv"))
    meta = d.drop_duplicates("source").set_index("source")[["source_type", "method", "url", "pull_date"]]
    M = d.pivot(index="team", columns="source", values="proj_wins")
    return M, meta


def rb_eligible():
    """team -> (eligible, reason). Eligible = continuity >= threshold and none of the top-3 projected-minutes players changed teams or played < rb_min_games_prev games in 2025-26."""
    pr = params(); from ..ratings.model import Data
    D = Data(); P = pd.read_csv(C("player_projection_2027.csv")); tp = pd.read_csv(C("team_projection_2027.csv")).set_index("abbr")
    st26 = D.st[(D.st.season == 2026) & D.st.bbref_id.notna()]; ps26 = D.ps[D.ps.season == 2026].drop_duplicates("bbref_id").set_index("bbref_id")
    out = {}
    for t, d in P.groupby("abbr"):
        why = []
        if tp.continuity[t] < pr["rb_min_continuity"]: why.append(f"continuity {tp.continuity[t]:.2f} < {pr['rb_min_continuity']}")
        for _, r in d.nlargest(3, "proj_min").iterrows():
            teams = set(st26[st26.bbref_id == r.bbref_id].team)
            if teams and t not in teams: why.append(f"{r['name']} changed teams")
            g = float(ps26.games.get(r.bbref_id, np.nan)) if r.bbref_id in ps26.index else np.nan
            if pd.notna(g) and g < pr["rb_min_games_prev"]: why.append(f"{r['name']} played {g:.0f} games in 2025-26")
        out[t] = (len(why) == 0, "; ".join(why))
    return out


def table(o):
    """o: pricing_table with WINS OVER rows (line, fair). Returns (T, summary) - T indexed by team."""
    pr = params(); M, meta = raw(); tp = pd.read_csv(C("team_projection_2027.csv")).set_index("abbr")
    w = o[(o.market == "WINS") & (o.side == "OVER")].set_index("team")
    T = pd.DataFrame(index=w.index); T["line"] = w.line; T["fair_over"] = w.fair; T["median"] = T.line + (T.fair_over - 0.5) / pr["p_per_win"]
    proj = pd.DataFrame({"ours": tp.pred_wins.reindex(T.index)}); proj = proj.join(M.reindex(T.index))
    summ = {}
    for s in proj.columns:
        b, a = np.polyfit(T["median"], proj[s], 1); res = proj[s] - (a + b * T["median"])
        T["proj_" + s] = proj[s]; T["res_" + s] = res; summ[s] = dict(slope=float(b), intercept=float(a), resid_sd=float(res.std(ddof=2)), r2=float(np.corrcoef(T["median"], proj[s])[0, 1] ** 2),
                                                                     type=("STAT_MODEL" if s == "ours" else meta.source_type[s]), method=("roster_aware" if s == "ours" else meta.method[s]))
    m = pr["cons_min"]; ra = pr["roster_aware"]; rbs = [s for s in M.columns if meta.method[s] == "results_based"]
    elig = rb_eligible(); T["rb_eligible"] = [elig[t][0] for t in T.index]; T["rb_reason"] = [elig[t][1] for t in T.index]
    up = np.ones(len(T), bool); dn = np.ones(len(T), bool)
    for s in ra: up &= (T["res_" + s] >= m).values; dn &= (T["res_" + s] <= -m).values
    rb_oppose_up = np.zeros(len(T), bool); rb_oppose_dn = np.zeros(len(T), bool)          # results-based both point against the bet (only if eligible)
    if rbs:
        rb_oppose_up = (np.all([T["res_" + s] <= -m for s in rbs], axis=0)) & T.rb_eligible.values      # bet OVER vetoed
        rb_oppose_dn = (np.all([T["res_" + s] >= m for s in rbs], axis=0)) & T.rb_eligible.values      # bet UNDER vetoed
    T["pass_over"] = up & ~rb_oppose_up; T["pass_under"] = dn & ~rb_oppose_dn
    T["res_min_roster_aware"] = np.minimum.reduce([T["res_" + s].abs().values for s in ra])
    T["strong"] = T.res_min_roster_aware >= pr["cons_strong"]
    T["sources_display"] = ""
    return T, summ
