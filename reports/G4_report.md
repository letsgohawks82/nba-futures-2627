# G4 report: player markets (2026-10-15)

**Status: built, awaiting your approval.** Stat leaders (PPG/RPG/APG/SPG/BPG/3PM), MVP, DPOY and ROY are modelled on the same 100k season sims as the team card and priced on `M_Players`. **5 Tier 1 player bets, 2.3% of bankroll**, which comes to about 4.3% with the 2.0% team Tier 1. Tier 2 has 25 player bets (unstaked, almost all longshots).

## Correction you need to know about
**The "TPG" market is three-pointers made per game, not turnovers.** Curry is −125, and the field is LaMelo, Knueppel, Edwards and Miller. The G1 report and my first G4 pass read it as turnovers, which produced absurd output (Harden at 11% against a 0.3% price). It is now modelled as 3PM per game. The 58-game rule still applies, and there is no official qualifier for it.

## Models
- **Rates.** Per-minute rates from a 3-season decayed projection shrunk to a position prior (M0 150-300 minutes, picked by backtest), times the minutes-model mpg. The calibration (slope, intercept, log SD) comes from the top-30 predicted players per stat, 2019-26. PPG slope is 0.80 (regression to the mean among the top scorers). Log SDs: PPG 0.14, RPG 0.19, APG 0.23, SPG 0.22, BPG 0.29, 3PM 0.21.
- **Leaders.** Per-sim season averages, rounded to 0.1, with dead-heat 1/k credit. A player qualifies with at least 58 games or at least the NBA.com season total (1,400 pts / 800 reb / 400 ast / 125 stl / 100 blk). Games come from the season sims, so they are consistent with team wins.
- **Sharpening (new).** A backtest of the leader engine on 2019-26 (leave-one-season-out rates, actual games) shows mid-range probabilities are calibrated. Longshots are overstated about 2× (3.2% predicted vs 1.6% realised in the 2-5% bucket) and favourites are understated (50% predicted vs 78% realised above 35%; top pick hit rate 48% vs a mean top probability of 31%). I apply p^1.4 renormalised per market. The exponent was fitted on that same backtest (one parameter, in-sample), after which the buckets reconcile. Without it, the card was nearly all fake longshot edges. Awards are not sharpened.
- **MVP / DPOY / ROY.** A conditional logit on 2014-26 winners against each season's candidate pool (ridge 0.5). Leave-one-season-out, the winner was ranked first in:
  - MVP 10 of 13 (mean probability on the winner 0.58)
  - DPOY 9 of 13 (0.42)
  - ROY 8 of 12 (0.55)
  
  Features are:
  - MVP: BPM, PPG, team win%, games, prior-year share.
  - DPOY: DBPM, steals+blocks, blocks, win%, team defence, big flag, games, prior-year share.
  - ROY: PPG, REB+AST, games, draft slot.
  
  Each sim draws that sim's team record, games and box lines (BPM error SD 1.97 and DBPM SD 0.81, conservative baseline errors). Rookie box lines come from per-36 fits on draft slot and age with a rookie minutes SD of 0.32 (an upper bound). The 65-game rule is a toggle: games ≥65 and projected mpg ≥20, and it is on by default. Only 13 winners fit each award, and the candidate pool is 2014+ (full player tables); the voting file goes back to 2000 but without non-finalists.
- **Uncertainty.** 80% interval from 40 season-block bootstrap refits of the rate calibration and award coefficients. Scenarios: rate SD ×0.8 and ×1.25, 65-game rule off, rookie minutes SD 0.22. The bet test uses the worst scenario.
- Dead-heat on awards is not modelled (ties are rare).

## What the model says vs the book (fair prob, Shin)
| Market | Model | Book fair |
|---|---|---|
| MVP SGA | 32% [26, 39] | 19% |
| MVP Wembanyama | 10% | 29% |
| MVP Jokic | 18% | 14% |
| DPOY Wembanyama | 44% | 74% |
| ROY Dybantsa | 33% [30, 41] | 18% |
| ROY Boozer | 14% | 22% |
| ROY Peterson | 25% | 21% |
| ROY Wilson | 10% | 20% |
| PPG Luka | 35% | 50% |
| PPG SGA | 37% | 26% |
| BPG Wembanyama | 80% | 78% |
| 3PM Curry | 30% | 50% |

The model is far less confident than the book on Wembanyama's awards (the 65-game rule and his projected 60 games). It likes SGA. Those are unbettable as priced (only YES prices are offered) except SGA MVP, whose shrunk edge is marginal (lower bound about 0.2%, so Tier 2 only).

## Tier 1 player bets (shrink 0.75, fair ≥5%, CI low >0, worst scenario ≥3%)
| Bet | Book | Fair | Model [10-90] | EV (model) | EV at shrink 0.75 | Stake |
|---|---|---|---|---|---|---|
| ROY AJ Dybantsa | +400 | 17.7% | 32.7% [29.7, 40.8] | +63% | +7% | 0.50% |
| RPG Rudy Gobert | +990 | 7.9% | 22.1% [19.8, 23.7] | +140% | +25% | 0.70% |
| RPG Domantas Sabonis | +900 | 8.6% | 18.3% [16.0, 20.1] | +83% | +11% | 0.40% |
| APG Tyrese Haliburton | +780 | 9.9% | 20.7% [18.0, 25.1] | +82% | +11% | 0.40% |
| 3PM LaMelo Ball | +1100 | 7.1% | 18.9% [16.5, 23.2] | +127% | +21% | 0.50% |

Drivers, with the weak points:
- **Dybantsa.** Projected 24 mpg and 80 games with a rookie box line from his draft slot. The edge is mostly "the model rates Boozer, Wilson and Peterson less"; rookie minutes are the risk.
- **Gobert.** 10.9 RPG in 31 mpg over 63 games, against rival Sabonis (11.4 RPG but only 53 games).
- **Sabonis.** The same RPG race, with 53 projected games. His edge rests on the totals-based qualification path, which is an unverified edge case.
- **Haliburton.** 8.6 APG, but only 52 projected games.
- **LaMelo.** 3.4 3PM per game in 27 mpg over 62 games, against Curry at 4.1 (model 30% vs book 50%).

Treat these as lower-conviction than the Kawhi/Toronto idea: three of the five are availability-heavy and the others are lean on a named driver. Total Tier 1 player stake is 2.3% (about 4.3% with team Tier 1, cap 10%).

## Caveats
- No market benchmark exists for any of these; the model has not been shown to beat the book. The sharpening exponent and the 10-90 intervals reflect parameter uncertainty only, not model error.
- The leader backtest uses the previous-season minutes proxy and pools six stats. 8 seasons × 6 stats means only about 48 leader outcomes.
- Award models have only 12-13 training winners each. Wembanyama's games (60 projected, 49% chance of ≥65) drive the MVP/DPOY gaps heavily.
- Qualification: 58 games or the NBA.com totals rule; 3PM uses 58 games only (your default). Please confirm the book's rules for the two edge cases (totals path, 65-game minutes).

## Workbook
`M_Players` now holds all 236 modelled player-market rows with live EV, shrunk EV, Tier 2 / Tier 1 formulas (using Assumptions) and a driver column. Excel agrees with Python (25 Tier 2, 5 Tier 1), 0 error cells, 0 failing checks. The player bets are not yet merged into `Tier1_Card` / `Exposure` (they live on `M_Players`), so the existing Dashboard Tier 1 numbers are team-only. Say if you want them merged before G6.

Code: `src/players/{rates,pool,simgp,leaders,awards,rookies,run_g4,leader_backtest}.py`, `src/pricing/price_players.py`. Outputs: `data/clean/player_market_probs.csv`, `player_pricing_table.csv`, `g4_*.json`.
