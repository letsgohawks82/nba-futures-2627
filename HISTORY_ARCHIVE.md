# HISTORY_ARCHIVE.md: raw Basketball-Reference pages behind the committed tables

Release: `v1.0-preseason.1` (this addendum is tagged `v1.0-preseason.1-history`; the release tag itself is untouched). Private audit use only; see `DATA_LICENSES.md`.

## What it is
`nba_futures_bbref_history_2026-10-15.tar.gz` (33.6 MB; 429 files; 240.5 MB raw) is a **GitHub release asset of `v1.0-preseason.1`, not committed to git**. It holds every raw Basketball-Reference page that feeds the committed tables in `data/clean/`: player season tables (`player_rs`, `player_po`), game results (`games`), team, awards, draft, roster-check, the 2027 schedule, the 142 player game logs and the coaches page. Archive SHA-256: `5c1dacd90f1398ecabc8c8e796bf6af97581c7740b380d5d713a1fab0e0cbaed` (committed in `inputs/BBREF_HISTORY.sha256`; the archive is deterministic, so it rebuilds to the same hash).

`inputs/bbref_history_manifest.csv` lists every file with: relative path, byte size, SHA-256, source URL, retrieval timestamp, the code that consumes it, the tables derived from it, the parser path, the parser version (git blob id of the parser plus the pinned bs4 / lxml / pandas versions from `requirements.lock.txt`), and whether the file is also in the first input archive (`inputs/nba_futures_inputs_2026-10-15.tar.gz`; the 142 game logs are in both). Every SHA-256 equals the pull-time hash in `data/manifest.csv`.

## Restore and verify (no network access by the scripts)
```
gh release download v1.0-preseason.1 -p "nba_futures_bbref_history_*.tar.gz" -D dist     # one-time fetch of the frozen asset (or copy it to dist/ by hand)
python scripts/verify_history_archive.py --restore --rederive
```
`verify_history_archive.py` checks the archive hash, that the members are exactly the manifest's files, every file's size and SHA-256 against the manifest and against `data/manifest.csv`, extracts into `data/raw/` (git-ignored), and with `--rederive` re-parses the raw pages and compares every committed table (`src/data/rederive_history.py`). It exits non-zero on any problem. The result of the run for this release is `reports/history_rederivation.md`.

## How it relates to the `v1.0-preseason.1` outputs
```
raw bbref pages (this archive) --parse/clean--> data/clean/*.parquet|csv (committed) --> ratings --> simulation --> pricing --> card
```
- The production reproduction (`scripts/cleanroom.sh`) starts from the committed parquets and needs only the first archive; this archive is **not** needed to run the model. It exists so that the committed parquets can be shown to be derived from the pages, honestly and completely.
- Re-derivation result: **all 12 tables agree cell for cell** (player_rs x4, player_po x2, games_hist, team_season_hist, award_voting, draft_picks, schedule_raw_bbref, and the team/player membership of `rosters_bbref_2027_20261015.csv`): 61,953 rows, 0 mismatched cells, 0 missing or extra rows.
- Two documented transformations are applied by the re-derivation because the committed tables contain them: (1) the raw pages were saved mojibake (UTF-8 bytes decoded as latin-1), and the committed tables carry the repaired text (`CLAUDE.md`, G1; implemented as `fix_text` in `rederive_history.py`); (2) the roster-check list drops the two-way `(TW)` tag.
- **Parser provenance, honestly:** `src/data/clean_players.py` and `clean_games.py` (player and game tables) and `pull_schedule.py` / `clean_schedule.py` (schedule) are committed code. The parsers that produced `team_season_hist`, `award_voting`, `draft_picks` and the roster-check tables were run ad hoc in the G1 / G5 sessions and were **never committed**; `rederive_history.py` is a new independent parser for them, and its agreement with the committed tables is the evidence. Likewise the mojibake repair has no original script.
- Game logs: `src/ratings/tank_carryover.py` reads them directly (its outputs, `data/clean/tank_carryover_*.csv` and `pre_deadline_role_override_2026.csv`, are tracked and feed the 2027 projections as a role override).
- Not in this archive (they are in the first archive or tracked): Barttorvik, DARKO, ESPN, the odds transcription, pick-ownership and lottery pages, the consensus and exchange inputs.
- Point-in-time integrity: every page was retrieved on 2026-10-15 (timestamps in the manifest), after the 2025-26 season; the committed historical tables therefore contain only final results for 2014-2026, and the backtest's point-in-time construction is in `reports/G2_report.md` / `G2_addendum.md` (box-score ratings only; DARKO excluded).
