# NBA 2026-27 Futures Model — Build Spec (Claude Code)

Owner: Max. Builder: Claude Code (Sonnet 5.5). Spec date: 2026-10-15.
Root: `%USERPROFILE%\Desktop\NBA\` (resolve the real Desktop path; it may be OneDrive-redirected, e.g. `%USERPROFILE%\OneDrive\Desktop\NBA\`). Local git only, no remote.

Objective: an independent, academically rigorous projection model for every 2026-27 NBA futures market on Max's book with enough data to model. It must be priced against the book's odds (`odds_2026-10-15.csv`) and delivered as an institutional-grade, formula-driven Excel 365 workbook backed by a Python data and simulation engine.

**First locks: Tue 10/20 2:10 PM CST (BOS/DET wins and playoffs; all title, conference, division, play-in and award markets).** Team markets and the Bet Card must be done by Mon 10/19 night. Player markets come after.

---

## 0. Operating rules (non-negotiable)

1. **Gated build.** Stop at the end of every gate (G0–G6). Write `reports/G#_report.md` covering what was built, the validation results, open issues and decisions needed. Wait for Max's explicit "approve G#". Commit at each gate (`git commit -m "G#: ..."`).
2. **Independent model.** Market odds are never a model input. They appear only in pricing and edge tabs, and as an out-of-sample *benchmark* in backtests.
3. **No fabricated data.** Every number traces to a logged source or a documented assumption. If a source fails, log it, try the listed fallback, and if that fails too, stop and report. Never fill gaps with "reasonable" values silently.
4. **Provenance on every fitted parameter.** `params/provenance.json` records value, method, data window, n, fit date, and code path. Silent defaults and hardcoded placeholders are the #1 historical failure mode.
5. **Pass/fail standard.** A point estimate that passes but whose CI touches break-even is a **fail**. Bets require the lower CI bound of EV > 0 (see §6).
6. **Variance ratio** is judged against a computed self-consistency ceiling (simulate from the model itself), not a naive 1.0.
7. **Independent verification** at G3 and G6: a separate verification script re-derives key outputs from raw data without importing the model code.
8. **Be polite to sources.** Cache every raw pull to `data/raw/` with a timestamp. Basketball-Reference: ≤ 15 requests/min. nba_api: browser headers, 0.6 s sleep, retries with backoff.
9. Keep `CLAUDE.md` in the repo root with a running summary of state, decisions and gotchas, so context survives across sessions.

---

## G0 — Environment (stop + report)

- Confirm Python ≥ 3.11 (`py --version`). If it's missing, give Max the exact install command (`winget install Python.Python.3.12`) and stop.
- Create a venv. Install: `pandas numpy scipy statsmodels scikit-learn numba nba_api requests requests-cache beautifulsoup4 lxml openpyxl xlwings pywin32 pyarrow tqdm pdfplumber`.
- Confirm Excel 365 is reachable via xlwings (open, recalc, close a test book). xlwings and the Excel COM interface are used for the recalc and error scan in G5.
- Repo layout:
  ```
  NBA/
    SPEC.md  CLAUDE.md  odds_2026-10-15.csv
    src/ (data/, ratings/, sim/, awards/, pricing/, workbook/, verify/)
    data/raw/  data/clean/  params/  sims/  reports/  output/
    run.py   # CLI: run.py pull | ratings | sim | price | build | verify | all
  ```
- Copy `odds_2026-10-15.csv` into `data/raw/odds/`.

---

## G1 — Data acquisition + validation (stop + report)

Pull, cache, clean, validate. Write a source-status table to the report, with columns: source, endpoint, rows, date range, status, fallback used.

| Need | Primary (free) | Fallback |
|---|---|---|
| Player box + advanced, 2013-14 → 2025-26 (regular season + playoffs) | `nba_api` (LeagueDashPlayerStats, Base/Advanced/Misc/Defense/Hustle) | Basketball-Reference season tables |
| Player BPM / VORP / WS / on-off | Basketball-Reference (advanced, play-by-play tables) | — |
| Multi-year RAPM / impact metric | DARKO (darko.app, free daily DPM export if available), plus any free public RAPM dataset with a downloadable CSV | Build in-house RAPM from nba_api play-by-play stints (ridge, 3-year window, luck-adjusted) — preferred if feasible in time |
| Team game logs and ratings history | `nba_api` LeagueGameLog / TeamEstimatedMetrics | bbref schedules |
| 2026-27 full schedule (incl. NBA Cup group games, dates, B2Bs) | `nba_api` ScheduleLeagueV2 / cdn.nba.com static schedule JSON | bbref 2027 schedule |
| Current rosters (post-offseason, as of today) | `nba_api` CommonTeamRoster (season 2026-27) | bbref 2027 team pages |
| Injuries / expected absences | ESPN NBA injuries page; bbref injuries page | Manual override column only |
| 2026 draft class (pick slot, college stats) | bbref 2026 draft page + Sports-Reference CBB player pages; barttorvik.com player data | — |
| Future draft-pick ownership (2027 1st, swaps, protections) | Tankathon / RealGM future picks / bbref team pages | Spotrac |
| Lottery history (who picked top-5 in 2025, 2026; who won #1 in 2026) | bbref draft pages + NBA.com lottery results | — |
| **Official 3-2-1 lottery rules** (exact ball allocation for all 16 teams, draw count, restrictions, 8-seed inclusion definition) | NBA.com official release / NBA communications PDF | ESPN / The Athletic reporting. **If exact allocation can't be confirmed from ≥ 2 sources, STOP and report.** |
| Historical award voting (MVP, DPOY, ROY shares, 2000–2026) | bbref awards pages | — |
| Stat-leader qualification rules (2026-27) | NBA.com stats qualifiers | — |
| Coach list per team (display only) | bbref | — |

Validation checks (all reported):
- Every 2026-27 roster player is matched to a player ID. Build an explicit name-map table (`data/clean/name_map.csv`) covering book spellings too: "Kelel Ware" = Kel'el Ware, "Luguentz Dort" = Luguentz Dort, "DeAaron Fox" = De'Aaron Fox, "Alperen Segun" = Sengun, and so on. Unmatched names are listed; there are no fuzzy-match guesses above a 0.9 threshold without a report line.
- Schedule: 1,230 games, 82 per team, Cup group games flagged, B2Bs computed.
- Every team has a 2027 1st-round pick owner, with protections parsed.
- Book odds file loaded. The `flag` column (BACKFILL_PDF1, BACKFILL_PDF_TEXT, IMPUTED_20C_LADDER) is preserved through to the workbook, where those cells get an orange fill.

---

## G2 — Player and team ratings + backtest (stop + report)

### 2.1 Player impact (per 100 possessions, O and D split)
Ensemble, with weights as Assumptions inputs. Defaults are fit by backtest:
- Multi-year RAPM / DPM (weighted 3-yr, recency decay).
- Box prior (BPM-style, refit on nba_api box data against RAPM, à la BPM 2.0).
- Aging curve (fit from 2013–2026 year-over-year deltas by age and position).
- Regression to a minutes-dependent replacement level, with shrinkage ∝ 1 / √(possessions).
- Rookies: draft-slot prior plus college-translation model (barttorvik BPM, age, height → NBA rookie BPM, fit on drafts 2015–2025).

### 2.2 Minutes and availability
- Projected minutes = a depth-chart allocation from last-season minutes share. Adjust for roster changes, age and role. Constrain to 240 team minutes per game with position-coverage constraints.
- Games missed: player-level distribution (negative binomial fit on age, prior-3-year games missed, current injury status). Draw per sim.
- Assumptions overrides: per-player minutes, games-missed, and manual rating adjustment (blue input cells).

### 2.3 Team rating
Team net rating = Σ(minutes share × player net impact) + continuity adjustment + regression toward a prior-season-SRS-based prior. The blend weight is an Assumption, fit by backtest. Also produce ORtg/DRtg and pace.

### 2.4 Backtest (preseason projections 2018-19 → 2025-26)
- Out-of-sample: fit on seasons < t, predict t, using only info available at that preseason. Train/test split clearly marked.
- Metrics: wins RMSE / MAE, rank correlation, calibration of P(over X wins) and P(playoffs), and Brier / log-loss.
- Benchmark only: historical closing preseason win totals, where a free archive exists (search for one; if none exists, say so and skip).
- Report a CI on every metric (bootstrap by season-team). The standard of §0.5 applies.

### 2.5 League-consistency constraint
Projected wins must sum to 1,230 (zero-sum). Note: the book's lines sum to 1,241. Report that as market inflation, not a model target.

---

## G3 — Simulation engine + calibration (stop + report)

Monte Carlo (numba). Default N = 20,000 seasons, set on Assumptions.

**Per-season draws (once per sim):**
- Team true-strength shock ~ N(0, σ_team), with σ fit from G2 backtest residuals. This is what fattens futures tails; don't omit it.
- Player availability draws, with ratings recomputed when stars miss games.

**Per-game:** P(home win) = Φ((rating_diff + HCA − B2B/rest adj) / σ_game). HCA, rest and σ_game are fit on 2021-22 → 2025-26 and recorded in provenance.

**Tanking module (the 3-2-1 rules):**
1. Encode the confirmed 3-2-1 lottery: 16 teams, ball allocation by finish, and the restrictions (no back-to-back #1; no top-5 in three straight drafts; whatever the official text defines). Build an exact lottery simulator.
2. Per team, per sim, at the trade deadline (date from the official calendar): compute the marginal draft equity of losing more, i.e. Δ(expected pick value) per extra loss, using a pick-value curve. Fit the curve from historical draft-slot → career VORP/WS, or use a published free curve; document it.
3. Set incentive to 0 when:
   - the team doesn't own its 2027 1st (or a swap or protection makes losing worthless), or
   - the team is barred from top-5 or #1 by the restriction rules, or
   - the team is in the playoff/play-in race. Note that the 8-seed is now in the lottery; handle it per the official rules.
4. Post-deadline effort suppression = κ × normalized incentive × (1 − commissioner deterrent).
   - Calibrate κ on 2018-19 → 2025-26 post-deadline net-rating changes for teams with positive old-system incentive vs. controls (diff-in-diff), and report the CI.
   - Under 3-2-1, bottom-3 finishes carry *negative* marginal equity vs. 4th–10th. The model must allow incentive to flip sign, so teams near the bottom stop sinking.
   - κ, the deterrent and the on/off toggle are Assumptions inputs.

**Season resolution:**
- Standings with official NBA tiebreakers (implement fully, including multi-team ties).
- Play-in (7–10).
- Playoffs: best-of-7 with home court. Apply the playoff rating adjustment as an Assumption: minutes re-concentrate to the top 8 and playoff HCA is fit separately.
- Champion.

**NBA Cup:**
- Group stage uses the actual scheduled group games. Verify the groups match the book's CUP_* groups; report any mismatch.
- Tiebreakers per official Cup rules (H2H, point differential, points scored, etc.), so simulate scores, not just W/L: margin ~ N(mean diff, σ_margin).
- Wildcards, knockout rounds, neutral-site semis and final.

**Outputs written to `sims/`:**
- Per-team distributions: wins, seed, play-in, playoffs, division, conference, title, Cup group, Cup, lottery position, 2027 pick.
- Per-player game counts, for stat-leader and award eligibility.

**Calibration:**
- Re-run the engine on 2023-24 → 2025-26 preseason inputs. Report reliability diagrams for P(playoffs), P(division) and win intervals.
- Report the variance ratio vs. the self-consistency ceiling (§0.6).
- `verify/` independently recomputes title odds from a stripped-down sim and checks agreement within MC error.

---

## G4 — Player markets (stop + report; can run after the team Bet Card ships)

Full models:
- **Stat leaders (PPG/RPG/APG/SPG/BPG/TPG).**
  - Per-player per-game rate projections (rate × minutes, with role and usage changes) and season-to-season rate variance.
  - Games-played draws come from the G3 sims.
  - Apply the official qualification rule and dead-heat rules.
  - Leader probability = share of sims in which the player leads among qualifiers.
- **MVP.**
  - Vote-share model: fractional logit or a ranking model on 2000–2026 voting data.
  - Features: player impact, box line, team win% / seed, availability, and the 65-game eligibility rule (an Assumptions toggle).
  - Evaluated per sim, using that sim's team record and the player's games played.
- **DPOY.** Same approach. Features: defensive impact (D-RAPM/DPM), blocks + steals rates, team DRtg rank, position (big-man prior), and 65 games.
- **ROY.** Rookies only. Inputs: college translation + draft slot + projected minutes; voting model fit on 2000–2026.

Display-only (market de-vig + fair price shown, no model probability, no bets): MIP, 6MOY, COY, Clutch, Cup MVP.

---

## G5 — Workbook build (stop + report)

File: `output/NBA_Futures_Model_v1_YYYYMMDD_MS.xlsx`. Retain prior versions.

### Formatting standard (Max's institutional standard; mandatory)
- **Fonts and colors:**
  - Arial 10 throughout.
  - **Blue font = hardcoded inputs. Black = formulas. Green = cross-sheet links. Red = error/check flags.** No fills for the input convention. The only fills are orange for imputed/backfilled odds and conditional formats on edge.
  - Headers: bold, white text on navy `#1F3864`.
- **Layout:**
  - No merged cells (use Center Across Selection). Gridlines off.
  - Bottom border on subtotals; double top+bottom border on grand totals.
  - Widths: label columns ≥ 24, number columns ≥ 14. Row heights: data 15, wrapped headers 30, spacers 6. Wrap headers only. Auto-fit numeric columns last.
- **Number formats:** `0.0%` probabilities; American odds `+0;-0`; currency `$#,##0`; `0.00` decimal odds; no blank data cells (use `-`).
- **Tab headers:** every tab carries the same header rows (project, tab name, version date).
- Use grouping, not hiding.

### Tab architecture
1. **Cover** — title, version, data timestamp, sim N, run hash, nav links.
2. **Assumptions** — every knob in one table: name, value (blue), units, description, provenance link, default. Includes:
   - HCA, σ_game, σ_team, prior-blend weight, player-metric blend weights, aging on/off, rookie prior weight.
   - Tank toggle / κ / deterrent, playoff adjustment, sim N.
   - De-vig method selector, bankroll (blank input), Kelly fraction (0.25), min EV (3%), CI level (80%), max bet ($1,000), max total exposure (25% bankroll).
   - Model-to-market shrink for **staking only** (default 0.25; 0 = pure model; the model itself is never shrunk).
   - 65-game toggle.
3. **Overrides** — per-player minutes / games-missed / rating adjustments; per-team rating adjustments (blue).
4. **Odds_Input** — paste area plus parser output. The repo also ships `run.py parse-odds <file>`, which converts a raw PDF or text dump in this book's format into the CSV schema and handles its concatenation bugs, e.g. "+3752\n0764" = "+375" then rotation 20764. The parser must reconcile rotation numbers.
5. **M_DeVig** — per market: implied probabilities, overround, fair probabilities under multiplicative / power / Shin (Shin's z solved with formulas — iterative or a LAMBDA). The selected method drives downstream. Two-way markets are de-vigged as pairs.
6. **M_TeamRatings** — player → team rating build, linked from data tabs; ORtg/DRtg/Net/pace, with ranks.
7. **M_WinDist** — live analytic layer: per-team normal approximation of wins (mean from rating × schedule, variance = game-level + strength-uncertainty). P(over line), and model fair odds for every wins line. Reprices live on Assumptions changes. Show sim-based probabilities alongside, with the delta flagged when |Δ| > 2pp.
8. **M_Sims** — sim outputs (values written by Python, clearly labeled as engine output with run hash and timestamp) for every team market. Includes MC standard error per probability.
9. **M_Lottery2027** — 3-2-1 rules table, per-team lottery-position distribution, P(#1), P(top-4), pick-ownership flags and tank-incentive scores.
10. **M_Players** — stat-leader / MVP / DPOY / ROY probabilities and drivers.
11. **S_Markets** — one block per market: book price, fair market probability, model probability, model fair odds, EV per $1, Kelly stake, and edge-CI lower bound. Edge cells are color-coded.
12. **Bet_Card** — all qualifying bets. A bet qualifies when its EV ≥ min EV and its edge-CI lower bound > 0.
    - CI method: bootstrap over the parameter posterior and MC error; Python writes the lower and upper bounds. If computing full CIs per bet is too slow, use parameter-draw re-sims at reduced N and document it.
    - Sorting and dynamic filtering via FILTER/SORTBY.
    - Stake calculation:
      1. Fractional Kelly.
      2. **Correlation-aware portfolio sizing:** Python solves a simultaneous Kelly (maximize E[log wealth] across sims jointly, using the actual per-sim outcomes of every candidate bet, constrained by the per-bet max and total exposure). The workbook shows naive Kelly vs. portfolio Kelly side by side.
    - Lock time per bet (CST) and a rule text column (e.g. "82 games required", "play-in counts as playoffs", "all wagers action", "dead heat").
13. **Exposure** — portfolio P&L distribution from the sims: P(profit), median, 5th / 95th percentile, max drawdown scenarios, and exposure by team. Correlation matrix of the bet card.
14. **Dashboard** — the 5–7 headline metrics:
    - bet count, total stake, portfolio EV, P(profit), largest single-team exposure;
    - top-10 edges chart;
    - model vs. market wins scatter;
    - title odds model vs. market bar chart.
    - Clean, navy/white, no clutter.
15. **Sensitivity** — tornado of title / wins probabilities for the top-5 bets vs. the key Assumptions (σ_team, HCA, tank κ, prior blend); a Bull/Base/Bear Assumptions scenario selector.
16. **Backtest** — G2 and G3 results: RMSE, calibration tables, reliability charts, CIs, train/test periods marked.
17. **Tracker** — bet log for placed bets (blue inputs): placed price, stake, current price / closing price → CLV, settlement, P&L, ROI by market type.
18. **Checks** — integrity flags, each showing a green 0 or a red delta:
    - fair probabilities sum to 1 per market;
    - model probabilities sum to 1 (title, conf, division, Cup, groups);
    - model wins sum to 1,230;
    - P(playoffs) ≥ P(top-6);
    - P(conference) ≤ P(playoffs);
    - title ≤ conference;
    - no #N/A / #VALUE! / #REF!;
    - odds-file row count reconciles;
    - imputed-odds count.
19. **Data_Sources** — every source: URL, pull timestamp, rows, status, license note.
20. **Raw_*** tabs — clean data the formulas reference.

### Dynamism rules
- Everything downstream of Odds_Input, Assumptions, Overrides, M_Sims and the Raw tabs is a live formula. No pasted values anywhere else.
- Changing an Assumption reprices the analytic layer live. Sim-dependent cells show a **"STALE — rerun sims"** red flag if their Assumptions hash differs from the hash stored with the last sim run. Python writes the hash, and a formula compares it.
- One command refreshes everything: `run.py all`. Optionally, an xlwings button on Cover triggers it.

Post-build: recalc in Excel via xlwings, scan every sheet for errors, run the six-bug audit:
1. hardcodes in formulas;
2. inconsistent dragged formulas;
3. circulars;
4. external links;
5. sign conventions;
6. summary tabs not linked.

Report the findings table.

---

## G6 — Audit + delivery (stop + report)

- `verify/` re-derives, independently:
  - de-vig numbers for 10 random markets;
  - 5 Bet_Card rows (EV, Kelly) by hand-calc in Python;
  - the title odds sanity check;
  - the lottery simulator against the official rule examples.
- Final report `reports/G6_final.md`:
  - the Bet Card table;
  - top model-vs-market disagreements, with the driver of each (which rating, injury or tank assumption);
  - known weaknesses;
  - everything imputed.
- Export a Dashboard + Bet_Card PDF.

---

## Market rules (from the book; encode in pricing)
- **Title / Conference / Division / Cup / Cup groups:** all wagers action.
- **Regular-season wins:** the team must play all 82 games for action; play-in games don't count.
- **To make playoffs:** the play-in counts as playoffs, so **YES = finish top-10 in the conference**. Action requires 82 games unless already determined.
- **Play-In markets (PLAYIN_EAST/WEST):** interpreted as **"team participates in the play-in" (finishes 7–10)**. Supporting evidence: implied probabilities sum to ~4.4 per conference with 4 slots. Flag this interpretation on the sheet.
- **Awards:** all in, no refunds. **Stat leaders:** dead-heat rules apply; use official qualification.
- TOR, GSW and LAC have no playoff lines on this sheet. Model them anyway; no bet rows.

## Odds file notes
`odds_2026-10-15.csv` was transcribed from the book screenshots on 10/15.
- `flag` values:
  - `BACKFILL_PDF1` — missing on the 10/15 12:12 sheet; taken from the 12:06 sheet.
  - `BACKFILL_PDF_TEXT` — the image cell was blank but the text layer had a price.
  - `IMPUTED_20C_LADDER` — one-sided line; the missing side was priced on a 20¢ ladder.
- Imputed sides **must not appear on the Bet Card**. They're used only to de-vig the visible side.

## First action
Read this spec fully, create `CLAUDE.md`, execute **G0**, and stop.
