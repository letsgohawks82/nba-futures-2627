"""Verify (and optionally restore) the frozen input archive. Fails closed: exit 1 on ANY problem.
  python scripts/verify_inputs.py --restore     extract the archive into the repo (data/raw/...) then verify every file
  python scripts/verify_inputs.py               verify only (archive hash, extracted files)
Checks: (1) SHA-256 of the archive == inputs/INPUTS.sha256 == params/release.json inputs_archive_sha256;
        (2) every file in inputs/inputs_manifest.csv exists on disk with the listed SHA-256;
        (3) every such file that data/manifest.csv knows has the same SHA-256 there (the pull-time hash); files missing from data/manifest.csv are listed and are an error unless they
            are recorded in inputs/manifest_additions.csv (hashes of files that pre-date the manifest or were pulled without a manifest row).
The archive is never refreshed from the network: reproduction reads only what is in it."""
import csv, gzip, hashlib, io, json, os, sys, tarfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ARCHIVE = os.path.join(ROOT, "inputs", "nba_futures_inputs_2026-10-15.tar.gz")


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def main(restore):
    errs = []
    if not os.path.exists(ARCHIVE): print("ERROR: archive missing:", ARCHIVE); return 1
    a = sha(ARCHIVE); listed = open(os.path.join(ROOT, "inputs", "INPUTS.sha256")).read().split()[0]
    rel = json.load(open(os.path.join(ROOT, "params", "release.json"))).get("inputs_archive_sha256")
    if a != listed: errs.append(f"archive sha256 {a} != inputs/INPUTS.sha256 {listed}")
    if rel and a != rel: errs.append(f"archive sha256 {a} != params/release.json {rel}")
    if not rel: errs.append("params/release.json has no inputs_archive_sha256")
    man = {r["path"]: r for r in csv.DictReader(open(os.path.join(ROOT, "inputs", "inputs_manifest.csv"), encoding="utf-8"))}
    if restore:
        n = 0
        with tarfile.open(ARCHIVE, "r:gz") as tar:
            for m in tar.getmembers():
                if not m.isfile(): continue
                dest = os.path.normpath(os.path.join(ROOT, m.name))
                if not dest.startswith(ROOT + os.sep) or m.name not in man: errs.append(f"unexpected or unsafe archive member {m.name}"); continue
                data = tar.extractfile(m).read()
                if os.path.exists(dest) and hashlib.sha256(open(dest, "rb").read()).hexdigest() == hashlib.sha256(data).hexdigest(): continue
                os.makedirs(os.path.dirname(dest), exist_ok=True); open(dest, "wb").write(data); n += 1
        print(f"restored {n} files into data/raw (others already identical)")
    dm = {}
    for r in csv.DictReader(open(os.path.join(ROOT, "data", "manifest.csv"), encoding="utf-8")): dm[r["file"]] = r["sha256"]       # later rows win (re-pulls)
    add = {}
    ap = os.path.join(ROOT, "inputs", "manifest_additions.csv")
    if os.path.exists(ap): add = {r["path"]: r["sha256"] for r in csv.DictReader(open(ap, encoding="utf-8"))}
    n_ok = 0; not_in = []
    for p, r in man.items():
        full = os.path.join(ROOT, p)
        if not os.path.exists(full): errs.append(f"missing: {p}"); continue
        h = sha(full)
        if h != r["sha256"]: errs.append(f"sha256 differs from inputs_manifest.csv: {p}"); continue
        if p in dm:
            if dm[p] != h: errs.append(f"sha256 differs from data/manifest.csv: {p}")
            else: n_ok += 1
        elif p in add:
            if add[p] != h: errs.append(f"sha256 differs from inputs/manifest_additions.csv: {p}")
            else: n_ok += 1
        else: not_in.append(p)
    if not_in: errs.append(f"{len(not_in)} files are in neither data/manifest.csv nor inputs/manifest_additions.csv, e.g. {not_in[:3]}")
    print(f"archive sha256 {a}\nfiles in inputs_manifest.csv: {len(man)}; verified against a manifest: {n_ok}")
    for e in errs: print("ERROR:", e)
    print("INPUTS OK" if not errs else "INPUTS FAILED")
    return 0 if not errs else 1


if __name__ == "__main__":
    sys.exit(main("--restore" in sys.argv))
