# G6 final report (2026-10-15)

**Deliverables:** `output/NBA_Futures_Model_v1_20261015_MS.xlsx` (23 tabs), `output/NBA_Futures_Dashboard_BetCard_20261015.pdf` (4 pages), this report. Excel recalculated with 0 error cells and 0 failing checks.

## 1. Tier 1 card: 9 bets, 4.9% of bankroll (cap 10%)
Stakes come from one portfolio Kelly solved jointly across team and player bets on the shared 100k sims (sims exponentially tilted to the shrunk probabilities, 0.25 Kelly, model weight 0.25). EV is at the model probability; "EV at 0.75 shrink" is what the Tier 1 test uses.

| # | Selection | Book | Model | Market fair | EV (model) | EV at 0.75 shrink | Stake | Named driver |
|---|---|---|---|---|---|---|---|---|
| 1 | DIV_ATLANTIC Toronto YES | +650 | 33.4% | 10.5% | +151% | +21.9% | 0.82% | Kawhi Leonard arrival (rated +6.1, DARKO +6.3, 30 mpg, 56 g, +2.8 SRS vs 2025-26); Gradey Dick gone (1,067 min at −3.6 BPM, +1.0 SRS) |
| 2 | PLAYIN_EAST Chicago YES | +800 | 25.4% | 9.3% | +129% | +20.0% | 0.61% | Rob Dillingham gone (644 min at −7.3 BPM, +1.3 SRS). **Weak driver (bench departure)** |
| 3 | PLAYOFFS Minnesota NO | +550 | 31.8% | 12.5% | +107% | +12.4% | 0.58% | Julius Randle gone (2,610 min at +1.5 BPM, −1.1 SRS) |
| 4 | CONF_EAST Toronto YES | +900 | 17.6% | 8.3% | +76% | +6.4% | 0.00% | Same Kawhi / Dick facts as #1; sized to zero (correlation 0.35 with #1) |
| 5 | ROY AJ Dybantsa | +400 | 32.7% | 17.7% | +63% | +7.2% | 0.44% | Projected 24 mpg and 80 games, box line from draft slot; the edge is mostly that the model rates Boozer/Wilson/Peterson lower. Rookie minutes are the risk |
| 6 | RPG leader Domantas Sabonis | +900 | 21.1% | 8.6% | +111% | +17.5% | 0.59% | 11.4 RPG in 30 mpg (the model's top RPG) but only 53 projected games. **The book price is a backfill from the 12:06 sheet (`BACKFILL_PDF1`); confirm it on the live board** |
| 7 | RPG leader Rudy Gobert | +990 | 25.6% | 7.9% | +179% | +34.2% | 0.92% | 10.9 RPG in 31 mpg over 63 games; rival Sabonis 11.4 RPG over 53 games |
| 8 | APG leader Tyrese Haliburton | +780 | 22.1% | 9.9% | +95% | +14.1% | 0.44% | 8.6 APG in 30 mpg, 52 projected games; rival Jokic 8.5 |
| 9 | 3PM leader LaMelo Ball | +1100 | 19.5% | 7.1% | +134% | +22.7% | 0.51% | 3.4 3PM in 27 mpg over 62 games; rival Curry 4.1 (model 33% vs book 50%) |

Locks: team bets Tue 10/20 02:10 PM CST (#3 Wed 10/21 06:40 PM CST); player markets Tue 10/20 02:10 PM CST. Joint portfolio in the model world: expected return +4.9% of bankroll (+1.0% at the shrunk probabilities), P(profit) 77.9%, worst case −4.9% (all nine lose).

**Correlation matrix of the 9 bets (shared sims).** Only two pairs are non-trivial: Toronto division/conference +0.35, and Sabonis/Gobert −0.22 (same race). Everything else is within ±0.03. The full 9×9 matrix is on `Exposure` and in `data/clean/joint_corr.csv`.

## 2. Your four G6 requests

### Sharpening exponent: leave-one-season-out CV
- Per fold (held-out season): 2019 1.40, 2020 1.50, 2021 1.60, 2022 1.50, 2023 1.50, 2024 1.45, 2025 1.45, 2026 1.35. The folds are stable (range 1.35–1.60).
- **Pooled γ = 1.50; 80% season-block bootstrap CI [1.30, 1.75].** Bootstrap SD 0.19.
- Out-of-sample (each season scored with γ fit on the other seven):

| | Brier | log score of actual leader |
|---|---|---|
| Before sharpening | 0.02139 | −2.180 |
| After (out of sample) | 0.02066 | −2.116 |

  The reliability buckets improve in the tails and the top. In the 2–5% bucket, 3.2% predicted vs 1.4% realised becomes 3.2% vs 3.1%. In the >35% bucket, 50% predicted vs 75% realised becomes 60% vs 61%.
- **Tier 1 player bets must hold at both CI bounds (γ 1.30 and 1.75).** All five do (the player Tier 1 count is unchanged at 5, and the check is built into `M_Players`). Caveat: 8 seasons × 6 stats means roughly 48 leader outcomes, so the CI reflects limited data.

### Root cause: simulated SD vs history
- **Source of the over-dispersion.** The residual SD was fit on the top-30 predicted players, but leader races are among the top ~5-15, whose residuals are smaller. Fixed: SD and calibration are now estimated on the top-15.

| Stat | Log SD before | Log SD after |
|---|---|---|
| PPG | 0.136 | 0.118 |
| RPG | 0.188 | 0.147 |
| APG | 0.231 | 0.193 |
| SPG | 0.215 | 0.193 |
| BPG | 0.293 | 0.265 |
| 3PM | 0.213 | 0.186 |

- **Remaining gap to history.** The simulated SD for the top 5 (e.g. PPG about 3.4 at a mean of 28) is still above the implied idiosyncratic SD of the top-10 producers' year-over-year changes (YoY SD / √2: PPG 2.05, RPG 1.04, APG 1.14, 3PM 0.36). Part of it is the minutes proxy (rate-only log SD of the top 15 is 0.10 PPG, 0.11 RPG, 0.17 APG, 0.15 3PM against 0.12, 0.15, 0.19, 0.19 with the previous-season-minutes proxy). The production minutes model should be at least as good as the proxy, so the sims are, if anything, conservative on dispersion. I did not cut further, because that would be fit to the history this check was run on. Details: `data/clean/g4_variance_check.json`.
- **Is sharpening still needed after the fix? Yes.** γ moved from 1.40 to 1.50 (the CV is run on the fixed engine). The overstated longshots and understated favourites are therefore not just an SD problem; a lognormal with fixed SD does not capture how fat the tails are in who emerges as a leader. Sharpening stays, with CI-bound protection on the bets.

### Joint portfolio
Joint Kelly across the 4 team and 5 player bets on shared sims: total 4.90% (team 2.01%, player 2.89%). Team stakes are essentially unchanged from the team-only solution (Toronto 0.82%, Chicago 0.61%, Minnesota 0.58%). The Dashboard, `Tier1_Card` (team block at row 8, player block at row 41) and `Exposure` (joint summary, correlation matrix, live team vs player totals, cap check) now show all nine.

## 3. Independent verification (`src/verify/g6_independent.py`, imports no model code)
| Check | Result |
|---|---|
| De-vig re-derived by bisection for **all 9 Tier 1 market groups** | max difference from the pricing tables 3.3e-15 |
| De-vig (Shin, power, multiplicative) for **10 random market groups** (seed 2026), all rows | max difference 4.4e-14; each group sums to 1 |
| EV and shrunk EV (0.75) for all 9 rows | exact match to the engine and Excel |
| Joint Kelly re-solved with an independent solver (Newton exponential tilt + projected gradient on the saved outcome matrix) | max stake difference 4.6e-7; total 4.9000% vs 4.9000% |
| Team model probabilities recomputed straight from the sims | 0 difference (4 of 4) |
| Excel cached values (Tier1_Card) vs engine and own derivation | 9 of 9 rows matched; fair diff ≤2e-10 |
| Title / conference / division / playoffs / top-6 vs an independent stripped-down sim (no availability, tank or Cup; mean-matching off in the comparison, as the independent sim has none) | max title diff 0.15pp (OKC +0.10pp), conference 0.26pp, playoffs 0.33pp, division 0.28pp, mean wins 0.14 |
| Lottery sim vs the 3-2-1 rules (37 balls, 16 draws) | pick-1 error 0.09pp, pick-2 0.06pp vs exact; published 5.4/8.1/2.7% reproduced (5.40/8.12/2.73); floor violations 0; UTA/WAS restrictions hold |

The comparison disagreed by 2pp on OKC before I turned calibration off in the stripped engine, because the production engine mean-matches ratings and the independent check does not.

## 4. Six-bug workbook audit (`python -m src.workbook.audit`)
| # | Check | Finding |
|---|---|---|
| 1 | Hardcodes in formulas | 2 structural literals only: `30` (team count, Assumptions!B48) and `9` (a Bet_Card column index in 17 Dashboard cells). No numeric constants in pricing formulas |
| 2 | Inconsistent dragged formulas | The flagged columns are block-structured (team vs player sections, section headers, spill cells); no stray overrides found |
| 3 | Circular references | None |
| 4 | External links | None |
| 5 | Sign conventions | EV = p·dec − 1 matches all 236 M_Players rows to 1e-9; 0 negative stakes (team or player); Kelly floored at 0 |
| 6 | Summary tabs linked | Dashboard, Exposure live rows, Tier1_Card and Bet_Card are formulas referencing source tabs (the sim-status cell uses a defined name). Exposure rows 8-13 and the M_Sims / M_Players probabilities and stakes are documented engine outputs |

Also: Arial 10 everywhere (the Excel-spilled `Tier1_Card` player block is now formatted), no merged cells, gridlines off.

## 5. Top model-vs-market disagreements (wins vs book line) and what the data shows
| Team | Book | Model | Gap | What the model inputs show |
|---|---|---|---|---|
| MIA | 46.5 | 38.0 | −8.5 | Continuity 0.48; Powell, Ware, Herro and Jaquez gone; Giannis projected 53 games; 16% of minutes have no DARKO |
| BKN | 24.5 | 32.3 | +7.8 | Randle and Ellis arrive, Claxton leaves; prior SRS −9.7 vs projected −4.0 (mean reversion) |
| SAS | 59.5 | 54.0 | −6.8 | Prior SRS 8.3 vs projected 5.3 (regression plus the compression the model shows vs the market); Wembanyama 60 projected games |
| NYK | 52.5 | 43.9 | −6.6 | Mitchell Robinson (+3.5 BPM, 1,175 min) gone; arrivals Brown, Agbaji and Drummond rate negative |
| MEM | 28.5 | 36.5 | +6.4 | Continuity 0.60; rookie Boozer (+0.8); Jackson Jr., Aldama, Caldwell-Pope and Landale gone |
| WAS | 35.5 | 27.8 | −6.3 | Young and Davis projected 50 games each; most of the top 8 rate between −0.2 and −3.3 |
| GSW | 39.5 | 43.8 | +5.8 | Departures Spencer (−2.3 BPM) and Post (−1.1) were negative contributors; Curry 52 games, Porzingis 44 |
| PHI | 50.5 | 44.4 | −5.6 | Continuity 0.43; Embiid projected 49 games; arrivals Brown, LeBron, Caldwell-Pope |
| UTA | 37.5 | 33.3 | −5.5 | Prior SRS −8.1 vs projected −3.2; rookie Peterson rates −1.9; Cody Williams and Clayton (both very negative) gone |
| POR | 42.5 | 45.6 | +4.3 | Avdija +2.3, Clingan +2.0, Holiday +0.7; Morant projected 52 games |

None of these drivers is externally verified, which is why wins bets stay in Tier 2 unless the named-driver test passes.

## 6. Known weaknesses
1. **No market benchmark.** The backtest shows the team model beats naive baselines (RMSE 8.92 first-roster vs 10.2) but nothing shows it beats the book. Model-vs-book wins RMSE is 4.2, with a compression slope of −0.24 [−0.34, −0.13].
2. **CIs cover parameter uncertainty only,** not model misspecification. Bets are staked at model weight 0.25, and nothing here prices model error.
3. **Player Tier 1 rests on availability-heavy projections** (Sabonis 53, Haliburton 52 projected games) and on a one-parameter sharpening fit on about 48 leader outcomes.
4. **Award models** have 12-13 training winners each, and the candidate pools start in 2014. MVP/DPOY/ROY are not sharpened. Wembanyama (60 projected games, about 49% to reach 65) is modelled far below the book on MVP and DPOY; the book may know something the model does not.
5. **Driver quality.** The named-driver rule is mechanical (Chicago/Dillingham is a bench departure; Toronto/Kawhi is the clearest).
6. **PLAYOFFS = 16-team field** (confirmed by you from implied sums) and **PLAYIN = finishes 7-10**: confirm both with the book. They decide bets #2 and #3.
7. **Rule edge cases:** the leader qualification totals path (e.g. 100 blocks) and the 65-game/20-minute award rule are my reading of NBA.com; 3PM uses 58 games only.
8. **Longshot edges** (EV +300-400% on 100:1 shots) sit in Tier 2, unstaked; do not read them as value.
9. **Stale inputs:** recheck pick ownership and injuries Oct 18-19, before the lock. Excel's native PDF export needs a printer driver, so the PDF is rendered from the workbook's values with matplotlib.

## 7. Everything imputed or backfilled
- **IMPUTED_20C_LADDER (4, used to de-vig only, never on the card):** WINS Milwaukee UNDER 25.5 (+100), Indiana UNDER 44.5 (+100), New Orleans UNDER 28.5 (+100), Lakers UNDER 45.5 (+120).
- **BACKFILL_PDF1 (8, from the 12:06 sheet):** CONF_WEST Memphis YES +25000; PLAYIN_WEST Memphis YES +325; WINS Miami OVER 46.5 +100; DPOY Walker Kessler +8000; ROY Ebuka Okorie +15000; COY Nick Nurse +1000; **LDR_RPG Domantas Sabonis +900 (a Tier 1 bet)**; LDR_TPG Trae Young +9100.
- **BACKFILL_PDF_TEXT (3):** WINS Philadelphia OVER 50.5 +100, Atlanta OVER 44.5 +105, Denver OVER 49.5 +120.
- **Model assumptions, not data:** DARKO blend weight 0.5 (documented rule, never backtested); sigma_team 3.5 (CV); tank κ 0.28 (CI includes 0); playoff λ 0.58; availability concentration 3.7; leader sharpening γ 1.5 (CV); rookie minutes SD 0.32; BPM/DBPM error SDs from a baseline model.

## 8. Files
Code: `src/players/{variance_check,sharpen_cv,leader_backtest}.py`, `src/pricing/{joint,price_players}.py`, `src/verify/g6_independent.py`, `src/workbook/export_pdf.py`. Outputs: `data/clean/{g4_leader_sharpen,g4_variance_check,joint_summary,joint_corr,joint_stakes,g6_verification,workbook_audit}.*`.
