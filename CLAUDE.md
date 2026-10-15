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
