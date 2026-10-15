# G5 Report (revised) — Workbook, team markets and Bet Card (2026-10-15)

**Status: complete, awaiting "approve G5".** This version replaces the first G5 report. It adds the miscalibration diagnosis, the simulator fix, and every filter you asked for. G4 (player markets) is still deferred; its tabs are placeholders with no model probabilities and no bets.

**Workbook:** `output/NBA_Futures_Model_v1_20261015_MS.xlsx` (22 tabs, one prior version kept). Rebuild with `run.py price`, then `run.py build`. Diagnostics: `python -m src.pricing.diagnostics | compression | drivers`.

## 0. Headline
- **The first 89-bet Bet Card was too optimistic, and part of the reason was a bug-like inconsistency in the simulator.** The sim's expected wins were more compressed than the calibrated projection it was built from (OKC 56.5 in the sim vs 59.7 in the projection). Fixing that and applying your filters cuts the card to **52 bets**; the first card had 89.
- **The model is still more compressed than the market.** The 30-team model-vs-market RMSE is **4.22 wins** (4.44 before the fix); the spread of team means is 8.6 wins against 10.3 for the market. The model is still treated as miscalibrated relative to the market, which is why the shrink is 0.5 and the compression rule applies. I cannot show the model beats the market (no free closing-line archive), so please treat the card as a list of model opinions to audit, not as proven edges.
- PLAYOFFS is priced as the 16-team playoff field (top-8, including via play-in), per your confirmation from the implied sums (my own check: 14.9 over 27 listed teams vs 14.3 for the bracket and 17.9 for top-10). Flagged "confirm with book" on the sheet, in the rule text and on Assumptions.

## 1. Root cause and fix
- **Diagnosis:** the book's win totals have a team-to-team SD of 10.3 and the model's sim means 7.6. In the 2023-24 to 2025-26 calibration the sim's top bin was 56.0 vs 59.8 actual and its bottom bin 27.8 vs 20.9 actual. The calibrated linear projection (wins = 41 + 2.44 × SRS) did not show that compression in the eight-season backtest (55.9 vs 55.1 at the top, 27.4 vs 27.6 at the bottom).
- **Cause:** Φ saturation, σ_team concavity and availability draws compress the sim's expected wins relative to the projection.
- **Fix:** `src/sim/meanmatch.py` adjusts the simulator's team ratings until its expected wins equal the calibrated projection (max error 0.08 wins; the matched sim agrees with the projection to RMSE 0.10). The ratings spread widens by 14%. The same matching is applied to every robustness scenario, every parameter draw and every historical calibration season.
- **σ_team refit with the matched sim** (leave-one-season-out CV over six full seasons, availability draws on; `sigma_team_cv_meanmatched.json`): optimum **3.5 SRS points** (folds chose 3.5 four times, 3.75 once, 3.0 once); simulated SD ÷ realized RMSE = **1.016** (8.82 vs 8.68); variance ratio **0.97** against a ceiling band of 0.85–1.17 (p = 0.62). Production predictive SD is **8.77 wins**, within ±5% of the backtest's 8.92. Out-of-sample reliability for P(over projection ±5/±10) is calibrated (bins 0.867 vs 0.874, 0.711 vs 0.718, 0.291 vs 0.269, 0.132 vs 0.146; Brier equals the climatological reference to within 0.002). P(top-6 seed) Brier is 0.165 vs 0.240; the 0.10–0.25 bin is low (predicted 0.18, observed 0.29, n = 28).
- **Bottom-8 carryover (unchanged from the G3 addendum):** UTA 32.6 → 33.3, BKN 30.8 → 31.3, WAS 27.4 → 27.8, DAL 33.8 → 34.0, IND 42.0 → 42.1, NOP 31.9 → 32.0, MEM 36.4 → 36.4, SAC 24.1 → 23.9 (before → after using pre-deadline roles).

## 2. Compression test (post-fix)
- Regressing (model − market fair median) on the market median across 30 teams: slope **−0.24, 95% CI [−0.34, −0.13]** (80% CI [−0.31, −0.17]). Before the fix it was −0.32 [−0.41, −0.23]. Still significantly negative.
- **Is the projection over-regressed against realized outcomes?** No. In the 240-team-season backtest the residual-on-predicted slope is **+0.015** (season-cluster 80% CI [−0.04, +0.07]; team bootstrap [−0.06, +0.09]). A leave-one-season-out re-fit of the slope gives held-out RMSE 8.94 vs 8.92 unchanged, so there is nothing to fix out-of-sample and I did not change the SRS→wins slope or the prior weight.
- **So the rule applies:** no wins unders on the market's top 5 and no wins overs on its bottom 5, unless a specific verifiable player or roster fact is on file (`params/verified_drivers.csv`, empty). It blocks 7 otherwise-qualifying bets: NYK under 52.5, PHI under 50.5, SAS under 59.5, MIL over 25.5, BKN over 24.5, NOP over 28.5, SAC over 20.5. NYK's Robinson loss is verified but explains about 1.4 SRS points, not the 6.6-win gap, so it does not clear the bar.

## 3. Model vs market wins, all 30 teams
Market fair median = book line shifted by the de-vigged P(over) (juice removed) using the model's predictive SD of 8.5 wins.

| Team | Line | Market median | Model mean | Model − market |
|---|---|---|---|---|
| MIA | 46.5 | 46.0 | 37.5 | −8.5 |
| SAS | 59.5 | 60.7 | 53.9 | −6.8 |
| NYK | 52.5 | 50.5 | 43.9 | −6.6 |
| WAS | 35.5 | 34.1 | 27.8 | −6.3 |
| PHI | 50.5 | 50.0 | 44.4 | −5.6 |
| UTA | 37.5 | 38.7 | 33.3 | −5.5 |
| MIN | 47.5 | 48.0 | 44.4 | −3.6 |
| OKC | 61.5 | 62.2 | 58.7 | −3.5 |
| ATL | 44.5 | 43.8 | 40.6 | −3.2 |
| IND | 44.5 | 45.0 | 42.0 | −3.0 |
| CLE | 47.5 | 48.2 | 46.6 | −1.6 |
| DET | 49.5 | 48.3 | 47.2 | −1.1 |
| LAL | 45.5 | 46.9 | 46.1 | −0.8 |
| DEN | 49.5 | 48.1 | 47.4 | −0.7 |
| ORL | 43.5 | 44.5 | 43.9 | −0.6 |
| PHX | 39.5 | 39.7 | 39.6 | −0.2 |
| DAL | 34.5 | 34.3 | 34.0 | −0.2 |
| BOS | 51.5 | 50.5 | 51.1 | +0.6 |
| CHA | 39.5 | 36.9 | 37.7 | +0.8 |
| CHI | 28.5 | 30.3 | 32.1 | +1.8 |
| SAC | 20.5 | 21.7 | 24.0 | +2.3 |
| NOP | 28.5 | 29.0 | 31.9 | +2.9 |
| TOR | 45.5 | 47.1 | 50.1 | +2.9 |
| LAC | 29.5 | 27.5 | 30.9 | +3.4 |
| HOU | 47.5 | 49.7 | 53.6 | +3.9 |
| MIL | 25.5 | 26.0 | 29.9 | +3.9 |
| POR | 42.5 | 41.3 | 45.6 | +4.3 |
| GSW | 39.5 | 38.1 | 43.8 | +5.8 |
| MEM | 28.5 | 30.1 | 36.5 | +6.4 |
| BKN | 24.5 | 23.5 | 31.3 | +7.8 |

**Statistics:** RMSE 4.22; mean signed difference −0.36; MAE 3.48; correlation 0.915; slope of model on market 0.76; SD of team means 8.57 (model) vs 10.34 (market). The book's lines sum to 1,241 and the market medians to 1,240.8; the model sums to 1,230. The diagnosis threshold (RMSE above about 4) is met, so the model is treated as miscalibrated relative to the market.

## 4. Bet Card anatomy (final 52 bets, shrink 0.5)
- **Overall:** median EV +57.6%, median edge (model − fair) +12.5pp, median EV CI low +45%; total stake 25.0% of bankroll (the exposure cap). Portfolio P&L (the model's own world): expected return +23.4%, P(profit) 94.4%, 5th percentile −0.6%, 1st percentile −6.9%, worst −17.2%. At the shrunk probabilities the expected return is +10.3%.
- **By market** (count, % of bankroll staked): WINS 10 (11.3%); PLAYOFFS 10 (6.0%); PLAYIN 10 (4.4%); DIV 7 (2.3%); CONF 4 (0.3%); Cup groups 3 (under 0.1%); TITLE 5 (0.3%); CUP 3 (0.3%).
- **WINS over vs under:** 5 overs (3.5% staked, median EV 38%) and 5 unders (7.8%, median EV 41%). Not one-directional; overall the card is 37 YES, 5 NO, 5 OVER, 5 UNDER.
- **Favorites vs longshots** (favorite = fair ≥ 10%):
  - TITLE: 0 / 5 (all longshots).
  - CONF: 0 / 4. CUP: 0 / 3.
  - CUP groups: 2 favorites / 1 longshot (stakes under 0.1%).
  - DIV: 4 favorites (1.9% staked) / 3 longshots (0.4%).
  - 16 of the 52 bets have fair probability below 5%.
- **Why the card is still heavy on YES bets:** futures markets only offer YES prices, so a model that thinks the market is too low on many teams can only back them.

## 5. Filters, in order (waterfall)
| Step | Bets | What it does |
|---|---|---|
| Reference: first card (compressed sim means) | 89 | EV ≥ 3% and CI low > 0, PLAYOFFS blocked |
| Raw (matched means) | **75** | EV ≥ 3%, CI low > 0, not imputed, PLAYOFFS still blocked |
| Playoff fix | **91** | PLAYOFFS priced as the 16-team field (+16) |
| Zero-sum (means rescaled to 1,241) | **89** | −2 WINS: OKC under 61.5, CLE under 47.5 |
| Shrink 0.5 (edge at the shrunk probability) | **63** | −26, mostly TITLE (5), CONF (7), Cup (8), DIV (3), PLAYOFFS (3) |
| Robustness (κ 0 / 1.57, σ_team ±10%, bottom-10 teams) | **63** | −0 |
| Longshot control (fair < 5%) | **63** | −0 (the shrink already binds) |
| Low-continuity shrink 0.75 | **59** | −4: LAC over 29.5, PHI NO, MIL YES, CHI YES (PLAYOFFS) |
| Compression rule | **52** | −7 (see §2) |
| **Final** | **52** | At shrink 0.25 the same filters would leave 62 |

- **WINS bets by step:** 20 → 20 → 18 → 18 → 18 → 18 → 17 → **10**.
- **Zero-sum filter:** rescaling the model's means by +0.367 wins per team (1,241 vs 1,230) removes only two wins bets, both unders (OKC, CLE), the kind inflated lines inflate. The remaining 18 are not driven by inflation alone.
- **EV by fair-probability bucket** (all modelled selections, model EV before shrink; `qualification_waterfall.json`):

| Fair bucket | n | Median EV | 25th–75th pct |
|---|---|---|---|
| < 2% | 59 | −1.2% | −57% to +69% |
| 2–5% | 32 | +18.7% | −19% to +46% |
| 5–15% | 39 | +13.9% | −34% to +84% |
| 15–50% | 96 | −18.5% | −33% to +5% |
| > 50% | 64 | −7.8% | −24% to +9% |

  No bucket has a median above your 20% threshold (2–5% is closest at 18.7%), so no bucket was excluded. The wide spreads in the long-shot buckets show why the shrink does the work there.

## 6. Biggest 10 disagreements and their drivers
The market is more extreme than the model on both ends. For none of these do I have a verified fact that explains the whole gap; the table gives the drivers I can see in the data (`top_disagreements_drivers.csv`).

| Team | Gap | Drivers in the model | Info-gap / fact check |
|---|---|---|---|
| MIA −8.5 | model low | Giannis (rated +6.8) arrived but 5 of last year's top rotation left (Powell, Herro, Ware, Jaquez, Jakučionis ≈ 7,500 minutes), replaced by older low-rated veterans (Hardaway, Klay, Portis, Richards); continuity 0.48; Giannis projected 53 games | Roster moves after the June 3 DARKO snapshot; market likely credits the star effect more than the box prior |
| SAS −6.8 | model low | Prior SRS +8.3 → predicted +5.3 with continuity 0.76; only addition is T. Harris; no injuries listed | No roster fact; this is the model's general regression of an elite team |
| NYK −6.6 | model low | Robinson left as a free agent for BOS (July 1, verified, ESPN + bbref NYK page); bench replaced by Brown, Agbaji, Drummond; SRS +6.0 → +1.1 | Robinson alone explains about 1.4 SRS points; the rest is regression |
| WAS −6.3 | model low | #1 pick Dybantsa rated −1.8 (rookie model); Young and Davis projected 50 games each; prior SRS −11.6 | Rookie rating and availability are the swing factors |
| PHI −5.6 | model low | Continuity 0.43; LeBron (41), J. Brown, Simons, Love arrive; Embiid 49 games | Players moved after the DARKO snapshot; ages weigh on LeBron |
| UTA −5.5 | model low | Peterson (#2 pick) rated −1.9; JJJ arrived in February; Markkanen 58 games | Post-snapshot role changes |
| BKN +7.8 | model high | Prior SRS −9.7 regresses to −4.0; Randle and Ellis added; Claxton, Z. Williams, J. Wilson gone | Market (23.5) may expect a tank; the model cuts tank incentive for BKN because HOU holds the swap right on BKN's pick |
| MEM +6.4 | model high | Lost JJJ, KCP, Aldama, Landale (≈4,700 minutes) but regresses SRS −5.8 → −1.9 | Largest suspected over-regression of a depleted roster; no verified offsetting fact |
| GSW +5.8 | model high | Curry 52 games, Porziņģis 44, Butler out until Jan 2 (ACL, already in the model, 28 games) | Age effects (Curry 38, Horford 40, Green 36) may be understated by the broad aging curve |
| POR +4.3 | model high | Morant arrived (rated +0.8, 52 games); Holiday 36; no-history minutes 0% | Role in the new rotation untested |

None of these is an injury since the DARKO snapshot that is missing from the model: all 23 ESPN "Out" players, including Butler, DiVincenzo, Beal, Ingram and Hukporti, are applied through their return dates.

## 7. Roster audit (your item 3)
- **ESPN, re-pulled today vs the model's rosters:** 627 vs 627 players, **0 differences** in team or status (`rosters_espn_refresh_20261015.csv`).
- **Second source, bbref 2027 team pages (30 teams):** 595 players on both lists, **0 with a different team**. ESPN-only: about 30 fringe players (two-way, camp, 10-day). bbref-only: 18 fringe players plus **Batum (LAC)** and Hayes (SAC), who played rotation minutes last year and are absent from ESPN; their absence is immaterial to those teams' totals. Alex Sarr / Bub Carrington / Nic Claxton appear as differences only because of name variants (`roster_audit_diff.csv`).
- **Mitchell Robinson:** left the Knicks for BOS as a free agent (3 years, $47.4M, announced July 1, 2026; AP / ESPN). It is a signing, not a trade. The model's NYK roster omits him and BOS includes him.

## 8. Workbook (Excel 365, recalculated through xlwings)
- **Errors:** 0 error cells; **Checks: 0 failing** (3 informational: 4 imputed rows, 11 backfilled rows, 2 of 30 WINS lines differ by more than 2pp between the live analytic layer and the sim).
- **Excel vs Python parity:** de-vig 2e-16 / 3e-10 / 3e-10 (Multiplicative / Power / Shin), team wins 2e-14, qualifying bets **52 in both**.
- **Qualification formulas are live** for min EV, shrink, zero-sum, longshot (fair < `longshot_threshold`) and continuity (`low_continuity_threshold`, `low_continuity_shrink`). Engine-supplied flags: edge CIs, robustness, portfolio Kelly, and the static bucket / compression block. Changing the shrink or the thresholds re-filters the card live; the portfolio Kelly stakes need `run.py price`.
- **Audit:** no circular references, no external links, 0 non-Arial cells, 0 merged cells; remaining hard-coded numbers are structural. New Assumptions: zero-sum filter, longshot and continuity thresholds, PLAYOFFS definition and confirmation flag, shrink 0.5.
- **Fixed during this pass:** the portfolio outcome for PLAYOFFS used top-10 while pricing used the bracket definition, which distorted the first portfolio stakes; both now use the bracket.

## 9. Limitations and next steps
- **No market benchmark.** The edge CI covers parameter uncertainty only. The strongest evidence of miscalibration is the compression gap in §2–3.
- The tightened rule (the shrunk edge must clear 3% and the CI low must be positive) goes beyond the spec's "shrink for staking only"; it follows your instruction after the diagnosis. Switch back by setting the shrink to 0.25; only the staking probability then changes.
- The PLAYOFFS definition still needs confirmation with the book.
- Excel's PDF export needs a printer driver; the Dashboard + Bet_Card PDF (G6) will use another route if none is available.
- Top-10 disagreements by driver (§6) should be examined with a human before real money; that is the G6 audit.

Awaiting "approve G5".
