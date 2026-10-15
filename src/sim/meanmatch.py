"""Moment-match the simulator's expected wins to the calibrated projection (41 + k x SRS, zero-sum). The raw sim compresses the extremes (Phi saturation, sigma_team
concavity, availability); the projection's linear map was calibrated on realized wins, so the sim ratings are adjusted until E_sim[wins_i] = target_i."""
import numpy as np
from .runner import simulate

def calibrate_ratings(inp, target, n=15_000, iters=6, seed=777, damp=0.9, k=None, tol=0.08):
    """inp: engine input dict (will be copied). target: array[30] of expected wins (sums to 1230 if complete season). Returns calibrated rating vector (SRS pts)."""
    k = k or float(inp["par"][26])
    inp = dict(inp); r = np.array(inp["rating"], float).copy(); hist = []
    for it in range(iters):
        inp["rating"] = r
        res = simulate(inp, n, seed, verbose=False)            # common random numbers across iterations -> smooth
        m = res["wins"].mean(0); err = target - m; hist.append(float(np.abs(err).max()))
        if np.abs(err).max() < tol: break
        r = r + damp * err / k
        r = r - r.mean()
    inp["rating"] = r
    return r, hist
