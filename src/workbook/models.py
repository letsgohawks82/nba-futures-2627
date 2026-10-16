"""Workbook model tabs: M_TeamRatings, M_WinDist, M_Sims, M_Lottery2027, M_Players."""
import json, math, os
import numpy as np, pandas as pd
from openpyxl.utils import get_column_letter as CL
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from openpyxl.styles import Font, PatternFill
from .styles import *
from .core import REG, C, ROOT, name, hash_key_string

TEAMS_N = 30


def build_team_ratings(wb):
    ws = wb.create_sheet("M_TeamRatings"); sheet_header(ws, "M_TeamRatings - player -> team rating build (live). Overrides flow through; minutes are re-scaled to 19,680 per team")
    rt = REG["raw_teams"]; rp = REG["raw_players"]; ov = REG["ov_player"]; ot = REG["ov_team"]
    put(ws, "A5", "Team SRS = b0 + b1 x (TeamSum - league mean) + b2 x prior SRS + b3 x continuity x prior SRS (+ override), re-centered to zero-sum; wins = 41 + k x SRS (sums to 1,230).", "text", italic=True)
    hdr = ["Team", "Conf", "Division", "TeamSum (minutes-weighted rating)", "TeamSum - league mean", "Prior SRS", "Continuity", "Raw SRS", "Team override (SRS)", "Projected SRS", "Projected wins", "ORtg", "DRtg", "Net rating", "Pace",
           "Rank - wins", "Rank - ORtg", "Rank - DRtg", "Python wins (reference)", "Delta vs Python"]
    headers(ws, 7, hdr)
    f, l = 8, 7 + TEAMS_N
    pb0 = 45; pf, pl = pb0 + 1, pb0 + rp["n"]       # player block rows
    rng = lambda col: f"${col}${pf}:${col}${pl}"
    for i in range(TEAMS_N):
        r = f + i; rr = rt["first"] + i
        put(ws, f"A{r}", f"=Raw_Teams!A{rr}", "link"); put(ws, f"B{r}", f"=Raw_Teams!B{rr}", "link"); put(ws, f"C{r}", f"=Raw_Teams!C{rr}", "link")
        put(ws, f"D{r}", f"=SUMIF({rng('A')},A{r},{rng('P')})", "formula", "num3")
        put(ws, f"E{r}", f"=D{r}-AVERAGE($D${f}:$D${l})", "formula", "num3")
        put(ws, f"F{r}", f"=Raw_Teams!D{rr}", "link", "num2"); put(ws, f"G{r}", f"=Raw_Teams!F{rr}", "link", "num3")
        put(ws, f"H{r}", f"=A_b0+A_b1*E{r}+A_b2*F{r}+A_b3*G{r}*F{r}", "formula", "num3")
        put(ws, f"I{r}", f"=INDEX(Overrides!$B${ot[0]}:$B${ot[1]},MATCH(A{r},Overrides!$A${ot[0]}:$A${ot[1]},0))", "link", "num2")
        put(ws, f"J{r}", f"=(H{r}-AVERAGE($H${f}:$H${l}))+I{r}-AVERAGE($I${f}:$I${l})", "formula", "num3")
        put(ws, f"K{r}", f"=A_games/2+A_kwins*J{r}", "formula", "num2")
        put(ws, f"L{r}", f"=A_lgortg+J{r}/2+((Raw_Teams!J{rr}-AVERAGE(Raw_Teams!$J${rt['first']}:$J${rt['last']}))-(Raw_Teams!K{rr}-AVERAGE(Raw_Teams!$K${rt['first']}:$K${rt['last']})))/2", "formula", "num1")
        put(ws, f"M{r}", f"=A_lgortg-(J{r}-(L{r}-A_lgortg))", "formula", "num1"); put(ws, f"N{r}", f"=L{r}-M{r}", "formula", "num1")
        put(ws, f"O{r}", f"=A_paceblend*Raw_Teams!G{rr}+(1-A_paceblend)*AVERAGE(Raw_Teams!$G${rt['first']}:$G${rt['last']})", "formula", "num1")
        put(ws, f"P{r}", f"=RANK(K{r},$K${f}:$K${l})", "formula", "int"); put(ws, f"Q{r}", f"=RANK(L{r},$L${f}:$L${l})", "formula", "int"); put(ws, f"R{r}", f"=RANK(M{r},$M${f}:$M${l},1)", "formula", "int")
        put(ws, f"S{r}", f"=Raw_Teams!M{rr}", "link", "num2"); put(ws, f"T{r}", f"=K{r}-S{r}", "formula", "num2")
    # fix: P in the team table is rank; player-block team sum uses column P of the player block (see below) -> use different columns
    total = l + 1
    put(ws, f"A{total}", "League", "text", bold=True); put(ws, f"K{total}", f"=SUM(K{f}:K{l})", "formula", "num2"); total_border(ws, total, 1, 20)
    REG["tr"] = dict(first=f, last=l, total=total)
    # player block
    put(ws, f"A{pb0-2}", "Player build (links to Raw_Players; overrides applied)", "text", bold=True)
    headers(ws, pb0, ["Team", "Player", "Rating", "Projected minutes", "Projected mpg", "Projected games", "mpg override", "Games override", "Rating adjustment", "Effective minutes (pre-scale)", "Team scale",
                      "Effective minutes", "Effective rating", "Minutes share of 5 slots", "(placeholder)", "Contribution"], height=30)
    O_N = f"Overrides!$A${ov[0]}:$A${ov[1]}"
    for i in range(rp["n"]):
        r = pf + i; rr = rp["first"] + i
        put(ws, f"A{r}", f"=Raw_Players!A{rr}", "link"); put(ws, f"B{r}", f"=Raw_Players!B{rr}", "link"); put(ws, f"C{r}", f"=Raw_Players!E{rr}", "link", "num3")
        put(ws, f"D{r}", f"=Raw_Players!F{rr}", "link", "num1"); put(ws, f"E{r}", f"=Raw_Players!G{rr}", "link", "num1"); put(ws, f"F{r}", f"=Raw_Players!H{rr}", "link", "num1")
        put(ws, f"G{r}", f'=IFERROR(IF(INDEX(Overrides!$B${ov[0]}:$B${ov[1]},MATCH(B{r},{O_N},0))="","",INDEX(Overrides!$B${ov[0]}:$B${ov[1]},MATCH(B{r},{O_N},0))),"")', "link", "num1")
        put(ws, f"H{r}", f'=IFERROR(IF(INDEX(Overrides!$C${ov[0]}:$C${ov[1]},MATCH(B{r},{O_N},0))="","",INDEX(Overrides!$C${ov[0]}:$C${ov[1]},MATCH(B{r},{O_N},0))),"")', "link", "num1")
        put(ws, f"I{r}", f'=IFERROR(IF(INDEX(Overrides!$D${ov[0]}:$D${ov[1]},MATCH(B{r},{O_N},0))="",0,INDEX(Overrides!$D${ov[0]}:$D${ov[1]},MATCH(B{r},{O_N},0))),0)', "link", "num2")
        put(ws, f"J{r}", f'=IF(AND(G{r}="",H{r}=""),D{r},IF(H{r}="",F{r},H{r})*IF(G{r}="",E{r},G{r}))', "formula", "num1")
        put(ws, f"K{r}", f"=A_teamminutes/SUMIF({rng('A')},A{r},{rng('J')})", "formula", "num4" if False else "0.0000")
        put(ws, f"L{r}", f"=J{r}*K{r}", "formula", "num1"); put(ws, f"M{r}", f"=C{r}+I{r}", "formula", "num3"); put(ws, f"N{r}", f"=L{r}/(A_teamminutes/5)", "formula", "num3")
        put(ws, f"O{r}", None, "text"); put(ws, f"P{r}", f"=N{r}*M{r}", "formula", "num4" if False else "0.0000")
    # NOTE: team table column D sums player column P (contribution); ranks are columns P..R of the TEAM table (different rows) - no clash
    REG["tr_players"] = dict(first=pf, last=pl)
    widths(ws, {"A": 8, "B": 28, "C": 10}); finish(ws, label_cols=("A", "B")); ws.freeze_panes = "B8"


def build_windist(wb, o):
    ws = wb.create_sheet("M_WinDist"); sheet_header(ws, "M_WinDist - live analytic win distribution (normal approximation) vs sim; reprices when Assumptions / Overrides change")
    put(ws, "A5", "Wins ~ Normal(mean, sd), mean = 41 + k x SRS (the calibrated projection; the sim is moment-matched to it): sd^2 = 82 p (1-p) + (82 phi(z) / sigma_game x sigma_team)^2 with p = mean/82, z = NORMSINV(p). Delta flagged when |analytic - sim| > 2pp.", "text", italic=True)
    srcs = ["ours"] + REG["cons"]["order"]
    hdr = ["Team", "Line", "Mean wins (live)", "SD wins", "P(over) analytic", "P(under) analytic", "P(over) sim", "Delta (pp)", "Flag", "Model fair odds - over", "Model fair odds - under", "Book over", "Book under", "Book fair over (selected)", "Market fair median wins"]
    for k in srcs: hdr += [f"Proj: {k}", f"Residual: {k}"]
    hdr += ["Results-based sources count? (engine)", "Why not (engine)", "Roster-aware residuals both >= strong", "Consensus PASS for OVER", "Consensus PASS for UNDER"]
    headers(ws, 7, hdr, height=45)
    tr = REG["tr"]; od = REG["odds"]; dv = REG["devig"]
    w = o[(o.market == "WINS") & (o.side == "OVER")]
    from ..data.teams import NAME2ABBR
    from ..pricing import consensus as CSE
    rb_elig = CSE.rb_eligible()
    for i, (idx, r) in enumerate(w.iterrows()):
        row = 8 + i; orow = od["first"] + idx; abbr = NAME2ABBR[r.selection]
        put(ws, f"A{row}", abbr, "text")
        put(ws, f"B{row}", f"=Odds_Input!E{orow}", "link", "num1")
        put(ws, f"C{row}", f"=INDEX(M_TeamRatings!$K${tr['first']}:$K${tr['last']},MATCH(A{row},M_TeamRatings!$A${tr['first']}:$A${tr['last']},0))", "link", "num2")
        put(ws, f"D{row}", f"=A_sdscale*SQRT(A_games*(C{row}/A_games)*(1-C{row}/A_games)+(A_games*EXP(-NORMSINV(C{row}/A_games)^2/2)/SQRT(2*PI())/A_sigma_game*A_sigma_team)^2)", "formula", "num2")
        put(ws, f"E{row}", f"=1-NORMDIST(B{row},C{row},D{row},TRUE)", "formula", "pct"); put(ws, f"F{row}", f"=1-E{row}", "formula", "pct")
        put(ws, f"G{row}", f"=M_Sims!$CK{{SIMS_ROW_{r.selection}}}", "link", "pct")      # placeholder replaced in M_Sims builder
        put(ws, f"H{row}", f"=(E{row}-G{row})*100", "formula", "num1"); put(ws, f"I{row}", f'=IF(ABS(H{row})>2,"CHECK >2pp","")', "flag")
        put(ws, f"J{row}", f"=IF(E{row}>=0.5,-100*E{row}/(1-E{row}),100*(1-E{row})/E{row})", "formula", "amer"); put(ws, f"K{row}", f"=IF(F{row}>=0.5,-100*F{row}/(1-F{row}),100*(1-F{row})/F{row})", "formula", "amer")
        put(ws, f"L{row}", f"=Odds_Input!F{orow}", "link", "amer"); put(ws, f"M{row}", f"=Odds_Input!F{orow+1}", "link", "amer")
        put(ws, f"N{row}", f"=M_DeVig!Q{dv['first']+idx}", "link", "pct")
        cs = REG["cons"]; put(ws, f"O{row}", f"=B{row}+(N{row}-0.5)/A_p_per_win", "formula", "num2")
        pc = {}; rc = {}
        for j, k in enumerate(srcs):
            pcol = CL(16 + 2 * j); rcol = CL(17 + 2 * j); pc[k] = pcol; rc[k] = rcol
            if k == "ours": put(ws, f"{pcol}{row}", f"=C{row}", "formula", "num2")
            else:
                rng = f"Raw_Consensus!${cs['cols'][k]}${cs['first']}:${cs['cols'][k]}${cs['last']}"
                put(ws, f"{pcol}{row}", f"=INDEX({rng},MATCH($A{row},Raw_Consensus!$A${cs['first']}:$A${cs['last']},0))", "link", "num2")
            put(ws, f"{rcol}{row}", f"={pcol}{row}-(INTERCEPT({pcol}$8:{pcol}$37,$O$8:$O$37)+SLOPE({pcol}$8:{pcol}$37,$O$8:$O$37)*$O{row})", "formula", "num2")
        base = 16 + 2 * len(srcs); rb = rb_elig.get(abbr, (True, ""))
        put(ws, f"{CL(base)}{row}", "Y" if rb[0] else "N", "input"); put(ws, f"{CL(base+1)}{row}", rb[1], "text")
        ra = [rc["ours"], rc["PredictionEngine"]]; rbs = [rc[k] for k in cs["order"] if cs["methods"][k] == "results_based"]
        put(ws, f"{CL(base+2)}{row}", f"=AND(ABS({ra[0]}{row})>=A_cons_strong,ABS({ra[1]}{row})>=A_cons_strong)", "formula")
        put(ws, f"{CL(base+3)}{row}", f'=AND({ra[0]}{row}>=A_cons_min,{ra[1]}{row}>=A_cons_min,NOT(AND({CL(base)}{row}="Y",{rbs[0]}{row}<=-A_cons_min,{rbs[1]}{row}<=-A_cons_min)))', "formula")
        put(ws, f"{CL(base+4)}{row}", f'=AND({ra[0]}{row}<=-A_cons_min,{ra[1]}{row}<=-A_cons_min,NOT(AND({CL(base)}{row}="Y",{rbs[0]}{row}>=A_cons_min,{rbs[1]}{row}>=A_cons_min)))', "formula")
        REG["windist_pass"] = (CL(base + 3), CL(base + 4)); REG["windist_strong"] = CL(base + 2)
    n_ = len(w); sr = 8 + n_ + 1
    put(ws, f"A{sr}", "Per-source regression of projection on the market fair median (30 teams)", "text", bold=True)
    for j, k in enumerate(srcs):
        pcol = CL(16 + 2 * j); rcol = CL(17 + 2 * j)
        for t_, (lab, f_) in enumerate((("Slope", f"=SLOPE({pcol}8:{pcol}{7+n_},$O$8:$O${7+n_})"), ("Intercept", f"=INTERCEPT({pcol}8:{pcol}{7+n_},$O$8:$O${7+n_})"), ("Residual SD", f"=STDEV({rcol}8:{rcol}{7+n_})"), ("R-squared", f"=RSQ({pcol}8:{pcol}{7+n_},$O$8:$O${7+n_})"))):
            put(ws, f"A{sr+1+t_}", lab, "text"); put(ws, f"{pcol}{sr+1+t_}", f_, "formula", "num3")
    REG["windist"] = dict(first=8, last=7 + len(w), n=len(w), idx=list(w.index), teams=[NAME2ABBR[s] for s in w.selection])
    ws.conditional_formatting.add(f"I8:I{7+len(w)}", FormulaRule(formula=['LEN(I8)>0'], font=Font(name="Arial", size=10, color=RED, bold=True)))
    widths(ws, {"A": 8}); finish(ws); ws.freeze_panes = "B8"


def build_sims(wb, o):
    """Values written by Python: clearly labelled engine output with run hash/timestamp. Returns column maps used by S_Markets."""
    ws = wb.create_sheet("M_Sims"); sheet_header(ws, "M_Sims - ENGINE OUTPUT (values written by Python; do not edit)", span=12)
    S = pd.read_csv(C("sim_team_summary.csv")).sort_values("team").reset_index(drop=True); meta = json.load(open(C("sim_run_meta.json")))
    par = meta["par"]; keyvals = [par["sigma_team"], par["HCA"], par["sigma_game"], 0.5, par["tank_kappa"], par["tank_deterrent"], par["tank_on"], par["po_lambda"], par["po_inj_prob"], par["n_draws"],
                                  par["cup_semis_neutral"], par["cup_cross_games"]]
    fit = json.load(open(C("ratings_fit_2027.json")))["team_layer"]; keyvals += fit["beta"] + [fit["k_wins"]]
    key = hash_key_string(keyvals)
    rows = [("Run timestamp (UTC)", meta["run_utc"]), ("Simulated seasons (N)", meta["n_sims"]), ("Seed", meta["seed"]), ("Engine assumptions hash", meta["assumptions_hash"]), ("Sim assumptions key (stored)", key)]
    for i, (k, v) in enumerate(rows):
        put(ws, f"A{5+i}", k, "text", bold=True); put(ws, f"B{5+i}", v, "input")
    put(ws, "A12", "Engine Tier 1 count", "text", bold=True); put(ws, "B12", int(o.tier1.sum()), "input", "int"); put(ws, "C12", "Engine Tier 2 (full card) count", "text", bold=True); put(ws, "D12", int(o.qualifies.sum()), "input", "int")
    put(ws, "A11", "Status", "text", bold=True); put(ws, "B11", '=IF(A_HashCurrent=B9,"OK - sims match current assumptions","STALE - rerun sims")', "formula")
    ws.conditional_formatting.add("B11", FormulaRule(formula=['LEFT(B11,5)="STALE"'], font=Font(name="Arial", size=10, color=RED, bold=True)))
    name(wb, "Sim_Stale", "M_Sims!$B$11"); REG["sims_status"] = "M_Sims!$B$11"; REG["sims_N"] = "M_Sims!$B$6"
    cols = ["team", "wins_mean", "wins_sd", "p_playoffs", "p_bracket", "p_top6", "p_division", "p_conference", "p_title", "p_cup_group", "p_cup", "p_pick1", "p_top4", "p_top5", "p_lottery", "pick_mean", "se_title", "se_playoffs"]
    labels = ["Team", "Mean wins", "SD wins", "P(top-10 in conf)", "P(16-team playoffs)", "P(top-6 seed)", "P(division)", "P(conference)", "P(title)", "P(Cup group)", "P(Cup)", "P(#1 pick)", "P(top-4 pick)", "P(top-5 pick)", "P(lottery)", "Mean pick", "MC SE title", "MC SE top-10"]
    put(ws, "A13", "Team probabilities (100,000 simulated seasons)", "text", bold=True); headers(ws, 14, labels)
    cm = {c: CL(i + 1) for i, c in enumerate(cols)}
    for i, r in S.iterrows():
        row = 15 + i
        for c in cols:
            v = r[c]; put(ws, f"{cm[c]}{row}", v if c == "team" else float(v), "input", None if c == "team" else ("pct" if c.startswith(("p_", "se_")) else "num2"))
    REG["sims_team"] = dict(first=15, last=14 + len(S), cols=cm)
    # conference-rank distribution (columns after the main table)
    off = len(cols) + 2
    for k in range(1, 16):
        put(ws, f"{CL(off+k)}14", f"P(conf rank {k})", "header")
        for i, r in S.iterrows():
            put(ws, f"{CL(off+k)}{15+i}", float(r[f"p_confrank_{k}"]), "input", "pct")
    REG["sims_rank_col0"] = off
    # wins pmf
    H = pd.read_csv(C("sim_robust_wins_hist.csv")); H = H[H.scenario == "base"]
    pr0 = 15 + len(S) + 3
    put(ws, f"A{pr0-1}", "Distribution of season wins P(W = w)", "text", bold=True)
    put(ws, f"A{pr0}", "Team \\ wins", "header")
    for w in range(83):
        put(ws, f"{CL(2+w)}{pr0}", w, "header")
    for i, t in enumerate(S.team):
        pm = H[H.team == t].sort_values("wins").p.values
        put(ws, f"A{pr0+1+i}", t, "input")
        for w in range(83):
            put(ws, f"{CL(2+w)}{pr0+1+i}", float(pm[w]), "input", "0.00000")
    REG["sims_pmf"] = dict(hdr=pr0, first=pr0 + 1, last=pr0 + len(S), c0=2, c1=84)
    # CI table
    ci0 = pr0 + len(S) + 4
    put(ws, f"A{ci0-1}", "Edge confidence intervals / robustness / portfolio Kelly per odds row (engine output)", "text", bold=True)
    hd = ["Row id", "EV CI low (80%)", "EV CI high (80%)", "P(EV>0) over parameter draws", "Alt-definition EV", "Alt EV CI low", "Alt EV CI high", "Robust OK", "EV kappa=0", "EV kappa=1.57", "EV sigma-10%", "EV sigma+10%", "Portfolio Kelly (frac of bankroll)", "Bottom-10 projected", "EV CI low - zero-sum model (WINS)", "Static block (miscalibrated EV bucket / compression rule)", "Tier 1 static OK (direction rule + named driver)", "Tier 1 portfolio Kelly (frac, engine cap)", "Tier 1 named driver", "Engine exclusion / hold (Tier 1)"]
    headers(ws, ci0, hd)
    for i, r in o.iterrows():
        row = ci0 + 1 + i
        vals = [int(r.row_id), r.ev_lo, r.ev_hi, r.p_ev_pos, r.ev_alt, r.ev_lo_alt, r.ev_hi_alt, int(bool(r.robust_ok)), r.ev_kappa_0, r.ev_kappa_hi, r.ev_sigma_lo, r.ev_sigma_hi, r.kelly_portfolio, int(bool(r.bottom10)), r.ev_lo_zs, int(bool(r.static_block)), int(bool(r.t1_static_ok)), r.tier1_kelly, (r.t1_driver if isinstance(r.t1_driver, str) else "-"), int(bool(r.t1_excluded))]
        fm = ["int", "num3", "num3", "pct", "num3", "num3", "num3", "int", "num3", "num3", "num3", "num3", "0.0000", "int", "num3", "int", "int", "0.0000", "text", "int"]
        for j, (v, f) in enumerate(zip(vals, fm)):
            put(ws, f"{CL(1+j)}{row}", "-" if (isinstance(v, float) and np.isnan(v)) else v, "input", f)
    REG["sims_ci"] = dict(first=ci0 + 1, last=ci0 + len(o))
    widths(ws, {"A": 26, "B": 22}); finish(ws); ws.freeze_panes = "B15"
    return key


def fix_windist_links(wb):
    """Replace the placeholder P(over) sim formula in M_WinDist with a SUMPRODUCT over the sim pmf."""
    ws = wb["M_WinDist"]; wd = REG["windist"]; pm = REG["sims_pmf"]
    hdr = f"M_Sims!${CL(pm['c0'])}${pm['hdr']}:${CL(pm['c1'])}${pm['hdr']}"
    for i in range(wd["n"]):
        row = wd["first"] + i
        trow = f"MATCH(A{row},M_Sims!$A${pm['first']}:$A${pm['last']},0)"
        ws[f"G{row}"].value = f"=SUMPRODUCT(({hdr}>B{row})*INDEX(M_Sims!${CL(pm['c0'])}${pm['first']}:${CL(pm['c1'])}${pm['last']},{trow},0))"


def build_lottery(wb):
    ws = wb.create_sheet("M_Lottery2027"); sheet_header(ws, "M_Lottery2027 - 3-2-1 lottery rules, restrictions, pick ownership, per-team pick distribution", span=10)
    rules = [("Teams in lottery", "16 (10 non-play-in, four #9/#10 seeds, two 7v8 play-in losers)", "NBA.com 5/28/2026"),
             ("Balls", "37: 3 worst x2; 4th-10th worst x3; #9/#10 seeds x2 (4 teams); 7v8 losers x1 (2 teams)", "NBA.com, ESPN, Hoops Rumors"),
             ("Draws", "All 16 picks drawn (lottery_n_draws = 16)", "NBA.com, Tankathon"),
             ("Floor", "Three worst records cannot fall below #12; others no lower than #16", "NBA.com"),
             ("Restrictions", "No #1 in consecutive drafts; no top-5 in three straight; apply to the ORIGINAL team's pick even if traded", "NBA.com, ESPN"),
             ("2027 restricted", "UTA: no top-5 (top-5 in 2025 and 2026). WAS: no #1 (won 2026 lottery)", "bbref draft history + ESPN"),
             ("Trade deadline", "Thursday Feb 11, 2027, 3:00 pm ET (tank module evaluation point)", "NBA.com key dates"),
             ("7v8 loser keeps ball if it wins the 8-seed game", "Assumption (default yes) - not stated explicitly", "assumptions.json")]
    headers(ws, 6, ["Rule", "Detail", "Source"])
    for i, (a, b, c) in enumerate(rules):
        put(ws, f"A{7+i}", a, "text"); put(ws, f"B{7+i}", b, "text"); put(ws, f"C{7+i}", c, "text")
    r0 = 7 + len(rules) + 2
    put(ws, f"A{r0-1}", "Per-team 2027 pick distribution (sim) and ownership", "text", bold=True)
    headers(ws, r0, ["Team", "P(lottery)", "P(#1)", "P(top-4)", "P(top-5)", "Mean pick", "Pick owner / status", "Protection / swap detail", "Tank-incentive factor (kprot)", "Reconciliation discrepancy"])
    S = REG["sims_team"]; cm = S["cols"]; rec = pd.read_csv(C("picks_2027_reconciled.csv")).set_index("team"); rules_t = pd.read_csv(os.path.join(ROOT, "params/pick_ownership_rules.csv")).set_index("team")
    own = pd.read_csv(C("picks_2027.csv")).set_index("team")
    from ..data.teams import TEAMS
    for i, t in enumerate(sorted(TEAMS)):
        r = r0 + 1 + i; sr = S["first"] + i
        put(ws, f"A{r}", t, "text")
        for col, key in (("B", "p_lottery"), ("C", "p_pick1"), ("D", "p_top4"), ("E", "p_top5"), ("F", "pick_mean")):
            put(ws, f"{col}{r}", f"=M_Sims!{cm[key]}{sr}", "link", "pct" if col != "F" else "num1")
        put(ws, f"G{r}", own.loc[t, "owner_status"], "text"); put(ws, f"H{r}", str(own.loc[t, "protection"]) + " | " + str(own.loc[t, "swap_or_conditional_detail"]), "text")
        put(ws, f"I{r}", int(rules_t.loc[t, "kprot"]), "text"); put(ws, f"J{r}", str(rec.loc[t, "discrepancy"]), "text")
    widths(ws, {"A": 22, "B": 60, "C": 26, "H": 50, "J": 40}); finish(ws)


def build_players(wb):
    ws = wb.create_sheet("M_Players"); sheet_header(ws, "M_Players - player markets (G4): stat leaders, MVP, DPOY, ROY", span=14)
    put(ws, "A4", "Probabilities are simulation outputs (100k season sims; 80% interval = season-block bootstrap of the rate/award fits); EV, shrunk EV and the Tier tests are live formulas on Assumptions. Stat-leader probabilities are sharpened p^gamma (gamma from leave-one-season-out CV; see Backtest notes / G6 report). TPG = three-pointers made per game. Display-only markets (MIP, 6MOY, COY, Clutch, Cup MVP) are on S_Markets.", "text", italic=True)
    put(ws, "A5", "Tier 1 here = Tier 2 test + fair >= A_t1_fair + edge survives A_t1_shrink; stakes are multi-outcome fractional Kelly on the shrunk probability within each market (cap 3% per market); Tier 2 stakes are not shown. MVP / DPOY / ROY are DISPLAY-ONLY (decision 2026-10-16: voting models trained on 12-13 winners and they fail sanity checks against the exchanges); stat-leader bets need an external reference (none exists today).", "text", italic=True)
    cols = ["Market", "Selection", "Team", "American", "Decimal", "Fair prob (Shin)", "Model prob", "Model p 10th pct", "Model p 90th pct", "EV (model)", "EV (shrunk)", "EV lo (shrunk)", "Worst scenario EV (shrunk)", "Tier 2",
            "Tier 1", "Tier 1 stake (frac)", "Tier 1 stake ($)", "Proj mpg", "Proj games", "Driver", "Tier 1 holds at sharpening-exponent CI bounds (engine)", "Joint-Kelly stake before ROY multiplier (engine)", "Min acceptable price (EV at shrink 0.75 = 0)", "Consensus", "Exchange average prob (Raw_MarketRef)", "Blended prob (book fair + exchange) / 2", "EV at blended prob", "Model vs exchange flag", "Engine exclusion (news / user)", "Display-only / no external reference (engine)"]
    headers(ws, 7, cols, height=45)
    from ..pricing import marketref as _MR
    _n = len(_MR.load()); _m0, _m1 = 8, 7 + _n
    o = pd.read_csv(C("player_pricing_table.csv")); o = o[o.modelled].copy()
    put(ws, "A6", "Engine Tier 1 count (players)", "text", bold=True); put(ws, "B6", int(o.tier1.sum()), "input", "int")
    o["ord"] = o.market.map({m: i for i, m in enumerate(["MVP", "DPOY", "ROY", "LDR_PPG", "LDR_RPG", "LDR_APG", "LDR_SPG", "LDR_BPG", "LDR_TPG"])})
    o = o.sort_values(["ord", "fair"], ascending=[True, False]).reset_index(drop=True)
    for i, r in o.iterrows():
        k = 8 + i
        put(ws, f"A{k}", r.market, "input"); put(ws, f"B{k}", r.selection, "input"); put(ws, f"C{k}", r.team if isinstance(r.team, str) else "-", "input"); put(ws, f"D{k}", int(r.american), "input", "0")
        put(ws, f"E{k}", f"=IF(D{k}>0,1+D{k}/100,1+100/ABS(D{k}))", "formula", "num3"); put(ws, f"F{k}", float(r.fair), "input", "pct2")
        put(ws, f"G{k}", float(r.p), "input", "pct2"); put(ws, f"H{k}", float(r.p_lo), "input", "pct2"); put(ws, f"I{k}", float(r.p_hi), "input", "pct2")
        put(ws, f"J{k}", f"=G{k}*E{k}-1", "formula", "pct"); put(ws, f"K{k}", f"=((1-A_shrink)*G{k}+A_shrink*F{k})*E{k}-1", "formula", "pct")
        put(ws, f"L{k}", f"=((1-A_shrink)*H{k}+A_shrink*F{k})*E{k}-1", "formula", "pct"); put(ws, f"M{k}", float(r.ev_s_worst_scenario), "input", "pct")
        put(ws, f"N{k}", f"=AND(K{k}>=A_minev,L{k}>0,M{k}>=A_minev,OR(NOT(ISNUMBER(Y{k})),AA{k}>0),NOT(AD{k}))", "formula")
        put(ws, f"Y{k}", f'=IFERROR(AVERAGEIFS(Raw_MarketRef!$G${_m0}:$G${_m1},Raw_MarketRef!$A${_m0}:$A${_m1},A{k},Raw_MarketRef!$D${_m0}:$D${_m1},B{k},Raw_MarketRef!$H${_m0}:$H${_m1},"Y"),"-")', "formula", "pct2")
        put(ws, f"Z{k}", f"=IF(ISNUMBER(Y{k}),(F{k}+Y{k})/2,F{k})", "formula", "pct2"); put(ws, f"AA{k}", f"=Z{k}*E{k}-1", "formula", "pct")
        put(ws, f"AB{k}", f'=IF(ISNUMBER(Y{k}),IF(OR(G{k}/Y{k}>A_blend_ratio,G{k}/Y{k}<1/A_blend_ratio),"FLAG: >"&A_blend_ratio&"x apart",""),"")', "flag"); put(ws, f"AC{k}", bool(r.t1_excluded), "input"); put(ws, f"AD{k}", bool(r.display_block), "input")
        put(ws, f"O{k}", f"=AND(N{k},U{k},NOT(AC{k}),F{k}>=A_t1_fair,((1-A_t1_shrink)*G{k}+A_t1_shrink*F{k})*E{k}-1>=A_minev,((1-A_t1_shrink)*H{k}+A_t1_shrink*F{k})*E{k}-1>0)", "formula")
        put(ws, f"V{k}", float(r.stake_t1_premult if r.market == "ROY" else r.stake_t1), "input", "0.0000"); put(ws, f"P{k}", f'=V{k}*IF(A{k}="ROY",A_roy_stake_mult,1)', "formula", "0.0000")
        ps_ = f"((1-A_t1_shrink)*G{k}+A_t1_shrink*F{k})"; put(ws, f"W{k}", f"=IF(1/{ps_}>=2,(1/{ps_}-1)*100,-100/(1/{ps_}-1))", "formula", "amer"); put(ws, f"X{k}", "n/a", "text"); put(ws, f"Q{k}", f'=IF(AND(O{k},ISNUMBER(A_bankroll)),P{k}*A_bankroll,"-")', "formula", "money")
        put(ws, f"R{k}", float(r.proj_mpg) if pd.notna(r.proj_mpg) else "-", "input", "num1"); put(ws, f"S{k}", float(r.proj_gp) if pd.notna(r.proj_gp) else "-", "input", "num1"); put(ws, f"T{k}", str(r.driver) if isinstance(r.driver, str) else "", "text"); put(ws, f"U{k}", bool(r.tier1_gamma_lo and r.tier1_gamma_hi), "input")
    last = 7 + len(o); REG["m_players"] = dict(first=8, last=last, rowmap={(r.market, r.selection): 8 + i for i, r in o.iterrows()})
    widths(ws, {"A": 12, "B": 28, "T": 90}); finish(ws)
