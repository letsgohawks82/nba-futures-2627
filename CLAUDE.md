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
