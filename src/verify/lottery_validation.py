"""Validate the lottery simulator (16 draws) against exact probabilities and NBA.com's published #1 odds (5.4% / 8.1% / 2.7% = 2/37, 3/37, 1/37)."""
import itertools, json, os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.sim.lottery import odds, BALLS
n = 16; b = BALLS.astype(float); T = b.sum()
P = odds(16, 1_000_000, 3)
ex1 = b / T
# exact P(team i gets pick 2) = sum_j!=i (b_j/T) * b_i/(T-b_j); floor not binding for early picks
ex2 = np.array([sum(b[j] / T * b[i] / (T - b[j]) for j in range(n) if j != i) for i in range(n)])
rep = dict(max_abs_err_pick1=float(np.abs(P[:, 0] - ex1).max()), max_abs_err_pick2=float(np.abs(P[:, 1] - ex2).max()),
           published_pick1_pct=dict(two_balls=round(2 / 37 * 100, 1), three_balls=round(3 / 37 * 100, 1), one_ball=round(1 / 37 * 100, 1)),
           sim_pick1_pct=dict(two_balls=round(P[0, 0] * 100, 2), three_balls=round(P[5, 0] * 100, 2), one_ball=round(P[15, 0] * 100, 2)),
           floor_violations_bottom3_below_12=float(P[:3, 12:].sum()),
           sum_prob_each_pick=float(P.sum(0).min()), n_balls=int(T))
# restriction checks: team 6 (index 5) barred from #1 -> P(#1)=0 ; barred top5 -> P(pick<=5)=0
nf = np.zeros(16, bool); nf[5] = True; nt = np.zeros(16, bool); nt[9] = True
Pr = odds(16, 300_000, 4, no_first=nf, no_top5=nt)
rep["restricted_no_first_P1"] = float(Pr[5, 0]); rep["restricted_no_top5_P_top5"] = float(Pr[9, :5].sum())
json.dump(rep, open(os.path.join(os.path.dirname(__file__), "..", "..", "data", "clean", "lottery_validation.json"), "w"), indent=1)
print(json.dumps(rep, indent=1))
