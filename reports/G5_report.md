# G5 Report — Workbook build, team markets and Bet Card (2026-10-15)

**Status: complete, awaiting "approve G5".** G4 (player markets) is deferred until after the team Bet Card, as you directed. Their tabs exist as placeholders with no model probabilities and no bets.

**Workbook:** `output/NBA_Futures_Model_v1_20261015_MS.xlsx` (22 tabs, one prior version retained). Rebuild with `run.py build` (it calls `src.workbook.build`; `run.py price` re-prices; `run.py sim` re-runs the engine).

## 0. Decisions I need from you before staking
1. **PLAYOFFS market definition (blocking for 54 rows).**
   - Your spec says YES = top-10 in the conference, because the sheet's rule text says the play-in tournament is considered part of the playoffs.
   - **The book's prices say otherwise.** Applying the book's own win totals (normalised to 1,230 wins) with the model's team noise, the implied P(top-10) sums to 18.2 over the 27 listed teams. The book's de-vigged YES prices sum to **14.9**, which matches a 16-team playoff bracket (top-8 per conference; 14.7) and not top-10.
   - Mean absolute error vs the book: 0.031 for top-8, 0.125 for top-10.
   - If the rule really is top-10, the YES prices on weak teams are wildly mispriced (BKN, MIL, CHI, SAC at +1150 to +2350 against model 11–34%). That is either a large edge or the printed rule is wrong.
   - **I did not pick a side.** `playoffs_definition` defaults to "Bracket" (matches prices) and `playoffs_rule_confirmed` = 0 **blocks every PLAYOFFS bet** until you confirm the rule with the book. Both probabilities and EVs are shown. If the Bracket definition is confirmed, 17 PLAYOFFS bets would qualify in addition to the 89; under top-10 the model sees much larger edges (the alternate EVs are on S_Markets).
2. **PLAYIN markets** are interpreted as "team finishes 7–10" (implied probabilities sum to 4.37 / 4.40 per conference for 4 slots, consistent). Flagged on the sheet.
3. **How much to trust the Bet Card at all** (see §4): no free market-line archive exists, so I cannot show the model beats the closing line. Please read §4 before sizing.

## 1. What was built (per spec)
| Tab | What it does |
|---|---|
| Cover | Title, version, timestamps, sim N, run hash, live sim status, navigation links |
| Assumptions | 42 knobs in one table (value, units, description, provenance, default, Bull/Base/Bear). Includes De-vig selector, bankroll (blank), Kelly 0.25, min EV 3%, CI level 80%, max bet $1,000, max exposure 25%, staking shrink 0.25, 65-game toggle, scenario selector, sim assumptions key |
| Overrides | Per-player minutes / games / rating adjustments, per-team SRS adjustments (blue) |
| Odds_Input | The 687 odds rows (blue inputs; orange fill on 15 backfilled/imputed rows); parser: `run.py parse-odds <pdf/txt>` |
| M_DeVig | Implied probabilities, overround, fair probabilities under Multiplicative / Power / Shin. Power k and Shin z are solved **in formulas** (32-step bisection per market, grouped columns, not hidden). Two-way markets are de-vigged as pairs; PLAYIN targets a sum of 4 (Shin falls back to Power there) |
| M_TeamRatings | Player → team build from Raw_Players with Overrides flowing through; ORtg / DRtg / net / pace and ranks |
| M_WinDist | Live analytic win distribution and P(over); compared with the sim; flags \|Δ\| > 2pp |
| M_Sims | Engine output (values, labelled): run hash, timestamp, N, team probabilities with MC SE, conference-rank distribution, wins pmf, per-bet edge CI / robustness / portfolio Kelly |
| M_Lottery2027 | 3-2-1 rules, restrictions (UTA no top-5, WAS no #1), pick ownership, per-team pick distribution |
| M_Players | G4 placeholder (projected ratings / games) |
| S_Markets | One block per market (34): book price, fair probability, model probability, model fair price, EV, edge, CI, Kelly, rule text, lock time; edges colour-coded |
| Bet_Card | `LET`/`FILTER`/`SORTBY`/`HSTACK` over S_Markets (dynamic), sorted by portfolio Kelly stake |
| Exposure, Dashboard, Sensitivity, Backtest, Tracker, Checks, Data_Sources, Raw_Teams / Raw_Players / Raw_Schedule | As specified |

**Formatting:** Arial 10 everywhere, blue inputs / black formulas / green cross-sheet links / red flags, navy headers, no merged cells, gridlines off, tab headers on every sheet, row heights 15 / 30 / 6. Audit: 0 non-Arial cells, 0 merged cells.

## 2. Verification (Excel 365 recalculated through xlwings)
- **Error scan:** 0 error cells on every sheet. **Checks tab: 0 failing** (all `OK`; 3 informational/flag lines):
  - Fair probabilities sum to target in every market (max deviation 4e-9); pair sums exact.
  - Model probabilities sum correctly (title 1, conference 2, division 6, Cup 1, Cup groups 6); P(top-10) ≥ P(top-6); P(conference) ≤ P(top-10); P(title) ≤ P(conference).
  - Live analytic wins sum to 1,230; odds row count reconciles.
  - Imputed odds rows: 4 (never bet); backfilled rows: 11.
  - FLAG (not an error): 8 of 30 WINS lines differ by more than 2pp between the analytic layer and the sim.
- **Excel vs Python parity:** de-vig Multiplicative / Power / Shin agree to **2e-16 / 3e-10 / 3e-10**; team wins to 2e-14; EV per bet to 2e-4 (CSV rounding on rare long shots); **qualifying bets 89 in both**.
- **Live behaviour tested:**
  - Overriding SGA's rating by −3 moves OKC from 58.7 to 54.8 wins.
  - Bankroll $10,000 gives $2,500 total portfolio stake.
  - Scenario "Bear" flips the sim status to STALE.
  - De-vig selector and PLAYOFFS definition change fair probabilities / EVs correctly.
  - Overrides move the analytic layer immediately; sim-based probabilities need `run.py sim` (STALE flag), and S_Markets shows a "live analytic" WINS probability / EV that reprices with Overrides.
- **Six-bug audit** (`workbook_audit.json`):
  1. Hardcodes in formulas: only structural constants remain (`INDEX` column numbers on the Dashboard, 100 in the American-odds conversion). Pace blend, 82 games, 19,680 team minutes and the 4 play-in slots were moved to Assumptions.
  2. Inconsistent dragged formulas: all flagged columns are block structure by design (one S_Markets block per market, team table vs player block). Row alignment was verified by value: every modelled S_Markets EV matches Python.
  3. Circular references: none.
  4. External links: none.
  5. Sign conventions documented: EV = p × decimal − 1; edge = model − fair; CLV = closing − placed implied.
  6. Summary tabs linked: Dashboard and Exposure team table are live formulas. The Exposure P&L distribution is engine output (labelled).

## 3. Pricing methodology
- **De-vig:** default Shin. Shin pushes long-shot fair probabilities down, which inflates EV on long shots; the Bet Card therefore ranks by portfolio stake, not by EV.
- **Model probability:** 100,000 production sims. WINS is the exact simulated P(wins > line).
- **Edge CI** (`param_draws.npz`): 60 parameter draws × 15,000 sims. Each draw perturbs σ_team, HCA, back-to-back effects, σ_game, playoff HCA and λ, tank κ, the DARKO weight (0.1–0.9) and a rating-scale factor, with independent seeds so MC error is included. The EV CI is the 10th–90th percentile across draws.
- **Qualification:** EV ≥ 3% **and** EV CI low > 0 **and** not an imputed side **and** the robustness filter (bottom-10 projected teams need EV > 0 at κ = 0, κ = 1.57, σ_team ±10%) **and** rule confirmed. Result: **89 bets**; the robustness filter removed none (all bottom-10 bets survive).
- **Staking:** probability for staking = 0.75 × model + 0.25 × fair. Naive Kelly = 0.25 × full Kelly. **Portfolio Kelly:** sim outcomes are exponentially tilted to match the shrunk marginals, then E[log wealth] is maximised jointly (bounds 0 to 0.6 per bet); stakes scale to the 25% exposure cap. Stakes are fractions of bankroll; the $1,000 cap applies in the workbook.

## 4. The Bet Card, and how far to trust it
- **89 bets**; total stake at the 25% exposure cap. By market: WINS 22 (15.0% of bankroll), play-in 12 (5.9%), division 12, conference 14, title 11, Cup and Cup groups 18 (almost all tiny).
- **Largest stakes** (fraction of bankroll): BKN wins over 24.5 (+110) 1.4%; NYK wins under 52.5 (−155) 1.2%; LAC over 29.5 (+135) 1.1%; BKN play-in YES (+1400) 1.1%; MIA under 46.5 (−120) 1.0%; MIN under 47.5 (+100) 1.0%; WAS under 35.5 (−140) 1.0%; MEM over 28.5 (−145) 0.9%.
- **Simulated portfolio:** expected return +20.6% of bankroll, P(profit) 94.7%, median +18.2%, 5th percentile −0.3%, 1st percentile −4.8%, worst −11.8% (all in the model's own world).
- **Caution:**
  1. The Bet Card is a list of model-vs-book disagreements. The model's mean absolute gap to the book's win totals is **3.9 wins**, with gaps up to 9 (NYK −9.1, MIA −8.1, SAS −6.7, PHI −6.2, WAS −6.0; MEM +8.0, BKN +7.6, MIL +6.1, SAC +5.4, HOU +4.5).
  2. The model's honest out-of-sample wins RMSE is 8.9 (G2) and no free closing-line archive exists, so **I cannot show the model beats the market**. A typical market RMSE is 7–8. The CI covers parameter uncertainty only, not the possibility that the market is simply better.
  3. The 25% staking shrink and the lower-CI rule are the only guards the spec provides. Total exposure is concentrated in a handful of team views (BKN 2.4%, MEM 1.8%, MIN / NYK 1.6% each).
  4. Before the Tuesday lock I would diagnose the top 10 disagreements by driver (injuries, roster moves, rookie / DARKO inputs) before placing real money. That is the G6 audit.
- **Lock times** (CST): season markets lock Tue 10/20 02:10 PM; each team's wins market locks 10 minutes after its first tip (BOS/DET 02:10 PM matches the sheet's printed locks).

## 5. Limitations / open items
- PLAYOFFS definition (§0.1) and the play-in interpretation.
- Excel's PDF export needs a printer driver; the Dashboard + Bet_Card PDF is a G6 deliverable and I will use another route if none is available. Chart rendering was not visually inspected here.
- The analytic layer approximates the engine (wins = 82 × Φ(SRS / s_eff), s_eff = 14.72; mean RMSE 0.30 wins vs the sim); 8 of 30 WINS lines differ by more than 2pp (flagged).
- `parse-odds` reproduces **640 of 687** rows of the CSV exactly (0 price mismatches). The 47 not reproduced are rows the PDF text layer has blank or garbled (exactly the backfilled / imputed rows) plus 4 spelling variants; unparsed lines are reported.
- Player markets (G4) have no model; display-only markets show fair prices only.
- Calibrations and tank / playoff assumptions are as in the G3 addenda.

Awaiting "approve G5".
