# G7 final report: pre-lock build (2026-10-15)

**Final card: 8 Tier 1 bets, 3.90% of bankroll** (cap 10%). Workbook `output/NBA_Futures_Model_v1_20261015_MS.xlsx` (24 tabs; new `Raw_Consensus`), PDF `output/NBA_Futures_Dashboard_BetCard_20261015.pdf` (4 pages). Excel recalculated with 0 error cells and 0 failing checks. This supersedes the cards in `G6_final.md` and `G6_update.md`.

## 1. The 8-bet card
Min price = the American odds at which EV at shrink 0.75 is zero (live formula on `Tier1_Card`). External values are the raw projected wins; the consensus basis is each source's bias-adjusted gap (wins) against the book's fair median.

| # | Selection | Book | Min price | Model | Market fair | EV | Stake | Lock (CST) | External consensus / driver |
|---|---|---|---|---|---|---|---|---|---|
| 1 | PLAYOFFS Minnesota NO | +550 | +478 | 31.8% | 12.5% | +107% | 0.58% | Wed 10/21 6:40 PM | Driver: Julius Randle gone (2,610 min at +1.5 BPM, −1.1 SRS) |
| 2 | ROY AJ Dybantsa | +400 | +314 | 43.4% | 17.7% | +117% | 0.53% | Tue 10/20 2:10 PM | Pick 1, age 19: 30 mpg × 17.9 pts/36 = 14.9 ppg, 80 games; last five ROY winners averaged 18.5 ppg in 31.8 mpg. Stake is the joint-Kelly stake (1.07%) × 0.5 |
| 3 | RPG leader Domantas Sabonis | +900 | +751 | 21.1% | 8.6% | +111% | 0.48% | Tue 10/20 2:10 PM | 12.8 RPG in 33 mpg, 53 projected games; rival Jokic 12.4 (28%). **Book price is a backfill (12:06 sheet); confirm** |
| 4 | 3PM leader LaMelo Ball | +1100 | +904 | 18.4% | 7.1% | +121% | 0.45% | Tue 10/20 2:10 PM | 3.7 3PM in 30 mpg over 62 games; rival Curry 4.4 (model 35% vs book 50%) |
| 5 | WINS Washington UNDER 35.5 | −140 | −170 | 82.3% | 56.4% | +41% | 0.50% | Wed 10/21 6:10 PM | Market median 34.0 (bias +2.2). Our gap −8.5 and PredictionEngine −7.8 (projection 28.5). Bleacher Report 38 (gap +1.7, display only) |
| 6 | WINS Utah UNDER 37.5 | +115 | −103 | 69.0% | 44.5% | +48% | 0.50% | Wed 10/21 7:10 PM | Market median 38.7 (bias +0.7). Ours −6.2, PredictionEngine −5.6 (33.9). Bleacher Report 38 (−1.5, display) |
| 7 | WINS Portland OVER 42.5 | +115 | +102 | 64.0% | 44.5% | +38% | 0.50% | Wed 10/21 9:10 PM | Market median 41.3 (bias −0.1). Ours +4.3, PredictionEngine +5.1 (46.3). Bleacher Report 42 (+0.8, display) |
| 8 | WINS Miami UNDER 46.5 | −120 | −150 | 83.3% | 52.3% | +53% | 0.35% | Wed 10/21 6:40 PM | Market median 46.0 (bias −1.6). Ours −7.1, PredictionEngine −5.6 (38.8). Bleacher Report 49 (+4.6, display; it disagrees). Stake ×0.7 for continuity 0.48 |

All four WINS bets sit at their caps (0.5%; MIA 0.35% = 0.5% × `A_lowcont_mult` 0.7).

**Joint vs capped stakes (fraction of bankroll).** The joint Kelly with no caps or multipliers would stake WAS 2.42%, MIA 2.62%, UTA 1.67%, POR 0.94%, MIN 0.51%, Dybantsa 1.07%, Sabonis 0.39%, LaMelo 0.38% (total 10.0%, at the cap). With the WINS caps and Dybantsa fixed at half, the others are re-solved to MIN 0.58%, Sabonis 0.48%, LaMelo 0.45% and the total falls to 3.90%.

**Portfolio.** Model-world expected return +2.64% of bankroll (+0.51% at the shrunk probabilities), P(profit) 71.2%, 5th percentile −2.2%, worst case −3.9%. The unconstrained joint solution would return +5.8%.

**8×8 correlation of bet outcomes (shared sims).** WAS and MIA are essentially independent (−0.02) despite the shared division-adjacent structure, because their outcomes depend on their own win totals. Non-trivial pairs: POR/MIN +0.07, UTA/MIN −0.06, UTA/POR +0.04, MIN/LaMelo −0.03; everything else is within ±0.02. Full matrix on `Exposure` and in `data/clean/joint_corr.csv`.

## 2. What changed vs your instructions, and where my output differed
1. **ROY stake.** `A_roy_stake_mult` = 0.5, applied after joint Kelly, others re-solved with Dybantsa fixed. Because the card now has 8 bets (the joint solution moved), Dybantsa lands at **0.53%** rather than 0.64% (his joint-Kelly stake is now 1.07%, not 1.28%). Say if you want a fixed 0.64%.
2. **Consensus layer.** Built (`Raw_Consensus`, `M_WinDist` columns, PASS/FAIL on `Bet_Card` and `Tier1_Card`). The compression slope you specified, −0.32, is **not** the G5 point estimate: the G5 test gave −0.24 (SE 0.06; 80% CI [−0.34, −0.13]). −0.32 is inside the CI and I used it as specified and recorded the provenance as "G5 test; user set −0.32". With −0.24 the WINS Tier 1 set is the same four.
3. **WINS expected set.** The consensus rule alone gave five passes: WAS, MIA, UTA, POR **and TOR OVER 45.5**. TOR passes only marginally (PredictionEngine gap +2.50 vs the 2.5 bar; it fails with −0.24), and **TOR OVER fails the shrink 0.75 test** (EV +2.3% < 3%, CI low +0.6%). GSW OVER 39.5 fails the consensus rule as you expected (PredictionEngine's gap is −3.6, the wrong way). The final set equals your expected set, so I proceeded.
4. **Minimum prices.** Six match your expected minimums to within a few points (MIN +478 vs +480, Dybantsa +314 vs +315, Sabonis +751 vs +750, LaMelo +904 vs +900, WAS −170, MIA −150). Two differ: **UTA U −103 (hand estimate +105) and POR O +102 (hand estimate +110)**. The hand-rounded estimates were approximations; the formula's values (EV at shrink 0.75 = 0) govern, and they are what `Tier1_Card` uses. (The estimates happen to be close to the EV = +3% price, which the formula does not target.)
5. **Other sources searched.** PredictionEngine and Bleacher Report only. No other free, dated, full-league statistical projection could be retrieved. Searched and not added (logged on `Raw_Consensus`): MacFax (Utah State) NBA 2026-27 model preview (full-league projected wins but the table is rendered client-side; no values in the page), ESPN's 2027 forecast (summary only, units unclear), Truehoop/Thorpe (expert, not a model), sportsbook and Kalshi lines (market data, excluded by rule), and nothing from BBall Index, Basketball-Reference, Dunks and Threes, EvanMiya, Hashtag, Dimers, TeamRankings or numberFire. With only one STAT_MODEL source, the rule rests on PredictionEngine alone.
6. **Tier1_Card layout.** To keep the blue inputs attached to the right bets, the card is now **one fixed row per Tier 1 bet** (all other columns are live formulas, plus a "Live Tier 1 status" column and a completeness check) instead of a FILTER spill. `run.py prelock` / `build` regenerates the rows.
7. **Rule flags.** `Book rule confirmed?` defaults to **N** for MIN NO, Sabonis and LaMelo, so `Still bet?` is FALSE for those three until you set Y. Live price is blank by default (the check uses the book price).
8. **Tracker.** One pre-populated row per Tier 1 bet (Group: Core ×4, Wins-consensus ×4; recommended stake, min price, lock time), blue inputs for date, placed price, stake, closing price; CLV by row, and CLV / P&L / ROI by group.

## 3. `run.py prelock`
Snapshots the Tier 1 state; re-pulls ESPN rosters, injuries and transactions; diffs them against the stored roster/injury tables (ESPN team codes are normalised and a malformed pull restores the inputs); re-runs ratings + sims only if something material changed; re-prices (team, player, joint Kelly); rebuilds the workbook; writes `reports/prelock_YYYYMMDD.md` with every Tier 1 bet whose model probability, EV, minimum price or stake moved, and any bet gained or lost. `--dry-run` reports without applying anything.

A dry run at 11:36 pm ET on Oct 15 found 3 roster additions, 19 rotation-player injury-status changes since the earlier pull, and no trade or pick transactions, so a real run on 10/18-19 would re-run the sims. I left the model inputs as they are for this build. The first live run exposed a bug in that pull (ESPN uses GS/NO/NY/SA/UTAH/WSH, which broke the projection step and overwrote four input tables); I restored them from git and added the code normalisation and guard. Pick ownership (Hoops Rumors / RealGM / Tankathon) is a manual source and is not re-pulled.

## 4. Close-out checks
- **Checks tab:** 0 failing, 0 error cells; the live Tier 1 count equals the engine count (8) and the stake-cap check is 0.
- **Six-bug audit:** hardcodes: 2 structural literals (`30`, `9`); inconsistent columns: block-structured only; circulars none; external links none; sign conventions: EV matches 236 player rows to 1e-9, 0 negative stakes; summary tabs linked: all linked. Arial 10 everywhere, no merged cells.
- **Independent verifier (all 8 Tier 1 rows, no model code imported):** de-vig max difference 3e-15 (and 4e-14 on 10 random groups); EV and shrunk EV exact; min prices within 0.06 of Excel (Excel uses the sim summary, the verifier the pricing table); WINS consensus re-derived from the raw inputs matches Excel PASS for all 4; joint Kelly re-solved with an independent solver incl. caps and the ROY fix: stakes within 1.8e-6 (uncapped within 3e-6); Excel stakes match to 1e-16.
- **PDF rebuilt** from the workbook's values (Dashboard with the 8-bet table, charts, Bet Card with the Consensus column).

## 5. Known weaknesses (unchanged except as noted)
- No market benchmark shows the model beats the book. The WINS bets rest on a model that is 4.2 wins RMSE from the market, now cross-checked by one external statistical model, which is a thin gate (and Bleacher Report disagrees on MIA).
- Dybantsa (model 43% vs book 18%) is the most assumption-driven bet: rookie minutes and an ROY model trained on 12-13 winners. It is halved by your override.
- Three bets need book-rule confirmation (MIN NO playoffs = 16-team field; LaMelo TPG = 3PM; Sabonis 58-game qualifier) and Sabonis's price is a backfill.
- Recheck pick ownership by hand and run `run.py prelock` Oct 18-19.
