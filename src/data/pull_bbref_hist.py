"""Resumable bbref pulls: (f) player/team history 2014-2026, (h) drafts, (i) awards. <=15 req/min."""
import os, glob, sys, datetime as dt
from .bbref import get
from .common import RAW
YEARS = range(2014, 2027)
def have(subdir, name):
    return bool(glob.glob(os.path.join(RAW, subdir, name + ".html_*")))
def pull(url, subdir, name):
    if have(subdir, name):
        return
    try:
        get(url, subdir, name); print("ok", name, flush=True)
    except Exception as e:
        print("FAIL", name, e, flush=True)
def run(stage):
    B = "https://www.basketball-reference.com"
    if stage in ("f", "all"):
        for y in YEARS:
            for t in ("totals", "advanced", "per_poss", "play-by-play"):
                pull(f"{B}/leagues/NBA_{y}_{t}.html", "player_rs", f"{y}_{t}")
            pull(f"{B}/leagues/NBA_{y}.html", "team", f"{y}_team")
            for t in ("totals", "advanced"):
                if y <= 2026:
                    pull(f"{B}/playoffs/NBA_{y}_{t}.html", "player_po", f"{y}_{t}")
        for y in YEARS:
            if y == 2027: continue
            for m in ("october","november","december","january","february","march","april","may","june"):
                if y in (2020, 2021) or True:
                    pull(f"{B}/leagues/NBA_{y}_games-{m}.html", "games", f"{y}_{m}")
    if stage in ("h", "all"):
        for y in range(2013, 2027):
            pull(f"{B}/draft/NBA_{y}.html", "draft", f"nba_{y}")
    if stage in ("i", "all"):
        for y in range(2000, 2027):
            pull(f"{B}/awards/awards_{y}.html", "awards", f"{y}")
if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "all")
