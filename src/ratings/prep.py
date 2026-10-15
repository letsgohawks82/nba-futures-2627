"""Build modelling tables from cleaned bbref parquets. Seasons are bbref end-years (2026 = 2025-26)."""
import os, re
import numpy as np, pandas as pd
from ..data.teams import NAME2ABBR, TEAMS
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
C = lambda f: os.path.join(ROOT, "data", "clean", f)
FIX = {"BRK": "BKN", "CHO": "CHA", "PHO": "PHX", "CHH": "CHA", "NOH": "NOP", "NJN": "BKN"}
TEAM_NAME_FIX = {"Charlotte Bobcats": "CHA"}

def num(s):
    return pd.to_numeric(s.astype(str).str.replace("+", "", regex=False).str.replace(",", ""), errors="coerce")

def player_seasons():
    adv = pd.read_parquet(C("player_rs_advanced.parquet")); tot = pd.read_parquet(C("player_rs_totals.parquet"))
    pb = pd.read_parquet(C("player_rs_play_by_play.parquet"))
    for d in (adv, tot, pb):
        d["season"] = d.season.astype(int); d["team"] = d.team_name_abbr.replace(FIX)
        d["multi"] = d.team.str.endswith("TM")
    keep_adv = ["season", "bbref_id", "name_display", "team", "multi", "age", "pos", "games", "mp", "per", "ts_pct", "usg_pct", "ws", "obpm", "dbpm", "bpm", "vorp"]
    a = adv[keep_adv].copy()
    for c in ["age", "games", "mp", "per", "ts_pct", "usg_pct", "ws", "obpm", "dbpm", "bpm", "vorp"]:
        a[c] = num(a[c])
    t = tot[["season", "bbref_id", "team", "ast", "trb", "stl", "blk", "tov", "pts", "fga", "fta", "games_started"]].copy()
    for c in ["ast", "trb", "stl", "blk", "tov", "pts", "fga", "fta", "games_started"]:
        t[c] = num(t[c])
    p = pb[["season", "bbref_id", "team", "plus_minus_on", "plus_minus_net"]].copy()
    p["on_net"] = num(p.plus_minus_on); p["onoff"] = num(p.plus_minus_net); p = p.drop(columns=["plus_minus_on", "plus_minus_net"])
    d = a.merge(t, on=["season", "bbref_id", "team"], how="left").merge(p, on=["season", "bbref_id", "team"], how="left")
    # one season row per player: the multi-team (2TM/3TM) row if present else the single row
    has_multi = d.groupby(["season", "bbref_id"]).multi.transform("max").astype(bool)
    season_rows = d[(has_multi & d.multi) | (~has_multi)].copy().drop(columns="multi")
    stints = d[~d.multi][["season", "bbref_id", "team", "games", "mp"]].rename(columns={"games": "g_team", "mp": "mp_team"})
    return season_rows.reset_index(drop=True), stints.reset_index(drop=True)

def team_seasons():
    t = pd.read_parquet(C("team_season_hist.parquet")); t["season"] = t.season.astype(int)
    t = t[t.team != "League Average"].copy()
    t["playoffs"] = t.team.str.contains(r"\*")
    t["name"] = t.team.str.replace("*", "", regex=False).str.strip()
    t["abbr"] = t.name.map(lambda n: TEAM_NAME_FIX.get(n) or NAME2ABBR.get(n))
    for c in ["wins", "losses", "mov", "srs", "off_rtg", "def_rtg", "net_rtg", "pace", "age"]:
        t[c] = num(t[c])
    t = t[["season", "abbr", "name", "wins", "losses", "mov", "srs", "off_rtg", "def_rtg", "net_rtg", "pace", "age", "playoffs"]]
    t["conf"] = t.abbr.map(lambda a: TEAMS[a][1] if a in TEAMS else None)
    t["div"] = t.abbr.map(lambda a: TEAMS[a][2] if a in TEAMS else None)
    t["gp"] = t.wins + t.losses
    return t

def draft():
    d = pd.read_parquet(C("draft_picks.parquet")); d["draft_year"] = d.draft_year.astype(int)
    d["pick"] = num(d.pick_overall)
    return d[["draft_year", "pick", "team_id", "player", "college_name"]]
