import re, pandas as pd, os
from .bbref import get, tables
from .common import ROOT
MONTHS = ["october","november","december","january","february","march","april"]
def run():
    frames = []
    for m in MONTHS:
        url = f"https://www.basketball-reference.com/leagues/NBA_2027_games-{m}.html"
        try:
            html, _ = get(url, "schedule", f"bbref_2027_games_{m}")
        except RuntimeError as e:
            print("skip", m, e); continue
        t = tables(html)[0]; t["month"] = m; frames.append(t)
        print(m, len(t))
    df = pd.concat(frames, ignore_index=True)
    df.to_csv(os.path.join(ROOT, "data", "clean", "schedule_raw_bbref.csv"), index=False)
    return df
if __name__ == "__main__":
    d = run(); print(d.shape); print(d.head(5).to_string()); print(d.columns.tolist())
