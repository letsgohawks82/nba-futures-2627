"""Parse cached bbref season tables (data-stat keyed, with player ids) -> data/clean/*.parquet"""
import glob, os, re, sys
import pandas as pd
from bs4 import BeautifulSoup
from .common import ROOT, RAW, log_manifest

def parse_table(html, table_ids):
    html = html.replace("<!--", "").replace("-->", "")
    soup = BeautifulSoup(html, "lxml")
    t = None
    for tid in table_ids:
        t = soup.find("table", id=tid)
        if t is not None: break
    if t is None:
        return pd.DataFrame()
    rows = []
    for tr in t.find("tbody").find_all("tr"):
        if "thead" in (tr.get("class") or []): continue
        d = {}
        for c in tr.find_all(["th", "td"]):
            k = c.get("data-stat")
            if not k: continue
            d[k] = c.get_text(strip=True)
            if c.get("data-append-csv"): d["bbref_id"] = c["data-append-csv"]
        if d: rows.append(d)
    df = pd.DataFrame(rows)
    return df.apply(pd.to_numeric, errors="ignore") if False else df

def season_files(subdir, kind):
    out = {}
    for f in glob.glob(os.path.join(RAW, subdir, f"*_{kind}.html_*")):
        y = int(os.path.basename(f)[:4]); out[y] = f
    return dict(sorted(out.items()))

SPECS = [("player_rs", "totals", ["totals_stats"]), ("player_rs", "advanced", ["advanced"]), ("player_rs", "per_poss", ["per_poss"]),
         ("player_rs", "play-by-play", ["pbp_stats"]), ("player_po", "totals", ["totals_stats"]), ("player_po", "advanced", ["advanced_stats"])]
def run():
    summary = []
    for sub, kind, ids in SPECS:
        frames = []
        for y, f in season_files(sub, kind).items():
            df = parse_table(open(f, encoding="utf-8").read(), ids)
            if df.empty: summary.append((sub, kind, y, 0)); continue
            df.insert(0, "season", y); frames.append(df)
        if not frames: continue
        d = pd.concat(frames, ignore_index=True)
        p = os.path.join(ROOT, "data", "clean", f"{sub}_{kind.replace('-','_')}.parquet")
        d.astype(str).to_parquet(p, index=False)
        log_manifest(p, "parsed from cached bbref html (data/raw/%s)" % sub, len(d), f"seasons {d.season.min()}-{d.season.max()}")
        summary.append((sub, kind, f"{d.season.min()}-{d.season.max()}", len(d)))
    return summary
if __name__ == "__main__":
    for s in run(): print(s)
