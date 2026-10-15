"""Drivers behind the biggest model-vs-market wins disagreements."""
import sys, os
import numpy as np, pandas as pd
from ..ratings.prep import player_seasons, team_seasons
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
C = lambda f: os.path.join(ROOT, "data", "clean", f)

def run(top_n=10, table="model_vs_market_wins_table.csv"):
    W = pd.read_csv(C(table), index_col=0); W["absd"] = W["diff"].abs()
    teams = W.sort_values("absd", ascending=False).head(top_n).index.tolist()
    ps, st = player_seasons(); ts = team_seasons(); P = pd.read_csv(C("player_projection_2027.csv")); T = pd.read_csv(C("team_projection_2027.csv")).set_index("abbr")
    inj = pd.read_csv(C("injuries_espn.csv")); R = pd.read_csv(C("rosters_espn.csv"))
    ids = pd.read_csv(C("player_ids.csv")); S26 = st[(st.season == 2026) & st.bbref_id.notna()]
    bpm = ps[ps.season == 2026].drop_duplicates("bbref_id").set_index("bbref_id")
    rows = []
    cur_team = dict(zip(ids.bbref_id.str.split(";").str[0], ids.team))
    for t in teams:
        d = P[P.abbr == t].sort_values("proj_min", ascending=False)
        top = d.head(8)
        out_ = inj[(inj.status == "Out")]
        lost = S26[(S26.team == t) & (S26.mp_team >= 800) & (S26.bbref_id.map(cur_team) != t)]
        gained = P[(P.abbr == t)]
        arrivals = [(r["name"], r.rating) for _, r in gained.iterrows() if isinstance(r.bbref_id, str) and r.bbref_id in S26.bbref_id.values and not ((S26.bbref_id == r.bbref_id) & (S26.team == t)).any() and r.proj_min > 800]
        nohist = d[d.no_history].proj_min.sum() / d.proj_min.sum()
        nodk = d[d.dpm.isna()].proj_min.sum() / d.proj_min.sum()
        rows.append(dict(team=t, line=W.loc[t, "line"], market=W.loc[t, "mkt_median"], model=W.loc[t, "model"], diff=W.loc[t, "diff"], prior_wins=T.loc[t, "prev_wins"], prior_srs=T.loc[t, "prev_srs"], pred_srs=T.loc[t, "pred_srs"],
                         continuity=T.loc[t, "continuity"], teamsum=T.loc[t, "teamsum"],
                         top8=" | ".join(f"{r['name']} r{r.rating:+.1f} dpm{r.dpm:+.1f} {r.proj_mpg:.0f}mpg/{r.proj_gp:.0f}g" if pd.notna(r.dpm) else f"{r['name']} r{r.rating:+.1f} dpm-- {r.proj_mpg:.0f}mpg/{r.proj_gp:.0f}g" for _, r in top.iterrows()),
                         departed=", ".join(f"{bpm.loc[b,'name_display'] if b in bpm.index else b}({bpm.loc[b,'bpm'] if b in bpm.index else 0:+.1f} bpm, {m:.0f} min)" for b, m in zip(lost.bbref_id, lost.mp_team)),
                         arrived=", ".join(f"{n} (r{r:+.1f})" for n, r in arrivals), out=", ".join(f"{n}({ty})" for n, ty in zip(out_[out_.team.str.contains(t, na=False)].name, out_[out_.team.str.contains(t, na=False)].type)),
                         pct_min_nohistory=nohist, pct_min_no_darko=nodk))
    D = pd.DataFrame(rows); D.to_csv(C("top_disagreements_drivers.csv"), index=False); return D

if __name__ == "__main__":
    D = run(); pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 400)
    for _, r in D.iterrows():
        print(f"\n== {r.team}: line {r.line} | market {r.market:.1f} | model {r.model:.1f} | diff {r['diff']:+.1f} | prior {r.prior_wins:.0f}w SRS {r.prior_srs:+.1f} -> pred SRS {r.pred_srs:+.1f}, continuity {r.continuity:.2f}")
        print("  top8:", r.top8); print("  departed:", r.departed); print("  arrived:", r.arrived); print("  out:", r.out); print(f"  minutes from no-history players {r.pct_min_nohistory:.0%}, without DARKO {r.pct_min_no_darko:.0%}")
