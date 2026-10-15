import numpy as np, pandas as pd, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.sim.lottery import odds, BALLS
rows = []
for K in (2, 4, 6, 16):
    P = odds(K, 400_000, 7)
    for t in range(16):
        rows.append(dict(n_draws=K, position=t + 1, balls=int(BALLS[t]), p_first=P[t, 0], p_top4=P[t, :4].sum(), p_top5=P[t, :5].sum(),
                         exp_pick=(P[t] * np.arange(1, 17)).sum(), p_worst_than_12=P[t, 12:].sum()))
d = pd.DataFrame(rows)
d.to_csv("data/clean/lottery_sensitivity_draws.csv", index=False)
exact_first = BALLS / 37
chk = d[d.n_draws == 16].set_index("position").p_first.values
print("max |P(#1) sim - balls/37| (K=16):", np.abs(chk - exact_first).max())
print("bottom-3 P(pick>12) at K=16 (floor):", d[(d.n_draws == 16) & (d.position <= 3)].p_worst_than_12.max())
for K in (2, 4, 6, 16):
    x = d[d.n_draws == K]
    print(f"K={K}: pos1 P1={x.p_first.iloc[0]:.3f} top4={x.p_top4.iloc[0]:.3f} exp={x.exp_pick.iloc[0]:.2f} | pos10 P1={x.p_first.iloc[9]:.3f} top4={x.p_top4.iloc[9]:.3f} exp={x.exp_pick.iloc[9]:.2f} | pos16 P1={x.p_first.iloc[15]:.3f} top4={x.p_top4.iloc[15]:.3f} exp={x.exp_pick.iloc[15]:.2f}")
