# Sizing waterfall (released card)

Policy: Kelly fraction **0.25**; probability used for sizing is **shrunk 75% toward the book's de-vigged fair price** (p_stake = 0.25 x model + 0.75 x fair); stakes are the joint solution over the whole portfolio on the same simulations (correlated bets share risk); then a hard per-bet cap (WINS 0.75%, or 0.50% when roster continuity < 0.55; PLAYOFFS uncapped; portfolio cap 10%). Stakes are a fraction of bankroll. `joint_uncapped` is already the 0.25-fraction.

| Bet | Book dec | Model p | Fair p | Sizing p | Full Kelly @ model p | Full Kelly @ sizing p | Joint 0.25 Kelly, uncapped | Cap | Final stake | Binding step |
|---|---|---|---|---|---|---|---|---|---|---|
| WINS Washington Wizards UNDER | 1.714 | 0.789 | 0.564 | 0.621 | 49.43% | 8.95% | 2.23% | 0.75% | **0.75%** | at cap |
| WINS Utah Jazz UNDER | 2.150 | 0.677 | 0.445 | 0.503 | 39.66% | 7.14% | 1.84% | 0.75% | **0.75%** | at cap |
| WINS Portland Trail Blazers OVER | 2.150 | 0.582 | 0.445 | 0.479 | 21.85% | 2.69% | 0.48% | 0.50% | **0.50%** | at cap |
| PLAYOFFS Minnesota Timberwolves NO | 6.500 | 0.326 | 0.125 | 0.175 | 20.35% | 2.49% | 0.65% | none | **0.63%** | joint Kelly re-solved after other stakes were capped |

Total staked: **2.63%** of bankroll. A stake can be reproduced from the table: shrink -> joint 0.25 Kelly (needs the sims, `src/pricing/joint.py`) -> min(cap, Kelly). Full Kelly at the raw model probability is shown only to make the haircut visible (20-50% of bankroll per bet, 8-70x the final stakes). The final column can differ from the uncapped joint Kelly in either direction: the joint problem is solved again with the capped stakes held fixed (src/pricing/joint.py), so an uncapped bet (MIN) is re-sized and a capped bet can sit at its cap even when its own uncapped Kelly is slightly below it (POR 0.48% -> 0.50%, the WINS low-continuity cap).

The recommended stake is **not** raised if the model's probability is raised; the only inputs that move a stake are the book price, the fair price and the model probability through the 25% weight.
