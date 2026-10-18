"""Restore-and-verify the Basketball-Reference HISTORY archive (a GitHub release asset). Nothing is downloaded by this script; fetch the asset once with
    gh release download v1.0-preseason.1 -p "nba_futures_bbref_history_*.tar.gz" -D dist
and check it with:
    python scripts/verify_history_archive.py [--archive dist/nba_futures_bbref_history_2026-10-15.tar.gz] [--restore] [--rederive]
Checks (exit 1 on ANY problem): archive SHA-256 == inputs/BBREF_HISTORY.sha256; the archive members are exactly the files in inputs/bbref_history_manifest.csv (no extras, no
path traversal); every file's byte size and SHA-256 equal the manifest; every manifest SHA-256 equals the pull-time hash in data/manifest.csv. --restore extracts into data/raw
(identical files are left alone); --rederive then re-parses the raw pages and compares every committed table (src/data/rederive_history.py)."""
import argparse, csv, hashlib, os, subprocess, sys, tarfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--archive", default=os.path.join(ROOT, "dist", "nba_futures_bbref_history_2026-10-15.tar.gz")); ap.add_argument("--restore", action="store_true"); ap.add_argument("--rederive", action="store_true"); a = ap.parse_args()
    errs = []
    if not os.path.exists(a.archive): print("ERROR: archive not found:", a.archive); return 1
    got = sha(a.archive); want = open(os.path.join(ROOT, "inputs", "BBREF_HISTORY.sha256")).read().split()[0]
    if got != want: errs.append(f"archive sha256 {got} != inputs/BBREF_HISTORY.sha256 {want}")
    man = {r["path"]: r for r in csv.DictReader(open(os.path.join(ROOT, "inputs", "bbref_history_manifest.csv"), encoding="utf-8"))}
    dm = {r["file"]: r["sha256"] for r in csv.DictReader(open(os.path.join(ROOT, "data", "manifest.csv"), encoding="utf-8"))}
    members = set(); n_new = 0
    with tarfile.open(a.archive, "r:gz") as tar:
        for m in tar.getmembers():
            if not m.isfile(): continue
            dest = os.path.normpath(os.path.join(ROOT, m.name)); members.add(m.name)
            if not dest.startswith(ROOT + os.sep) or m.name not in man: errs.append(f"unexpected or unsafe member {m.name}"); continue
            data = tar.extractfile(m).read(); h = hashlib.sha256(data).hexdigest(); r = man[m.name]
            if len(data) != int(r["bytes"]): errs.append(f"size differs from manifest: {m.name}")
            if h != r["sha256"]: errs.append(f"sha256 differs from manifest: {m.name}")
            if dm.get(m.name) != r["sha256"]: errs.append(f"manifest sha256 differs from data/manifest.csv: {m.name}")
            if a.restore and not errs[-1:] and not (os.path.exists(dest) and sha(dest) == h):
                os.makedirs(os.path.dirname(dest), exist_ok=True); open(dest, "wb").write(data); n_new += 1
    for miss in sorted(set(man) - members): errs.append(f"in manifest but not in the archive: {miss}")
    print(f"archive sha256 {got}\nfiles in manifest: {len(man)}; in archive: {len(members)}" + (f"; restored {n_new}" if a.restore else ""))
    for e in errs[:20]: print("ERROR:", e)
    if errs: print("HISTORY ARCHIVE FAILED"); return 1
    print("HISTORY ARCHIVE OK")
    if a.rederive:
        return subprocess.call([sys.executable, "-W", "ignore", "-m", "src.data.rederive_history"], cwd=ROOT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
