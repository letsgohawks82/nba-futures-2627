"""SHA-256 of the key inputs and outputs of a run (printed and written to repro/output_hashes.txt). Usage: python scripts/hash_outputs.py"""
import hashlib, json, os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from src.release.meta import META
OUT = os.environ.get("NBA_OUTPUT_DIR") or os.path.join(ROOT, "output")
FILES = ["requirements.lock.txt", "params/release.json", "inputs/nba_futures_inputs_2026-10-15.tar.gz", "data/clean/team_projection_2027.csv", "data/clean/player_projection_2027.csv", "data/clean/sim_team_summary.csv",
         "data/clean/pricing_table.csv", "data/clean/player_pricing_table.csv", "data/clean/joint_summary.json", "repro/rebuilt_card.csv", "release/final_card.csv"]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


lines = []
for f in FILES + [os.path.relpath(os.path.join(OUT, META["workbook_file"]), ROOT)]:
    p = os.path.join(ROOT, f)
    lines.append(f"{sha(p) if os.path.exists(p) else 'MISSING' + ' ' * 56}  {f}")
os.makedirs(os.path.join(ROOT, "repro"), exist_ok=True); open(os.path.join(ROOT, "repro", "output_hashes.txt"), "w").write("\n".join(lines) + "\n"); print("\n".join(lines))
