# G3 Report — Simulation engine + calibration (2026-10-15)

**Status: complete, awaiting "approve G3".** 100,000 simulated seasons run in about 15 s once compiled (about 70 s of JIT on first run). Outputs are in `sims/season_sims.npz` and `data/clean/sim_team_summary.csv`. The run hash is in `sims/run_meta.json`.

## 1. What the engine does (`src/sim/engine.py`, `season.py`, numba, one sim = one season)
1. **Per-season draws:**
   - True-strength shock ~ N(0, σ_team), re-centred to zero-sum.
   - Per-player availability rates ~ Beta (mean = projected games fraction, concentration 3.7), for the top 12 players per team by minutes.
2. **Per game** (1,200 scheduled + 30 Cup-dependent):
   - Margin ~ N(HCA + back-to-back effects + rating difference + availability swing + tank effort, σ_game).
   - Each game redraws which of a team's top 12 are present. Availability swings are applied around the team's expected rating.
   - Games-played counts per player are kept for G4. Ties after rounding go to overtime, where the edge is scaled by √(5/48); regulation margins count as 0 in the Cup tiebreakers.
3. **NBA Cup:**
   - Group play uses the real 60 scheduled group games, and the groups equal the book's six `CUP_*` groups.
   - Tiebreakers: group record → head-to-head among tied teams → group point differential (overtime counts 0) → points → 2025-26 record → random.
   - The six group winners plus the best second-place team per conference make the knockout; higher seeds host the quarterfinals.
   - **The 30 Cup-dependent games, per NBA.com's official rules:**
     - 4 quarterfinals, 2 semifinals (at the higher seed's arena) and 2 quarterfinal-loser games count toward the 82.
     - 22 non-qualifier games are drawn fresh each sim: random cycles within conference, one home and one away per team, with 2 cross-conference games.
     - The final does not count.
   - Invariant tested in every sim: each of the 30 teams ends at exactly 82 games.
4. **Standings:**
   - Official tiebreakers (two-team and multi-team), computed from a full head-to-head matrix, division/conference records, record vs. playoff-eligible teams and point differential.
   - Division winners are computed with the same rules; conference seeds are 1–15.
5. **Play-in** (seeds 7–10): 7v8 and 9v10, then the 7/8 loser against the 9/10 winner.
6. **Playoffs:**
   - Best-of-7 with 2-2-1-1-1 home court, a separately fit playoff HCA, and a playoff rating adjustment for minutes concentrating in the top 8 (fit, see §3).
   - A per-top-8-player chance of missing the whole postseason.
   - Finals home court goes to the better regular-season record.
7. **Lottery** (exact 3-2-1 simulator, 16 draws): positions are the 10 non-play-in teams, the four 9/10 seeds, then the two 7v8 losers. The 3-worst floor is #12, restrictions are redrawn, and picks 17–30 go to the rest by record.
8. **Tank module at the trade deadline (Feb 11, 2027):**
   - Marginal draft equity of one more loss, using the pick-value curve (career win shares by slot, drafts 2013–2021) and the exact 3-2-1 odds.
   - The incentive can flip sign: bottom-3 teams face lower odds than the 4th–10th worst.
   - It is zero when a team is in the playoff or play-in race, doesn't hold its pick, or is barred by the restriction rules.
   - Ownership factors come from `params/pick_ownership_rules.csv`, with probabilities of protection used for protected picks.
   - Post-deadline effort suppression = κ × normalized incentive × (1 − deterrent).

## 2. Fitted game parameters (2021-22 → 2025-26, 6,153 regular-season games; `game_model_fit.json`)
| Parameter | Value (SE) |
|---|---|
| Home-court advantage | 1.89 (0.20) pts |
| Back-to-back, home team | −2.65 (0.47) |
| Back-to-back, away team | +2.53 (0.44) for the home side |
| σ_game | 13.49 |
| Slope on rating difference | 1.00 (0.02), so ratings are on the SRS scale |
| Playoff/post-season HCA | 3.64 (0.72) from 452 post-regular-season games; 3.71 (0.48) in the playoff-adjustment fit below |

## 3. Tank module: κ and the playoff adjustment
- **κ (post-deadline effort suppression):**
  - Dose-response diff-in-diff on old-system incentives. Each team-season's change in opponent-adjusted margin after the deadline is regressed on normalized incentive, pre-deadline level and season fixed effects.
  - Excluding the 2020 bubble restart: **κ = 0.28 net-rating points per unit incentive, 80% CI [−0.52, 1.42]**. All 8 seasons give 0.23 [−0.53, 1.41]; also excluding 2021 gives 0.84 [−0.59, 2.64].
  - **The CI includes zero: no statistically detectable tanking effect in 2019–2026 data.** The simulator uses the point estimate 0.28, with a deterrent of 0 (assumption) and an on/off switch.
  - Simulated effect on wins: at most about −0.03 wins per team at κ = 0.28, and −0.1 at the upper 80% bound. Tanking and its sign flip do not move any market meaningfully.
- **Playoff rating adjustment** (the largest single sensitivity in the title market):
  - **λ_po = 0.58, 80% CI [0.32, 0.80]**. Source: post-season game margins on SRS difference plus the top-8 minutes-concentration delta, 956 games, 2015-16 to 2025-26.
  - The default of 1.0 would overstate star-heavy teams. At λ = 0 / 0.58 / 1.0, OKC's title probability is 15.6% / 19.5% / 23.3%.
  - Playoff injury chance per top-8 player is 7% (assumption).
- **LAC/TOR toggle:** flipping both teams' pick ownership to "own" (full incentive) changes win projections by **at most 0.02 wins** (P(playoffs) ≤ 0.2 pp). It is far below the 1.5-win threshold, so **no no-bet flag**.

## 4. Engine tests (`tests/test_engine.py`, 20,000 sims with tank on)
All pass:
- Every team plays exactly 82 games and league wins equal 1,230 in every sim.
- 20 playoff teams, 12 top-6, 6 division winners, 2 conference champions, 1 champion; title ≤ conference ≤ playoffs for every team.
- 6 Cup group winners; exactly 8 → 4 → 2 → 1 Cup survivors per sim.
- Conference ranks are a permutation of 1–15; picks are a permutation of 1–30; 16 lottery teams.
- WAS never gets #1; UTA is never top-5; the three worst records never pick below 12th.
- Hand-built tiebreak scenarios (head-to-head, division-winner priority, a three-team cycle).

## 5. Calibration on 2023-24 → 2025-26 preseason inputs (`sim_calibration.json`, figure `output/figs/G3_calibration.png`)
The engine is re-run on each season's preseason ratings, first-team roster proxy and actual schedule (Cup and tank off). 90 team-seasons. Inputs are preseason-only, but HCA, σ_game and σ_team were fit on windows that include these seasons (mildly in-sample).
- **Variance ratio** (observed squared forecast error ÷ model-implied variance), judged against the self-consistency ceiling (the same statistic computed on pseudo-seasons drawn from the engine itself):
  - Ceiling mean 1.00, 5th–95th percentile 0.78–1.24.
  - **σ_team = 2.74** (G2 estimate): VR 1.48, p = 0.002 → rejected.
  - **σ_team = 3.15** (pooled honest backtest): VR 1.28, p = 0.03 → rejected.
  - **σ_team = 3.5 (adopted): VR 1.16, p = 0.13 → inside the band.**
  - This was tuned on these 90 team-seasons, so it is a calibration choice, not an out-of-sample test. It is deliberately conservative (wider).
- **Win intervals:** the central 50 / 80 / 90% intervals cover 46% / 77% / 87% of actual win totals (nominal 50 / 80 / 90).
- **PIT:** KS distance 0.073 on 90 points (no formal rejection at this n).
- **Reliability and Brier** (reliability tables in the JSON, bins with n ≥ 5):
  - P(top-10 in conference): Brier **0.132** vs 0.222 climatology.
  - P(top-6): Brier **0.170** vs 0.240.
  - P(division title): Brier **0.118** vs 0.149.
  - The model is somewhat under-confident for the top-10 market in the 0.75–1.00 range (predicted 0.83 and 0.94, observed 0.96 and 1.00). It is a little over-confident in the 0.40–0.60 range (predicted 0.52, observed 0.33). Samples are n = 12 to 25 per bin.
  - Division bins run close to the diagonal with wide error bars.
- **Wins RMSE** on these seasons: 9.65 (worse than the 8.9 eight-season average).

## 6. Independent verification (`src/verify/title_check.py`, `compare_title.py`)
- A stripped-down simulator, using only numpy/pandas and the raw data files (ratings CSV, schedule, game-model JSON) and **no model code**, was compared with the engine in its stripped configuration.
- The stripped configuration has no availability, tank or playoff adjustment, and an 80-game schedule.
- 200,000 sims each. Title, conference, playoff, top-6 and division probabilities agree to within **0.22 / 0.31 / 0.28 / 0.51 / 0.34 pp** (max over 30 teams); mean wins agree to within 0.14.
- The largest standardized differences are z ≈ 2.5–3.2 across 150 comparisons.
- The remaining gap is structural: official vs. random tiebreaks and the overtime edge. Max title difference is 0.22 pp.

## 7. Headline 2026-27 simulation output (100,000 sims, assumptions hash in run_meta)
Top of the title market: OKC 19.5%, SAS 10.2%, HOU 8.5%, BOS 8.1%, TOR 7.8%, CLE 5.0%, DET 4.9%, DEN 4.9%. Mean wins: OKC 56.4, SAS 52.9, HOU 52.0, BOS 49.9, TOR 49.1. Full tables (wins distribution, seed, play-in, playoffs, division, conference, title, Cup group, Cup, lottery position, 2027 pick, MC standard errors) are in `data/clean/sim_team_summary.csv`. Per-player game counts are in `sim_player_games.csv`.

**Sensitivity of the title market** (`sim_sensitivity.csv`, 60,000 sims per case):

| Case | OKC | SAS | HOU | BOS | TOR |
|---|---|---|---|---|---|
| Base | 19.5 | 9.7 | 8.4 | 8.0 | 7.8 |
| Playoff adjustment λ = 0 | 15.6 | 10.3 | 9.4 | 8.2 | 7.2 |
| Playoff adjustment λ = 1.0 | 23.3 | 9.7 | 7.3 | 7.9 | 7.9 |
| σ_team = 3.0 | 20.8 | 10.4 | 9.0 | 8.3 | 7.9 |
| σ_team = 4.0 | 18.1 | 9.3 | 8.1 | 7.7 | 7.6 |
| Availability draws off | 20.6 | 10.2 | 8.4 | 8.2 | 7.8 |
| κ = 0 / 1.42 | 19.5 | 9.9 / 9.8 | 8.3 / 8.5 | 8.0 / 7.9 | 7.7 / 7.7 |
| Cup per the user spec (neutral semis / 0 cross-conf) | 19.5 / 19.7 | 9.8 / 9.9 | 8.4 / 8.5 | 7.9 / 7.9 | 7.8 / 7.7 |

HCA ±0.5 moves nothing by more than 0.4 pp. Wins move by at most 0.07 from HCA, 0.06 from κ, 0.02 from the Cup variants and 0.25 from σ_team. Turning availability draws off moves wins by up to 0.84.

## 8. Limitations and open items
1. **Calibration is thin.** It covers 90 team-seasons, the σ_team fix was tuned on the same data, and reliability bins are small. Treat probabilities as noisy, especially in the tails.
2. **The title market hinges on the playoff adjustment.** I fit it (0.58 [0.32, 0.80]), but the OKC title probability swings 15.6–21.4% across that CI. Expect disagreement with the market to concentrate on OKC.
3. **Preseason roster proxy for calibration** (first-team roster) is a point-in-time approximation, as in G2.
4. **Tank module:** the effect is statistically indistinguishable from zero. The incentive calculation approximates the finishing position at the deadline from expected wins with noise, and uses documented approximate ownership factors (UTA = 0.33, protected picks use their protection probability).
5. **Stat-leader qualifiers** (and the TPG market) use the player game counts from these sims in G4.
6. **Position-coverage constraints** are still not enforced in minutes allocation (G2 note).
7. **The 50/50 DARKO blend** from the G2 addendum is untested; weight sensitivity is in `sensitivity_w_darko.csv`.
8. The Cup final's neutral-site detail is a modelling choice. The two NBA.com differences from your Cup spec are documented and switchable.

Awaiting "approve G3".
