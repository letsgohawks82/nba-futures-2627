# Release report: v1.0-preseason.1

Immutable release of the NBA 2026-27 futures model. It makes the frozen `v1.0-preseason` build (commit `da40608`, tag untouched) reproducible by an independent auditor and fixes the release-control defects found in it. **No recommended bet, stake, price or model output changed.**

## 1. What was validated, and on which commit
| Item | Value |
|---|---|
| Baseline tag (not moved) | `v1.0-preseason` = `da40608119f53934171c416fc286a723eb8565e8` |
| **Validated commit** (code and data identical to the tag) | `e6906b0144688e8081b70c6df859353819f6f9a0`, a fresh `git clone`, run through `scripts/cleanroom.sh` |
| Release tag `v1.0-preseason.1` | the validated commit plus one commit that adds only documentation and run artifacts (`reports/release_report.md`, `reports/repro_check.md`, `reports/negative_controls.md`) and the final fix to `scripts/negative_controls.py` (a test tool, not used by the pipeline). `git diff e6906b0 v1.0-preseason.1 --stat` shows exactly these files |
| Input archive | `inputs/nba_futures_inputs_2026-10-15.tar.gz`, SHA-256 `b027f71974ff779cb40ce291ab643f978c0ada1a4471ddb68161d87f9701fc01` (231 files, 20.0 MB; deterministic, rebuilds to the same hash; also stored in `inputs/INPUTS.sha256` and `params/release.json`) |
| Dependency lock | `requirements.lock.txt`, SHA-256 `1847eaa8a88217457cfddcdde6d0a094d2eaf9c8c10f7a1196fa2e8ebac26827` (LF line endings; regenerated with `pip freeze`: the old lock was missing matplotlib and had no pytest) |
| Simulation | reduced N = 20,000, seed 2026 (production: N = 100,000, seed 2026) |
| Platform of the validation run | Windows 11, Python 3.13.15, Excel 365 (the Excel recalculation path). **The Linux / no-Excel path was not run (no Linux machine here)** |

## 2. Commands run in the final validation (all exit 0)
`scripts/cleanroom.sh` from a fresh clone with `data/raw/` absent:
1. venv from `requirements.lock.txt` (pywin32 and xlwings skipped off Windows; on Windows only colorama is filtered) - exit 0
2. `scripts/verify_inputs.py --restore`: restored 231 files; archive hash, `inputs_manifest.csv` and `data/manifest.csv` agree for all 231 (228 against `data/manifest.csv`, 3 against `inputs/manifest_additions.csv`, whose SHA-256 values were first recorded when the archive was built because those files had no pull-time hash) - **INPUTS OK**
3. static tests: `pytest -m "not e2e" tests`: **12 passed** (inputs, engine tie-break and sim invariants, release metadata, committed card vs committed workbook)
4. `run.py repro --n 20000 --seed 2026`: verify_inputs 0.6 s, ratings 28.7 s, sim 40.0 s, team pricing 24.4 s, Tier 1 5.0 s, player sims 154.0 s, player pricing 4.3 s, joint Kelly 17.2 s, card 1.7 s, all exit 0. **Numba cold compile time (empty cache): 73.0 s.** `reports/repro_check.md`: **PASS**
5. `python -m src.workbook.build` into `repro/output/` (Excel recalculation; fail-closed on any flag, failing check or error cell) - exit 0
6. `pytest -q tests`: **17 passed** (the 12 static tests plus 5 end-to-end tests on the rebuilt outputs)
7. `scripts/hash_outputs.py`

### What the reproduction showed (`reports/repro_check.md`)
- **Ratings reproduce exactly** (max |diff| 0.00e+00 wins vs the committed team projection).
- **Teams:** all 30 teams' mean wins, P(over line) and P(top-8) are within 4 Monte Carlo standard errors of the committed values (largest z over the 90 comparisons: 1.72).
- **Card:** all four bets are on the rebuilt card with the same stakes (MIN NO 0.60% vs 0.63%, the three WINS bets 0.75%/0.75%/0.50% unchanged); EV z-scores 0.16 to 1.00. POR O is "marginal" (its shrunk EV, +3.09%, sits within Monte Carlo error of the 3% bar at N = 20,000; it stayed on the card). At identical N and seed the test requires exact agreement (1e-6).

### Output SHA-256 (validation run, N = 20,000)
| File | SHA-256 |
|---|---|
| `data/clean/team_projection_2027.csv` (identical to the committed file) | `c391a9c53ebda8da3cc96e14386e2897f414bb33d4441424e34c68f506551e36` |
| `data/clean/player_projection_2027.csv` (identical to the committed file) | `1f93544621b66e9ed2cac4fce656d0d91f0ce6a8c5a019cdc5443021dfdce0ad` |
| `data/clean/sim_team_summary.csv` | `3db2e82718d049ae2690da336eae141585100ab376c696d05e54ed25aa8e4252` |
| `data/clean/pricing_table.csv` | `5f0cb9ff4419fedfd8ed737235025eafc92a2081d9958b8f0446bcd64f6de8fd` |
| `data/clean/player_pricing_table.csv` | `b6cc2f48cc64803cc4f26762aa7250a748a2b076138cb38fb2e756adf0155ee3` |
| `data/clean/joint_summary.json` | `e092924768f5e05fca02e72ee587d36a1266c31561b0977adb418c3302073b1e` |
| `repro/rebuilt_card.csv` | `93bc6f60626c787a01d30b829e5ebfb2d16c34913c7c8d09f91d1707e2122015` |
| `release/final_card.csv` (committed card) | `24075f1491a8cc9d7139c50e6233a36fa66e8868d352535f0b2b801e25d0ecec` |
| rebuilt workbook `repro/output/NBA_Futures_Model_v1_20261016_MS.xlsx` | `7b1242d1941209a26fdbe35f0ec5e82de76151577bef890d1888a50991219887` |

Hashes of simulation-dependent files change with N and seed; the committed (N = 100,000) outputs are byte-identical to the baseline tag. `NBA_N=100000 scripts/cleanroom.sh` reproduces the production N and requires the card to match to 1e-6; that full-N run was not performed in this release.

## 3. Release-control defects fixed
| Defect | Fix |
|---|---|
| Not reproducible from a clean clone (`data/raw/` ignored) | Running ratings, simulation and pricing from a clone with raw data copied in, with audit hooks logging every file opened, showed the production stages read exactly: `odds_2026-10-15.csv`, `darko_dpm_leaderboard_20261015.csv`, 13 Barttorvik `advstats_*` files, and (tank carryover) 142 game-log pages. All are in the archive, with ESPN roster/injury/schedule, schedule, pick and lottery sources as provenance files. `scripts/verify_inputs.py` verifies everything and fails closed; no stage downloads anything |
| Workbook said "8 bets" with 4 active | Title and Tracker rows are now generated from the engine card count (`4 active Tier 1 bets`); a test compares title, rows, count, stakes and the CSV card |
| Stale October 15 labels in the October 16 workbook | Version, as-of and build dates come from `params/release.json`: every tab header reads `v1.0-preseason.1 | prices as of 2026-10-15 | build 2026-10-16`; the Cover separates the build date, the book-price date (10/15) and the consensus-input date (10/16). The superseded 10/15 workbook and PDF were removed from the tree (still in the baseline tag) |
| `Checks!C23` FLAG (analytic vs simulated P(over) > 2 pp for WAS and SAC) | Root cause: an Excel operator-precedence bug. `-NORMSINV(x)^2` evaluates as `(-x)^2`, so the analytic SD used `exp(+z^2/2)` instead of `exp(-z^2/2)` (WAS SD 9.50 instead of 8.46). After fixing it the remaining differences (up to 3.6 pp for OKC) were real: the simulated win distributions are skewed (skew about -0.02 per win above 41), which a symmetric normal cannot reproduce. I added an Edgeworth skew term and re-fit the two display-layer parameters to the simulated SDs and skewnesses (SD scale 0.94 to 0.9423 by least squares; skew slope -0.0212 by OLS), not to the 2 pp check. Max difference is now 1.65 pp. The 2 pp threshold is unchanged. This layer is display and live-reprice only: bets, stakes and every model output are unchanged |
| FLAG not fail-closed | `python -m src.workbook.build` now exits 2 on any `FLAG`/`CHECK`/`STALE` cell, any non-OK status on `Checks`, any error cell, or analytic-vs-sim deltas above 2 pp (the last re-computed in Python when Excel is not available); a test enforces it. The model-vs-exchange divergence markers (a by-design analytical flag) were renamed `DIVERGES >2x vs exchange` so they cannot be confused with integrity flags |
| `or True` in `tests/test_engine.py` | Removed. The Utah assertion (the restricted pick never lands in the top 5 in any simulated lottery) now really tests, and passes at 20,000 sims. A test fails if a vacuous assertion is reintroduced |
| `run.py` stage `run_g4` crashed at reduced N | It sampled 10,000 or 40,000 simulations without replacement from a smaller population. Fixed with `min(n, N)`; no effect at N = 100,000 |
| Pipeline problems found while validating the validation | the first repro comparison used the wrong side of a bet (PLAYOFFS YES vs NO), a KeyError on a missing column, and a PDF test that looked in the wrong directory; all fixed before the validated commit, and each failed run was repeated from a new clone |

### DARKO blend (item 6)
No point-in-time DARKO history exists, so the 0.5 blend is labelled an **UNVALIDATED scenario input** in `README.md`, `AUDIT.md`, `params/release.json`, and the workbook's Assumptions row (a test requires the label). It is excluded from every out-of-sample claim; the backtest (RMSE 8.92, first-roster) uses box-score ratings only. No DARKO history was built and no validation claim is made.

## 4. Tests and fail-closed evidence
Static tests (12): required inputs present, archive and every SHA-256 verified against `data/manifest.csv`, production code reads only archived raw paths, no network use in the reproduction stages, engine tie-break cases and simulation invariants, committed card vs committed pricing tables, workbook Tier 1 rows/count/stakes/Tracker vs the card, no integrity flags, metadata agreement (version, tag, dates, workbook name, PDF, baseline commit), DARKO label, no vacuous assertions. End-to-end tests (5): every repro stage ran and exited 0, inputs unchanged, rebuilt outputs agree with committed outputs within Monte Carlo error, rebuilt card equals the committed card (exactly at identical N and seed), `repro_check.md` says PASS.

**Negative controls** (`scripts/negative_controls.py`, `reports/negative_controls.md`): each injected defect makes the right test fail, and the test passes again after restoring: a deleted raw input; one changed byte in a Barttorvik file; an edited stake in the card CSV; a mismatched version; a reintroduced `or True`; a FLAG injected into `Checks!C23`; an "8 bets" title; an extra bet on the rebuilt card; a missing run status; a stage exiting non-zero (10 of 10).

## 5. Every numerical change relative to `v1.0-preseason`
- Committed model outputs: **159 of 162 compared files in `data/clean/`, `output/`, `release/`, `reports/`, `params/` are byte-identical** (git blob ids). Changed: `data/clean/workbook_build_report.json`, the workbook and the PDF.
- Workbook, analytic layer only (`M_WinDist`, and `S_Markets` columns AB/AC which read it): analytic SD (mean |change| 0.45 wins, max 2.34), analytic P(over) (mean |change| 0.77 pp, max 3.03 pp), delta vs simulation (max |delta| 2.90 to 1.65 pp), `Checks` analytic row 2 FLAG to 0 OK; `A_sdscale` 0.94 to 0.9423; new `A_skew_slope` -0.021175. Tier 1 rows, stakes, minimum prices, fair and model probabilities in the workbook are unchanged.
- `requirements.lock.txt`: added matplotlib (and its dependencies) and pytest; no existing pin changed.
- Not changed: methodology, the final card, stakes, thresholds, sensitivity settings, or any bet recommendation.

## 6. Final card, with the condition to place each bet
Tier 1: 4 active bets, 2.63% of bankroll (joint Kelly with caps; cap 10%). Model probability, fair (market) probability, EV, and the minimum acceptable price (EV at the 25% model / 75% market blend equals zero) are from `release/final_card.csv`.

| Bet | Book | Min price | Model | Market fair | EV | Stake | Lock (CST) |
|---|---|---|---|---|---|---|---|
| WINS Washington UNDER 35.5 | -140 | -164 | 78.9% | 56.4% | +35% | 0.75% | Wed 10/21 6:10 PM |
| WINS Utah UNDER 37.5 | +115 | -101 | 67.7% | 44.5% | +46% | 0.75% | Wed 10/21 7:10 PM |
| WINS Portland OVER 42.5 | +115 | +109 | 58.2% | 44.5% | +25% | 0.50% | Wed 10/21 9:10 PM |
| PLAYOFFS Minnesota NO | +550 | +472 | 32.6% | 12.5% | +112% | 0.63% | Wed 10/21 6:40 PM |

**Place a bet only if ALL of these hold at the time of placing:** (1) the live price is at or better than the minimum price above (enter it as `Live price` on `Tier1_Card`; `Still bet?` must read TRUE); (2) the book's rule for that market is confirmed: for MIN NO, that PLAYOFFS means making the 16-team playoff field including via the play-in, with action only after all 82 games are played unless already determined; for the three win totals, that all 82 games must be played and play-in games do not count (set `Book rule confirmed?` to Y for MIN NO; it defaults to N); (3) the bet is placed before its lock time; (4) the price on the book's board is a real two-sided price, not one imputed by the model (the four imputed under prices on the 10/15 sheet are never bet); (5) the workbook still shows 0 failing checks. Everything else on `Bet_Card` is Tier 2 with no stake; the held bets (MIA U, MIA and IND playoffs NO, Gobert RPG) and the display-only awards stay unstaked. The model has not been shown to beat the market.

## 7. Failed or flagged checks
- Final validation: **none** (12/12 static, 17/17 full, repro PASS, 10/10 negative controls fail as intended).
- Informational lines kept on `Checks` (not flags): 4 imputed odds rows, 11 backfilled odds rows.
- Fixed before the release (see section 3): the `Checks!C23` analytic-vs-sim FLAG; the repro comparison, run_g4 reduced-N and PDF-test defects found during validation.

## 8. Limits an auditor should know
- The validation ran on Windows with Excel. The Linux / no-Excel route (workbook rebuilt without recalculation, integrity re-computed in Python) is implemented and tested for logic but was not run end to end, and the pinned wheels were not installed on Linux.
- The reduced run reuses the committed parameter-posterior draws and robustness scenarios; it does not regenerate them (`run.py sim` does, and is heavy). The workbook's `M_Sims` win-probability table comes from the committed robustness 'base' scenario, so at reduced N the Excel EV parity versus Python is about 1 pp instead of 0.15 pp.
- The sensitivity analysis requested earlier (Young/Davis/Morant/LaMelo at 65 games, DARKO weight 0 and 1, role override off) was not part of this release and has not been run.
- Third-party data in `inputs/` is retained for a private audit only; see `DATA_LICENSES.md`.
