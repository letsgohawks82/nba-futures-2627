"""Compare the COMMITTED files of two refs (git blob ids, so line-ending conversion cannot create false differences).
Usage: python scripts/compare_to_baseline.py [BASE_REF [NEW_REF]]   (defaults: the baseline tag in params/release.json, HEAD)"""
import json, os, subprocess, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
base = sys.argv[1] if len(sys.argv) > 1 else json.load(open(os.path.join(ROOT, "params", "release.json")))["baseline_tag"]; new = sys.argv[2] if len(sys.argv) > 2 else "HEAD"
def tree(ref):
    out = subprocess.run(["git", "ls-tree", "-r", ref], cwd=ROOT, capture_output=True, text=True).stdout
    return {l.split("\t")[1]: l.split()[2] for l in out.splitlines()}
a, b = tree(base), tree(new)
scope = ("data/clean/", "output/", "release/", "reports/", "params/")
both = [f for f in a if f in b and f.startswith(scope)]
changed = sorted(f for f in both if a[f] != b[f]); removed = sorted(f for f in a if f not in b); added = sorted(f for f in b if f not in a)
print(json.dumps(dict(base=base, new=new, compared=len(both), identical=len(both) - len(changed), changed=changed, removed=removed, added=added), indent=1))
