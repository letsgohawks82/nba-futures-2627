"""Project 2026-27: player ratings (bbref BPM-based ensemble + DARKO blend), minutes/availability, team rating, wins. Writes data/clean/*2027*.csv"""
import json, os, datetime
import numpy as np, pandas as pd
from .model import *
from .rookies import load_torvik, college_table, fit_rookie, predict_rookie
from ..data.namemap import norm
from ..data.teams import TEAMS

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
C = lambda f: os.path.join(ROOT, "data", "clean", f)
SEASON = 2027
W_DARKO_DEFAULT = 0.35          # ASSUMPTION: DARKO has no archived history -> cannot be backtested (see provenance)
SEASON_START, SEASON_END = pd.Timestamp("2026-10-20"), pd.Timestamp("2027-04-11")


def load_roster(D):
    R = pd.read_csv(C("rosters_espn.csv")); ids = pd.read_csv(C("player_ids.csv"))
    R = R.merge(ids[["name", "bbref_id", "category"]], on="name", how="left")
    dr26 = D.dr[D.dr.draft_year == 2026].assign(k=lambda d: d.player.map(norm))
    R["k"] = R.name.map(norm)
    R = R.merge(dr26[["k", "pick", "college_name"]], on="k", how="left")
    R["pid"] = np.where(R.bbref_id.notna(), R.bbref_id, "rk_" + R.k.str.replace(" ", "_"))
    R["pick_eff"] = R.pick.fillna(61.0)
    return R


def darko_map():
    d = pd.read_csv(C("../raw/darko/darko_dpm_leaderboard_20261015.csv"), dtype=str)
    d["darko_name"] = d.iloc[:, 0].str.replace(r"\s+[A-Z]{2,3}\|.*$", "", regex=True)
    for c in ["dpm", "off", "def", "box", "onoff", "mpg"]:
        d[c] = pd.to_numeric(d[c].str.replace("—", ""), errors="coerce")
    nm = pd.read_csv(C("name_map.csv"), keep_default_na=False)
    nm = nm[(nm.source == "darko") & (nm.canonical != "")][["source_name", "canonical"]]
    return d.merge(nm, left_on="darko_name", right_on="source_name").rename(columns={"canonical": "name"})[["name", "dpm", "off", "def", "box", "onoff", "mpg"]]


def injury_overrides(R):
    inj = pd.read_csv(C("injuries_espn.csv"))
    inj = inj[inj.status == "Out"].copy()
    inj["ret"] = pd.to_datetime(inj.ret, errors="coerce")
    span = (SEASON_END - SEASON_START).days
    inj["missed_frac"] = ((inj.ret - SEASON_START).dt.days / span).clip(0, 1).fillna(0.0)
    return inj[["name", "team", "status", "type", "detail", "ret", "missed_frac"]]


def run(w_darko=W_DARKO_DEFAULT, save=True, overrides=None):
    D = Data(); T = load_torvik()
    P = fit_player_model(D, 2026); Pr = fit_rookie(D, T, 2026, True)
    R = load_roster(D)
    # pick lookup for synthetic ids and 2026 draftees
    for r in R.itertuples():
        if r.pid.startswith("rk_"):
            D.pick_of[r.pid] = r.pick_eff
    ages = dict(zip(R.pid, R.age))
    pl = predict_players(D, SEASON, P, roster_ids=R.pid.unique(), ages=ages)
    ct = college_table(D, T)
    # rookie / no-history rating: college translation for 2026 draftees; slot-only for the rest
    for r in R.itertuples():
        if r.pid in pl.index and pl.loc[r.pid, "no_history"]:
            c = ct[(ct.draft_year == 2026) & (ct.k == r.k)]
            if len(c):
                c = c.iloc[0]; pl.loc[r.pid, "rating"] = predict_rookie(Pr, r.pick_eff, c.bpm_c, c.cls_n, c.ht_in)
            else:
                pl.loc[r.pid, "rating"] = predict_rookie(Pr, r.pick_eff)
    pl["rating_bbref"] = pl.rating
    # DARKO blend: map DPM onto our (shrunk, projected) scale by regression on overlap, then blend
    dk = darko_map(); name_of = dict(zip(R.pid, R.name)); pl["name"] = pl.index.map(name_of)
    pl = pl.merge(dk, on="name", how="left").set_index(pl.index)
    ov = pl[pl.dpm.notna() & (pl.S.fillna(0) > 1500)]
    b = np.polyfit(ov.dpm, ov.rating_bbref, 1)
    pl["dpm_on_scale"] = np.polyval(b, pl.dpm)
    pl["rating"] = np.where(pl.dpm.notna(), (1 - w_darko) * pl.rating_bbref + w_darko * pl.dpm_on_scale, pl.rating_bbref)
    # overrides: injuries (Out) + manual csv
    inj = injury_overrides(R); pl = pl.merge(inj[["name", "missed_frac", "detail", "type"]], on="name", how="left").set_index(pl.index)
    pl["gfrac_hat_raw"] = pl.gfrac_hat
    pl["gfrac_hat"] = (pl.gfrac_hat * (1 - pl.missed_frac.fillna(0))).clip(0.0, 0.97)
    mo = C("../../params/overrides_players.csv")
    adj = {}
    if os.path.exists(mo):
        o = pd.read_csv(mo)
        for r in o.itertuples():
            pid = R.loc[R.name == r.name, "pid"]
            if len(pid):
                pid = pid.iloc[0]
                if pd.notna(r.mpg_override): pl.loc[pid, "mpg_hat"] = r.mpg_override
                if pd.notna(r.gfrac_override): pl.loc[pid, "gfrac_hat"] = r.gfrac_override
                if pd.notna(r.rating_adj): adj[pid] = r.rating_adj
    roster = R[["team", "pid"]].rename(columns={"team": "abbr", "pid": "bbref_id"}).assign(w_team=1.0)
    f, _ = team_features(D, SEASON, P, roster=roster, pl=pl, rating_adj=adj or None)
    prev = D.ts[D.ts.season == 2026][["abbr", "srs", "wins", "off_rtg", "def_rtg", "pace", "conf"]].rename(columns={"srs": "prev_srs", "wins": "prev_wins", "pace": "prev_pace", "off_rtg": "prev_ortg", "def_rtg": "prev_drtg"})
    F = f.merge(prev, on="abbr")
    # team layer fit on all seasons through 2026 (each training season uses a player model fit only on earlier data)
    pf = {}
    def pfit(m):
        if m not in pf: pf[m] = fit_player_model(D, m)
        return pf[m]
    ts = D.ts.assign(w82=lambda d: d.wins / d.gp * 82)
    frames = []
    for s in range(2016, 2027):
        fr = season_frame(D, s, pfit(s - 1)); frames.append(fr.merge(ts[ts.season == s][["abbr", "w82"]], on="abbr").assign(wins=lambda d: d.w82))
    L = fit_team_layer(frames)
    out = predict_wins(F, L)
    # O/D split (approximation, see report) and pace
    lg_o = float(D.ts[D.ts.season == 2026].off_rtg.mean()); lg_pace = float(D.ts[D.ts.season == 2026].pace.mean())
    ps_ = D.ps
    rt = {}
    for met in ("obpm", "dbpm"):
        Pm = fit_player_model(D, 2026, metric=met)
        plm = predict_players(D, SEASON, Pm, metric=met, roster_ids=R.pid.unique(), ages=ages)
        fm, _ = team_features(D, SEASON, Pm, metric=met, roster=roster, pl=plm)
        rt[met] = fm.set_index("abbr").teamsum
    out["ts_o"] = out.abbr.map(rt["obpm"]); out["ts_d"] = out.abbr.map(rt["dbpm"])
    out["off_adv"] = out.pred_srs / 2 + ((out.ts_o - out.ts_o.mean()) - (out.ts_d - out.ts_d.mean())) / 2
    out["def_adv"] = out.pred_srs - out.off_adv
    out["pred_ortg"] = lg_o + out.off_adv; out["pred_drtg"] = lg_o - out.def_adv
    out["pred_pace"] = 0.7 * out.prev_pace + 0.3 * lg_pace
    out["sigma_wins"] = L["wins_resid_sd"]
    out = out.sort_values("pred_wins", ascending=False).reset_index(drop=True)
    if save:
        out.to_csv(C("team_projection_2027.csv"), index=False)
        # player table
        mins = []
        for abbr, d in roster.groupby("abbr"):
            d = d.merge(pl, left_on="bbref_id", right_index=True, how="left"); d["w_team"] = 1.0
            d["proj_min"] = allocate_minutes(d); d["abbr"] = abbr; mins.append(d)
        PM = pd.concat(mins)
        PM["proj_mpg"] = PM.proj_min / (82 * PM.gfrac_hat.clip(lower=0.01)); PM["proj_gp"] = PM.gfrac_hat * 82
        PM[["abbr", "bbref_id", "name", "age", "rating_bbref", "dpm", "dpm_on_scale", "rating", "no_history", "S", "mpg_hat", "gfrac_hat_raw", "gfrac_hat", "proj_min", "proj_mpg", "proj_gp", "missed_frac", "detail"]].to_csv(C("player_projection_2027.csv"), index=False)
        prov = dict(player_model={k: v for k, v in P.items()}, rookie_college_model=Pr, team_layer=L, darko_scale=dict(slope=float(b[0]), intercept=float(b[1]), n=int(len(ov))), w_darko=w_darko, lg_ortg=lg_o, lg_pace=lg_pace)
        json.dump(prov, open(C("ratings_fit_2027.json"), "w"), indent=1)
    return out, pl, L, P, Pr


if __name__ == "__main__":
    o, pl, L, P, Pr = run()
    print(o[["abbr", "teamsum", "continuity", "prev_srs", "pred_srs", "pred_wins", "prev_wins", "pred_ortg", "pred_drtg", "pred_pace"]].round(2).to_string())
    print("sum wins", o.pred_wins.sum(), "L", {k: (np.round(v, 3).tolist() if isinstance(v, list) else round(v, 3)) for k, v in L.items()})
