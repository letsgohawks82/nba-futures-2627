# G8 final report: consensus v2, market-reference gate, minutes fix (2026-10-16)

**Status: built and verified; not staked. Five bets pass the rules but are not on your expected list, so I have put them on HOLD (excluded from Tier 1, still on the Bet Card as Tier 2) until you decide.** Everything else follows your spec. Workbook `output/NBA_Futures_Model_v1_20261015_MS.xlsx` (25 tabs: new `Raw_MarketRef`, rebuilt `Raw_Consensus`), PDF `output/NBA_Futures_Dashboard_BetCard_20261016.pdf`. Excel: 0 error cells, 0 failing checks.

## 1. The card the rules produce (4 bets, 2.63% of bankroll, cap 10%)
| # | Selection | Book | Min price | Model | Blended | Market fair | EV | Stake | Consensus residuals (wins) and basis |
|---|---|---|---|---|---|---|---|---|---|
| 1 | WINS Washington UNDER 35.5 | −140 | −164 | 78.9% | n/a (no exchange) | 56.4% | +35% | 0.75% | Median 34.0. Roster-aware: ours −6.7, PredictionEngine −7.1 (both ≥ 4, so base stake). Results-based ignored (Young 15 games and Davis changed teams / 20 games in 2025-26; continuity 0.62): Opta −8.4, Massey −8.2. Display: ESPN −1.7, TeamRankings +0.4, Bleacher Report +4.5 |
| 2 | WINS Utah UNDER 37.5 | +115 | −101 | 67.7% | n/a | 44.5% | +46% | 0.75% | Median 38.7. Ours −5.5, PredictionEngine −5.2 (both ≥ 4). Results-based ignored (continuity 0.69 < 0.70): Opta −7.3, Massey −7.7. Display: ESPN −3.1, TR −0.6, BR −0.3 |
| 3 | WINS Portland OVER 42.5 | +115 | +109 | 58.2% | n/a | 44.5% | +25% | 0.50% | Median 41.3. Ours +3.3 (below 4, so reduced stake), PredictionEngine +5.4. Results-based ignored (continuity 0.69): Opta +2.2, Massey +1.2. Display: ESPN +0.5, TR +0.2, BR +1.1. EV at shrink 0.75 is +3.1%, barely above the 3% bar |
| 4 | PLAYOFFS Minnesota NO | +550 | +472 | 32.6% | n/a | 12.5% | +112% | 0.63% | Driver: Julius Randle gone (2,610 min at +1.5 BPM, −1.1 SRS). Locks Wed 10/21 6:40 PM CST |

Locks (CST): WAS Wed 10/21 6:10 PM, UTA 7:10 PM, POR 9:10 PM, MIN 6:40 PM. All stakes are joint-Kelly caps (joint Kelly with no caps would be 5.2% in total). Portfolio in the model world: expected return +1.4% of bankroll (+0.2% at the shrunk probabilities), P(profit) 75%, 5th percentile −1.4%, worst −2.6%. Correlations (shared sims) are all within ±0.08: POR/MIN +0.08, UTA/MIN −0.07, UTA/POR +0.04, the rest near 0.

## 2. Where this differs from your expected list (decisions for you)
| Your expectation | What I got | Why |
|---|---|---|
| UTA U 0.75%, min −102 | UTA U 0.75%, min −101 | Matches. |
| WAS U 0.5%, min −169 | WAS U **0.75%**, min −164 | Both roster-aware residuals (−6.7, −7.1) are above 4, so it earns the base stake. It survives the minutes fix easily: our WAS projection rose only from 27.9 to 28.8 wins, 5 below the market median. |
| POR O 0.5%, +102 | POR O 0.5%, +109 | Matches the stake; min moved with the new sims. |
| MIN NO 0.57%, +479 | MIN NO 0.63%, +472 | Same bet; re-solved joint stake, and the sims changed slightly. |
| LaMelo 3PM 0.45%, +904 | **Drops out** | The edge is gone: model 7.1% vs book fair 7.1% (it was 18.4%). LaMelo's projected minutes fell from 29.8 to 26.7 because the corrected allocation protects only the top 3 per team. This bet is fragile: with top-5 protection it was alive, with top-3 it is not. |
| Lendeborg ROY, +1250, 0.35% | **Does not qualify** | He is no longer a 0: model 3.7% (27 mpg starter assumption from the news). The book's board price is +1500 and fair is 5.0%, so the model is *below* the book. The exchanges (10.1%) are above the book, so he passes the blended leg (+21% EV) but fails the model leg. |
| Dybantsa drops | Drops | Exchange gate: blended EV −8% (book 17.7%, exchanges 19.0%). His model probability is still **46%** (it rose from 43%), so the missing candidates were not what was inflating him; the ROY model's inputs (pick 1, about 30 mpg, 14.9 ppg) are. |
| Sabonis drops | Dropped | News exclusion (still modelled at 25% to lead RPG). |
| MIA U drops | **Passes the rule as written** (HOLD) | Roster-aware residuals −4.8 (ours) and −5.6 (PredictionEngine). Results-based sources would not have counted for MIA (Giannis changed teams; continuity 0.50), so nothing removes it. |
| IND U drops | **Passes the consensus rule** (ours −3.1, PredictionEngine −6.7), but cannot be bet: the 44.5 under price is imputed (20c ladder, never allowed on the card). |
| CHA O drops | Drops | Our residual is only +1.0 (PredictionEngine +8.2). |
| Edwards MVP, Acuff ROY, NYK title | Do not qualify | Edwards (model 1.6% vs fair 4.2%) and Acuff (model 2.2% vs fair 6.3%) pass the blended leg but fail the model leg; NYK title is negative EV (model 3.9% vs fair 8.2%). Edwards MVP would also contradict the MIN NO thesis. |

**New candidates that the unchanged rules now pass after the minutes fix (all on HOLD):** PLAYOFFS Miami NO (+235, model 50.2% vs fair 27.4%, EV at 0.75 shrink +11%), PLAYOFFS Indiana NO (+180, 47.0% vs 33.5%, +3.2%), Rudy Gobert RPG (+990, 15.6% vs 7.9%, no exchange price), and MIA U (above). **CHI PLAYOFFS YES (+1150) is excluded** for the same weak driver (Dillingham) you cut on the play-in. If you want any of these live, tell me and I will stake them. MIA U and MIA NO rest on the same Giannis-availability view and would be strongly correlated.

## 3. Consensus rule v2: per-source regressions on the market fair median (30 teams)
| Source | Tag | Slope | Residual SD (wins) | R² |
|---|---|---|---|---|
| Ours | STAT_MODEL, roster-aware | 0.755 | 2.96 | 0.88 |
| PredictionEngine | STAT_MODEL, roster-aware | 0.732 | 4.00 | 0.79 |
| Opta TRACR | STAT_MODEL, results-based | 0.655 | 3.61 | 0.79 |
| Massey (80→82) | STAT_MODEL, results-based | 0.537 | 4.11 | 0.65 |
| ESPN | MARKET_INFORMED, display | 0.949 | 1.91 | 0.97 |
| TeamRankings | MARKET_INFORMED, display | 0.972 | 0.69 | 0.995 |
| Bleacher Report | EXPERT, display | 1.029 | 3.19 | 0.92 |

Rule as built: a WINS bet qualifies only when both roster-aware residuals point the bet's way, each ≥ 2.5 wins. Results-based sources (Opta, Massey) can only **veto**: when they count (continuity ≥ 0.70 and no top-3-minutes player who changed teams or played under 41 games in 2025-26) and both point the other way by ≥ 2.5, the bet fails. Your text said they "count" without saying whether they confirm or veto, so this is my reading; it never changed an outcome (they were ignored for all four bets). Stake is 0.75% when both roster-aware residuals are ≥ 4.0, otherwise 0.5% (and ×0.7 below 0.55 continuity). Massey's scaled values are as you supplied (they sum to 1,230.3). The residual SD for ours is 2.96 wins and the Massey/Opta slopes (0.54, 0.66) confirm they are compressed relative to the market.

## 4. Market-reference layer (`Raw_MarketRef`)
Exchange markets are normalised to sum to 1 over the listed names (Kalshi and Polymarket sums: ROY 107 and 99; TITLE 94 and 85.2; MVP 108; CONF_WEST 114.7; DPOY 81). Exchange average = the mean of the exchanges listing a name; the GM survey is displayed only. Prices below 10% are noted for longshot bias, not adjusted. Gate: EV > 0 at the blended probability (book fair + exchange average) / 2 as well as at the model probability, in `M_Players` and on the engine. Ratio flags (model vs exchange average more than 2× apart) are in the comparison table. The big ones: MVP Wembanyama model 8.4% vs exchanges 30.6%; DPOY Wembanyama 41.0% vs 90.1% (normalised over two names; Kalshi lists 73%); ROY Dybantsa 46.3% vs 19.0%, Wilson 5.3% vs 19.5%, Acuff 2.2% vs 9.7%, Lendeborg 3.7% vs 10.1%; SGA MVP 30.7% vs 14.8%. Our model is far below the markets on Wembanyama's awards (60 projected games and the 65-game rule) and far above on Dybantsa, which is the main reason to keep these unstaked.

## 5. Before and after the bug fixes
**Candidate pools (D.1).** The name map was not the problem: every book-listed player was in the pool. The zeros came from the award eligibility gate, which required *projected mean* minutes of at least 20 (all the rookies sit at 13-20 mpg). It now uses simulated minutes (rookie SD 0.32, veterans 0.12) with the 65-game rule, so rookies have a real chance. Result: Acuff 2.2%, Lendeborg 3.7%, Wagler 3.9% and the other named rookies now have non-zero ROY probabilities. **Still at 0 after the fix, with reasons** (the model projects them as bench players who cannot lead): Edey RPG (16.7 mpg, 49 games, 6.4 RPG), Kel'el Ware RPG (15.7 mpg in a deep MIL rotation, 5.9 RPG), Day'Ron Sharpe RPG (15.9 mpg, 5.7), Dort SPG (21.1 mpg, 0.7), Davion Mitchell SPG (19.5 mpg, 0.6), Maluach BPG (8.3 mpg, 0.5), Ty Jerome 3PM (15.5 mpg, 49 games, 1.4). Diabaté, Robinson, Sheppard and Klay Thompson are no longer at 0. Clingan RPG moved from 0.5% to 1.5% (23.9 mpg; his 15 rebounds per 36 minutes still give 9.9 RPG, short of the 12+ leaders need). These are model judgements, not unmatched names.

**Team-layer star minutes (D.2).** It had **not** reached the team layer: the G6 fix was player-market only. The team layer (`allocate_minutes`) normalised everyone's minutes proportionally to team minutes, which cut stars about 6-12% (Giannis showed 26-27 mpg in `Raw_Players`; now 32.5). I tested allocations on 2022-26 rosters (`src/ratings/minutes_backtest.py`): bias for the top 5 by minutes −1.82 mpg (normalised) vs −0.39 mpg with the top 3 protected and calibrated (actual mpg ≈ 6.64 + 0.834 × mpg_hat), overall minutes RMSE 5.45 → 5.39 (top 5 protected: 5.48; top 10: 6.12), so I protect the top 3. The team layer was refit (coefficients moved; SRS residual SD 3.213 → 3.248 and wins residual SD 8.04 → 8.07, a slight in-sample cost) and all sims re-run. Not re-fit: σ_team (3.5). The Lendeborg preseason-starter news is applied as a 27 mpg override (an assumption). Projected wins, before → after (30 teams; delta):

| Team | Before | After | Δ | Team | Before | After | Δ |
|---|---|---|---|---|---|---|---|
| MIA | 37.4 | 39.7 | +2.3 | LAC | 31.2 | 31.4 | +0.3 |
| NYK | 43.9 | 45.5 | +1.6 | CLE | 46.7 | 47.0 | +0.3 |
| DEN | 47.5 | 49.2 | +1.6 | UTA | 33.4 | 33.6 | +0.2 |
| PHI | 44.7 | 45.6 | +0.9 | DET | 47.2 | 47.4 | +0.1 |
| WAS | 27.9 | 28.8 | +0.9 | TOR | 48.3 | 48.4 | +0.1 |
| ATL | 40.9 | 41.6 | +0.7 | SAC | 24.0 | 23.9 | −0.1 |
| CHA | 37.9 | 38.6 | +0.7 | ORL | 44.1 | 44.0 | −0.1 |
| NOP | 32.1 | 32.6 | +0.4 | OKC | 58.8 | 58.7 | −0.1 |
| CHI | 32.1 | 32.4 | +0.4 | PHX | 39.6 | 39.4 | −0.3 |
| MIL | 30.2 | 29.9 | −0.3 | DAL | 34.1 | 33.7 | −0.4 |
| MIN | 44.5 | 43.9 | −0.6 | LAL | 46.1 | 45.5 | −0.7 |
| BOS | 51.1 | 50.5 | −0.7 | GSW | 44.0 | 43.4 | −0.7 |
| BKN | 31.4 | 30.7 | −0.7 | HOU | 52.7 | 51.8 | −0.9 |
| SAS | 54.0 | 52.9 | −1.1 | MEM | 36.5 | 35.3 | −1.2 |
| POR | 45.6 | 44.2 | −1.4 | IND | 42.1 | 40.7 | −1.4 |

Of the teams you named: WAS +0.9, MIA +2.3, MIN −0.6, IND −1.4, POR −1.4, UTA +0.2. Leader sanity: unchanged vs G6 (sim top-5 values within about 0-7% of 2022-26).

## 6. News applied
Sabonis: RPG bet on no-bet (override; still modelled). Lendeborg: 27 mpg override. Wizards: Young and Davis are healthy but their projected availability (50 games) comes from their injury histories and is unchanged; the 17-minute preseason games and Dybantsa's 23 minutes are not used (too small a sample). Curry: knee management is noted; the model already projects him at 52 games (63%), and he is now the 3PM-leader favourite at 22% (book 50%), so I made no change.

## 7. Close-out checks
- Checks tab 0 failing; six-bug audit: 2 structural literals only, no circulars or external links, signs and summary links clean, Arial 10 and no merged cells.
- Independent verifier on all 4 Tier 1 rows (and de-vig on 10 random groups): de-vig exact to 4e-14; EV and shrunk EV exact; **consensus re-derived from the raw odds and the raw consensus file (own Shin de-vig and OLS residuals) matches Excel PASS for all three WINS bets and reproduces the slopes and residual SDs above**; stakes re-solved with an independent solver including the caps: within 3e-8 (uncapped within 2e-6); min prices within 0.05 of Excel.
- PDF rebuilt.

## 8. Weaknesses to keep in view
- One external roster-aware model (PredictionEngine) gates every WINS bet; all three are cases where our projection and PredictionEngine agree and Opta/Massey would agree too, but those two are results-based and compressed.
- Player-market minutes remain the most fragile input (LaMelo flips between top-3 and top-5 protection; Gobert and Sabonis likewise).
- `run.py prelock` should be re-run 10/18-19; it now also re-prices the consensus and exchange layers (exchange prices and the consensus file are manual inputs and are not re-pulled).
