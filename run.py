"""NBA futures model CLI: run.py pull | ratings | sim | price | build | verify | all | parse-odds <file>"""
import sys

STAGES = ["pull", "ratings", "sim", "price", "build", "verify"]

def main(argv):
    if len(argv) < 2 or argv[1] not in STAGES + ["all", "parse-odds"]:
        print(__doc__); return 2
    cmd = argv[1]
    todo = STAGES if cmd == "all" else [cmd]
    for s in todo:
        print(f"[{s}] not implemented yet (built in a later gate)")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
