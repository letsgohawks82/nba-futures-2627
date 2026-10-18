"""Independent re-derivation of the committed Basketball-Reference parquet tables from the raw page archive (data/raw/...), WITHOUT writing any table:
    python -m src.data.rederive_history [--report reports/history_rederivation.md]
Parsers: player_rs / player_po / games reuse the committed parsers (src/data/clean_players.py, clean_games.py logic); team / awards / draft / roster_check had NO committed parser (they were
parsed ad hoc in the G1 session), so they are re-parsed here from the raw HTML by data-stat keys and compared with the committed tables. Exit code 1 if any table disagrees."""
import argparse, glob, json, os, re, sys
import numpy as np, pandas as pd
from bs4 import BeautifulSoup
from .clean_players import parse_table, season_files, SPECS

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW = os.path.join(ROOT, "data", "raw"); CL = lambda f: os.path.join(ROOT, "data", "clean", f)


def tables_by_id(path):
    h = open(path, encoding="utf-8").read().replace("<!--", "").replace("-->", ""); s = BeautifulSoup(h, "lxml")
    return {t.get("id"): t for t in s.find_all("table") if t.get("id")}


def rows_of(t):
    out = []
    for tr in t.find("tbody").find_all("tr"):
        if "thead" in (tr.get("class") or []): continue
        d = {}
        for c in tr.find_all(["th", "td"]):
            k = c.get("data-stat")
            if not k: continue
            d[k] = c.get_text(strip=True)
            if c.get("data-append-csv"): d["bbref_id"] = c["data-append-csv"]
        if d: out.append(d)
    return out


def fix_text(s):
    """The raw pages were saved mojibake (UTF-8 bytes decoded as latin-1); the committed tables carry the repaired text (CLAUDE.md, G1). Same repair here."""
    if not isinstance(s, str): return s
    try: return s.encode("latin-1").decode("utf-8")
    except Exception: return s


def norm_df(d):
    d = d.copy()
    for c in d.columns: d[c] = d[c].map(fix_text)
    return d.astype(object).where(d.notna(), "<NA>").astype(str)


def compare(name, new, old, keys=None):
    """Positional comparison (both tables are built in file order: season, then page order). new/old: DataFrames. Returns dict(rows..., mismatched_cells, ...)."""
    new = norm_df(new).reset_index(drop=True); old = norm_df(old).reset_index(drop=True)
    cols = [c for c in old.columns if c in new.columns]
    if len(new) != len(old): return dict(table=name, rows_rederived=len(new), rows_committed=len(old), matched_keys=0, only_rederived=abs(len(new) - len(old)), only_committed=0, columns_compared=len(cols), columns_committed_not_rederived=[], mismatched_cells=-1, examples=["row counts differ"])
    bad = 0; ex = []
    for c in cols:
        d = (new[c] != old[c]); bad += int(d.sum())
        if d.any() and len(ex) < 3: ex.append((c, int(d.idxmax()), new[c][d].iloc[0], old[c][d].iloc[0]))
    return dict(table=name, rows_rederived=len(new), rows_committed=len(old), matched_keys=len(new), only_rederived=0, only_committed=0, columns_compared=len(cols),
                columns_committed_not_rederived=[c for c in old.columns if c not in new.columns], mismatched_cells=bad, examples=ex)


def _compare_old_keys(name, new, old, keys):
    new = new.astype(str); old = old.astype(str)
    cols = [c for c in old.columns if c in new.columns and c not in keys]
    n = new.drop_duplicates(keys).set_index(keys); o = old.drop_duplicates(keys).set_index(keys)
    both = n.index.intersection(o.index); bad = 0; ex = []
    for c in cols:
        a = n.loc[both, c]; b = o.loc[both, c]; d = (a != b)
        bad += int(d.sum())
        if d.any() and len(ex) < 3: ex.append((c, str(d[d].index[0]), a[d].iloc[0], b[d].iloc[0]))
    return dict(table=name, rows_rederived=len(new), rows_committed=len(old), matched_keys=len(both), only_rederived=len(n.index.difference(o.index)), only_committed=len(o.index.difference(n.index)),
                columns_compared=len(cols), columns_committed_not_rederived=[c for c in old.columns if c not in new.columns and c not in keys], mismatched_cells=bad, examples=ex)


def players_and_games():
    res = []
    for sub, kind, ids in SPECS:
        frames = []
        for y, f in season_files(sub, kind).items():
            df = parse_table(open(f, encoding="utf-8").read(), ids)
            if df.empty: continue
            df.insert(0, "season", y); frames.append(df)
        new = pd.concat(frames, ignore_index=True); old = pd.read_parquet(CL(f"{sub}_{kind.replace('-', '_')}.parquet"))
        r = compare(f"{sub}_{kind.replace('-', '_')}.parquet", new, old, ["season", "ranker"] if "ranker" in new.columns else ["season", "player"]); res.append(r)
    rows = []
    for f in sorted(glob.glob(os.path.join(RAW, "games", "*.html_*"))):
        y, m = os.path.basename(f).split(".")[0].split("_", 1)
        t = BeautifulSoup(open(f, encoding="utf-8").read(), "lxml").find("table", id="schedule")
        if t is None: continue
        for tr in t.find("tbody").find_all("tr"):
            if "thead" in (tr.get("class") or []): continue
            d = {c.get("data-stat"): c.get_text(strip=True) for c in tr.find_all(["th", "td"])}; d["season"] = int(y); d["file_month"] = m; rows.append(d)
    g = pd.DataFrame(rows); g = g[g.visitor_pts.str.len() > 0].copy(); g["playoff"] = g["game_remarks"].fillna("").ne("") & False
    old = pd.read_parquet(CL("games_hist.parquet")); keys = [c for c in ("season", "file_month", "date_game", "visitor_team_name", "home_team_name") if c in old.columns]
    res.append(compare("games_hist.parquet", g, old, keys)); return res


def team_awards_draft():
    res = []
    rows = []
    for f in sorted(glob.glob(os.path.join(RAW, "team", "*_team.html_*"))):
        y = int(os.path.basename(f)[:4]); t = tables_by_id(f).get("advanced-team")
        for d in rows_of(t): d["season"] = y; d["tbl"] = "advanced-team"; rows.append(d)
    res.append(compare("team_season_hist.parquet", pd.DataFrame(rows), pd.read_parquet(CL("team_season_hist.parquet")), ["season", "ranker"]))
    rows = []
    for f in sorted(glob.glob(os.path.join(RAW, "awards", "*.html_*"))):
        y = int(os.path.basename(f)[:4]); tb = tables_by_id(f)
        for aw in tb:                      # page order (mvp, roy, dpoy), as in the committed table
            if aw in ("mvp", "roy", "dpoy"):
                for d in rows_of(tb[aw]): d["season"] = y; d["award"] = aw; rows.append(d)
    new = pd.DataFrame(rows); old = pd.read_parquet(CL("award_voting.parquet")); keys = ["season", "award", "rank"]
    res.append(compare("award_voting.parquet", new, old, keys))
    rows = []
    for f in sorted(glob.glob(os.path.join(RAW, "draft", "nba_*.html_*"))):
        y = int(re.search(r"nba_(\d{4})", os.path.basename(f)).group(1)); t = tables_by_id(f).get("stats")
        for d in rows_of(t): d["draft_year"] = str(y); rows.append(d)
    new = pd.DataFrame(rows); old = pd.read_parquet(CL("draft_picks.parquet"))
    res.append(compare("draft_picks.parquet", new, old, ["draft_year", "pick_overall"]))
    return res


def roster_check():
    """rosters_bbref_2027_20261015.csv (G5 revision) vs the raw roster-check pages: team membership by player name."""
    old = pd.read_csv(CL("rosters_bbref_2027_20261015.csv")); ocol = [c for c in old.columns if "name" in c.lower() or c.lower() == "player"][0]; tcol = [c for c in old.columns if c.lower() in ("team", "abbr")][0]
    new = []
    for f in sorted(glob.glob(os.path.join(RAW, "roster_check", "*_2027.html_*"))):
        ab = os.path.basename(f).split("_")[0]; t = tables_by_id(f).get("roster")
        for d in rows_of(t): new.append(dict(team=ab, player=d.get("player", "")))
    new = pd.DataFrame(new); new["player"] = new.player.map(fix_text).str.replace(r"\(TW\)$", "", regex=True)           # the committed list drops the two-way tag
    a = set(zip(new.team, new.player)); b = set(zip(old[tcol].astype(str), old[ocol].astype(str)))
    return [dict(table="rosters_bbref_2027_20261015.csv (team, player)", rows_rederived=len(a), rows_committed=len(b), matched_keys=len(a & b), only_rederived=len(a - b), only_committed=len(b - a), columns_compared=2,
                 columns_committed_not_rederived=[], mismatched_cells=len(a ^ b), examples=sorted(a ^ b)[:3])]


def schedule_raw():
    """data/clean/schedule_raw_bbref.csv vs the archived 2027 schedule pages, parsed with the committed pull-time parser (src/data/pull_schedule.py: bbref.tables(html)[0])."""
    from .bbref import tables
    frames = []
    for m in ["october", "november", "december", "january", "february", "march", "april"]:
        f = glob.glob(os.path.join(RAW, "schedule", f"bbref_2027_games_{m}.html_*"))
        if not f: continue
        t = tables(open(f[0], encoding="utf-8").read())[0]; t["month"] = m; frames.append(t)
    new = pd.concat(frames, ignore_index=True); old = pd.read_csv(CL("schedule_raw_bbref.csv"))
    return [compare("schedule_raw_bbref.csv", new, old)]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--report", default=os.path.join(ROOT, "reports", "history_rederivation.md")); a = ap.parse_args()
    res = players_and_games() + team_awards_draft()
    try: res += schedule_raw()
    except Exception as e: res.append(dict(table="schedule_raw_bbref.csv", error=repr(e)))
    try: res += roster_check()
    except Exception as e: res.append(dict(table="rosters_bbref_2027 (roster check)", error=repr(e)))
    ok = all(("error" not in r) and r["mismatched_cells"] == 0 and r["only_rederived"] == 0 and r["only_committed"] == 0 for r in res)
    L = ["# History re-derivation: raw Basketball-Reference pages vs the committed tables", "",
         f"**Result: {'ALL TABLES AGREE' if ok else 'DIFFERENCES FOUND'}.** Each table is re-parsed from the archived raw pages and compared cell by cell (as strings) with the committed parquet / csv on the key shown. Parsers: player_rs, player_po and games use the committed code in `src/data/clean_players.py` / `clean_games.py`; team, awards, draft and the roster check had no committed parser and are re-parsed by `src/data/rederive_history.py`.", "",
         "| Table | Rows re-derived | Rows committed | Keys matched | Only re-derived | Only committed | Columns compared | Mismatched cells |", "|---|---|---|---|---|---|---|---|"]
    for r in res:
        if "error" in r: L.append(f"| {r['table']} | error: {r['error']} | | | | | | |"); continue
        L.append(f"| `{r['table']}` | {r['rows_rederived']:,} | {r['rows_committed']:,} | {r['matched_keys']:,} | {r['only_rederived']} | {r['only_committed']} | {r['columns_compared']} | {r['mismatched_cells']} |")
    notes = [f"- `{r['table']}`: committed columns not present in the re-parse: {r['columns_committed_not_rederived']}" for r in res if r.get("columns_committed_not_rederived")]
    ex = [f"- `{r['table']}`: {r['examples']}" for r in res if r.get("examples")]
    if notes: L += ["", "## Columns the re-parse does not produce"] + notes
    if ex: L += ["", "## Examples of differences"] + ex
    open(a.report, "w", encoding="utf-8").write("\n".join(L) + "\n"); print("\n".join(L)); return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
