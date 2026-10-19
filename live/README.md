# live/ - append-only prediction log

`opportunities_<UTC date>_<HHMM>.csv` = one snapshot of EVERY market the model evaluated (team + player, 1,080 rows for the 10/15 book), with the book price, de-vigged fair price, model probability, EV, status (CARD / HELD / EXCLUDED / TIER2 / DISPLAY_ONLY / IMPUTED / NOT_BET), recommended stake, git commit, release, sim N and seed. Files are never edited or overwritten (`snapshot` refuses if the name exists); `*.sha256` hashes the content.

**The prices in a snapshot are the book's 10/15 transcription, not a live quote.** To log live prices, update `data/raw/odds` through the normal pipeline and snapshot again; do not edit a snapshot.

Closing prices are typed in by hand (nothing is scraped) in a CSV with columns `market,selection,side,line,closing_american[,closed_at_utc,result]` and appended with
```bash
.venv/Scripts/python.exe -m src.live.opportunity_log close closes.csv
```
which writes `clv_ledger.csv` (CLV in implied-probability points against the FIRST snapshot's price) and prints mean / median / share-positive by status. Statuses are logged for held and unbet markets too, so selection can be judged: does the CARD beat the NOT_BET and HELD sets on CLV?

Interpretation: positive CLV on the 4 card bets alone is far too small a sample to conclude anything; the TIER2 / HELD / NOT_BET rows give a larger shadow sample. The workbook Tracker tab records placed bets and CLV for real stakes.
