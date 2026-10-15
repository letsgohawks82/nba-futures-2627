"""Parameter-posterior draws for edge confidence intervals: M draws x N sims. Each draw perturbs: sigma_team, HCA, B2B effects, sigma_game, playoff lambda,
tank kappa, DARKO weight, rating scale; MC error is included naturally (independent seeds, reduced N). Output: data/clean/param_draws.npz"""
import json, os, sys, time
import numpy as np, pandas as pd
from ..sim.inputs import build, lottery_tables, PAR_NAMES, TEAM_LIST
from ..sim.runner import simulate, FLAGS
from ..ratings import project_2027 as pj
from ..sim.meanmatch import calibrate_ratings

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PI = {k: i for i, k in enumerate(PAR_NAMES)}

def rating_vectors():
    out = {}
    for w in (0.0, 1.0):
        o, *_ = pj.run(w_darko=w, save=False)
        out[w] = o.set_index("abbr").loc[TEAM_LIST].pred_srs.values
    return out

def run(M=60, N=15_000, seed=99):
    gm = json.load(open(os.path.join(ROOT, "data/clean/game_model_fit.json"))); pf = json.load(open(os.path.join(ROOT, "data/clean/playoff_adj_fit.json")))
    lt = lottery_tables(16, 150_000)
    base = build({"_lottery_tables": lt, "_calibrate": False}); p0 = base["par"].copy(); r05 = base["rating_raw"].copy()
    rv = rating_vectors(); slope = (rv[1.0] - rv[0.0])         # dRating/dw (linear)
    rng = np.random.default_rng(seed); draws = []; res = {k: [] for k in ("title", "conference", "division", "cup", "cup_group", "playoffs", "top6", "bracket")}; ranks = []; whist = []
    t0 = time.time()
    for d in range(M):
        par = p0.copy()
        par[PI["sigma_team"]] = float(np.clip(rng.normal(p0[PI["sigma_team"]], 0.30), 2.4, 4.3))
        par[PI["HCA"]] = rng.normal(gm["hca"], gm["hca_se"]); par[PI["b2b_home"]] = rng.normal(gm["b2b_home"], gm["b2b_home_se"]); par[PI["b2b_away"]] = rng.normal(gm["b2b_away"], gm["b2b_away_se"])
        par[PI["sigma_game"]] = rng.normal(gm["sigma_game"], 0.12); par[PI["sigma_po"]] = par[PI["sigma_game"]]
        par[PI["HCA_po"]] = rng.normal(gm["hca_post"], gm["hca_post_se"])
        par[PI["po_lambda"]] = max(rng.normal(pf["lambda_po"], 0.19), 0.0)
        par[PI["tank_kappa"]] = abs(rng.normal(p0[PI["tank_kappa"]], 0.5))
        w = rng.uniform(0.1, 0.9); scale = rng.normal(1.0, 0.06)
        inp = dict(base); inp["par"] = par; srs_d = (r05 + (w - 0.5) * slope) * scale; srs_d = srs_d - srs_d.mean(); inp["rating"] = srs_d
        target = 41.0 + par[PI["k_wins"]] * srs_d                                            # calibrated linear projection for this draw
        inp["rating"], _ = calibrate_ratings(inp, target, n=8_000, iters=4)                  # moment-match the sim to it
        r = simulate(inp, N, seed * 1000 + d, verbose=False)
        for k, bit in FLAGS.items():
            if k in res: res[k].append(((r["flags"] & bit) > 0).mean(0))
        ranks.append(np.stack([(r["conf_rank"] == k).mean(0) for k in range(1, 16)], 1))
        whist.append(np.stack([np.bincount(r["wins"][:, i], minlength=83) / N for i in range(30)]))
        draws.append(dict(draw=d, w_darko=w, rating_scale=scale, **{k: float(par[PI[k]]) for k in ("sigma_team", "HCA", "b2b_home", "b2b_away", "sigma_game", "HCA_po", "po_lambda", "tank_kappa")}))
        if d % 10 == 0: print("draw", d, round(time.time() - t0), "s", flush=True)
    np.savez_compressed(os.path.join(ROOT, "data/clean/param_draws.npz"), **{k: np.array(v) for k, v in res.items()}, confrank=np.array(ranks), wins_pmf=np.array(whist), teams=np.array(TEAM_LIST))
    pd.DataFrame(draws).to_csv(os.path.join(ROOT, "data/clean/param_draws_params.csv"), index=False)
    return draws

if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 60, int(sys.argv[2]) if len(sys.argv) > 2 else 15000)
