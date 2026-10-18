# repro_check

Generated 2026-10-18 11:54. Rebuilt with N = 20,000, seed 2026 (committed outputs: N = 100,000, seed 2026); tolerance = 4 Monte Carlo standard errors of the difference (sqrt(1/N + 1/N0)).

**Result: PASS.** Numba COLD compile time (first 64-sim run, empty cache): **73.0 s**. Ratings reproduced to max |diff| 0.00e+00 wins (deterministic).

## Stages
| Stage | Exit | Seconds | Log |
|---|---|---|---|
| -W ignore verify_inputs.py | 0 | 0.6 | `repro/logs/verify_inputs.log` |
| -W ignore -m src.ratings.project_2027 | 0 | 28.7 | `repro/logs/ratings_project.log` |
| -W ignore -m src.sim.run_sim 20000 2026 | 0 | 40.0 | `repro/logs/sim.log` |
| -W ignore -m src.pricing.run_pricing | 0 | 24.4 | `repro/logs/price_teams.log` |
| -W ignore -m src.pricing.tier1 | 0 | 5.0 | `repro/logs/price_tier1.log` |
| -W ignore -m src.players.run_g4 | 0 | 154.0 | `repro/logs/players_sim.log` |
| -W ignore -m src.pricing.price_players | 0 | 4.3 | `repro/logs/price_players.log` |
| -W ignore -m src.pricing.joint | 0 | 17.2 | `repro/logs/joint_kelly.log` |
| -W ignore write_final_card.py rebuilt_card.csv | 0 | 1.7 | `repro/logs/write_card.log` |

## Teams (max z over all 30 teams and 3 statistics: 1.72)
| Team | Mean wins (committed) | Mean wins (rebuilt) | z | P(over line) committed | rebuilt | z | P(top-8) committed | rebuilt | z |
|---|---|---|---|---|---|---|---|---|---|
| ATL | 41.48 | 41.51 | 0.38 | 0.373 | 0.373 | 0.09 | 0.567 | 0.569 | 0.51 |
| BKN | 30.70 | 30.69 | 0.07 | 0.756 | 0.757 | 0.37 | 0.150 | 0.148 | 0.72 |
| BOS | 50.54 | 50.48 | 0.77 | 0.472 | 0.466 | 1.39 | 0.875 | 0.874 | 0.54 |
| CHA | 38.52 | 38.55 | 0.38 | 0.452 | 0.452 | 0.07 | 0.435 | 0.437 | 0.53 |
| CHI | 32.52 | 32.51 | 0.17 | 0.669 | 0.671 | 0.69 | 0.201 | 0.201 | 0.06 |
| CLE | 47.08 | 47.15 | 0.97 | 0.490 | 0.492 | 0.32 | 0.781 | 0.782 | 0.36 |
| DAL | 33.68 | 33.66 | 0.28 | 0.452 | 0.451 | 0.34 | 0.238 | 0.234 | 1.32 |
| DEN | 49.11 | 49.14 | 0.41 | 0.499 | 0.501 | 0.52 | 0.835 | 0.835 | 0.12 |
| DET | 47.52 | 47.44 | 1.12 | 0.425 | 0.424 | 0.29 | 0.796 | 0.794 | 0.64 |
| GSW | 43.27 | 43.16 | 1.64 | 0.660 | 0.658 | 0.44 | 0.641 | 0.638 | 0.89 |
| HOU | 51.72 | 51.66 | 0.98 | 0.693 | 0.690 | 0.79 | 0.899 | 0.895 | 1.38 |
| IND | 40.63 | 40.64 | 0.15 | 0.340 | 0.340 | 0.04 | 0.530 | 0.533 | 0.76 |
| LAC | 31.33 | 31.32 | 0.17 | 0.570 | 0.565 | 1.32 | 0.162 | 0.165 | 1.03 |
| LAL | 45.52 | 45.51 | 0.17 | 0.510 | 0.510 | 0.07 | 0.730 | 0.731 | 0.35 |
| MEM | 35.45 | 35.50 | 0.73 | 0.780 | 0.780 | 0.01 | 0.304 | 0.305 | 0.37 |
| MIA | 39.92 | 39.95 | 0.36 | 0.243 | 0.244 | 0.42 | 0.498 | 0.499 | 0.36 |
| MIL | 29.76 | 29.74 | 0.31 | 0.678 | 0.676 | 0.43 | 0.125 | 0.124 | 0.51 |
| MIN | 43.95 | 43.96 | 0.16 | 0.357 | 0.357 | 0.11 | 0.674 | 0.677 | 0.90 |
| NOP | 32.49 | 32.54 | 0.78 | 0.666 | 0.669 | 0.94 | 0.200 | 0.202 | 0.89 |
| NYK | 45.57 | 45.67 | 1.34 | 0.232 | 0.235 | 1.01 | 0.731 | 0.731 | 0.07 |
| OKC | 58.68 | 58.73 | 0.75 | 0.396 | 0.399 | 0.68 | 0.977 | 0.976 | 0.79 |
| ORL | 43.85 | 43.85 | 0.01 | 0.521 | 0.521 | 0.03 | 0.666 | 0.666 | 0.21 |
| PHI | 45.37 | 45.36 | 0.03 | 0.297 | 0.298 | 0.49 | 0.723 | 0.723 | 0.07 |
| PHX | 39.37 | 39.39 | 0.24 | 0.493 | 0.496 | 0.73 | 0.470 | 0.471 | 0.13 |
| POR | 44.27 | 44.30 | 0.42 | 0.582 | 0.584 | 0.44 | 0.685 | 0.683 | 0.49 |
| SAC | 23.96 | 24.01 | 0.84 | 0.652 | 0.653 | 0.21 | 0.032 | 0.034 | 1.23 |
| SAS | 52.95 | 52.83 | 1.72 | 0.237 | 0.235 | 0.52 | 0.920 | 0.918 | 1.07 |
| TOR | 48.44 | 48.36 | 1.16 | 0.635 | 0.632 | 0.70 | 0.819 | 0.815 | 1.28 |
| UTA | 33.57 | 33.65 | 1.23 | 0.323 | 0.326 | 1.00 | 0.234 | 0.235 | 0.54 |
| WAS | 28.78 | 28.74 | 0.48 | 0.211 | 0.210 | 0.16 | 0.104 | 0.105 | 0.62 |

## Card bets
| Bet | EV committed | EV rebuilt | z | EV at 0.75 shrink committed | rebuilt | Stake committed | rebuilt | On rebuilt card | Marginal |
|---|---|---|---|---|---|---|---|---|---|
| PLAYOFFS Minnesota Timberwolves NO | +1.119 | +1.098 | 0.90 | +0.137 | +0.132 | 0.0063 | 0.0060 | True | False |
| WINS Portland Trail Blazers OVER | +0.251 | +0.255 | 0.44 | +0.031 | +0.032 | 0.0050 | 0.0050 | True | True |
| WINS Utah Jazz UNDER | +0.456 | +0.448 | 1.00 | +0.082 | +0.080 | 0.0075 | 0.0075 | True | False |
| WINS Washington Wizards UNDER | +0.353 | +0.354 | 0.16 | +0.064 | +0.064 | 0.0075 | 0.0075 | True | False |

## Problems
- none
