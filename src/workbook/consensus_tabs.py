"""Raw_Consensus: dated external win projections (source URL, type, pull date) per team; feeds the M_WinDist consensus columns."""
import json, os
import pandas as pd
from openpyxl.utils import get_column_letter as CL
from .styles import *
from .core import REG, ROOT

def build_consensus(wb):
    ws = wb.create_sheet("Raw_Consensus"); sheet_header(ws, "Raw_Consensus - external projected wins (dated sources; STAT_MODEL gates WINS bets, EXPERT is displayed only)", span=8)
    meta = json.load(open(os.path.join(ROOT, "data/consensus/sources.json"))); src = meta["sources"]
    M = pd.read_csv(os.path.join(ROOT, "data/consensus/consensus_wins_2026-10-15.csv")).set_index("team")
    put(ws, "A5", "Values are copied as supplied on 2026-10-15 (blue = inputs). Market odds are never model inputs; these are external projections used only as an independent cross-check.", "text", italic=True)
    headers(ws, 7, ["Source ID", "Source", "URL", "Type", "Pull date", "As of", "Note"])
    for i, s in enumerate(src):
        r = 8 + i
        for col, k in zip("ABCDEFG", ("id", "name", "url", "type", "pull_date", "as_of", "note")): put(ws, f"{col}{r}", s[k], "input")
    r0 = 8 + len(src) + 2
    put(ws, f"A{r0}", "Searched, not added", "text", bold=True)
    for j, x in enumerate(meta.get("searched_not_added", [])):
        put(ws, f"A{r0+1+j}", x["source"], "text"); put(ws, f"C{r0+1+j}", x["url"], "text"); put(ws, f"G{r0+1+j}", x["why"], "text")
    hr = r0 + len(meta.get("searched_not_added", [])) + 3
    put(ws, f"A{hr-1}", "Type", "text", bold=True)
    headers(ws, hr, ["Team"] + [s["name"] for s in src])
    cols = {}
    for j, s in enumerate(src):
        c = CL(2 + j); cols[s["id"]] = c; put(ws, f"{c}{hr-1}", s["type"], "input")
    teams = sorted(M.index)
    for i, t in enumerate(teams):
        r = hr + 1 + i; put(ws, f"A{r}", t, "input")
        for s in src: put(ws, f"{cols[s['id']]}{r}", float(M.loc[t, s["id"]]), "input", "num1")
    tot = hr + 1 + len(teams); put(ws, f"A{tot}", "League total", "text", bold=True)
    for s in src: put(ws, f"{cols[s['id']]}{tot}", f"=SUM({cols[s['id']]}{hr+1}:{cols[s['id']]}{tot-1})", "formula", "num1")
    REG["cons"] = dict(first=hr + 1, last=tot - 1, cols=cols, types={s["id"]: s["type"] for s in src}, names={s["id"]: s["name"] for s in src})
    widths(ws, {"A": 22, "B": 30, "C": 60, "G": 70}); finish(ws)
