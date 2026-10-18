# Audit evidence (raw command output)

Collected 2026-10-18 from a FRESH CLONE of master commit `e10de95a16255d73820d3e17ec6368cd943e99ca` (Windows 11, Python 3.13, Excel 365), with outbound network blocked (`NBA_BLOCK_NETWORK=1`; attempts logged = 0). Nothing below was edited; each block is the saved stdout of the command shown. No model code, bet, stake or parameter was changed to produce this evidence.

Note on the card: the committed card (N=100,000) and the rebuilt card (N=20,000, seed 2026) list the same four bets at the same prices; the MIN playoffs-NO stake differs (0.00631 vs 0.00604) because it is Monte Carlo dependent; the other three are at the 0.75%/0.75%/0.50% caps. The test compares within 4 Monte Carlo SE. The published card is the N=100,000 one.

## audit_raw\01_tags.txt: 

```
$ git show-ref --tags
da40608119f53934171c416fc286a723eb8565e8 refs/tags/v1.0-preseason
3e09e7c5b9a441c4718b56ec638dcc0a942743ee refs/tags/v1.0-preseason.1
fcb16fa9d9843d8d3d12f6a608287719ea8edfbc refs/tags/v1.0-preseason.1-history

$ git rev-parse <tag>^{commit}
v1.0-preseason da40608119f53934171c416fc286a723eb8565e8
v1.0-preseason.1 6ca60138d2ec317ab0d3139fdbb0707b00efe072
v1.0-preseason.1-history 6304a948b2108724670e64bd89d01279d2fc3289

$ git log --oneline -n 6 master
324fef9 Clean-room: optional network guard (NBA_BLOCK_NETWORK=1) that fails the run if any outbound connection is attempted
684d15d Remove the history archive blob from the tree (release asset is the canonical copy); ignore dist/; note in HISTORY_ARCHIVE.md
6304a94 History archive addendum: bbref raw-page archive manifest + verifier + independent re-derivation of every committed historical table (all 12 agree)
6ca6013 Release v1.0-preseason.1: release report, repro check, negative controls
e6906b0 Release prep: compare reads the rebuilt card file; negative controls inject real workbook defects
3fc66f5 Release prep: repro compare fixes (side match, cold numba compile timing), PDF test, cleanroom PDF step, .gitattributes, baseline comparison + negative-control scripts

== tree of v1.0-preseason: files under dist/ (history archive blob), inputs/ ===
== tree of v1.0-preseason.1: files under dist/ (history archive blob), inputs/ ===
103 inputs/INPUTS.sha256
6664 inputs/REQUIRED_GAMELOG_READS.txt
56716 inputs/inputs_manifest.csv
716 inputs/manifest_additions.csv
19980596 inputs/nba_futures_inputs_2026-10-15.tar.gz
== tree of v1.0-preseason.1-history: files under dist/ (history archive blob), inputs/ ===
33613124 dist/nba_futures_bbref_history_2026-10-15.tar.gz
110 inputs/BBREF_HISTORY.sha256
103 inputs/INPUTS.sha256
6664 inputs/REQUIRED_GAMELOG_READS.txt
204693 inputs/bbref_history_manifest.csv
56716 inputs/inputs_manifest.csv
716 inputs/manifest_additions.csv
19980596 inputs/nba_futures_inputs_2026-10-15.tar.gz
== tree of master: files under dist/ (history archive blob), inputs/ ===
110 inputs/BBREF_HISTORY.sha256
103 inputs/INPUTS.sha256
6664 inputs/REQUIRED_GAMELOG_READS.txt
204693 inputs/bbref_history_manifest.csv
56716 inputs/inputs_manifest.csv
716 inputs/manifest_additions.csv
19980596 inputs/nba_futures_inputs_2026-10-15.tar.gz
```

## audit_raw\02_assets.txt: 

```
$ gh release view v1.0-preseason.1 --json tagName,url,assets
{"assets":[{"digest":"sha256:fb6a1c71d0c143aec81a8d2033f44bad5c397229598b5030de80d2fb5325a9a1","name":"BBREF_HISTORY.sha256","size":111},{"digest":"sha256:2588db80a7b6052ef399f8f5319c988cc5fe11c222ebdaa9eced72dc9c315ccd","name":"bbref_history_manifest.csv","size":205123},{"digest":"sha256:873d4cb5bbab74fa258addba2b870bbaa760822f01ecd8f7135f48d6a61065f5","name":"HISTORY_ARCHIVE.md","size":4577},{"digest":"sha256:9b249aedc9adf24088648ea9f1752c8bc4dc8a5ceac67f9a2af795333a1dcbcb","name":"history_rederivation.md","size":1536},{"digest":"sha256:5c1dacd90f1398ecabc8c8e796bf6af97581c7740b380d5d713a1fab0e0cbaed","name":"nba_futures_bbref_history_2026-10-15.tar.gz","size":33613124},{"digest":"sha256:b027f71974ff779cb40ce291ab643f978c0ada1a4471ddb68161d87f9701fc01","name":"nba_futures_inputs_2026-10-15.tar.gz","size":19980596},{"digest":"sha256:fb5f6b6d71cb9da7400372bc8f18ca69240a67fd653abb7ceebff18ea8be8eff","name":"release_report.md","size":14189},{"digest":"sha256:cb750eabd08dcea6b89fb4b1f8c983fb29ab730081ceb69673f1e07401b80bc4","name":"repro_check.md","size":4407}],"tag":"v1.0-preseason.1","url":"https://github.com/letsgohawks82/nba-futures-2627/releases/tag/v1.0-preseason.1"}

$ gh release download v1.0-preseason.1 -D audit_raw/dl  (all assets)

$ sha256sum of downloaded assets
fb6a1c71d0c143aec81a8d2033f44bad5c397229598b5030de80d2fb5325a9a1 *BBREF_HISTORY.sha256
873d4cb5bbab74fa258addba2b870bbaa760822f01ecd8f7135f48d6a61065f5 *HISTORY_ARCHIVE.md
2588db80a7b6052ef399f8f5319c988cc5fe11c222ebdaa9eced72dc9c315ccd *bbref_history_manifest.csv
9b249aedc9adf24088648ea9f1752c8bc4dc8a5ceac67f9a2af795333a1dcbcb *history_rederivation.md
5c1dacd90f1398ecabc8c8e796bf6af97581c7740b380d5d713a1fab0e0cbaed *nba_futures_bbref_history_2026-10-15.tar.gz
b027f71974ff779cb40ce291ab643f978c0ada1a4471ddb68161d87f9701fc01 *nba_futures_inputs_2026-10-15.tar.gz
fb5f6b6d71cb9da7400372bc8f18ca69240a67fd653abb7ceebff18ea8be8eff *release_report.md
cb750eabd08dcea6b89fb4b1f8c983fb29ab730081ceb69673f1e07401b80bc4 *repro_check.md

$ expected hashes committed in git (master)
b027f71974ff779cb40ce291ab643f978c0ada1a4471ddb68161d87f9701fc01  nba_futures_inputs_2026-10-15.tar.gz
5c1dacd90f1398ecabc8c8e796bf6af97581c7740b380d5d713a1fab0e0cbaed  nba_futures_bbref_history_2026-10-15.tar.gz

$ sha256sum of committed manifests / lock / params
8ad059ef9fca01b6ff87d8981831d61e3bc5167007169f1c829eb34d3621d560 *inputs/inputs_manifest.csv
b90c53825f6b7fb64f6cec5c29fd36b8f9e8304a24dd0301eedbf7620f512510 *inputs/manifest_additions.csv
2588db80a7b6052ef399f8f5319c988cc5fe11c222ebdaa9eced72dc9c315ccd *inputs/bbref_history_manifest.csv
2baa37c6fcabb7846b9771f9da14e666471daf736eabcf5574f9a2ff340ba5b1 *params/release.json
1847eaa8a88217457cfddcdde6d0a094d2eaf9c8c10f7a1196fa2e8ebac26827 *requirements.lock.txt (git blob content, LF)

$ compare
MATCH nba_futures_inputs_2026-10-15.tar.gz b027f71974ff779cb40ce291ab643f978c0ada1a4471ddb68161d87f9701fc01
MATCH nba_futures_bbref_history_2026-10-15.tar.gz 5c1dacd90f1398ecabc8c8e796bf6af97581c7740b380d5d713a1fab0e0cbaed

$ git show v1.0-preseason.1-history:dist/... | sha256sum (archive blob inside the history tag)
5c1dacd90f1398ecabc8c8e796bf6af97581c7740b380d5d713a1fab0e0cbaed *-
```

## audit_raw\03_cleanroom.txt: 

```
$ cleanroom log (steps, results)
=== [cleanroom] 1. venv from requirements.lock.txt (pywin32 / xlwings skipped off Windows) ===
[cleanroom] outbound network blocked for steps 2-7 (log: repro/network_attempts.log)
=== [cleanroom] 2. restore + verify the frozen input archive (SHA-256 against data/manifest.csv) ===
restored 231 files into data/raw (others already identical)
archive sha256 b027f71974ff779cb40ce291ab643f978c0ada1a4471ddb68161d87f9701fc01
files in inputs_manifest.csv: 231; verified against a manifest: 231
INPUTS OK
=== [cleanroom] 3. static tests (inputs, engine invariants, release metadata, committed card vs committed workbook) ===
============================== warnings summary ===============================
-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
12 passed, 5 deselected, 6 warnings in 192.13s (0:03:12)
=== [cleanroom] 4. ratings -> fixed-seed simulation (N=20000, seed=2026) -> pricing -> reports/repro_check.md ===
[repro] numba COLD compile time (first 64-sim run, empty cache): 95.9 s
[repro] verify_inputs: exit 0 (0.8 s)
[repro] ratings_project: exit 0 (41.1 s)
[repro] sim: exit 0 (47.5 s)
[repro] price_teams: exit 0 (32.1 s)
[repro] price_tier1: exit 0 (7.1 s)
[repro] players_sim: exit 0 (178.8 s)
[repro] price_players: exit 0 (4.8 s)
[repro] joint_kelly: exit 0 (18.9 s)
[repro] write_card: exit 0 (1.8 s)
[repro] wrote C:\Users\Max Shiner\Desktop\audit_check\reports\repro_check.md
=== [cleanroom] 5. rebuild the workbook (fail-closed on any integrity flag) and, with Excel, the dashboard PDF ===
built C:/Users/Max Shiner/Desktop/audit_check/repro/output\NBA_Futures_Model_v1_20261016_MS.xlsx 22.8 s
=== [cleanroom] 6. end-to-end tests against the rebuilt outputs ===
============================== warnings summary ===============================
-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
17 passed, 6 warnings in 62.27s (0:01:02)
=== [cleanroom] 7. SHA-256 of key inputs and outputs ===
93bc6f60626c787a01d30b829e5ebfb2d16c34913c7c8d09f91d1707e2122015  repro/rebuilt_card.csv
[cleanroom] network attempts during steps 2-7: 0
[cleanroom] ALL STEPS PASSED

$ repro/run_status.json
N 20000 seed 2026 numba_cold_s 95.9
  verify_inputs exit 0 0.8 s
  ratings_project exit 0 41.1 s
  sim exit 0 47.5 s
  price_teams exit 0 32.1 s
  price_tier1 exit 0 7.1 s
  players_sim exit 0 178.8 s
  price_players exit 0 4.8 s
  joint_kelly exit 0 18.9 s
  write_card exit 0 1.8 s

$ wc -l repro/network_attempts.log
0

$ head of reports/repro_check.md
# repro_check

Generated 2026-10-18 16:56. Rebuilt with N = 20,000, seed 2026 (committed outputs: N = 100,000, seed 2026); tolerance = 4 Monte Carlo standard errors of the difference (sqrt(1/N + 1/N0)).

**Result: PASS.** Numba COLD compile time (first 64-sim run, empty cache): **95.9 s**. Ratings reproduced to max |diff| 0.00e+00 wins (deterministic).

## Stages
| Stage | Exit | Seconds | Log |
**Result: PASS.** Numba COLD compile time (first 64-sim run, empty cache): **95.9 s**. Ratings reproduced to max |diff| 0.00e+00 wins (deterministic).
```

## audit_raw\04_history.txt: 

```
$ gh release download v1.0-preseason.1 -p "nba_futures_bbref_history_*.tar.gz" -D dist   (one-time fetch of the frozen asset; the only network use in this step)
exit 0
 
197609 16:59
5c1dacd90f1398ecabc8c8e796bf6af97581c7740b380d5d713a1fab0e0cbaed *dist/nba_futures_bbref_history_2026-10-15.tar.gz

$ NBA_BLOCK_NETWORK: PYTHONPATH=scripts/nonet python scripts/verify_history_archive.py --restore --rederive
# History re-derivation: raw Basketball-Reference pages vs the committed tables

**Result: ALL TABLES AGREE.** Each table is re-parsed from the archived raw pages and compared cell by cell (as strings) with the committed parquet / csv on the key shown. Parsers: player_rs, player_po and games use the committed code in `src/data/clean_players.py` / `clean_games.py`; team, awards, draft and the roster check had no committed parser and are re-parsed by `src/data/rederive_history.py`.

| Table | Rows re-derived | Rows committed | Keys matched | Only re-derived | Only committed | Columns compared | Mismatched cells |
|---|---|---|---|---|---|---|---|
| `player_rs_totals.parquet` | 8,870 | 8,870 | 8,870 | 0 | 0 | 34 | 0 |
| `player_rs_advanced.parquet` | 8,870 | 8,870 | 8,870 | 0 | 0 | 31 | 0 |
| `player_rs_per_poss.parquet` | 8,870 | 8,870 | 8,870 | 0 | 0 | 35 | 0 |
| `player_rs_play_by_play.parquet` | 8,857 | 8,857 | 8,857 | 0 | 0 | 27 | 0 |
| `player_po_totals.parquet` | 2,817 | 2,817 | 2,817 | 0 | 0 | 32 | 0 |
| `player_po_advanced.parquet` | 2,817 | 2,817 | 2,817 | 0 | 0 | 30 | 0 |
| `games_hist.parquet` | 16,798 | 16,798 | 16,798 | 0 | 0 | 15 | 0 |
| `team_season_hist.parquet` | 390 | 390 | 390 | 0 | 0 | 31 | 0 |
| `award_voting.parquet` | 1,009 | 1,009 | 1,009 | 0 | 0 | 26 | 0 |
| `draft_picks.parquet` | 840 | 840 | 840 | 0 | 0 | 24 | 0 |
| `schedule_raw_bbref.csv` | 1,200 | 1,200 | 1,200 | 0 | 0 | 13 | 0 |
| `rosters_bbref_2027_20261015.csv (team, player)` | 615 | 615 | 615 | 0 | 0 | 2 | 0 |
archive sha256 5c1dacd90f1398ecabc8c8e796bf6af97581c7740b380d5d713a1fab0e0cbaed
files in manifest: 429; in archive: 429; restored 280
HISTORY ARCHIVE OK
EXIT CODE: 0
network attempts: 0

# History re-derivation: raw Basketball-Reference pages vs the committed tables

**Result: ALL TABLES AGREE.** Each table is re-parsed from the archived raw pages and compared cell by cell (as strings) with the committed parquet / csv on the key shown. Parsers: player_rs, player_po and game

| Table | Rows re-derived | Rows committed | Keys matched | Only re-derived | Only committed | Columns compared | Mismatched cells |
|---|---|---|---|---|---|---|---|
| `player_rs_totals.parquet` | 8,870 | 8,870 | 8,870 | 0 | 0 | 34 | 0 |
| `player_rs_advanced.parquet` | 8,870 | 8,870 | 8,870 | 0 | 0 | 31 | 0 |
| `player_rs_per_poss.parquet` | 8,870 | 8,870 | 8,870 | 0 | 0 | 35 | 0 |
| `player_rs_play_by_play.parquet` | 8,857 | 8,857 | 8,857 | 0 | 0 | 27 | 0 |
| `player_po_totals.parquet` | 2,817 | 2,817 | 2,817 | 0 | 0 | 32 | 0 |
| `player_po_advanced.parquet` | 2,817 | 2,817 | 2,817 | 0 | 0 | 30 | 0 |
| `games_hist.parquet` | 16,798 | 16,798 | 16,798 | 0 | 0 | 15 | 0 |
| `team_season_hist.parquet` | 390 | 390 | 390 | 0 | 0 | 31 | 0 |
| `award_voting.parquet` | 1,009 | 1,009 | 1,009 | 0 | 0 | 26 | 0 |
| `draft_picks.parquet` | 840 | 840 | 840 | 0 | 0 | 24 | 0 |
| `schedule_raw_bbref.csv` | 1,200 | 1,200 | 1,200 | 0 | 0 | 13 | 0 |
| `rosters_bbref_2027_20261015.csv (team, player)` | 615 | 615 | 615 | 0 | 0 | 2 | 0 |
```

## audit_raw\05_outputs.txt: 

```
$ deterministic outputs: rebuilt file sha256 vs the same path in git tag v1.0-preseason.1 (committed baseline, LF bytes)
IDENTICAL data/clean/team_projection_2027.csv 5bbfb8805ea6fd4a7f1e174f816405dadb9ed2890bf261bad7feaf8f0d79c883
IDENTICAL data/clean/player_projection_2027.csv 20e50f6081423df36f44fd0d4a7d1ca82027bf108609ccb2a827b9e36974aafe

$ MC-dependent outputs (expected to differ: N=20000 vs N=100000)
data/clean/sim_team_summary.csv tag=d603fd4750e24874 rebuilt=0f1250f65ed2d5a1 differs
data/clean/pricing_table.csv tag=ca78b92d593bc465 rebuilt=bf6e1b8536705b63 differs
data/clean/player_pricing_table.csv tag=3ac6b6b40e22b07f rebuilt=6c4d1ab53b619349 differs
data/clean/joint_summary.json tag=386ac43dc65cab19 rebuilt=01038af0ff207611 differs

$ committed card vs rebuilt card
market,selection,side,line,american,stake_frac
PLAYOFFS,Minnesota Timberwolves,NO,,550,0.00630726989
WINS,Portland Trail Blazers,OVER,42.5,115,0.005
WINS,Utah Jazz,UNDER,37.5,115,0.0075
WINS,Washington Wizards,UNDER,35.5,-140,0.0075
---
market,selection,side,line,american,stake_frac
PLAYOFFS,Minnesota Timberwolves,NO,,550,0.006040472825
WINS,Portland Trail Blazers,OVER,42.5,115,0.005
WINS,Utah Jazz,UNDER,37.5,115,0.0075
WINS,Washington Wizards,UNDER,35.5,-140,0.0075

$ workbook_build_report.json (rebuilt workbook)
{'excel_recalc': True, 'overall_checks_failing': 0.0, 'tier1_count': 4.0, 'bet_count': 39.0, 'sim_status': 'OK - sims match current assumptions'}

$ integrity flags (rebuilt workbook)
flags: [] | computed cached statuses: True
analytic vs sim max pp, rows >2pp: (np.float64(1.795490320336529), [])
     market               selection   side source  cached_stake
0  PLAYOFFS  Minnesota Timberwolves     NO   team       0.00604
1      WINS      Washington Wizards  UNDER   team       0.00750
2      WINS               Utah Jazz  UNDER   team       0.00750
3      WINS  Portland Trail Blazers   OVER   team       0.00500
card_from_tables:
     market               selection   side  stake_frac
0  PLAYOFFS  Minnesota Timberwolves     NO     0.00604
1      WINS  Portland Trail Blazers   OVER     0.00500
2      WINS               Utah Jazz  UNDER     0.00750
3      WINS      Washington Wizards  UNDER     0.00750
tier1 live flags: [True, True, True, True]
Tier1_Card A2: Tier1_Card - the staked card (4 active Tier 1 bets): min acceptable price, live price check, consensus basis
Tier1_Card A3: Version: v1.0-preseason.1 | prices as of 2026-10-15 | build 2026-10-16
Cover: [('Version', 'v1.0-preseason.1 (baseline tag v1.0-preseason)'), ('Build date', '2026-10-16'), ('Prices as of', '2026-10-15 (book odds transcription); external consensus / exchange inputs as of 2026-10-16'), ('Data timestamp', 'Rosters/injuries ESPN pulled 2026-10-15; DARKO through 2026-06-03'), ('DARKO blend', 'UNVALIDATED scenario input: production blend weight 0.5 is a documented rule; there is no point-in-time DARKO history, so DARKO never entered the historical backtest and the blend is excluded from every out-of-sample performance claim'), ('Sim N', 20000)]
Checks C col statuses: ['INFO', 'OK']

$ params/release.json
{
 "version": "v1.0-preseason.1",
 "baseline_tag": "v1.0-preseason",
 "odds_as_of": "2026-10-15",
 "consensus_as_of": "2026-10-16",
 "build_date": "2026-10-16",
 "workbook_file": "NBA_Futures_Model_v1_20261016_MS.xlsx",
 "workbook_title": "NBA 2026-27 Futures Model",
 "darko_blend_status": "UNVALIDATED scenario input: production blend weight 0.5 is a documented rule; there is no point-in-time DARKO history, so DARKO never entered the historical backtest and the blend is excluded from every out-of-sample performance claim",
 "analytic_sd_scale": 0.9423,
 "analytic_skew_slope": -0.021175,
 "analytic_provenance": "Display/live-reprice layer only (bets use the simulation). SD scale = least-squares fit of the formula SD to the 30 simulated SDs (100k sims, G8 build); skew slope = OLS of the 30 simulated win-distribution skewnesses on (mean wins - 41), applied as an Edgeworth skew term. Neither parameter was tuned to the 2pp check.",
 "inputs_archive": "inputs/nba_futures_inputs_2026-10-15.tar.gz",
 "inputs_archive_sha256": "b027f71974ff779cb40ce291ab643f978c0ada1a4471ddb68161d87f9701fc01",
 "baseline_commit": "da40608119f53934171c416fc286a723eb8565e8"
}
$ DARKO label evidence
README.md:28:The player-rating blend gives DARKO a weight of 0.5 (`w_darko`). It is an **unvalidated scenario input**: there is no point-in-time DARKO history, so DARKO n
AUDIT.md:10:- **Player impact and team strength.** Basketball-Reference BPM-based player ratings (decayed three-season prior, reliability shrinkage, aging, a college/draf
params/release.json:9: "darko_blend_status": "UNVALIDATED scenario input: production blend weight 0.5 is a documented rule; there is no point-in-time DARKO history, so DA
Assumptions row 16 : DARKO_weight (player-metric blend) | UNVALIDATED scenario input: production DARKO vs box-prior blend (documented rule). There is no point-in-time DARKO history, so DARKO never entered the historical backtest and the blend is excluded from every out-of-sample performance claim
```

## audit_raw\06_pytest.txt: 

```
$ pytest -v (fresh clone e10de95)
tests/test_engine.py::test_tiebreak_cases PASSED                         [  5%]
tests/test_engine.py::test_sim_invariants PASSED                         [ 11%]
tests/test_inputs.py::test_required_inputs_present PASSED                [ 17%]
tests/test_inputs.py::test_archive_and_every_hash_verify PASSED          [ 23%]
tests/test_inputs.py::test_production_code_only_reads_archived_raw_paths PASSED [ 29%]
tests/test_inputs.py::test_no_network_in_reproduction_stages PASSED      [ 35%]
tests/test_release_static.py::test_tests_do_not_contain_vacuous_assertions PASSED [ 41%]
tests/test_release_static.py::test_final_card_csv_matches_committed_pricing_tables PASSED [ 47%]
tests/test_release_static.py::test_workbook_tier1_rows_count_and_stakes_agree_with_card PASSED [ 52%]
tests/test_release_static.py::test_workbook_has_no_integrity_flags PASSED [ 58%]
tests/test_release_static.py::test_release_metadata_agrees_everywhere PASSED [ 64%]
tests/test_release_static.py::test_darko_blend_is_labelled_unvalidated PASSED [ 70%]
tests/test_repro_outputs.py::test_every_stage_ran_and_exited_zero PASSED [ 76%]
tests/test_repro_outputs.py::test_ratings_and_pricing_ran_from_the_frozen_inputs_only PASSED [ 82%]
tests/test_repro_outputs.py::test_rebuilt_outputs_agree_with_committed_outputs_within_monte_carlo_error PASSED [ 88%]
tests/test_repro_outputs.py::test_rebuilt_final_card_equals_committed_card PASSED [ 94%]
tests/test_repro_outputs.py::test_repro_report_says_pass PASSED          [100%]
================== 17 passed, 6 warnings in 68.57s (0:01:08) ==================
pytest exit: 0
```
