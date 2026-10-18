"""Discover every input file a pipeline stage reads, using Python audit hooks (open + glob events), and append them to a log.
Usage:  python scripts/discover_inputs.py LOG.txt <module> [args...]   (runs `python -m <module> args` in this process with the hook installed)
Only reads are logged. Paths are stored relative to the repo root with forward slashes."""
import os, runpy, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOG = sys.argv[1]; MOD = sys.argv[2]; sys.argv = [MOD] + sys.argv[3:]
seen = set()


def rel(p):
    try:
        p = os.path.abspath(p)
    except Exception:
        return None
    if not p.startswith(ROOT): return None
    return os.path.relpath(p, ROOT).replace(os.sep, "/")


def hook(event, args):
    if event == "open":
        path, mode = args[0], args[1]
        if isinstance(path, (str, bytes, os.PathLike)) and (mode is None or "w" not in str(mode) and "a" not in str(mode) and "x" not in str(mode) and "+" not in str(mode)):
            r = rel(os.fsdecode(path)) if not isinstance(path, int) else None
            if r and r not in seen and os.path.isfile(os.path.join(ROOT, r)): seen.add(r); open(LOG, "a").write(r + "\n")
    elif event == "glob.glob":
        pat = os.fsdecode(args[0]); r = rel(pat)
        if r and ("glob:" + r) not in seen: seen.add("glob:" + r); open(LOG, "a").write("GLOB " + r + "\n")


sys.addaudithook(hook)
sys.path.insert(0, ROOT)
runpy.run_module(MOD, run_name="__main__", alter_sys=True)
