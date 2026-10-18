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
