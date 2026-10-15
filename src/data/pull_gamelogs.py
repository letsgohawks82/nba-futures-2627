import os, glob, pandas as pd
from .bbref import get
from .common import RAW, ROOT
def run():
    ids = pd.read_csv(os.path.join(ROOT, "data/clean/bottom8_players_2026.csv")).bbref_id.unique()
    for i in ids:
        name = f"{i}_2026"
        if glob.glob(os.path.join(RAW, "gamelogs", name + ".html_*")): continue
        try:
            get(f"https://www.basketball-reference.com/players/{i[0]}/{i}/gamelog/2026", "gamelogs", name); print("ok", i, flush=True)
        except Exception as e:
            print("FAIL", i, e, flush=True)
if __name__ == "__main__": run()
