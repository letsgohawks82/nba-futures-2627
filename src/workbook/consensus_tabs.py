"""Raw_Consensus (dated external win projections, tagged STAT_MODEL / MARKET_INFORMED / EXPERT, roster_aware / results_based) and Raw_MarketRef (exchange prices, normalised)."""
import json, os
import pandas as pd
from openpyxl.utils import get_column_letter as CL
from .styles import *
from .core import REG, ROOT


def build_consensus(wb):
    ws = wb.create_sheet("Raw_Consensus"); sheet_header(ws, "Raw_Consensus - external projected wins (dated sources; per-source regressions on the market median give the residuals used by the WINS consensus rule)", span=8)
    d = pd.read_csv(os.path.join(ROOT, "data/consensus/raw_consensus_20261016.csv"))
    meta = d.drop_duplicates("source").set_index("source"); M = d.pivot(index="team", columns="source", values="proj_wins")
    order = ["PredictionEngine", "Opta TRACR", "Massey (80->82 scaled)", "ESPN projection", "TeamRankings", "Bleacher Report"]
    put(ws, "A5", "Values copied as supplied (blue = inputs). ESPN / TeamRankings are MARKET_INFORMED (display only); Bleacher Report is EXPERT (display only); Opta and Massey are STAT_MODEL but RESULTS-BASED (they do not see offseason moves). Our own model is the roster-aware STAT_MODEL beside PredictionEngine. Market odds are never model inputs.", "text", italic=True)
    headers(ws, 7, ["Source ID", "Source", "URL / origin", "Type", "Method", "results_based", "Pull date"])
    for i, s in enumerate(order):
        r = 8 + i; m = meta.loc[s]
        for col, v in zip("ABCDEFG", (s, s, m.url, m.source_type, m.method, "Y" if m.method == "results_based" else "N", m.pull_date)): put(ws, f"{col}{r}", v, "input")
    r0 = 8 + len(order) + 1
    put(ws, f"A{r0}", "Massey: raw EW/EL is on the 80 published games; scaled here as EW x 82 / (EW + EL) as supplied (some rows sum to 81, not forced to 80). Opta TRACR xwins as supplied by the user (The Analyst).", "text", italic=True)
    sn = json.load(open(os.path.join(ROOT, "data/consensus/sources.json"))).get("searched_not_added", [])
    hr = r0 + 3
    put(ws, f"A{hr-1}", "Type / method", "text", bold=True)
    headers(ws, hr, ["Team"] + order)
    cols = {}
    for j, s in enumerate(order):
        c = CL(2 + j); cols[s] = c; put(ws, f"{c}{hr-1}", meta.loc[s].source_type + " / " + meta.loc[s].method, "input")
    teams = sorted(M.index)
    for i, t in enumerate(teams):
        r = hr + 1 + i; put(ws, f"A{r}", t, "input")
        for s in order: put(ws, f"{cols[s]}{r}", float(M.loc[t, s]), "input", "num2")
    tot = hr + 1 + len(teams); put(ws, f"A{tot}", "League total", "text", bold=True)
    for s in order: put(ws, f"{cols[s]}{tot}", f"=SUM({cols[s]}{hr+1}:{cols[s]}{tot-1})", "formula", "num1")
    put(ws, f"A{tot+2}", "Searched, not added (earlier pass)", "text", bold=True)
    for j, x in enumerate(sn): put(ws, f"A{tot+3+j}", x["source"], "text"); put(ws, f"C{tot+3+j}", x["url"], "text"); put(ws, f"G{tot+3+j}", x["why"], "text")
    REG["cons"] = dict(first=hr + 1, last=tot - 1, cols=cols, order=order, types={s: meta.loc[s].source_type for s in order}, methods={s: meta.loc[s].method for s in order})
    widths(ws, {"A": 22, "B": 26, "C": 44, "G": 40}); finish(ws)


def build_marketref(wb, o):
    """Raw_MarketRef: exchange/survey inputs (blue), normalised probabilities, exchange averages; compared with the book fair and the model."""
    from ..pricing import marketref as MR
    from ..data.namemap import norm
    ws = wb.create_sheet("Raw_MarketRef"); sheet_header(ws, "Raw_MarketRef - exchange prices and the GM survey (display + gating only; NEVER a model input)", span=10)
    put(ws, "A5", "Each exchange market is normalised to sum to 1 over the listed names (the unlisted tail is ignored). Prices below 10% carry a longshot bias: noted, not adjusted. Gate on M_Players: EV > 0 at the blended probability (book fair + exchange average) / 2 as well as at the model probability; model vs exchange average more than A_blend_ratio apart is flagged.", "text", italic=True)
    d = MR.load(); nm = pd.read_csv(os.path.join(ROOT, "data/clean/name_map.csv")); nm = nm[nm.source == "odds_book"].set_index("source_name").canonical
    odds_sel = {}
    for _, r in o[o.market.isin(["TITLE", "CONF_WEST", "MVP", "ROY", "DPOY"])].iterrows():
        c = nm.get(r.selection); odds_sel[(r.market, norm(c if isinstance(c, str) else r.selection))] = r.selection
    for m_, k_ in ((m, k) for m, k in zip(o.market, o.selection)): pass
    teams = {}
    from ..data.teams import NAME2ABBR
    for _, r in o[o.market.isin(["TITLE", "CONF_WEST"])].iterrows(): odds_sel[(r.market, norm(r.selection))] = r.selection
    headers(ws, 7, ["Market", "Source", "Selection (as listed)", "Selection (book spelling)", "Price / % (input)", "Listed sum", "Normalised prob", "Exchange?", "Date", "URL", "Note"])
    r = 8; first = r; n = len(d)
    for _, x in d.iterrows():
        sel = odds_sel.get((x.market, x.key), "")
        put(ws, f"A{r}", x.market, "input"); put(ws, f"B{r}", x.source, "input"); put(ws, f"C{r}", x.selection, "input"); put(ws, f"D{r}", sel if sel else "(not on the book's board)", "text")
        put(ws, f"E{r}", float(x.pct), "input", "num1")
        put(ws, f"F{r}", f"=SUMIFS($E${first}:$E${first + n - 1},$A${first}:$A${first + n - 1},A{r},$B${first}:$B${first + n - 1},B{r})", "formula", "num1"); put(ws, f"G{r}", f"=E{r}/F{r}", "formula", "pct")
        put(ws, f"H{r}", "Y" if x.is_exchange else "N", "input"); put(ws, f"I{r}", x.date, "input"); put(ws, f"J{r}", x.url, "text"); put(ws, f"K{r}", x.longshot_bias_note, "text")
        r += 1
    last = r - 1; REG["mref"] = dict(first=first, last=last)
    r += 2; put(ws, f"A{r}", "Comparison: book fair vs exchange average vs model", "text", bold=True); r += 1
    headers(ws, r, ["Market", "Selection (book spelling)", "Book fair", "Exchange average", "Blended (fair + exchange) / 2", "Model prob", "Model / exchange", "Flag"]); r += 1
    seen = set(); c0 = r; sk = REG["smk"]["last"]; mp = REG["m_players"]
    for _, x in d[d.is_exchange].iterrows():
        sel = odds_sel.get((x.market, x.key))
        if not sel or (x.market, sel) in seen: continue
        seen.add((x.market, sel))
        put(ws, f"A{r}", x.market, "text"); put(ws, f"B{r}", sel, "text")
        put(ws, f"C{r}", f"=SUMIFS(S_Markets!$I$8:$I${sk},S_Markets!$A$8:$A${sk},A{r},S_Markets!$B$8:$B${sk},B{r})", "link", "pct")
        put(ws, f"D{r}", f'=AVERAGEIFS($G${first}:$G${last},$A${first}:$A${last},A{r},$D${first}:$D${last},B{r},$H${first}:$H${last},"Y")', "formula", "pct")
        put(ws, f"E{r}", f"=(C{r}+D{r})/2", "formula", "pct")
        put(ws, f"F{r}", f'=SUMIFS(S_Markets!$J$8:$J${sk},S_Markets!$A$8:$A${sk},A{r},S_Markets!$B$8:$B${sk},B{r})+SUMIFS(M_Players!$G${mp["first"]}:$G${mp["last"]},M_Players!$A${mp["first"]}:$A${mp["last"]},A{r},M_Players!$B${mp["first"]}:$B${mp["last"]},B{r})', "link", "pct")
        put(ws, f"G{r}", f'=IF(D{r}>0,F{r}/D{r},"-")', "formula", "num2")
        put(ws, f"H{r}", f'=IF(ISNUMBER(G{r}),IF(F{r}=0,"",IF(OR(G{r}>A_blend_ratio,G{r}<1/A_blend_ratio),"DIVERGES >"&A_blend_ratio&"x vs exchange","")),"")', "flag")
        r += 1
    REG["mref"].update(cmp_first=c0, cmp_last=r - 1)
    widths(ws, {"A": 12, "B": 26, "C": 26, "D": 28, "J": 60, "K": 36}); finish(ws)
