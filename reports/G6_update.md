# G6 update (2026-10-15): minutes fix, Toronto scenario, updated Tier 1 card

**Tier 1 is now 4 bets, 2.78% of bankroll** (was 9 bets, 4.9%). This supersedes the card in `G6_final.md`; the rest of that report stands, except that the player probabilities below changed. Workbook rebuilt (0 error cells, 0 failing checks) and the PDF regenerated.

## Updated Tier 1 card (joint Kelly on shared sims, cap 10%)
| # | Selection | Book | Model | Market fair | EV (model) | EV at 0.75 shrink | Stake | Named driver |
|---|---|---|---|---|---|---|---|---|
| 1 | PLAYOFFS Minnesota NO | +550 | 31.8% | 12.5% | +107% | +12.4% | 0.57% | Julius Randle gone (2,610 min at +1.5 BPM, −1.1 SRS) |
| 2 | ROY AJ Dybantsa | +400 | 43.4% [41-49] | 17.7% | +117% | +20.7% | 1.28% | Pick 1, age 19: 30 mpg (slot/age fit 32) × 17.9 pts/36 = 14.9 ppg; 80 games projected. Last five ROY winners averaged 18.5 ppg in 31.8 mpg |
| 3 | RPG leader Domantas Sabonis | +900 | 21.1% | 8.6% | +111% | +17.6% | 0.48% | 12.8 RPG in 33 mpg (model's top RPG) but only 53 projected games; rival Jokic 12.4. **Price is a backfill (12:06 sheet); confirm on the live board** |
| 4 | 3PM leader LaMelo Ball | +1100 | 18.4% | 7.1% | +121% | +19.6% | 0.45% | 3.7 3PM in 30 mpg over 62 games; rival Curry 4.4 (model 35% vs book 50%) |

Joint portfolio (model world): total stake 2.78%, expected return +2.7% (+0.5% at the shrunk probabilities), P(profit) 72%, worst case −2.8%. The four bets are essentially uncorrelated (all |ρ| ≤ 0.03). Independent re-derivation (de-vig, EV, joint Kelly) again matches to ≤1e-6; Excel matches for 4 of 4.

Dropped from the 9: **Chicago play-in** (cut at your request), **both Toronto bets** (scenario below), **Gobert RPG and Haliburton APG** (no longer survive after the minutes fix; Jokic is now a real rival in both). Dybantsa's weight went up, and that is the card's largest single-bet risk: it is a 2.4× model-over-book call that depends on rookie minutes.

## 1. Leader-level sanity check (2021-22 to 2025-26 actual top 5 vs the simulated top 5)
Before the fix, the simulated top-5 values were 7-17% below history: PPG −6.9%, RPG −16.1%, APG −12.7%, SPG −7.1%, BPG −16.7%, 3PM −7.6%. The simulated top-5 played 30.8 mpg against 35.4 historically.

**Cause.** The player minutes came from the team layer, which normalises every player's expected minutes proportionally to 240 × 82. On the average roster the sum of mpg_hat × availability is 1.10× team minutes, because per-game-played mpg already includes teammates' absences. Stars were therefore cut 6-12% (Jokic 33.9 → 30.0). On top of that, the minutes model itself runs low for high-minute players (actual mpg ≈ 6.64 + 0.834 × mpg_hat on the top-40 each season 2022-26; leave-one-season-out RMSE 2.39 → 2.18).

**Fix (player markets only).** On each team the top 5 by mpg_hat keep their minutes, calibrated by the fit above and capped at 38; the rest absorb the scaling. Rookies keep raw mpg_hat (the calibration was fit on veterans). The team-strength layer is unchanged (its coefficients were fit on the normalised minutes), so team prices and sims are untouched.

| Stat | Hist top-5 mean | Sim top-5 before | Sim top-5 after | Gap after | Sim top-5 mpg (hist) |
|---|---|---|---|---|---|
| PPG | 30.32 | 28.23 | 30.27 | −0.2% | 33.7 (35.4) |
| RPG | 12.38 | 10.38 | 11.77 | −4.9% | 31.6 (32.4) |
| APG | 9.70 | 8.47 | 9.52 | −1.9% | 33.2 (34.8) |
| SPG | 1.87 | 1.74 | 1.83 | −2.1% | 31.0 (32.0) |
| BPG | 2.37 | 1.98 | 2.20 | −7.0% | 28.8 (29.2) |
| 3PM | 3.75 | 3.46 | 3.80 | +1.4% | 32.3 (33.5) |

Games of the simulated top 5 match history (67-71). The residual BPG gap is Wembanyama-era minutes. **γ was re-fit:** the CV is unchanged at **γ = 1.50, 80% CI [1.30, 1.75]**, because the leader backtest uses prior-season minutes and does not depend on the production minutes model. Player Tier 1 bets are required to hold at both CI bounds. The bets that survive do.

## 2. Jokic (after the fix)
- **RPG:** 12.0 calibrated projection (rate × 34.9 mpg), 61 projected games, P(≥58 games) 64%, **P(lead) 19.6%** (the highest RPG probability of any player; Sabonis is higher on projection, 12.3, but has 53 games); rivals Sabonis 12.3 (53 games, 16.3%), Towns 11.2, Gobert 11.1.
- **APG:** 9.5 projected, same minutes and games, **P(lead) 23.1%, the highest APG probability**; rivals Trae Young 9.7 (but only 50 games), Haliburton 9.0 (52 games), Cunningham 8.8.
- **Why he was not the top rival before.** The minutes deflation took him from 33.9 to 30.0 mpg, which cut his RPG and APG by about 12%. With the fix he is the leading or co-leading rival in both. His remaining discount is games: 61 projected, 64% to reach 58.

## 3. Toronto Atlantic with NYK and PHI at market-implied wins
NYK set to 50.5 wins and PHI to 50.0 (book line plus fair-probability median; the other 28 teams shifted −0.43 wins each so the league still sums to 1,230). 100k mean-matched sims plus 40 parameter draws:
- **TOR division title 22.6% [21.6, 24.5]** (was 33.4%), against a book fair of 10.5%. EV at 0.75 shrink is +1.6% with a lower bound of −0.3%.
- **TOR East title 14.9% [13.7, 16.7]**, against a fair of 8.3%. EV at 0.75 shrink is negative (lower bound −3.4%).
- Neither passes the Tier 1 test, so **both Toronto bets leave Tier 1** (still Tier 2). Most of the original edge came from the model having NYK and PHI 6-7 wins below the book; with Kawhi/Dick as the only driver, the Raptors are still 2× the book's division price, but that does not survive the 0.75 shrink. Rule recorded in `params/tier1_overrides.json`.

## 4. Rookie usage
Top ROY candidates vs the last five winners (ppg and mpg actual: Barnes 15.3 / 35.4, Banchero 20.0 / 33.8, Wembanyama 21.4 / 29.7, Castle 14.7 / 26.7, Flagg 21.0 / 33.5):

| Candidate | Pick | Projected mpg | Slot/age fit mpg | pts/36 | Projected ppg |
|---|---|---|---|---|---|
| Dybantsa | 1 | 30.0 | 32.0 | 17.9 | 14.9 |
| Peterson | 2 | 28.6 | 27.7 | 16.7 | 13.3 |
| Boozer | 3 | 26.8 | 25.4 | 16.0 | 11.9 |
| Wilson | 4 | 25.4 | 24.2 | 15.4 | 10.9 |
| Mikel Brown Jr. | 6 | 23.6 | 22.3 | 14.8 | 9.7 |

Before the fix these candidates sat at 24-25 mpg (Dybantsa 24); minutes are now in line with the slot/age fit and with history (winners average 31.8 mpg). Expected lines for each candidate are below the winners' because winners are selected on a good outcome. The right check is the simulated winner: **19.0 ppg (history 18.5)**, 37.5 mpg and 79 games (history 31.8 and 73.6); that mpg overshoot is the minutes noise (SD 0.32, an upper bound) plus the 65-game rule, so the model is not deflating rookies. I left pts/36 alone.

## 5-6. Cut and re-run
Chicago play-in is excluded by `params/tier1_overrides.json`. `run.py price` now ends with tier1, price_players and joint Kelly; the workbook, verification, audit and PDF were rebuilt from those.

## Caveats
- Dybantsa at 1.28% is the biggest stake and rests on one assumption set (rookie minutes, draft slot). He is 2.4× the book's probability; consider halving it by hand.
- The Sabonis price is a backfill from an earlier sheet.
- MIN Playoffs NO relies on the PLAYOFFS = 16-team-field reading (confirm with the book).
