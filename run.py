"""NBA futures model CLI: run.py pull | ratings | sim | price | build | verify | all | parse-odds <file>"""
import subprocess, sys, os

PY = sys.executable
STAGES = ["pull", "ratings", "sim", "price", "build", "verify"]

def sh(*mod):
    return subprocess.call([PY, "-W", "ignore", "-m", *mod], cwd=os.path.dirname(os.path.abspath(__file__)))

def stage(s):
    if s == "ratings":
        return sh("src.ratings.backtest") or sh("src.ratings.project_2027")
    if s == "pull":
        print("[pull] G1 pulls are cached; re-run src.data.pull_espn / pull_schedule / pull_bbref_hist manually (see CLAUDE.md)")
        return 0
    print(f"[{s}] not implemented yet (built in a later gate)")
    return 0

def main(argv):
    if len(argv) < 2 or argv[1] not in STAGES + ["all", "parse-odds"]:
        print(__doc__); return 2
    for s in (STAGES if argv[1] == "all" else [argv[1]]):
        if argv[1] == "parse-odds":
            print("parse-odds: not implemented yet (G5)"); return 0
        rc = stage(s)
        if rc: return rc
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
