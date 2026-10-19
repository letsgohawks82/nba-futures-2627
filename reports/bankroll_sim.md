# Bankroll simulation - released Tier 1 card

Card: PLAYOFFS Minnesota Timberwolves NO (0.63%), WINS Portland Trail Blazers OVER (0.50%), WINS Utah Jazz UNDER (0.75%), WINS Washington Wizards UNDER (0.75%); total 2.63% of bankroll. Outcomes from the 100,000 production season sims that priced the card; each scenario re-weights the sims (exponential tilt, joint structure kept) so the four marginals equal the scenario's TRUE probabilities. Seasons are independent draws, compounded 10 times (20,000 paths). Futures settle once per season, so 'drawdown' is measured at season ends; a path ruin means equity < 10% of start.

Scenarios: **model right** = model_prob; **shrunk** = 0.25 model + 0.75 book-fair (the probability the stakes are sized on); **half** = half of the shrunk edge; **no edge** = the book's fair price is right (vig still paid).

| Stake x | True probabilities | Season E[return] | P(profit) | 5th pct | Median | Worst | P(lose all 4) | 10-season median CAGR | 5th pct CAGR | P(DD>20%) | P(DD>40%) | P(ruin) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1x (2.63%) | model right | 1.44% | 75.38% | -1.35% | 1.34% | -2.63% | 2.01% | 1.41% | 0.32% | 0.00% | 0.00% | 0.00% |
| 1x (2.63%) | shrunk (sizing prob) | 0.21% | 51.68% | -2.63% | 0.06% | -2.63% | 8.39% | 0.16% | -0.74% | 0.00% | 0.00% | 0.00% |
| 1x (2.63%) | half of shrunk edge | 0.01% | 47.25% | -2.63% | -0.27% | -2.63% | 10.13% | -0.04% | -0.91% | 0.00% | 0.00% | 0.00% |
| 1x (2.63%) | no edge (book fair) | -0.20% | 42.72% | -2.63% | -0.27% | -2.63% | 12.11% | -0.24% | -1.08% | 0.00% | 0.00% | 0.00% |
| 2x (5.26%) | model right | 2.88% | 75.38% | -2.69% | 2.68% | -5.26% | 2.01% | 2.74% | 0.60% | 0.00% | 0.00% | 0.00% |
| 2x (5.26%) | shrunk (sizing prob) | 0.42% | 51.68% | -5.26% | 0.11% | -5.26% | 8.39% | 0.31% | -1.52% | 1.51% | 0.00% | 0.00% |
| 2x (5.26%) | half of shrunk edge | 0.01% | 47.25% | -5.26% | -0.54% | -5.26% | 10.13% | -0.11% | -1.85% | 3.26% | 0.00% | 0.00% |
| 2x (5.26%) | no edge (book fair) | -0.40% | 42.72% | -5.26% | -0.54% | -5.26% | 12.11% | -0.50% | -2.14% | 6.68% | 0.00% | 0.00% |
| 4x (10.52%) | model right | 5.75% | 75.38% | -5.38% | 5.37% | -10.52% | 2.01% | 5.37% | 1.18% | 1.26% | 0.00% | 0.00% |
| 4x (10.52%) | shrunk (sizing prob) | 0.85% | 51.68% | -10.52% | 0.23% | -10.52% | 8.39% | 0.47% | -3.12% | 29.82% | 0.74% | 0.00% |
| 4x (10.52%) | half of shrunk edge | 0.03% | 47.25% | -10.52% | -1.08% | -10.52% | 10.13% | -0.33% | -3.79% | 40.48% | 1.64% | 0.00% |
| 4x (10.52%) | no edge (book fair) | -0.79% | 42.72% | -10.52% | -1.08% | -10.52% | 12.11% | -1.13% | -4.40% | 52.60% | 3.27% | 0.00% |

Reading it: the card risks at most its total stake in a season (all four lose). Under 'no edge' the expected loss is the vig on the four prices; the gap between that row and the 'shrunk' row is what the sizing assumes the model is worth. A live CLV / calibration record (live/) is what decides which row is real.
