"""Build the frozen input archive (deterministic .tar.gz: sorted members, mtime 0, no owner info) from the local data/raw, plus inputs/inputs_manifest.csv and inputs/INPUTS.sha256.
Tiers: required = files production stages read (discovered with scripts/discover_inputs.py in a clean clone); provenance = raw roster / injury / schedule / pick / lottery sources the tracked
data/clean tables derive from (verified, not read at reproduction time). Usage: python scripts/make_inputs_archive.py"""
import csv, glob, gzip, hashlib, io, json, os, sys, tarfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT_DIR = os.path.join(ROOT, "inputs"); ARCHIVE = os.path.join(OUT_DIR, "nba_futures_inputs_2026-10-15.tar.gz")
os.makedirs(OUT_DIR, exist_ok=True)
G = lambda pat: sorted(p.replace(os.sep, "/") for p in glob.glob(os.path.join(ROOT, pat)) if os.path.isfile(p))
rel = lambda p: os.path.relpath(p, ROOT).replace(os.sep, "/")
SRC = {"odds": ("user-supplied transcription of the book's 10/15 board (screenshots)", "no third-party license; user-owned transcription of a public odds board"),
       "darko": ("DARKO leaderboard (darko.app), ratings through 2026-06-03", "third-party; retained for private audit only; DARKO terms apply"),
       "barttorvik": ("barttorvik.com getadvstats.php csv", "third-party; retained for private audit only; Barttorvik terms apply"),
       "gamelogs": ("basketball-reference.com player game logs 2025-26", "third-party; retained for private audit only; Sports Reference terms apply"),
       "espn": ("ESPN site API (rosters, injuries, schedule)", "third-party; retained for private audit only; ESPN terms apply"),
       "schedule": ("basketball-reference.com schedule pages", "third-party; retained for private audit only; Sports Reference terms apply"),
       "picks": ("Hoops Rumors 2027 pick ownership", "third-party; retained for private audit only"),
       "lottery": ("NBA.com 3-2-1 lottery rules (WebFetch summaries)", "third-party summaries; retained for private audit only")}


def files():
    required = G("data/raw/odds/odds_2026-10-15.csv") + G("data/raw/darko/darko_dpm_leaderboard_20261015.csv") + G("data/raw/barttorvik/advstats_*.csv_20261015")
    reads = [l.strip() for l in open(os.path.join(ROOT, "inputs", "REQUIRED_GAMELOG_READS.txt"))] if os.path.exists(os.path.join(ROOT, "inputs", "REQUIRED_GAMELOG_READS.txt")) else []
    required += [os.path.join(ROOT, r).replace(os.sep, "/") for r in reads]
    prov = G("data/raw/darko/darko_official_20261015.csv") + G("data/raw/espn/*_20261015") + G("data/raw/schedule/*") + G("data/raw/picks/*") + G("data/raw/lottery/*")
    out = {}
    for p in required: out[rel(p)] = "required"
    for p in prov: out.setdefault(rel(p), "provenance")
    return out


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def main():
    fl = files(); rows = []
    with open(ARCHIVE, "wb") as raw:
        gz = gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9)
        with tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as tar:
            for name in sorted(fl):
                full = os.path.join(ROOT, name); ti = tar.gettarinfo(full, arcname=name); ti.mtime = 0; ti.uid = ti.gid = 0; ti.uname = ti.gname = ""; ti.mode = 0o644
                with open(full, "rb") as f: tar.addfile(ti, f)
                src = SRC.get(name.split("/")[2], ("", ""))
                rows.append(dict(path=name, sha256=sha(full), bytes=os.path.getsize(full), tier=fl[name], source=src[0], license_note=src[1]))
        gz.close()
    with open(os.path.join(OUT_DIR, "inputs_manifest.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["path", "sha256", "bytes", "tier", "source", "license_note"]); w.writeheader(); w.writerows(rows)
    a = sha(ARCHIVE); open(os.path.join(OUT_DIR, "INPUTS.sha256"), "w").write(f"{a}  {os.path.basename(ARCHIVE)}\n")
    n_req = sum(r["tier"] == "required" for r in rows)
    print(f"archive {ARCHIVE}\n  sha256 {a}\n  files {len(rows)} (required {n_req}, provenance {len(rows) - n_req}); size {os.path.getsize(ARCHIVE) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
