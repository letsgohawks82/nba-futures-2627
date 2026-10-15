"""Season-long tank carryover audit for the 8 worst 2025-26 teams: pre- vs post-deadline (Feb 5 2026) minutes, availability, lineup quality."""
import glob, io, os, re
import numpy as np, pandas as pd
from bs4 import BeautifulSoup
from .prep import player_seasons, team_seasons
from ..sim.fit_game_model import games_frame
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEADLINE = pd.Timestamp("2026-02-05")

def parse_log(path):
    html = open(path, encoding="utf-8").read().replace("<!--", "").replace("-->", "")
    t = BeautifulSoup(html, "lxml").find("table", id="player_game_log_reg")
    if t is None: return pd.DataFrame()
    rows = []
    for tr in t.find("tbody").find_all("tr"):
        if "thead" in (tr.get("class") or []): continue
        d = {c.get("data-stat"): c.get_text(strip=True) for c in tr.find_all(["th", "td"])}
        rows.append(d)
    return pd.DataFrame(rows)

def mins(s):
    try:
        m, sec = s.split(":"); return int(m) + int(sec) / 60
    except Exception:
        return np.nan

def run():
    ps, st = player_seasons(); ts = team_seasons()
    b8 = ts[ts.season == 2026].sort_values("wins").head(8).abbr.tolist()
    bpm = ps[ps.season == 2026].set_index("bbref_id").bpm
    S = pd.read_csv(os.path.join(ROOT, "data/clean/bottom8_players_2026.csv"))
    G = games_frame(); G = G[G.season == 2026]
    tg = {}
    for t in b8:
        x = G[(G.home == t) | (G.away == t)]; x = x[~x.post]
        tg[t] = (int((x.date <= DEADLINE).sum()), int((x.date > DEADLINE).sum()))
    rows = []
    for r in S.itertuples():
        f = glob.glob(os.path.join(ROOT, "data/raw/gamelogs", f"{r.bbref_id}_2026.html_*"))
        if not f: continue
        L = parse_log(f[0])
        if L.empty: continue
        L["date"] = pd.to_datetime(L.date, errors="coerce"); L = L[L.date.notna()]
        L = L[L.team_name_abbr.replace({"BRK": "BKN", "CHO": "CHA", "PHO": "PHX"}) == r.team]
        L["m"] = L.mp.map(mins); L["played"] = L.m.notna()
        for per, sub in (("pre", L[L.date <= DEADLINE]), ("post", L[L.date > DEADLINE])):
            nt = tg[r.team][0 if per == "pre" else 1]
            gp = int(sub.played.sum()); mp = float(sub.m.sum())
            rea = sub[~sub.played].reason.value_counts().to_dict() if "reason" in sub else {}
            rows.append(dict(team=r.team, bbref_id=r.bbref_id, period=per, team_games=nt, gp=gp, avail=gp / nt if nt else np.nan, mp=mp, mpg=mp / gp if gp else np.nan,
                             gs=int((sub.gs == "1").sum()) if "gs" in sub else np.nan, dnp_reasons=str(rea)))
    A = pd.DataFrame(rows)
    names = ps[ps.season == 2026].drop_duplicates("bbref_id").set_index("bbref_id").name_display
    W = A.pivot(index=["team", "bbref_id"], columns="period", values=["team_games", "gp", "avail", "mp", "mpg", "gs"]); W.columns = [f"{a}_{b}" for a, b in W.columns]; W = W.reset_index()
    W["name"] = W.bbref_id.map(names); W["bpm26"] = W.bbref_id.map(bpm); W["mpg_change_pct"] = W.mpg_post / W.mpg_pre - 1; W["avail_change"] = W.avail_post - W.avail_pre
    W["shutdown_flag"] = ((W.avail_pre > 0.6) & (W.avail_post < 0.35) & (W.mp_pre > 800)) | ((W.mpg_pre > 20) & (W.mpg_post < 0.6 * W.mpg_pre) & (W.gp_post >= 8))
    W["cut_flag"] = (W.mpg_pre > 15) & (W.mpg_post < 0.75 * W.mpg_pre) & (W.gp_post >= 8)
    T = []
    for t, d in W.groupby("team"):
        d = d.dropna(subset=["bpm26"])
        q = lambda c: float(np.average(d.bpm26, weights=d[c].fillna(0))) if d[c].fillna(0).sum() > 0 else np.nan
        top5 = lambda c: float(d.nlargest(5, "bpm26")[c].sum() / d[c].sum())
        T.append(dict(team=t, lineup_bpm_pre=q("mp_pre"), lineup_bpm_post=q("mp_post"), top5_bpm_min_share_pre=top5("mp_pre"), top5_bpm_min_share_post=top5("mp_post"),
                      n_shutdown=int(d.shutdown_flag.sum()), n_cut=int(d.cut_flag.sum()), team_games_pre=tg[t][0], team_games_post=tg[t][1]))
    T = pd.DataFrame(T); T["lineup_bpm_change"] = T.lineup_bpm_post - T.lineup_bpm_pre
    W.to_csv(os.path.join(ROOT, "data/clean/tank_carryover_players.csv"), index=False); T.to_csv(os.path.join(ROOT, "data/clean/tank_carryover_teams.csv"), index=False)
    return W, T

if __name__ == "__main__":
    W, T = run(); pd.set_option("display.width", 200)
    print(T.round(2).to_string()); print(W[W.shutdown_flag | W.cut_flag][["team", "name", "mpg_pre", "mpg_post", "gp_pre", "gp_post", "avail_pre", "avail_post", "shutdown_flag", "cut_flag", "bpm26"]].round(2).to_string())
