import glob, os, pandas as pd
from bs4 import BeautifulSoup
from .common import ROOT, RAW, log_manifest
rows = []
for f in sorted(glob.glob(os.path.join(RAW, "games", "*.html_*"))):
    y, m = os.path.basename(f).split(".")[0].split("_", 1)
    soup = BeautifulSoup(open(f, encoding="utf-8").read(), "lxml")
    t = soup.find("table", id="schedule")
    if t is None: continue
    for tr in t.find("tbody").find_all("tr"):
        if "thead" in (tr.get("class") or []): continue
        d = {c.get("data-stat"): c.get_text(strip=True) for c in tr.find_all(["th","td"])}
        d["season"] = int(y); d["file_month"] = m; rows.append(d)
g = pd.DataFrame(rows)
g = g[g.visitor_pts.str.len() > 0].copy()
g["playoff"] = g["game_remarks"].fillna("").ne("") & False
p = os.path.join(ROOT, "data/clean/games_hist.parquet"); g.astype(str).to_parquet(p, index=False)
log_manifest(p, "parsed from cached bbref schedule pages (data/raw/games)", len(g), "played games incl. playoffs; 2014-2026")
print(g.groupby("season").size().to_string()); print(g.columns.tolist())
