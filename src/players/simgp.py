"""Per-sim games for the whole G4 pool: slotted players come straight from the season sims (consistent with team wins); other odds-named players draw
Beta-binomial availability with the engine's concentration (3.7) and their projected games fraction."""
import numpy as np, pandas as pd

CONC = 3.7


def sim_gp(pool, Z, n=None, rng=None, idx=None):
    rng = rng or np.random.default_rng(11)
    tm = list(Z["teams"]); GP = Z["gp"] if not isinstance(Z, dict) else Z["gp"]; N = GP.shape[0]
    idx = np.arange(N) if idx is None else idx
    n = len(idx)
    gp = np.zeros((n, len(pool)), np.int16); team_i = np.zeros(len(pool), int)
    for j, (i, r) in enumerate(pool.iterrows()):
        team_i[j] = tm.index(r.abbr)
        if r.slotted:
            gp[:, j] = GP[idx, tm.index(r.abbr), int(r.slot)]
        else:
            f = float(np.clip(r.gfrac_hat, 0.02, 0.98)); p = rng.beta(f * CONC, (1 - f) * CONC, n); gp[:, j] = rng.binomial(82, p)
    return gp, team_i
