# AUDIT.md: NBA 2026-27 futures model (prices as of 2026-10-15; build of 2026-10-16)

Release: `v1.0-preseason.1` (baseline tag `v1.0-preseason` is untouched). Reproduce everything with `scripts/cleanroom.sh` (see `README.md`).

Private repo for an external audit. Everything needed to review the model, its gates and the final card is here; raw scraped pages and the large simulation arrays are not (see "What is not in the repo").

## 1. What the model is
An independent (market-free) NBA 2026-27 futures model plus an Excel 365 workbook that prices it against one sportsbook's board (`odds_2026-10-15.csv`, 687 rows). Book odds are **never model inputs**: they are used only to de-vig, to compute edges, and (since G8) to cross-check.

- **Player impact and team strength.** Basketball-Reference BPM-based player ratings (decayed three-season prior, reliability shrinkage, aging, a college/draft-slot rookie model, a DARKO blend at a weight of 0.5 that is an UNVALIDATED scenario input (no point-in-time DARKO history; never in the backtest; excluded from out-of-sample claims)), minutes and availability models, and a team layer (SRS regressed on minutes-weighted rating, prior SRS and continuity). Wins = 41 + 2.44 × SRS, zero-sum to 1,230. As of G8 the team layer allocates star-protected minutes (top 3 per team keep calibrated minutes; backtest in `src/ratings/minutes_backtest.py`).
- **Simulation.** A numba Monte Carlo of the full 1,230-game season (home court, back-to-backs, per-player availability, true-strength team shocks, NBA Cup, full tiebreakers, play-in, playoffs, the exact 3-2-1 lottery with pick-ownership rules, a tank module). 100,000 seasons; ratings are moment-matched to the calibrated projection.
- **Pricing.** Shin de-vig, EV, parameter-posterior confidence intervals, robustness scenarios, a shrink of the model toward the market in the edge test, zero-sum, longshot and low-continuity filters, a compression rule, and a portfolio Kelly solved on exponentially tilted sims.
- **External consensus (G7/G8).** For WINS bets: per-source regressions of external projections on the book's fair median; a bet needs both roster-aware residuals (ours and PredictionEngine) to point the bet's way by at least 2.5 wins.
- **Player markets (G4).** Stat-leader, MVP, DPOY and ROY models exist and are shown on `M_Players`, but **MVP, DPOY and ROY are display-only** and **stat-leader bets need an external reference that does not currently exist**, so there are no player bets. See "Known weaknesses" below.

## 2. The final card (4 bets, 2.63% of bankroll; cap 10%)
| Bet | Book | Min price (EV at 0.75 shrink = 0) | Model | Market fair | EV | Stake | Lock (CST) |
|---|---|---|---|---|---|---|---|
| WINS Washington UNDER 35.5 | −140 | −164 | 78.9% | 56.4% | +35% | 0.75% | Wed 10/21 6:10 PM |
| WINS Utah UNDER 37.5 | +115 | −101 | 67.7% | 44.5% | +46% | 0.75% | Wed 10/21 7:10 PM |
| WINS Portland OVER 42.5 | +115 | +109 | 58.2% | 44.5% | +25% | 0.50% | Wed 10/21 9:10 PM |
| PLAYOFFS Minnesota NO | +550 | +472 | 32.6% | 12.5% | +112% | 0.63% | Wed 10/21 6:40 PM |

On hold (pass the rules, not staked by decision): MIA U, MIA playoffs NO, IND playoffs NO, Gobert RPG. Details and the consensus residuals behind each bet are in `reports/G8_final.md`. The model has no demonstrated edge over the market (no market-line benchmark exists), so the stakes are small and the card is a set of model opinions to audit, not a track record.

## 3. Reports to read, in order
1. `reports/G0_report.md` environment and scope
2. `reports/G1_report.md` data sources, name map, schedule validation, lottery rules
3. `reports/G2_report.md`, `reports/G2_addendum.md` ratings model, backtest (leakage audit, first-roster RMSE 8.92)
4. `reports/G3_report.md`, `reports/G3_addendum.md` simulation engine, calibration, sigma_team cross-validation, tank carryover
5. `reports/G4_report.md` player markets (superseded in part by G6/G8: leader sharpening, minutes, display-only decision)
6. `reports/G5_report.md`, `reports/G5_tier1.md` workbook, team pricing, filter waterfall (75 raw bets to 52), Tier 1 design
7. `reports/G6_final.md`, `reports/G6_update.md` sharpening CV, variance and minutes checks, joint Kelly, independent verification, six-bug audit
8. `reports/G7_final.md` consensus layer v1, minimum prices, tracker, `run.py prelock`
9. `reports/G8_final.md` **the current card**: minutes fix in the team layer, consensus v2 (per-source regressions), market-reference gate, candidate-pool fixes, holds
10. `reports/prelock_20261015.md` (dry run) and `reports/prelock_20261016.md` (a real pre-lock refresh). These pre-date the G8 changes; rerun `run.py prelock` for a current one.

`CLAUDE.md` is the running log (including known weaknesses for next season); `SPEC.md` is the original requirement document.

## 4. Reproducing
`scripts/cleanroom.sh` does everything from a fresh clone of the tag: venv from `requirements.lock.txt` (Windows-only packages skipped elsewhere), restore and hash-verify the frozen input archive (`inputs/`, listed in `inputs/inputs_manifest.csv` and checked against `data/manifest.csv`), static tests, ratings, a fixed-seed reduced-N simulation (`python run.py repro --n 20000 --seed 2026`), pricing, a workbook rebuild, end-to-end tests, and SHA-256 hashes. `NBA_N=100000 scripts/cleanroom.sh` runs the production N at the production seed, where the card must match the committed card exactly. `reports/repro_check.md` compares every team's mean wins, P(over) and P(top-8) and every card bet's EV with the committed outputs, within Monte Carlo error.

Other entry points: `python run.py all` (Windows + Excel 365: ratings, sim, price, build, verify), `python run.py prelock [--dry-run]` (live ESPN refresh, not used in the clean-room), `python -m pytest tests`, and the independent checks `python -m src.verify.g6_independent`, `python -m src.workbook.audit`, `python src/verify/title_check.py`, `python src/verify/compare_title.py`, `python src/verify/lottery_validation.py`. Parameters and provenance: `params/` (`provenance.json`, `assumptions.json`, `tier1_overrides.json`, `release.json`). `data/external/` holds the user-supplied consensus and exchange files (identical copies in `data/consensus/`, which the code reads). Raw sources: `inputs/` (see `DATA_LICENSES.md`).

## 5. What is not in the repo
`sims/` (simulation arrays, regenerated by `run.py repro` / `run.py sim`), `.venv/`, scratch copies of earlier workbook builds, and any sportsbook screenshots or PDFs. `data/raw/` is git-ignored but its required contents are restored from the frozen archive in `inputs/` (231 files, 20 MB). The odds were transcribed to `odds_2026-10-15.csv`; no account information is in the repo.

## 6. Known weaknesses an auditor should probe first
1. **No market benchmark.** The backtest (2019-2026) beats naive baselines but there is no free archive of historical lines, so nothing shows the model beats the book. Model-vs-book wins RMSE is 4.2.
2. **Compression.** The model is more compressed than the market (slope about 0.76); the WINS consensus rule works on per-source regression residuals for that reason.
3. **Confidence intervals** reflect parameter uncertainty only, not model misspecification.
4. **MVP / DPOY / ROY** models (trained on 12-13 winners) fail sanity checks against exchanges and the GM survey and are display-only.
5. **Minutes allocation** is the most fragile input (see the LaMelo/Gobert sensitivity in `reports/G8_final.md`); the team-layer fit degraded slightly in-sample after the fix.
6. **Unconfirmed book rules:** PLAYOFFS = 16-team field including the play-in; PLAYIN = finishes 7-10; stat-leader qualification and TPG = three-pointers made. A few quoted prices are backfilled or imputed (listed in `reports/G6_final.md` section 7); imputed sides are never bet.
7. **Manual sources:** pick ownership tables and the exchange / consensus inputs are not re-pulled by `run.py prelock`.
