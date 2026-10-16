"""Item reports: (a) Jokic RPG/APG/mpg/games and P(lead) vs his rivals; (b) ROY candidates' projected PPG/mpg vs the last 5 ROY winners' lines (from the ROY model);
(c) the simulated ROY winner's line vs the last five winners. Writes data/clean/g4_jokic_rookie.json"""
import json
import numpy as np, pandas as pd
from . import leaders as L, run_g4 as G, simgp, rookies as RK
from .rates import C, table

def main():
    pool = pd.read_csv(C("g4_pool.csv")); pm = pd.read_csv(C("player_market_probs.csv")); R = pd.read_csv(C("g4_rate_backtest.csv")); cal = L.calib_from_backtest(R); out = {}
    for mk, sn in (("LDR_RPG", "RPG"), ("LDR_APG", "APG")):
        g = pm[pm.market == mk].sort_values("p", ascending=False).head(6)
        rows = []
        for r in g.itertuples():
            x = pool[pool.key == r.key].iloc[0]; mu = float(L.calibrated_pred(np.array([x["pg_" + sn]]), cal[sn])[0])
            rows.append(dict(player=r.player, proj_per_game_calibrated=mu, proj_mpg=float(x.proj_mpg), proj_games=float(x.proj_gp), p_qualify_58=None, p_lead_raw=float(r.p)))
        out[mk] = rows
    # Jokic per-sim games and qualification
    import os
    Z = np.load(os.path.join(os.path.dirname(__file__), "..", "..", "sims", "season_sims.npz")); P2 = G.prep_pool()
    gp, ti = simgp.sim_gp(P2, {"gp": Z["gp"][:30000], "teams": Z["teams"]}, rng=np.random.default_rng(1))
    j = int(np.where(P2.key.values == "nikola jokic")[0][0]); out["jokic"] = dict(mean_games=float(gp[:, j].mean()), p_ge58=float((gp[:, j] >= 58).mean()), p_ge65=float((gp[:, j] >= 65).mean()))
    # ROY candidates vs last 5 winners
    f, _ = RK.fit(); ps = table(); win = {2022: "barnes", 2023: "banchero", 2024: "wembanyama", 2025: "castle", 2026: "flagg"}
    W = []
    for s, nm in win.items():
        d = ps[(ps.season == s) & ps.name_display.str.lower().str.contains(nm)]
        if len(d): d = d.iloc[0]; W.append(dict(season=s, player=d.name_display, ppg=float(d.pts / d.games), mpg=float(d.mp / d.games), games=int(d.games), pick=None))
    out["roy_last5"] = W
    c = pool[pool.draft26].sort_values("pick").copy(); rows = []
    top = pm[pm.market == "ROY"].sort_values("p", ascending=False).head(6)
    for r in top.itertuples():
        x = pool[pool.key == r.key].iloc[0]; pr = RK.predict(f, float(x.pick), float(x.age)); mp = float(x.proj_mpg); mfit = pr["mpg"]
        rows.append(dict(player=r.player, pick=float(x.pick), age=float(x.age), proj_mpg_minutes_model=mp, mpg_from_slot_age_fit=mfit, pts36_fit=pr["pts36"], ppg_with_minutes_model=pr["pts36"] * mp / 36, ppg_with_slot_fit=pr["pts36"] * mfit / 36, p_roy=float(r.p)))
    out["roy_candidates"] = rows
    json.dump(out, open(C("g4_jokic_rookie.json"), "w"), indent=1, default=float); return out

if __name__ == "__main__":
    print(json.dumps(main(), indent=1, default=float))
