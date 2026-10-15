# G3 Addendum — dispersion, tank κ, tank carryover, robustness (2026-10-15)

Responds to the conditional G3 approval. **σ_team changes from 3.5 to 3.25.** The 2027 projection was refreshed for the carryover fix. The production sim was re-run (100,000 sims), and the engine tests and the independent title check were re-run.

## 1. Dispersion check (blocking item)
Engine run with availability draws ON, as in production, so injury variance is not double counted in σ_team. Six full 82-game seasons (2019, 2022–2026; 2020 and 2021 are shortened), 180 team-seasons, preseason first-team-roster inputs, 30,000 sims per season per σ_team value (`sigma_team_cv.json`).

| σ_team (SRS) | Mean simulated SD of wins | Realized RMSE of the same projections | SD ÷ RMSE | Log score | Variance ratio (p vs ceiling) |
|---|---|---|---|---|---|
| 3.00 | 8.19 | 8.73 | 0.94 | −3.588 | 1.13 (0.09) |
| **3.25** | **8.58** | 8.74 | **0.98** | **−3.579** | **1.04 (0.33)** |
| 3.50 | 8.96 | 8.75 | 1.02 | −3.581 | 0.95 (0.68) |
| 3.75 | 9.34 | 8.76 | 1.07 | −3.579 | 0.88 (0.90) |
| 4.00 | 9.72 | 8.77 | 1.11 | −3.584 | 0.81 (0.98) |

- **Leave-one-season-out CV:** the selected σ_team in each held-out fold was 3.75 (2019), 3.25 (2022), 4.00 (2023), 3.25 (2024), 3.25 (2025) and 3.25 (2026). The all-season optimum is 3.25.
  - The held-out log score barely differs between 3.25 and 3.5, so the log score is flat across 3.25–3.75.
  - I chose 3.25: it has the best CV log score (tied with 3.75) and lands the predictive SD within 2% of the realized RMSE.
  - Variance ratio vs the self-consistency ceiling (5th–95th percentile 0.84–1.17): 1.04 observed (p = 0.33), inside the band.
- **Production predictive SD** (2026-27 sim, all components on): **8.51 wins** (mean across teams; range 7.6–9.1).
  - Against the G2 backtest RMSE of 8.44: +0.9%.
  - Against the honest first-team-roster RMSE of 8.92: −4.6%.
  - Against the 8.74 realized in the CV seasons: −2.6%.
  - All are within ±5% of what the backtest supports.
- **Out-of-sample reliability** (each season uses the σ_team chosen without it; 180 team-seasons):
  - P(wins > projection −10 / −5 / +5 / +10): bins at predicted 0.86 / 0.71 / 0.29 / 0.13 realize 0.865 / 0.709 / 0.282 / 0.135. Brier scores equal the climatological reference to three decimals (0.1167 vs 0.1156, 0.2064 vs 0.2054, 0.2061 vs 0.2054, 0.1173 vs 0.1156). That is calibration with no discrimination, which is expected for fixed offsets.
  - P(top-6 seed): Brier 0.167 vs 0.240 climatology. The 0.60–0.75 bin is under-confident (predicted 0.67, observed 0.87, n = 23), and the 0.40–0.60 bin is slightly over-confident (0.50 vs 0.41, n = 58).

## 2. Tank κ
- **Did the diff-in-diff control for deadline roster or rating changes? No.** Its controls were season fixed effects and the pre-deadline opponent-adjusted margin (a regression-to-the-mean control). No roster or rating data were available.
- Re-estimated on team-level outcomes without that control (excluding the 2020 bubble; κ in net-rating points per unit incentive, 80% CI), `tank_kappa_fit_v2.json`:

| Outcome | κ | 80% CI |
|---|---|---|
| Raw net rating (margin per game) | +0.19 | [−0.47, +1.22] |
| Win% pre → post (converted) | +0.04 | [−0.73, +0.84] |
| Adjusted margin, season fixed effects only | −0.08 | [−0.83, +1.09] |
| Adjusted margin with the pre-level control (production) | +0.28 | [−0.49, +1.57] |

- **Production keeps κ at 0.28**; the filter's upper bound is **1.57**, as you instructed.

## 3. Season-long tank carryover (new check)
Pre- vs post-deadline (Feb 5, 2026) role and lineup quality for the eight worst 2025-26 teams (WAS 17 wins, IND 19, BKN 20, UTA 22, SAC 22, MEM 25, NOP 26, DAL 26). The source is bbref game logs for 142 players, 148 team-player rows (`tank_carryover_*.csv`, `data/raw/gamelogs/`).
- **Lineup quality** (minutes-weighted BPM of the players on the floor): fell sharply after the deadline at UTA (−1.51), MEM (−1.39), WAS (−1.31), SAC (−1.15) and BKN (−0.67). It was flat at IND and DAL and rose at NOP.
  - The five best players' share of minutes fell at UTA (0.35 → 0.15), WAS (0.36 → 0.13) and SAC (0.44 → 0.22).
- **Shutdowns** (players who stayed, played ≤8 of ~30 post-deadline games after a normal pre-deadline role; the bbref "reason" field was blank in my parse, so injuries and coach decisions can't be separated):
  - MEM: Aldama (0 of 33), Caldwell-Pope (3).
  - UTA: Markkanen (4), Nurkić (3), Mykhailiuk (6), Keyonte George (7).
  - WAS: Kyshawn George (7), Sarr (8).
  - BKN: Dëmin (8).
  - SAC: LaVine (1).
  - Other post-deadline absences were trades, not shutdowns: JJJ, Landale, Alvarado, Schröder, Clayton, McCollum and Middleton all played elsewhere. Toppin was an injury return.
- **Was the 2026-27 minutes projection contaminated?** Yes. The projection used 2025-26 season totals, so tank-mode games and minutes lowered both role and availability for returning players on those teams.
- **Fix** (`pre_deadline_role_override_2026.csv`, 29 players; applied only when post-deadline availability dropped by more than 0.30 or minutes were cut by 25% or more, and not for players traded): their 2025-26 totals are replaced by pre-deadline availability × 82 games and pre-deadline minutes per game.
- **Win projection before → after the fix:**

| Team | Before | After | Change |
|---|---|---|---|
| WAS | 27.4 | 27.8 | +0.4 |
| IND | 42.0 | 42.1 | +0.1 |
| BKN | 30.8 | 31.3 | +0.5 |
| UTA | 32.6 | 33.3 | +0.7 |
| SAC | 24.1 | 23.9 | −0.1 |
| MEM | 36.4 | 36.4 | 0.0 |
| NOP | 31.9 | 32.0 | +0.1 |
| DAL | 33.8 | 34.0 | +0.3 |

The other 22 teams move by −0.2 to 0.0 (zero-sum). The effect is small and the largest shift is UTA's +0.7.

## 4. Robustness scenarios (for the Bet Card)
- `sim_robust_summary.csv` and `sim_robust_wins_hist.csv` hold the base case and the κ = 0, κ = 1.57, σ_team −10% (2.93) and +10% (3.58) scenarios, each with 100,000 sims on common random numbers.
- The bottom-10 projected teams are SAC, WAS, MIL, BKN, LAC, NOP, CHI, UTA, DAL and MEM (`sim_robust_meta.json`).
- `src/pricing/robust.py` implements the rule: a bet on any bottom-10 team needs positive EV under all four alternative scenarios. The σ_team ±10% test is applied to bottom-10 bets only by default (switchable to all bets).
- κ barely moves anything: P(playoffs) changes by at most 0.6 pp. σ_team ±10% moves bottom-10 playoff probabilities by about 2 pp (SAC 9.4% / 11.3% / 13.2%).

## 5. Re-checks after the changes
- `tests/test_engine.py` passes (20,000 sims).
- The independent title check vs the engine (stripped configuration, σ_team 3.25): max difference 0.17 pp for title, 0.22 for conference, 0.29 for playoffs, 0.45 for top-6, 0.37 for division, and 0.13 for mean wins.
- **New title leaders:** OKC 20.0%, SAS 10.2%, HOU 8.6%, BOS 8.3%, TOR 7.9%, DET 5.0%, CLE 5.0%, DEN 4.9%.

Proceeding to G5 (team markets, workbook), per your instruction.
