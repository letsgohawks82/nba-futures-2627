| Control | Test | Before | With the defect | After restore | Last line |
|---|---|---|---|---|---|
| a required raw input (odds CSV) is deleted | `test_required_inputs_present` | passes | **FAILS** | passes | 1 failed in 0.26s |
| one byte of a Barttorvik file is changed | `test_archive_and_every_hash_verify` | passes | **FAILS** | passes | 1 failed in 0.93s |
| a stake in release/final_card.csv is edited | `test_final_card_csv_matches_committed_pricing_tables` | passes | **FAILS** | passes | 1 failed in 1.67s |
| params/release.json carries a different version than README/AUDIT/workbook | `test_release_metadata_agrees_everywhere` | passes | **FAILS** | passes | 1 failed in 1.65s |
| `or True` is put back in tests/test_engine.py | `test_tests_do_not_contain_vacuous_assertions` | passes | **FAILS** | passes | 1 failed in 1.70s |
| a FLAG is injected into Checks!C23 of the workbook | `test_workbook_has_no_integrity_flags` | passes | **FAILS** | passes | 1 failed, 1 warning in 3.87s |
| the Tier1_Card title says 8 bets while 4 are active | `test_workbook_tier1_rows_count_and_stakes_agree_with_card` | passes | **FAILS** | passes | 1 failed, 2 warnings in 9.15s |
| a bet is added to the rebuilt card | `test_rebuilt_final_card_equals_committed_card` | passes | **FAILS** | passes | 1 failed in 1.77s |
| the repro run status is missing | `test_every_stage_ran_and_exited_zero` | passes | **FAILS** | passes | 1 error in 1.56s |
| a stage (ratings) exited non-zero | `test_every_stage_ran_and_exited_zero` | passes | **FAILS** | passes | 1 failed in 1.60s |
