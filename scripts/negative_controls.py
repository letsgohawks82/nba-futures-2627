"""Negative controls: prove the release tests FAIL (fail closed) when they should. Works on a COPY of a repo directory that has completed `scripts/cleanroom.sh`.
Usage: python scripts/negative_controls.py REPO_DIR [PYTHON]  -> prints a markdown table and writes it to REPO_DIR/repro/negative_controls.md (in the original dir)."""
import csv, os, shutil, subprocess, sys, tempfile

SRC = os.path.abspath(sys.argv[1]); PY = sys.argv[2] if len(sys.argv) > 2 else sys.executable
TMP = os.path.join(tempfile.mkdtemp(prefix="nba_neg_"), "repo")
shutil.copytree(SRC, TMP, ignore=shutil.ignore_patterns(".venv_cleanroom", ".git", "__pycache__", "data/raw"), symlinks=False)
# data/raw is needed by the input tests: copy it separately (ignore pattern above matches only a directory named data/raw by basename 'raw'?)
if not os.path.exists(os.path.join(TMP, "data", "raw")) and os.path.exists(os.path.join(SRC, "data", "raw")): shutil.copytree(os.path.join(SRC, "data", "raw"), os.path.join(TMP, "data", "raw"))
subprocess.run(["git", "init", "-q"], cwd=TMP)
ENV = dict(os.environ, PYTHONIOENCODING="utf-8"); ENV.pop("NBA_OUTPUT_DIR", None)


def pytest(*args, outdir=None):
    env = dict(ENV)
    if outdir: env["NBA_OUTPUT_DIR"] = outdir
    r = subprocess.run([PY, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", *args], cwd=TMP, capture_output=True, text=True, env=env)
    return r.returncode, (r.stdout + r.stderr)


def read(p): return open(os.path.join(TMP, p), encoding="utf-8").read()
def write(p, s): open(os.path.join(TMP, p), "w", encoding="utf-8", newline="").write(s)


rows = []
def control(name, test, mutate, restore, outdir=None):
    base_rc, _ = pytest(test, outdir=outdir)
    mutate(); rc, out = pytest(test, outdir=outdir); restore()
    rc2, _ = pytest(test, outdir=outdir)
    rows.append((name, test.split("::")[-1], "passes" if base_rc == 0 else "FAILS", "FAILS" if rc != 0 else "PASSES (BAD)", "passes" if rc2 == 0 else "FAILS", out.strip().splitlines()[-1][:110] if rc else ""))


# 1 missing raw input
f = os.path.join(TMP, "data", "raw", "odds", "odds_2026-10-15.csv"); keep = open(f, "rb").read()
control("a required raw input (odds CSV) is deleted", "tests/test_inputs.py::test_required_inputs_present", lambda: os.remove(f), lambda: open(f, "wb").write(keep))
# 2 source hash differs
g = os.path.join(TMP, "data", "raw", "barttorvik", "advstats_2020.csv_20261015"); keep2 = open(g, "rb").read()
control("one byte of a Barttorvik file is changed", "tests/test_inputs.py::test_archive_and_every_hash_verify", lambda: open(g, "wb").write(keep2 + b" "), lambda: open(g, "wb").write(keep2))
# 3 card csv disagrees with the committed tables
card = read("release/final_card.csv")
control("a stake in release/final_card.csv is edited", "tests/test_release_static.py::test_final_card_csv_matches_committed_pricing_tables", lambda: write("release/final_card.csv", card.replace("0.0075", "0.0080", 1)), lambda: write("release/final_card.csv", card))
# 4 metadata disagree
rel = read("params/release.json")
control("params/release.json carries a different version than README/AUDIT/workbook", "tests/test_release_static.py::test_release_metadata_agrees_everywhere", lambda: write("params/release.json", rel.replace('"version": "v1.0-preseason.1"', '"version": "v1.0-preseason.2"')), lambda: write("params/release.json", rel))
# 5 vacuous assertion
t = read("tests/test_engine.py")
control("`or True` is put back in tests/test_engine.py", "tests/test_release_static.py::test_tests_do_not_contain_vacuous_assertions", lambda: write("tests/test_engine.py", t + "\n\ndef test_x():\n    assert 1 == 2 or True\n"), lambda: write("tests/test_engine.py", t))
# 6/7 workbook defects injected by editing the XML inside the .xlsx (cached values of the real workbook are kept)
import json, re, zipfile
META = json.load(open(os.path.join(TMP, "params", "release.json"))); wbp = os.path.join(TMP, "repro", "output", META["workbook_file"])
if not os.path.exists(wbp): wbp = os.path.join(TMP, "output", META["workbook_file"])       # the workbook rebuilt by the clean-room run (matches the rebuilt card)
outd = os.path.join(TMP, "neg_out"); os.makedirs(outd, exist_ok=True)
def sheet_member(zf, name):
    wbx = zf.read("xl/workbook.xml").decode(); rels = zf.read("xl/_rels/workbook.xml.rels").decode()
    rid = re.search(r'<sheet [^>]*name="%s"[^>]*r:id="([^"]+)"' % name, wbx).group(1)
    tgt = re.search(r'<Relationship [^>]*Id="%s"[^>]*Target="([^"]+)"' % rid, rels) or re.search(r'<Relationship [^>]*Target="([^"]+)"[^>]*Id="%s"' % rid, rels)
    t = tgt.group(1).lstrip("/"); return t if t.startswith("xl/") else "xl/" + t
def mutate_xlsx(dst, fn):
    with zipfile.ZipFile(wbp) as zin:
        members = {"Checks": sheet_member(zin, "Checks"), "Tier1_Card": sheet_member(zin, "Tier1_Card")}
        with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                zout.writestr(zipfile.ZipInfo(item.filename, item.date_time), fn(members, item.filename, zin.read(item.filename)), zipfile.ZIP_DEFLATED)
def flag_fn(members, name, data):
    if name == members["Checks"]:
        x = data.decode(); y = re.sub(r'(<c r="C23"[^>]*>(?:<f>[^<]*</f>)?<v>)OK(</v>)', r'FLAG', x, count=1)
        if y == x: y = re.sub(r'(<c r="C23"[^>]*>)<is><t>OK</t></is>', r'<is><t>FLAG</t></is>', x, count=1)
        assert y != x, "could not inject FLAG into Checks!C23"; return y.encode()
    return data
def title_fn(members, name, data):
    if name == "xl/sharedStrings.xml" or name == members["Tier1_Card"]:
        x = data.decode(); return x.replace("active Tier 1 bets", "bets (stale)").replace("(4 bets (stale))", "(8 bets)").encode()
    return data
shutil.copy(wbp, os.path.join(outd, META["workbook_file"]))
t6 = "tests/test_release_static.py::test_workbook_has_no_integrity_flags"; rc0, _ = pytest(t6, outdir=outd)
mutate_xlsx(os.path.join(outd, META["workbook_file"]), flag_fn); rc1, o1 = pytest(t6, outdir=outd)
shutil.copy(wbp, os.path.join(outd, META["workbook_file"])); rc2, _ = pytest(t6, outdir=outd)
rows.append(("a FLAG is injected into Checks!C23 of the workbook", t6.split("::")[-1], "passes" if rc0 == 0 else "FAILS", "FAILS" if rc1 else "PASSES (BAD)", "passes" if rc2 == 0 else "FAILS", o1.strip().splitlines()[-1][:110] if rc1 else ""))
t7 = "tests/test_release_static.py::test_workbook_tier1_rows_count_and_stakes_agree_with_card"; rc0, _ = pytest(t7, outdir=outd)
mutate_xlsx(os.path.join(outd, META["workbook_file"]), title_fn); rc1, o1 = pytest(t7, outdir=outd)
shutil.copy(wbp, os.path.join(outd, META["workbook_file"])); rc2, _ = pytest(t7, outdir=outd)
rows.append(("the Tier1_Card title says 8 bets while 4 are active", t7.split("::")[-1], "passes" if rc0 == 0 else "FAILS", "FAILS" if rc1 else "PASSES (BAD)", "passes" if rc2 == 0 else "FAILS", o1.strip().splitlines()[-1][:110] if rc1 else ""))
# 8 rebuilt card differs / run missing (only if a repro run exists)
if os.path.exists(os.path.join(TMP, "repro", "rebuilt_card.csv")):
    rc = read("repro/rebuilt_card.csv")
    control("a bet is added to the rebuilt card", "tests/test_repro_outputs.py::test_rebuilt_final_card_equals_committed_card", lambda: write("repro/rebuilt_card.csv", rc.rstrip("\n") + "\nWINS,Boston Celtics,OVER,50.5,100,0.5,0.6,0.2,0.05,100,0.005\n"), lambda: write("repro/rebuilt_card.csv", rc))
    st = read("repro/run_status.json")
    control("the repro run status is missing", "tests/test_repro_outputs.py::test_every_stage_ran_and_exited_zero", lambda: os.remove(os.path.join(TMP, "repro", "run_status.json")), lambda: write("repro/run_status.json", st))
    stj = __import__("json").loads(st); stj["stages"][1]["exit"] = 1
    control("a stage (ratings) exited non-zero", "tests/test_repro_outputs.py::test_every_stage_ran_and_exited_zero", lambda: write("repro/run_status.json", __import__("json").dumps(stj)), lambda: write("repro/run_status.json", st))
md = ["| Control | Test | Before | With the defect | After restore | Last line |", "|---|---|---|---|---|---|"] + [f"| {a} | `{b}` | {c} | **{d}** | {e} | {f} |" for a, b, c, d, e, f in rows]
text = "\n".join(md); print(text); open(os.path.join(SRC, "repro", "negative_controls.md"), "w", encoding="utf-8").write(text + "\n")
shutil.rmtree(os.path.dirname(TMP), ignore_errors=True)
