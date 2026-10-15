"""3-2-1 lottery simulator (numba). Slots 0..15 = lottery positions by reverse record (0 = worst record ... 9 = 10th worst,
10-13 = the four #9/#10 play-in seeds ordered worst record first, 14-15 = the two 7-vs-8 play-in losers).
Ball counts: [2,2,2, 3x7, 2x4, 1x2] = 37. Assumption inputs (see params/assumptions.json):
  n_draws (default 4, NBA text suggests 16 -> sensitivity), redraw_blocked (always), floor_pick=12 for the 3 worst.
Restrictions per team: no_top5[i], no_first[i] (booleans over the 16 lottery positions' teams)."""
import numpy as np
from numba import njit

BALLS = np.array([2, 2, 2] + [3] * 7 + [2] * 4 + [1] * 2, dtype=np.int64)

@njit(cache=True)
def _one(balls, no_first, no_top5, n_draws, floor_pick, u, out):
    n = 16
    taken = np.zeros(n, np.bool_)
    for s in range(n):
        slot = s + 1
        cand = np.zeros(n, np.bool_)
        for t in range(n):
            if taken[t]:
                continue
            if no_first[t] and slot == 1:
                continue
            if no_top5[t] and slot <= 5:
                continue
            cand[t] = True
        # floor: the 3 worst records may not fall below floor_pick
        und = 0
        for t in range(3):
            if not taken[t] and cand[t]:
                und += 1
        if slot <= floor_pick and und > 0 and und == floor_pick - slot + 1:
            for t in range(3, n):
                cand[t] = False
        if s < n_draws:
            tot = 0
            for t in range(n):
                if cand[t]:
                    tot += balls[t]
            r = u[s] * tot
            acc = 0.0
            pick = -1
            for t in range(n):
                if cand[t]:
                    acc += balls[t]
                    if r < acc:
                        pick = t
                        break
            if pick < 0:
                for t in range(n):
                    if cand[t]:
                        pick = t
        else:  # reverse-record order among remaining eligible
            pick = -1
            for t in range(n):
                if cand[t]:
                    pick = t
                    break
        if pick < 0:  # should not happen; fall back to any untaken team
            for t in range(n):
                if not taken[t]:
                    pick = t
                    break
        taken[pick] = True
        out[pick] = slot

@njit(cache=True)
def simulate(n_sims, balls, no_first, no_top5, n_draws, floor_pick, seed):
    np.random.seed(seed)
    res = np.zeros((n_sims, 16), np.int8)
    out = np.zeros(16, np.int64)
    u = np.zeros(16)
    for k in range(n_sims):
        for j in range(16):
            u[j] = np.random.random()
        _one(balls, no_first, no_top5, n_draws, floor_pick, u, out)
        for t in range(16):
            res[k, t] = out[t]
    return res

def odds(n_draws=4, n_sims=400_000, seed=1, no_first=None, no_top5=None, floor_pick=12):
    nf = np.zeros(16, np.bool_) if no_first is None else np.asarray(no_first, np.bool_)
    nt = np.zeros(16, np.bool_) if no_top5 is None else np.asarray(no_top5, np.bool_)
    r = simulate(n_sims, BALLS, nf, nt, n_draws, floor_pick, seed)
    P = np.zeros((16, 16))
    for t in range(16):
        P[t] = np.bincount(r[:, t] - 1, minlength=16) / n_sims
    return P  # P[position, pick-1]
