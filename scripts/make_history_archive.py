"""Build the Basketball-Reference HISTORY archive (release asset, not committed): every raw bbref page consumed by the cleaning / audit code, as a deterministic .tar.gz, plus
inputs/bbref_history_manifest.csv (path, bytes, sha256, source_url, retrieval_timestamp, consumer, derived outputs, parser + parser version) and inputs/BBREF_HISTORY.sha256.
Usage: python scripts/make_history_archive.py   (writes dist/nba_futures_bbref_history_2026-10-15.tar.gz)"""
import csv, glob, gzip, hashlib, os, subprocess, sys, tarfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DIST = os.path.join(ROOT, "dist"); ARCHIVE = os.path.join(DIST, "nba_futures_bbref_history_2026-10-15.tar.gz"); os.makedirs(DIST, exist_ok=True)
LIBS = "beautifulsoup4==4.15.0; lxml==6.1.3; pandas==3.0.6 (requirements.lock.txt)"


def blob(path):
    return subprocess.run(["git", "hash-object", path], cwd=ROOT, capture_output=True, text=True).stdout.strip()


# directory -> (consumer, derived outputs, parser path or None, parser note)
SPEC = {
    "player_rs": ("src/data/clean_players.py (SPECS: totals, advanced, per_poss, play-by-play)", "data/clean/player_rs_{totals,advanced,per_poss,play_by_play}.parquet", "src/data/clean_players.py", ""),
    "player_po": ("src/data/clean_players.py (SPECS: playoff totals, advanced)", "data/clean/player_po_{totals,advanced}.parquet", "src/data/clean_players.py", ""),
    "games": ("src/data/clean_games.py", "data/clean/games_hist.parquet", "src/data/clean_games.py", ""),
    "team": ("NO committed parser (parsed ad hoc in the G1 session); re-derived by src/data/rederive_history.py", "data/clean/team_season_hist.parquet", "src/data/rederive_history.py", "table advanced-team"),
    "awards": ("NO committed parser (G1 session); re-derived by src/data/rederive_history.py", "data/clean/award_voting.parquet", "src/data/rederive_history.py", "tables mvp, roy, dpoy"),
    "draft": ("NO committed parser (G1 session); re-derived by src/data/rederive_history.py", "data/clean/draft_picks.parquet", "src/data/rederive_history.py", "table stats"),
    "roster_check": ("NO committed parser (G5 revision); re-derived by src/data/rederive_history.py", "data/clean/rosters_bbref_2027_20261015.csv, roster_audit_diff.csv", "src/data/rederive_history.py", "table roster; two-way (TW) tags stripped"),
    "schedule": ("src/data/pull_schedule.py (pull-time parse) then src/data/clean_schedule.py", "data/clean/schedule_raw_bbref.csv, schedule_games.csv, schedule_team_games.csv", "src/data/pull_schedule.py", "bbref.tables(html)[0]"),
    "gamelogs": ("src/ratings/tank_carryover.py (read directly)", "data/clean/tank_carryover_*.csv, pre_deadline_role_override_2026.csv", "src/ratings/tank_carryover.py", ""),
    "coaches": ("not read by production code (reference page for the COY market)", "none", None, ""),
}
INPUTS_ARCHIVE = set()
p1 = os.path.join(ROOT, "inputs", "inputs_manifest.csv")
if os.path.exists(p1): INPUTS_ARCHIVE = {r["path"] for r in csv.DictReader(open(p1, encoding="utf-8"))}


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def main():
    dm = {}
    for r in csv.DictReader(open(os.path.join(ROOT, "data", "manifest.csv"), encoding="utf-8")): dm[r["file"]] = r          # later rows win (re-pulls)
    pv = {}
    for d, (_, _, pp, note) in SPEC.items():
        if pp and pp not in pv: pv[pp] = blob(os.path.join(ROOT, pp))
    rows = []
    for d in SPEC:
        for f in sorted(os.listdir(os.path.join(ROOT, "data", "raw", d))):
            rel = f"data/raw/{d}/{f}"; full = os.path.join(ROOT, rel)
            if not os.path.isfile(full): continue
            m = dm.get(rel)
            if not m: sys.exit(f"ERROR: {rel} is not in data/manifest.csv (no source URL / timestamp)")
            h = sha(full)
            if h != m["sha256"]: sys.exit(f"ERROR: {rel} sha256 differs from data/manifest.csv")
            cons, outs, pp, note = SPEC[d]
            rows.append(dict(path=rel, bytes=os.path.getsize(full), sha256=h, source_url=m["source_url"], retrieval_timestamp=m["pull_timestamp"], consumer=cons, derived_outputs=outs,
                             parser=(pp or "none"), parser_version=(f"git blob {pv[pp]}; {LIBS}" + (f"; {note}" if note else "") if pp else "n/a"), in_inputs_archive=("Y" if rel in INPUTS_ARCHIVE else "N")))
    with open(ARCHIVE, "wb") as raw:
        gz = gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9)
        with tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as tar:
            for r in rows:
                ti = tar.gettarinfo(os.path.join(ROOT, r["path"]), arcname=r["path"]); ti.mtime = 0; ti.uid = ti.gid = 0; ti.uname = ti.gname = ""; ti.mode = 0o644
                with open(os.path.join(ROOT, r["path"]), "rb") as f: tar.addfile(ti, f)
        gz.close()
    with open(os.path.join(ROOT, "inputs", "bbref_history_manifest.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    a = sha(ARCHIVE); open(os.path.join(ROOT, "inputs", "BBREF_HISTORY.sha256"), "w").write(f"{a}  {os.path.basename(ARCHIVE)}\n")
    print(f"archive {ARCHIVE}\n  sha256 {a}\n  files {len(rows)}; raw bytes {sum(r['bytes'] for r in rows) / 1e6:.1f} MB; archive {os.path.getsize(ARCHIVE) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
