"""NBA futures model CLI: run.py pull | ratings | sim | price | build | verify | all | parse-odds <file>"""
import subprocess, sys, os

PY = sys.executable
STAGES = ["pull", "ratings", "sim", "price", "build", "verify"]
ROOT = os.path.dirname(os.path.abspath(__file__))


def sh(*mod):
    return subprocess.call([PY, "-W", "ignore", "-m", *mod], cwd=ROOT)


def stage(s):
    if s == "ratings":
        return sh("src.ratings.backtest") or sh("src.ratings.project_2027")
    if s == "sim":
        return sh("src.sim.run_sim") or sh("src.sim.robust") or sh("src.pricing.param_draws")
    if s == "price":
        return sh("src.pricing.run_pricing")
    if s == "build":
        return sh("src.workbook.build")
    if s == "verify":
        return subprocess.call([PY, "-W", "ignore", os.path.join("src", "verify", "title_check.py")], cwd=ROOT) or subprocess.call([PY, "-W", "ignore", os.path.join("tests", "test_engine.py")], cwd=ROOT) or sh("src.workbook.audit")
    if s == "pull":
        print("[pull] G1 pulls are cached in data/raw; re-run src.data.pull_espn / pull_schedule / pull_bbref_hist / pull_gamelogs as needed (nba_api is blocked from this network)")
        return 0
    return 0


def main(argv):
    if len(argv) < 2 or argv[1] not in STAGES + ["all", "parse-odds"]:
        print(__doc__); return 2
    if argv[1] == "parse-odds":
        if len(argv) < 3:
            print("usage: run.py parse-odds <file.pdf|file.txt> [out.csv]"); return 2
        return subprocess.call([PY, "-W", "ignore", "-m", "src.pricing.parse_odds", *argv[2:]], cwd=ROOT)
    for s in (STAGES if argv[1] == "all" else [argv[1]]):
        rc = stage(s)
        if rc:
            return rc
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
