"""Frozen-input tests: every raw input the production code reads must be in the archive, restored, and hash-identical to data/manifest.csv."""
import csv, fnmatch, glob, os, re, subprocess, sys
import pytest
from conftest import ROOT

MAN = os.path.join(ROOT, "inputs", "inputs_manifest.csv")


def manifest():
    return list(csv.DictReader(open(MAN, encoding="utf-8")))


def test_required_inputs_present():
    rows = [r for r in manifest() if r["tier"] == "required"]
    assert len(rows) >= 150, f"expected >= 150 required inputs, found {len(rows)}"
    missing = [r["path"] for r in rows if not os.path.exists(os.path.join(ROOT, r["path"]))]
    assert not missing, f"required raw inputs missing (run scripts/verify_inputs.py --restore): {missing[:5]} ({len(missing)} total)"


def test_archive_and_every_hash_verify():
    rc = subprocess.call([sys.executable, os.path.join(ROOT, "scripts", "verify_inputs.py")], cwd=ROOT)
    assert rc == 0, "scripts/verify_inputs.py failed: archive hash, inputs_manifest.csv or data/manifest.csv disagree with the files on disk"


def test_production_code_only_reads_archived_raw_paths():
    """Every data/raw/... literal in production code (not the pull_/clean_ scripts) must be covered by an entry of inputs_manifest.csv (exact path or glob)."""
    paths = [r["path"] for r in manifest()]
    skip = ("pull_", "clean_", "recv_chunks", "prelock.py", "common.py")
    lit = re.compile(r"data/raw/[A-Za-z0-9_./*\-]+")
    for dp, dn, fn in os.walk(os.path.join(ROOT, "src")):
        for f in fn:
            if not f.endswith(".py") or any(s in f for s in skip): continue
            txt = open(os.path.join(dp, f), encoding="utf-8").read()
            for m in lit.findall(txt):
                m = m.rstrip(".")
                if "*" in m: ok = any(fnmatch.fnmatch(p, m + "*") for p in paths)
                elif m.endswith("/") or "." not in os.path.basename(m): ok = any(p.startswith(m) for p in paths)
                else: ok = m in paths
                assert ok, f"{os.path.join(dp, f)} reads {m} which is not in inputs/inputs_manifest.csv"
    # glob-built paths (tank carryover reads gamelogs by bbref id)
    assert any(p.startswith("data/raw/gamelogs/") for p in paths)


def test_no_network_in_reproduction_stages():
    """The stages run by `run.py repro` must not import requests / urllib / polite_get."""
    for mod in ("src/ratings/project_2027.py", "src/sim/run_sim.py", "src/pricing/run_pricing.py", "src/pricing/tier1.py", "src/pricing/price_players.py", "src/pricing/joint.py", "src/players/run_g4.py", "src/release/repro.py"):
        txt = open(os.path.join(ROOT, mod), encoding="utf-8").read()
        assert not re.search(r"^\s*(import requests|from urllib|import urllib|from \.\.data\.common import .*polite_get|import socket)", txt, re.M), f"{mod} touches the network"
