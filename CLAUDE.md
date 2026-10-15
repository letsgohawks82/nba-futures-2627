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
