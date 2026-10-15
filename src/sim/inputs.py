"""Build the numpy inputs for the season engine."""
import json, os, datetime
import numpy as np, pandas as pd
from scipy.optimize import curve_fit
from ..data.teams import TEAMS
from .lottery import odds

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
C = lambda f: os.path.join(ROOT, "data", "clean", f)
TEAM_LIST = sorted(TEAMS)
IDX = {t: i for i, t in enumerate(TEAM_LIST)}
DIVS = {"Atlantic": 0, "Central": 1, "Southeast": 2, "Northwest": 3, "Pacific": 4, "Southwest": 5}
K_TOP = 12
START = pd.Timestamp("2026-10-20")
R_REPL = -2.0            # BPM replacement level (definition of BPM/VORP)
B_TEAM = 1.07            # team-layer coefficient on the minutes-weighted rating sum (G2 fit)

PAR_NAMES = ["HCA", "b2b_home", "b2b_away", "sigma_game", "HCA_po", "sigma_po", "mean_total", "sd_total", "sigma_team", "repl_rating", "b_team",
             "avail_concentration", "po_lambda", "po_inj_prob", "tank_kappa", "tank_deterrent", "tank_on", "cup_cross_games", "cup_semis_neutral",
             "n_draws", "floor_pick", "ot_margin", "tank_boost", "tank_REF", "avail_on", "deadline_noise", "k_wins", "cup_on"]


def fit_pick_value(save=True):
    d = pd.read_parquet(C("draft_picks.parquet")); d["draft_year"] = d.draft_year.astype(int)
    d["pick"] = pd.to_numeric(d.pick_overall, errors="coerce"); d["ws"] = pd.to_numeric(d.ws, errors="coerce").fillna(0.0)
    d = d[(d.draft_year <= 2021) & d.pick.notna()]
    g = d.groupby("pick").ws.mean()
    f = lambda p, a, b, c: a * np.power(p, -b) + c
    (a, b, c), _ = curve_fit(f, g.index.values.astype(float), g.values, p0=[30, 0.7, 2], maxfev=20000)
    val = np.zeros(31)
    for p in range(1, 31):
        val[p] = max(f(p, a, b, c), 0.0)
    out = dict(a=float(a), b=float(b), c=float(c), n_players=int(len(d)), draft_years="2013-2021", metric="career win shares through 2026 (bbref)", value_by_pick=val[1:].tolist())
    if save:
        json.dump(out, open(os.path.join(ROOT, "params/pick_value_curve.json"), "w"), indent=1)
    return val, out


def lottery_tables(n_draws=16, n=300_000):
    Pgen = odds(n_draws, n, 11)
    Pnf = np.zeros((16, 16, 16)); Pnt5 = np.zeros((16, 16, 16))
    nf = np.zeros(16, bool); nt = np.zeros(16, bool)
    for s in range(16):
        nf[:] = False; nt[:] = False; nf[s] = True
        Pnf[s] = odds(n_draws, 120_000, 20 + s, no_first=nf)
        nf[:] = False; nt[s] = True
        Pnt5[s] = odds(n_draws, 120_000, 40 + s, no_top5=nt)
    return Pgen, Pnf, Pnt5


def load_assumptions():
    A = {a["name"]: a["value"] for a in json.load(open(os.path.join(ROOT, "params/assumptions.json")))}
    return A


def build(overrides=None, season_label=2027):
    """overrides: dict of par overrides (by PAR_NAMES) and optional keys: rules_override {team:(kprot,fover)}"""
    overrides = overrides or {}
    A = load_assumptions()
    gm = json.load(open(C("game_model_fit.json")))
    prov = json.load(open(os.path.join(ROOT, "params/provenance.json")))
    tp = pd.read_csv(C("team_projection_2027.csv")).set_index("abbr").loc[TEAM_LIST]
    pp = pd.read_csv(C("player_projection_2027.csv"))
    sig_team = float(prov["sigma_team_srs"]["value"]); kw = float(prov["k_wins_per_srs"]["value"])
    par = dict(HCA=gm["hca"], b2b_home=gm["b2b_home"], b2b_away=gm["b2b_away"], sigma_game=gm["sigma_game"], HCA_po=gm["hca_post"], sigma_po=gm["sigma_game"],
               mean_total=gm["mean_total"], sd_total=gm["sd_total"], sigma_team=sig_team, repl_rating=R_REPL, b_team=B_TEAM,
               avail_concentration=3.7, po_lambda=1.0, po_inj_prob=0.07, tank_kappa=0.0, tank_deterrent=0.0, tank_on=0.0,
               cup_cross_games=float(A.get("cup_nonqualifier_cross_conf_games", 2) > 0), cup_semis_neutral=float(A.get("cup_semis_neutral", 0)),
               n_draws=float(A.get("lottery_n_draws", 16)), floor_pick=12.0, ot_margin=3.0, tank_boost=0.0, tank_REF=1.0, avail_on=1.0,
               deadline_noise=1.0, k_wins=kw, cup_on=1.0)
    tk = json.load(open(C("tank_kappa_fit.json")))["excl_2020_bubble"]       # kappa fit excluding the 2020 bubble restart
    par.update(tank_kappa=max(tk["kappa"], 0.0), tank_REF=tk["ref_dV"], tank_on=1.0, po_lambda=json.load(open(C("playoff_adj_fit.json")))["lambda_po"])
    par.update({k: v for k, v in overrides.items() if k in par})
    parr = np.array([par[k] for k in PAR_NAMES], float)
    conf = np.array([0 if TEAMS[t][1] == "E" else 1 for t in TEAM_LIST], np.int64)
    div = np.array([DIVS[TEAMS[t][2]] for t in TEAM_LIST], np.int64)
    cg = json.load(open(C("cup_groups_validation.json")))["schedule"]
    grp = np.zeros(30, np.int64); grp_conf = np.zeros(6, np.int64)
    for g, members in enumerate(cg):
        for t in members:
            grp[IDX[t]] = g
        grp_conf[g] = conf[IDX[members[0]]]
    prevw = tp.prev_wins.values.astype(float)
    rating = tp.pred_srs.values.astype(float)
    # players
    pw = np.zeros((30, K_TOP)); pa = np.zeros((30, K_TOP)); pw_po = np.zeros((30, K_TOP)); po_delta = np.zeros(30)
    pnames = [[""] * K_TOP for _ in range(30)]; pids = [[""] * K_TOP for _ in range(30)]
    for t, d in pp.groupby("abbr"):
        i = IDX[t]
        d = d.sort_values("proj_min", ascending=False).reset_index(drop=True)
        healthy = d.mpg_hat.clip(upper=38.0).values
        norm_reg = healthy * (240.0 / healthy.sum())
        top = d.head(K_TOP)
        for k, r in top.iterrows():
            pw[i, k] = max(B_TEAM * (healthy[k] / 48.0) * (r.rating - R_REPL), 0.0)
            pa[i, k] = r.gfrac_hat
            pnames[i][k] = r["name"]; pids[i][k] = r.bbref_id
        # playoffs: top-8 by healthy minutes, minutes re-concentrated to ~ 228 team minutes, cap 42
        o8 = np.argsort(-healthy)[:8]
        mp8 = healthy[o8] * (228.0 / healthy[o8].sum()); mp8 = np.minimum(mp8, 42.0)
        mp8 = mp8 * (228.0 / mp8.sum()) if mp8.sum() > 0 else mp8
        rating_arr = d.rating.values
        ts_reg = (norm_reg / 48.0 * rating_arr).sum(); ts_po = (mp8 / 48.0 * rating_arr[o8]).sum()
        po_delta[i] = B_TEAM * (ts_po - ts_reg)
        for k, ix in enumerate(o8):
            col = int(np.where(top.index == ix)[0][0]) if ix < K_TOP else None
            if col is not None:
                pw_po[i, col] = max(B_TEAM * (mp8[k] / 48.0) * (rating_arr[ix] - R_REPL), 0.0)
    # schedule
    g = pd.read_csv(C("schedule_games.csv")); L = pd.read_csv(C("schedule_team_games.csv"))
    L["key"] = L.date + "|" + L.team + "|" + L.opp
    b2b = dict(zip(L.key, L.b2b))
    g["day"] = (pd.to_datetime(g.date) - START).dt.days
    g = g.sort_values(["day", "game_no"]).reset_index(drop=True)
    gh = g.home.map(IDX).values.astype(np.int64); ga = g.away.map(IDX).values.astype(np.int64)
    gb2bh = np.array([b2b.get(f"{d}|{h}|{a}", 0) for d, h, a in zip(g.date, g.home, g.away)], np.float64)
    gb2ba = np.array([b2b.get(f"{d}|{a}|{h}", 0) for d, h, a in zip(g.date, g.home, g.away)], np.float64)
    gday = g.day.values.astype(np.int64); gcup = g.cup_group.values.astype(np.bool_)
    deadline_day = int((pd.Timestamp("2027-02-11") - START).days); cup_ko_day = int((pd.Timestamp("2026-12-04") - START).days)
    # pick value + lottery tables
    val, pvc = fit_pick_value(save=False)
    Pgen, Pnf, Pnt5 = overrides.get("_lottery_tables") or lottery_tables(int(par["n_draws"]))
    rules = pd.read_csv(os.path.join(ROOT, "params/pick_ownership_rules.csv")).set_index("team").loc[TEAM_LIST]
    kprot = rules.kprot.values.astype(np.int64); fover = rules.fover.fillna(-1.0).values.astype(np.float64)
    for tm, (kp, fo) in overrides.get("rules_override", {}).items():
        kprot[IDX[tm]] = kp; fover[IDX[tm]] = fo
    return dict(par=parr, conf=conf, div=div, grp=grp, grp_conf=grp_conf, prevw=prevw, rating=rating, pw=pw, pa=pa, pw_po=pw_po, po_delta=po_delta,
                gh=gh, ga=ga, gb2bh=gb2bh, gb2ba=gb2ba, gday=gday, gcup=gcup, deadline_day=deadline_day, cup_ko_day=cup_ko_day,
                pickval=val, Pgen=Pgen, Pnf=Pnf, Pnt5=Pnt5, kprot=kprot, fover=fover, nf_team=IDX["WAS"], nt5_team=IDX["UTA"],
                teams=TEAM_LIST, pnames=pnames, pids=pids, par_dict=par, sched=g)


if __name__ == "__main__":
    v, o = fit_pick_value(); print({k: o[k] for k in ("a", "b", "c", "n_players")}, np.round(v[[1, 2, 5, 10, 15, 20, 30]], 2))
