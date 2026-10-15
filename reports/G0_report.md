# G0 Report — Environment (2026-10-15)

## Built
- Python 3.13.15 (≥3.11 ✔). venv `.venv`; all 17 requested packages installed (pandas 3.0.6, numpy 2.5.4, scipy 1.18.1, statsmodels 0.15.0, scikit-learn 1.9.1, numba 0.68.0, nba_api 1.11.4, requests 2.34.2, requests-cache 1.3.3, beautifulsoup4 4.15.0, lxml 6.1.3, openpyxl 3.1.5, xlwings 0.37.6, pywin32 312, pyarrow 26.0.0, tqdm 4.70.1, pdfplumber 0.11.10). Versions pinned in `requirements.lock.txt`.
- Excel 365 (v16.0) via xlwings: opened, wrote formula, recalculated (=A1*21 → 42), saved, closed. ✔
- Repo layout per spec (src/{data,ratings,sim,awards,pricing,workbook,verify}, data/{raw,clean}, params, sims, reports, output), `run.py` stub CLI, `CLAUDE.md`, `.gitignore`.
- `odds_2026-10-15.csv` copied to `data/raw/odds/` (687 rows).
- Local git initialised; commit "G0".

## Open issues / decisions
- Desktop is not OneDrive-redirected; root is `C:\Users\Max Shiner\Desktop\NBA`.
- `.gitignore` excludes `data/raw/` and `sims/` (large caches); say so if you want them tracked.
- `run.py parse-odds` is declared in the CLI but not yet implemented (scheduled with G5 workbook/odds work).

Awaiting "approve G0".
