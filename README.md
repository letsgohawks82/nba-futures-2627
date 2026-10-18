# NBA 2026-27 futures model

Release: `v1.0-preseason.1` (immutable; supersedes nothing: the baseline tag `v1.0-preseason`, commit `da40608`, is untouched). Prices as of 2026-10-15; build 2026-10-16.
Private repository for an independent audit. Start with `AUDIT.md`, then `reports/` G0 to G8, then `reports/release_report.md`.

## One command: clean-room reproduction and validation
From a fresh clone of the tag (Python 3.13; Linux, macOS, or Git Bash on Windows):

```
git clone <repo> nba-futures-2627 && cd nba-futures-2627 && git checkout v1.0-preseason.1
scripts/cleanroom.sh                 # reduced N = 20,000 at the fixed seed 2026 (about 10-15 min)
NBA_N=100000 scripts/cleanroom.sh    # production N at the production seed: the card must match exactly
```

It (1) creates `.venv_cleanroom` from `requirements.lock.txt` (skipping `pywin32` and `xlwings` off Windows); (2) restores and verifies the frozen input archive `inputs/nba_futures_inputs_2026-10-15.tar.gz` against `data/manifest.csv` (**nothing is downloaded**); (3) runs the static tests; (4) reruns ratings, the fixed-seed simulation and pricing (team, player, joint Kelly) via `run.py repro`, writing `reports/repro_check.md`; (5) rebuilds the workbook into `repro/output/` (without Excel there is no recalculation, so the integrity checks are re-computed in Python; the committed Excel-built workbook is never overwritten); (6) runs the end-to-end tests; (7) prints SHA-256 hashes of the key inputs and outputs. Any failed step stops the run with a non-zero exit code (fail closed).

Other commands: `python run.py all` (Windows + Excel: ratings, sim, price, build, verify), `python run.py prelock [--dry-run]` (live ESPN refresh; not used by the clean-room), `python run.py repro --n N --seed S`, `python scripts/verify_inputs.py [--restore]`, `python -m pytest tests`.

## What is frozen
- `inputs/`: the input archive (231 files: odds transcription, Barttorvik, DARKO, game logs, ESPN rosters/injuries/schedule, picks, lottery rules), its SHA-256 (`INPUTS.sha256`, also in `params/release.json`) and a per-file manifest. `DATA_LICENSES.md` lists sources and terms.
- `release/final_card.csv`: the committed final card (the baseline every rebuilt card is compared with).
- `params/release.json`: version, tag, as-of dates, workbook name, baseline commit.

## Status of the DARKO blend (read this before relying on any performance claim)
The player-rating blend gives DARKO a weight of 0.5 (`w_darko`). It is an **unvalidated scenario input**: there is no point-in-time DARKO history, so DARKO never entered the historical backtest, and the weight is a documented rule rather than a fitted value. It is excluded from every out-of-sample performance claim in this repository; the backtest (RMSE 8.92, first-roster) uses box-score ratings only. The effect of the weight on team wins is shown in `data/clean/sensitivity_w_darko.csv`. Validating it would need a point-in-time DARKO archive and an end-to-end historical re-run, which has not been done.

## The final card (Tier 1: 4 active bets, 2.63% of bankroll)
Place a bet **only if all three hold**: (1) the live price is at or better than the bet's *minimum acceptable price* (EV at the 25% model / 75% market blend is still at least zero); (2) the book's rule for that market has been confirmed (PLAYOFFS = 16-team field including the play-in for MIN NO; "all 82 games must be played" for the win totals); (3) `Tier1_Card!Still bet?` is TRUE in the workbook after you enter the live price. The exact card and stakes are in `reports/release_report.md`. The model has not been shown to beat the market; the stakes are small by design.
