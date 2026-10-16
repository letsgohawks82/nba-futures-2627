# CLAUDE.md — NBA 2026-27 Futures Model
Running state for context across sessions. Full requirements in SPEC.md (authoritative).

## Rules to remember
- Gated build G0–G6: stop after each gate, write reports/G#_report.md, wait for Max's "approve G#", commit "G#: ...".
- Market odds are NEVER model inputs (pricing/edge tabs + backtest benchmark only).
- No fabricated data; provenance for every fitted param in params/provenance.json.
- Bet needs lower CI bound of EV > 0. Imputed odds sides never on Bet Card.
- Excel format: Arial 10, blue inputs / black formulas / green cross-sheet / red flags, navy #1F3864 headers, no merged cells.
- Be polite to sources: cache raw to data/raw/ w/ timestamp; bbref <=15 req/min; nba_api 0.6s sleep + backoff.

## Environment (G0, 2026-10-15)
- Root: C:\Users\Max Shiner\Desktop\NBA (Desktop not OneDrive-redirected). Local git, no remote.
- Python 3.13.15 (py launcher); venv at .venv — use `.venv\Scripts\python.exe`.
- Excel 365 (16.0) verified via xlwings (src/verify/xl_smoke.py).
- run.py is a stub CLI; stages implemented in later gates.

## Status
- G0: done, awaiting approval.

## Gotchas
- Windows shell; use .venv\Scripts\python.exe explicitly.
- Odds CSV: 687 data rows; columns market,selection,side,line,american,flag.

## G1 (2026-10-15) - data pulled, awaiting approval
- nba_api/cdn.nba.com blocked from this IP -> bbref + ESPN site API + barttorvik fallbacks; no tracking/hustle; in-house RAPM infeasible.
- Schedule = 1,200 games (80/team); 2 games/team Dec 4-10 depend on Cup results (generate in G3). 60 Cup group games; groups equal the book groups.
- 3-2-1: 37 balls (6+21+8+2), floor #12 for 3 worst, restrictions follow the original team's pick; deadline Feb 11 2027 3pm ET. Draw mechanics not public (assumption in report).
- Code: src/data/. Clean outputs: data/clean/. data/manifest.csv is committed; data/raw is git-ignored.
- Raw bbref html from first pull is mojibake; clean parquets repaired.
- Gotcha: pandas 3 string dtype is not object; use pd.api.types.is_string_dtype.

## G2 (2026-10-15) - ratings + backtest done, awaiting approval
- Model: src/ratings/{prep,model,rookies,backtest,project_2027}.py. BPM-based player impact (lambda .55, M0 600), college rookie model, availability model, team layer SRS~teamsum+prevSRS; wins=41+2.44*SRS, sums to 1230.
- Backtest 2019-2026: RMSE 8.44 [7.97,8.90] vs 10.2 baselines (paired diff CI excludes 0). No free market-line archive -> no market benchmark. Roster membership proxy leaks slightly.
- w_darko=0.35 is an ASSUMPTION (no DARKO history). nba_api still blocked -> no in-house RAPM until after lock.
- Lottery sim src/sim/lottery.py (draws param). User default 4 draws conflicts with sources (16). Restricted: UTA no top-5, WAS no #1. LAC/TOR pick terms = toggle.
- Cup module spec in params/assumptions.json (NBA.com: semis at higher seed, 2 cross-conf nonqualifier games; user spec differs; toggles).
- Overrides: params/overrides_players.csv (blank template); ESPN Out injuries applied automatically.
- run.py ratings = backtest + project_2027.

## G2 addendum (approved w/ changes)
- lottery_n_draws=16 (documented fact). Cup: NBA.com official (semis at higher seed home; 2 of 22 non-qualifier games cross-conference). Both in params/assumptions.json.
- Backtest headline = FIRST-TEAM roster proxy RMSE 8.92 [8.42,9.42] (not 8.44, which leaks in-season trades). No-moves bound 10.30 (no better than baselines): skill depends on knowing offseason moves. Strongest baseline B4 RMSE 10.21. DARKO never in backtest; production w_darko=0.5 documented rule, untested.
- LAC/TOR conflict resolved (timing only; penalty took 2029-33 picks). Tank win-delta to be reported in G3.

## G3 (2026-10-15) - simulation engine done, awaiting approval
- Code: src/sim/{engine,season,runner,inputs,lottery,fit_game_model,tank_fit,calibrate,run_sim}.py. `run.py sim` = 100k sims (~15s after JIT; clear src/sim/__pycache__/*.nb* after editing engine.py - numba cache is keyed to season.py).
- par[] layout is documented in engine.py docstring; PAR_NAMES in inputs.py (index 27 = cup_on).
- Fits: HCA 1.89, b2b -2.65/+2.53, sigma_game 13.49, post HCA 3.64; kappa 0.28 (CI includes 0; excl. 2020 bubble); playoff lambda 0.58 [0.32,0.80]; sigma_team_srs 3.5 (calibrated by variance ratio, p=0.13).
- LAC/TOR toggle delta <=0.02 wins -> no no-bet flag. Title market is most sensitive to playoff lambda (OKC 15.6-23.3%).
- Tests: tests/test_engine.py; independent check: src/verify/title_check.py + compare_title.py (max title diff 0.22pp).

## G3 addendum (conditional approval) - done
- sigma_team_srs = 3.25 (LOSO CV, availability ON; SD/RMSE 0.98; VR 1.04 p=0.33). Production predictive SD 8.51 wins. kappa production 0.28; robustness upper kappa 1.57; sigma +/-10%.
- Tank carryover: bottom-8 2025-26 teams had post-deadline lineup collapse (UTA, MEM, WAS, SAC, BKN). params: data/clean/pre_deadline_role_override_2026.csv applied in project_2027 (role_override=True). Max win shift UTA +0.7.
- Robustness scenarios: data/clean/sim_robust_*.csv; Bet Card rule in src/pricing/robust.py (bottom-10 projected teams need EV>0 under kappa0/kappa_hi/sigma_lo/sigma_hi).
- Next: G5 team markets (G4 player markets deferred until after Bet Card).

## G5 (2026-10-15) - workbook + team Bet Card, awaiting approval
- Build: `run.py price` (src/pricing/run_pricing.py) then `run.py build` (src/workbook/build.py -> output/NBA_Futures_Model_v1_YYYYMMDD_MS.xlsx; Excel/xlwings sets Bet_Card + Dashboard dynamic arrays, recalcs, scans errors, reads Checks). Audit: `python -m src.workbook.audit`.
- 22 tabs; formulas live except engine outputs (M_Sims). Sim staleness via Assumptions key vs M_Sims!B9. bet_card_formula uses LET/FILTER/SORTBY/HSTACK (Excel 365 only).
- PLAYOFFS market: book prices sum to ~top-8, rule text says top-10 -> unresolved; A_poconf=0 blocks PLAYOFFS bets. 89 qualifying bets otherwise (EV>=3%, CI low>0, robust, not imputed).
- Bet Card caveat: model-vs-book mean |gap| 3.9 wins; no market benchmark exists; CI = parameter uncertainty only.
- Gotchas: openpyxl cannot write the spill operator (#) -> set via xlwings formula2; Excel PageSetup/PDF export fails without a printer; numba cache clear needed after engine edits; Bash heredocs with certain quotes fail -> use Write tool.
- Next: G4 (player markets) then G6 (audit + delivery PDF).

## G5 revision (miscalibration diagnosis; approved fixes)
- ROOT CAUSE: sim expected wins were compressed vs the calibrated projection. Fix = src/sim/meanmatch.py (moment-match sim ratings to 41+k*SRS), applied in inputs.build (default), robust scenarios, param draws, hist calibration. sigma_team refit to 3.5 (LOSO, matched). Production predictive SD 8.77.
- Filters (run_pricing.py): zero-sum (WINS means +0.367), shrink 0.5 edge test, robustness, longshot (<5% fair), EV-bucket exclusion (none flagged), continuity<0.55 -> shrink 0.75 for WINS/PLAYOFFS/DIV, compression rule (no WINS unders on mkt top-5 / overs on bottom-5; params/verified_drivers.csv for exceptions). Waterfall in data/clean/qualification_waterfall.json: raw 75 -> 91 -> 89 -> 63 -> 63 -> 63 -> 59 -> 52 final.
- PLAYOFFS = 16-team field (Bracket), user-confirmed; confirm with book. PLAYOFFS portfolio outcome now uses the bracket flag (bit 128).
- Model vs market: RMSE 4.22, slope .76, compression slope -0.24 [-0.34,-0.13]; backtest residual slope +0.015 (no over-regression). Roster audit: ESPN vs model 0 diffs; Robinson signed with BOS (FA).
- New modules: src/pricing/{diagnostics,drivers,compression}.py, src/sim/{meanmatch,sensitivity}.py.

## G5 Tier 1 (2026-10-15)
- Tier 1 = filter tab (Tier1_Card) over the 52-bet Tier 2 card; Tier 2 unstaked by default (Assumptions tier2_staking_on=0). Code src/pricing/tier1.py (run via `run.py price`). Funnel 52 -> 27 (shrink .75) -> 20 (fair>=5%) -> 19 (direction) -> 4 (named driver). Stake 2.0% total, cap 10%. Report reports/G5_tier1.md.
- Next: G4 player markets (user: awards/stat leaders are softer markets).

## G4 (2026-10-15) - player markets built, awaiting approval
- LDR_TPG = THREE-POINTERS MADE per game (not turnovers; G1 note was wrong). src/players/*, `run.py sim` ends with run_g4; `run.py price` ends with price_players. Leader probs sharpened p^1.4 (g4_leader_sharpen.json). 5 player Tier 1 bets (2.3% stake) on M_Players; not yet merged into Tier1_Card/Exposure. Report reports/G4_report.md.
- Next: G6 (independent verification, final report, PDF); merge player Tier 1 into Exposure if Max wants.

## G6 (2026-10-15) - done, awaiting approval
- Leader sharpening gamma by LOSO CV = 1.50 [1.30,1.75]; SD/calibration now on top-15. Joint Kelly (src/pricing/joint.py; run.py price order: run_pricing, tier1, price_players, joint) -> 9 Tier 1 bets, 4.9% stake. Tier1_Card player block at row 41; Exposure has joint corr. Independent verify: src/verify/g6_independent.py. PDF via src/workbook/export_pdf.py (matplotlib, no printer needed). Final report reports/G6_final.md.

## G6 update (2026-10-15)
- Player minutes: top-5 per team keep calibrated mpg_hat (src/players/pool.py star_protected_mpg, g4_mpg_calib.json); team layer untouched. Tier 1 = 4 bets (MIN playoffs NO, ROY Dybantsa, RPG Sabonis, 3PM LaMelo), 2.78% stake. params/tier1_overrides.json holds the CHI exclusion and TOR scenario gate (src/pricing/scenario_market_ratings.py; srs_shift override in inputs.build). Report reports/G6_update.md.

## G7 (2026-10-15) - final pre-lock build
- 8 Tier 1 bets, 3.90% stake: MIN playoffs NO, ROY Dybantsa (x0.5 via A_roy_stake_mult), RPG Sabonis, 3PM LaMelo, WINS WAS/UTA/MIA U and POR O (consensus rule, caps 0.5%, MIA x0.7). Consensus: src/pricing/consensus.py + Raw_Consensus tab + M_WinDist cols; inputs data/consensus/. Tier1_Card is now fixed rows with blue inputs (live price, rule confirmed); Tracker pre-populated. `run.py prelock [--dry-run]` = src/prelock.py (ESPN codes normalised; guard restores inputs). Params in params/tier1_overrides.json. Report reports/G7_final.md.

## G8 (2026-10-16)
- Team-layer minutes: allocate_minutes now star-protected (top-3 by mpg_hat keep a+b*mpg_hat minutes; src/ratings/model.py STAR_K=3, backtest src/ratings/minutes_backtest.py); team layer refit, sims re-run. Consensus v2 (src/pricing/consensus.py): per-source regression residuals, roster-aware pair (ours+PredictionEngine) must agree >=2.5; results-based sources only veto. Data: data/consensus/raw_consensus_20261016.csv, raw_marketref_20261016.csv. Blended-probability gate (src/pricing/marketref.py, price_players). params/tier1_overrides.json has exclude + HOLD lists (MIA U/NO, IND NO, Gobert RPG, CHI playoffs, Sabonis). Card = WAS U, UTA U, POR O, MIN NO (2.63%). Report reports/G8_final.md. Awaiting user decision on HOLD items.

## Known weaknesses for next season (G8 decision, 2026-10-16)
- MVP / DPOY / ROY models are DISPLAY-ONLY: voting models trained on 12-13 winners, rookie minutes unknowable pre-season, and they fail sanity checks against exchanges and the GM survey (Dybantsa ROY 46% vs ~19%, Wembanyama MVP 8% vs 33%). Revisit with a longer voting history (pre-2014 pools), a proper candidate-pool/ballot model, and a minutes model that handles Wembanyama-type availability before re-enabling.
- Stat-leader bets are eligible only with an external reference (exchange average in Raw_MarketRef); none exists today so no player bets. Leader probabilities are very sensitive to minutes allocation (LaMelo/Gobert flip between top-3 and top-5 minutes protection).
- Final G8 card: WAS U, UTA U, POR O, MIN NO (2.63%); held (not released): MIA U/NO, IND NO, Gobert RPG.
