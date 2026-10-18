"""Release checks shared by the build (fail-closed), the clean-room runner and the tests.
- integrity_flags(path): cached-value scan of a workbook for integrity flags (FLAG / CHECK / STALE strings, any non-OK/INFO status on Checks, M_WinDist deltas).
- analytic_vs_sim(): Python re-computation of the Checks!'Analytic vs sim P(over)' comparison (so it can run without Excel).
- workbook_card(path): decodes the Tier 1 rows of a workbook WITHOUT Excel (formula text -> engine rows) and, when cached values exist, also reads the displayed stakes.
- card_from_tables(): the final Tier 1 card as computed by the pricing stages (pricing_table.csv + player_pricing_table.csv)."""
import json, math, os, re
import numpy as np, pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
C = lambda f: os.path.join(ROOT, "data", "clean", f)
FLAG_RE = re.compile(r"^(FLAG|CHECK|STALE)\b")
CARD_COLS = ["market", "selection", "side", "line", "american", "fair", "model_prob", "ev", "ev_shrunk75", "min_price", "stake_frac"]


def card_from_tables():
    return card_from_tables_at(C("pricing_table.csv"), C("player_pricing_table.csv"))


def card_from_tables_at(team_path, player_path):
    o = pd.read_csv(team_path); T = o[o.tier1].copy()
    rows = [dict(market=r.market, selection=r.selection, side=r.side, line=(None if pd.isna(r.line) else float(r.line)), american=float(r.american), fair=float(r.fair), model_prob=float(r.model_prob),
                 ev=float(r.ev), ev_shrunk75=float((0.25 * r.model_prob + 0.75 * r.fair) * r.dec - 1), min_price=float(r.min_price), stake_frac=float(r.tier1_kelly)) for r in T.itertuples()]
    P = pd.read_csv(player_path); P = P[P.tier1]
    rows += [dict(market=r.market, selection=r.selection, side="YES", line=None, american=float(r.american), fair=float(r.fair), model_prob=float(r.p), ev=float(r.ev),
                  ev_shrunk75=float((0.25 * r.p + 0.75 * r.fair) * r.dec - 1), min_price=float(r.min_price), stake_frac=float(r.stake_t1)) for r in P.itertuples()]
    return pd.DataFrame(rows, columns=CARD_COLS).sort_values(["market", "selection"]).reset_index(drop=True)


def analytic_vs_sim(threshold_pp=2.0):
    """Normal-approximation P(over) (the M_WinDist formula, corrected exp(-z^2/2)) vs the simulation's P(over), per WINS line. Returns (max_abs_pp, rows over threshold)."""
    from scipy.stats import norm
    gm = json.load(open(C("game_model_fit.json"))); prov = json.load(open(os.path.join(ROOT, "params", "provenance.json")))
    sg = gm["sigma_game"]; st = float(prov["sigma_team_srs"]["value"]); rel = json.load(open(os.path.join(ROOT, "params", "release.json"))); scale = float(rel["analytic_sd_scale"]); kskew = float(rel["analytic_skew_slope"])
    tp = pd.read_csv(C("team_projection_2027.csv")).set_index("abbr"); o = pd.read_csv(C("pricing_table.csv")); w = o[(o.market == "WINS") & (o.side == "OVER")]
    bad = []; mx = 0.0
    for r in w.itertuples():
        m = float(tp.pred_wins[r.team]); p = m / 82.0; sd = scale * math.sqrt(82 * p * (1 - p) + (82 * norm.pdf(norm.ppf(p)) / sg * st) ** 2)
        z = (r.line - m) / sd; g = kskew * (m - 41.0); pover = 1 - (norm.cdf(z) - norm.pdf(z) * g / 6.0 * (z * z - 1))
        d = (pover - r.model_prob) * 100.0; mx = max(mx, abs(d))
        if abs(d) > threshold_pp: bad.append((r.team, r.line, round(d, 2)))
    return mx, bad


def integrity_flags(path):
    """Returns (flags, computed). flags = list of (sheet, cell, value); computed = False when the workbook has no cached values (built without Excel)."""
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True); flags = []; computed = False
    ck = wb["Checks"]
    for r in range(8, ck.max_row + 1):
        a, b, c = ck.cell(r, 1).value, ck.cell(r, 2).value, ck.cell(r, 3).value
        if c is not None: computed = True
        if c not in (None, "OK", "INFO") and a: flags.append(("Checks", f"C{r}", f"{a}: {c}"))
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                v = cell.value
                if isinstance(v, str) and FLAG_RE.match(v) and ws.title != "Checks": flags.append((ws.title, cell.coordinate, v))
    return flags, computed


def _rowid_map():
    return {int(r): i for i, r in enumerate(pd.read_csv(C("pricing_table.csv")).row_id)}


def workbook_card(path):
    """Tier 1 rows of the workbook, decoded without Excel: Tier1_Card rows 8.. carry formulas pointing at S_Markets / M_Players rows; S_Markets col Z holds the static odds row id and
    M_Players cols A/B hold static market/selection. Returns DataFrame(market, selection, stake_formula_source, cached_stake)."""
    import openpyxl
    wf = openpyxl.load_workbook(path); wv = openpyxl.load_workbook(path, data_only=True); t = wf["Tier1_Card"]; tv = wv["Tier1_Card"]; sm = wf["S_Markets"]; mp = wf["M_Players"]
    o = pd.read_csv(C("pricing_table.csv")); rows = []
    for r in range(8, t.max_row + 1):
        mkt = t.cell(r, 2).value
        if not mkt or str(mkt).startswith("Live Tier 1"): break
        f = t.cell(r, 3).value; m = re.match(r"=(S_Markets|M_Players)!B(\d+)", str(f))
        if not m: continue
        src, rr = m.group(1), int(m.group(2))
        if src == "S_Markets":
            rid = int(sm.cell(rr, 26).value); x = o[o.row_id == rid].iloc[0]; rows.append(dict(market=x.market, selection=x.selection, side=x.side, source="team", cached_stake=tv.cell(r, 15).value))
        else:
            rows.append(dict(market=mp.cell(rr, 1).value, selection=mp.cell(rr, 2).value, side="YES", source="player", cached_stake=tv.cell(r, 15).value))
    return pd.DataFrame(rows)


def tier1_flags_live(path):
    """Cached 'Live Tier 1 status' (col U) of every listed row, plus the cached completeness difference; None when the workbook has no cached values."""
    import openpyxl
    wv = openpyxl.load_workbook(path, data_only=True); t = wv["Tier1_Card"]; out = []
    for r in range(8, t.max_row + 1):
        if not t.cell(r, 2).value or str(t.cell(r, 2).value).startswith("Live Tier 1"): break
        out.append(t.cell(r, 21).value)
    return out
