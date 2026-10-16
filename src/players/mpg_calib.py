"""Calibration of the minutes model's per-game-played minutes (mpg_hat) for high-minute players: actual mpg ~ a + b * mpg_hat on the top-40 by mpg_hat each season 2022-2026
(predictions use only prior seasons; players with >= 40 games). data/clean/g4_mpg_calib.json"""
import json
import numpy as np, pandas as pd
from ..ratings.model import Data, fit_player_model, predict_players
from .rates import C

def main():
    D = Data(); rows = []
    for s in range(2022, 2027):
        P = fit_player_model(D, s - 1); ids = D.ps[D.ps.season == s - 1].bbref_id.dropna().unique(); pl = predict_players(D, s, P, roster_ids=ids)
        act = D.ps[D.ps.season == s].drop_duplicates("bbref_id").set_index("bbref_id"); j = pl.join(act[["mp", "games"]], how="inner"); j["mpg"] = j.mp / j.games; j = j[j.games >= 40]
        rows.append(j.nlargest(40, "mpg_hat").assign(season=s)[["mpg_hat", "mpg", "season"]])
    R = pd.concat(rows); b, a = np.polyfit(R.mpg_hat, R.mpg, 1)
    # leave-one-season-out check of the calibrated vs raw error
    err_raw = []; err_cal = []
    for s in R.season.unique():
        tr = R[R.season != s]; te = R[R.season == s]; bb, aa = np.polyfit(tr.mpg_hat, tr.mpg, 1)
        err_raw.append(((te.mpg - te.mpg_hat) ** 2).mean()); err_cal.append(((te.mpg - (aa + bb * te.mpg_hat)) ** 2).mean())
    out = dict(a=float(a), b=float(b), n=int(len(R)), bias_raw=float((R.mpg - R.mpg_hat).mean()), rmse_raw_loso=float(np.sqrt(np.mean(err_raw))), rmse_cal_loso=float(np.sqrt(np.mean(err_cal))))
    json.dump(out, open(C("g4_mpg_calib.json"), "w"), indent=1); print(out); return out

if __name__ == "__main__":
    main()
