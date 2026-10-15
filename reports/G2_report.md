# G2 Report — Player & team ratings + backtest (2026-10-15)

**Status: complete, awaiting "approve G2".**

## 2027 lottery restrictions (header, as requested)
- **Cannot pick top-5 in 2027** (top-5 in both 2025 and 2026): **Utah (UTA)** only. UTA was #5 in 2025 and #2 in 2026. Its 2027 pick is owned by Memphis under the cluster trade, and the restriction travels with UTA's pick, so it can land no higher than #6.
- **Cannot win #1 in 2027** (the 2026 #1 winner): **Washington (WAS)**.
- bbref lists the team that *made* each pick, not the original owner. The 2025 top-5 holders were DAL, SAS, PHI, CHA, UTA. The 2026 top-5 holders were WAS, UTA, MEM, CHI, LAC. UTA is the only team in both sets, and ESPN independently states UTA is the only team affected. The original-owner check is **partly inferred**.

## 0. Pre-G2 items (your approval list)

**Cup-dependent games (30).** NBA.com's "Cup 101" page confirms the rules, with two differences from your spec.
- **Semifinals** are played at the higher seed's home arena, not a neutral site. Quarterfinals and semifinals count as regular-season games and the Championship does not. Toggle: `cup_semis_neutral` (default 0 = NBA.com; set 1 for your spec).
- **Non-qualifier games:** NBA.com says **2 of the 22 non-qualifier games are cross-conference**. Your default is 0, and it is stored as `cup_nonqualifier_cross_conf_games` (default 0, your default). NBA.com's value is 2.
- Everything else matches your spec:
  - 22 non-advancing teams play 2 games each, 22 games in total.
  - The 4 quarterfinal losers (2 per conference) play 2 games, paired within conference.
  - 4 quarterfinal games + 2 semifinal games.
  - The check is 22 + 2 + 4 + 2 = 30, and every team ends at exactly 82.
- The module itself is built in G3. The spec is stored in `params/assumptions.json`.

**Pick ownership (tank-critical).**
- **Reconciled table:** `data/clean/picks_2027_reconciled.csv`, with a discrepancy column, built from Hoops Rumors (Sep 2026), RealGM's detailed ledger (read 10/15 through the browser) and Tankathon's live draft order. The ESPN trade tracker (updated 9/22) lists no 2027 first-round trades since September 1.
- **Wording and semantics:**
  - The cluster rules agree across sources: MEM/UTA/PHX over CLE/MIN/UTA, NOP/ATL over NOP/MIL, SAC/OKC over SAS, the OKC/LAC/TOR/DEN swap chain, and the CHA, HOU, BKN, NYK and LAL pieces.
  - RealGM says "barred from 1–5" where Hoops Rumors says "top-5 protected" for UTA. The effect is identical.
- **Unresolved conflict:** none on substance. One post-9/1 item remains, a **LAC–TOR agreement dated 9/14/2026** in RealGM. Hoops Rumors' 9/11 snapshot already describes the TOR swap, and the semantics match. I could not read the full agreement text, so **LAC and TOR are set to a tank-incentive toggle** (`tank_incentive_toggle_teams`), not a modelled value.
- **Tankathon:** its projection owners (which team holds each slot) match this table.

**bbref ID gap (118 of 627 unmatched).** `data/clean/player_id_gap_by_category.csv`:

| Category | Count | Notes |
|---|---|---|
| 2026 rookie draftees | 53 | rookie model |
| Undrafted / two-way / camp, no NBA games | 59 | includes 2025 first-rounder Thomas Sorber, who has not played |
| International / no US college, no NBA games | 5 | |
| **Veterans with prior NBA games** | **0** | |

- Fixing the one real veteran bug (ESPN "Ronald Holland II" = bbref "Ron Holland", `hollaro01`, 159 NBA games) took matched players from 509 to **510**.
- The 14 earlier "unmatched veterans" were 13 players with 0 NBA games, whose ESPN "experience" counts G League or international years, plus that one alias.
- Rosters are otherwise complete: only Westbrook and Batum had ≥1,200 minutes in 2025-26 and are not on a 2026-27 roster.

**Lottery ambiguities (Assumptions inputs, logged in provenance as assumptions).**
- `lottery_n_draws` = **4** (your default), `lottery_redraw_blocked` = 1, `lottery_restrictions_follow_pick` = 1 (toggle), `lottery_7v8_loser_keeps_ball_if_makes_playoffs` = 1.
- ⚠ **The 4-draw default conflicts with three sources.** NBA.com ("lottery balls … drawn to determine the order of selection for the first 16 picks"), Tankathon ("Picks 1 through 16 are ALL awarded via drawing of lottery balls") and Hoops Rumors ("all 16 picks will be drawn") all say all 16 are drawn. I implemented your default but strongly recommend 16.
- **Sensitivity** (`data/clean/lottery_sensitivity_draws.csv`, exact simulator `src/sim/lottery.py`, 400k sims). The simulator reproduces P(#1) = balls/37 within 0.09 pp, and the three-worst floor at #12 never binds.
- **Expected pick by lottery position and number of draws:**

| Position (balls) | 2 draws | 4 | 6 | 16 |
|---|---|---|---|---|
| Worst record (2) | 2.84 | 4.45 | 5.83 | 8.09 |
| 10th worst (3) | 9.13 | 8.45 | 7.96 | 7.45 |
| 7v8 loser (1) | 15.19 | 14.43 | 13.72 | 11.64 |

- P(#1) is fixed at 5.4% / 8.1% / 2.7% regardless of draws.
- P(top-4) for the worst team is 100% at 2 draws, 22% at 4 draws and 22% at 6 or 16 draws. Under 2 or 4 draws the worst team still gets a very high pick (certain top-4 at 2, expected pick 4.45 at 4), whereas under 16 draws its expected pick is 8.1. This materially changes the sign of the marginal draft equity of losing, i.e. the tank-incentive module in G3.

**DARKO official CSV.** Done. I clicked "Download CSV" (user-approved), and the browser pane produced the CSV in-page; it could not write to disk (no download handler, and localhost posting is blocked by the site's content policy).
- I verified it instead by hashing: the official CSV (530 rows, 19 columns) matches my scraped table exactly. The SHA-256 of the sorted rows `DPM|ODPM|DDPM|Box|OnOff|MPG` is identical, and the column sums and the 47 missing-MPG dashes match. **Max deviation: 0.0.**
- The official CSV also has only one decimal of precision, so there is no extra precision to gain. Extra columns not yet stored: pace, pts/100, ast/100, shooting %, salary.

**nba_api retry.** Retried once with the full header set (User-Agent, Referer, Origin, x-nba-stats-origin/token, 60 s). It still times out (`ReadTimeout`). Accepted bbref/ESPN, and **in-house RAPM is dropped until after the Tuesday lock**, as you directed.

**TPG qualifier.** Stored on Assumptions as `tpg_min_games_pct` = 0.70 (58-game rule), flagged **unconfirmed with the book**.

## 1. What was built
- **Player impact** (`src/ratings/model.py`, `rookies.py`). Per-100-possession BPM with O/D split, then:
  - A decayed 3-year prior with reliability shrinkage `r = S/(S+M0)`, where S is decayed prior minutes. The fit gives λ = 0.55 and M0 = 600.
  - A quadratic aging curve fit on 2014–2026.
  - An in-sample weighted RMSE of 1.65 BPM points.
  - Rookies: a draft-slot + barttorvik college translation (college BPM, class, height), with leave-future-draft-year RMSE 2.04 vs 2.27 for slot only.
- **DARKO ensemble** (weight `w_darko` = 0.35):
  - ⚠ **ASSUMPTION.** DARKO has no archived history, so its weight cannot be fit by backtest.
  - DPM is mapped onto the model scale by regression, then blended. 75% of roster players have a DARKO rating.
  - The effect of the weight on team wins (`data/clean/sensitivity_w_darko.csv`) ranges up to ±2.6 wins at 0 and ±4.8 at 1, with the largest moves at OKC, NYK, DAL, CHI and LAC.
- **Minutes and availability:**
  - Projected mpg is a decayed prior-minutes average shrunk toward 12 mpg, with a 38-mpg cap.
  - An availability model for games-played fraction (prior two seasons + age; residual sd 0.20).
  - Team minutes are rescaled to 240 per game.
  - ESPN "Out" injuries are applied as games missed through the return date.
  - `params/overrides_players.csv` (empty template) carries manual mpg, games and rating overrides.
  - **Position-coverage constraints are not enforced** (only the cap and the 240 total). This is a known simplification.
- **Team rating:** `SRS = a + b·Σ(minutes share × player impact) + c·prior SRS + d·continuity·prior SRS`.
  - The fitted b is ≈ 1.07, consistent with BPM's calibration to team rating.
  - Wins are `41 + 2.44 × SRS`, centered so projected wins sum to exactly **1,230** (checked every season).
  - ORtg/DRtg come from an O/D BPM split (approximate), and pace is 0.7 × prior pace + 0.3 × league mean (assumption, not backtested).
  - The book's lines sum to **1,241**, which is market inflation, not a model target.
- **σ_team (true-strength shock):** wins residual sd 8.08, less 4.5 wins of game noise, gives **σ_team ≈ 6.7 wins ≈ 2.7 SRS points**. This is a starting value; G3 re-estimates it from the game-level fit.
- Every fitted parameter is in `params/provenance.json` (value, method, window, n, date, code path).

## 2. Backtest (2018-19 → 2025-26 test seasons; each season fit only on earlier data)
n = 240 team-seasons. 80% bootstrap CIs resample team-seasons. Wins are scaled to 82 games in the shortened 2020 and 2021 seasons.

| Model | Wins RMSE [80% CI] | MAE [80% CI] | Spearman ρ |
|---|---|---|---|
| **This model** | **8.44 [7.97, 8.90]** | **6.66 [6.24, 7.10]** | **0.71** |
| Prior-wins regression | 10.23 [9.60, 10.85] | 8.21 [7.70, 8.72] | 0.55 |
| Prior-SRS regression | 10.21 [9.60, 10.83] | 8.11 [7.61, 8.64] | 0.53 |
| Naive (prior wins) | 11.48 [10.70, 12.24] | 8.82 [8.21, 9.45] | 0.55 |

- **Paired RMSE difference (model − baseline):** −1.80 [−2.24, −1.35] vs the prior-wins regression, and −1.76 [−2.17, −1.35] vs prior SRS. **Both CIs exclude zero, so the model passes vs baselines.**
- **Probabilistic (Brier vs climatology, 80% CI for the model):**
  - P(top-10 in conference): 0.140 [0.124, 0.158] vs 0.222.
  - P(top-6): 0.149 [0.135, 0.165] vs 0.240.
  - P(over line) at lines 30.5, 35.5, 41.5, 47.5, 52.5: 0.132 vs 0.250.
- **Calibration:** reliability tables are in `backtest_metrics.json`.
  - The over-line bins track closely.
  - The top-10 bins show some noise at the extremes (e.g. 0–5% bin, n = 2).
- Mean bias is +0.05 wins. By-season RMSE ranges from 6.0 (2023) to 9.8 (2026), always better than the baselines.
- **Variance ratio** (§0.6) is judged in G3 against the engine's self-consistency ceiling.

⚠ **Honest caveats**
1. **The benchmark failed.** I found no free archive of historical preseason win-total closing lines (Sports Betting Dime has partial web tables only). So skill is shown only against statistical baselines, not against the market. Typical market RMSE is around 7–8 wins, so an 8.4 model should be treated as likely below market quality. The stake shrink (0.25) and the lower-CI rule matter.
2. **Roster look-ahead:** the backtest takes team membership from actual season-t stints (who played for the team), while ratings, minutes and availability use only earlier seasons. This is the closest available proxy to preseason rosters; it leaks in-season trades and signings slightly, so true out-of-sample RMSE is likely somewhat worse than reported.
3. The team layer is fit on only 90 to 300 team-seasons.
4. DARKO is not backtestable (assumption weight). Pace, ORtg/DRtg split and the mpg shrinkage are assumptions.

## 3. 2026-27 projection (`data/clean/team_projection_2027.csv`, `player_projection_2027.csv`)
Top: OKC 59.7, SAS 53.5, HOU 53.0, BOS 51.2, TOR 49.6, DEN 48.3, DET 47.0, CLE 47.0, LAL 46.4. Bottom: SAC 24.3, WAS 27.6, LAC 30.3, MIL 30.4, BKN 30.9, UTA 32.1, NOP 32.2. Full table in the CSV (wins, SRS, ORtg, DRtg, pace, σ = 8.08).

**Benchmark only, not a model input** (`benchmark_model_vs_book_wins.csv`): the model correlates 0.89 with the book's lines (mean absolute difference 3.8 wins). Largest gaps (model − line): NYK −9.6, MIA −9.5, WAS −7.9, SAS −6.0, UTA −5.4; and MEM +7.7, BKN +6.4, HOU +5.5, MIL +4.9, CHI +4.5. These need driver diagnosis before any bet (G6), e.g. NYK's roster no longer includes Mitchell Robinson and has a weak bench.

## 4. Open issues
- Position-coverage constraint is not enforced; ORtg/DRtg split is approximate.
- Roster look-ahead (§2) and the missing market benchmark.
- Draw-count default (4) vs sources (16).
- LAC/TOR pick terms (toggle on); the Cup site/pairing toggles.
- Torvik column order is verified on two known players only.
- Cup games and the lottery tank module are G3.

Awaiting "approve G2".
