# G1 Report — Data acquisition + validation (2026-10-15)

**Status: complete, awaiting "approve G1".** Raw pulls are cached in `data/raw/` (git-ignored). `data/manifest.csv` (file, source URL, pull timestamp, rows, SHA-256, note) is committed and covers every raw pull plus the derived clean files.

## 0. Decisions needed from Max (read first)
1. **Schedule is 1,200 games, not 1,230.** The NBA released 80 of 82 games per team. The other **2 per team (30 games) are played Dec 4–10 and are determined by Emirates NBA Cup group results** (NBA release, found via search). bbref and ESPN both show exactly 1,200 and agree game for game. G3 must generate those 30 games from simulated Cup outcomes, and I have not found the pairing rule. The spec check "1,230 / 82 per team" therefore fails by design. Please confirm the G3 approach.
2. **stats.nba.com and cdn.nba.com are unreachable from this machine.** stats.nba.com read-times-out at 90 s; cdn.nba.com returns 403. I used the bbref fallback wherever the spec lists one. Consequences: no Hustle/Defense tracking splits, and the in-house RAPM fallback (needs nba_api play-by-play stints) is not feasible from this IP. Options: (a) run the nba_api pulls from another network and drop the files in `data/raw/`; (b) accept bbref on/off + BPM + DARKO as the impact inputs.
3. **DARKO:** the free site has only an on-page leaderboard (530 players, "Ratings through June 3, 2026"; no stable API). I read the table through the browser pane and trimmed it to DPM/O/D/box/on-off/MPG. I did not use the "Download CSV" button, because downloads need your OK. The ratings are 4+ months old, so they are fine as a prior but not as current. I found no free multi-year RAPM CSV (nbarapm.com has dataset pages but no confirmed download URL; squared2020 is paid and covers only 1985–96).
4. **3-2-1 details missing from every public source** (see §1): the draw count and mechanics, and what happens when a restricted team's ball is drawn at a blocked slot. I need your call on the modelling assumption; my default is in §1.
5. **Pick ownership** rests on one full source (Hoops Rumors, Sep 2026 snapshot, citing RealGM) plus partial confirmations (OverTheApron ledger for NYK/BKN/HOU/LAL, ESPN for UTA→MEM). Trades since September are not captured. I recommend re-checking before G3.
6. **TPG (turnover leader) market:** NBA.com lists no official turnover qualifier. I need the book's rule text.

## 1. Official 3-2-1 lottery (halt condition — passed for ball allocation)
The allocation is confirmed by **3 sources** (NBA.com release 5/28/2026, ESPN, Hoops Rumors). There are 16 teams and **37 balls**:
- 3 worst records × 2 balls = 6
- 4th–10th worst × 3 balls = 21
- #9/#10 play-in seeds in each conference × 2 balls (4 teams) = 8
- Losers of the 7-vs-8 play-in games × 1 ball (2 teams) = 2

All 16 first-round picks are drawn. The 3 worst teams cannot fall below #12; all others can fall to #16. The system applies to the 2027–2029 drafts, with an opt-out after 2029. The vote was 29–1.

- **Which teams count as the "8-seed" that enters the lottery:**
  - It is the loser of each conference's 7-vs-8 play-in game (1 ball), not the 8th-place finisher. NBA.com's wording is that 7-vs-8 play-in losers get one ball.
  - That team still plays the 9/10 winner afterward and can become the 8 seed. No source says whether a team that wins that second game and makes the playoffs keeps its ball. ESPN loosely says the lottery "adds the 8-seed".
  - The quoted 2.7% for #1 (1/37) implies the ball exists at lottery time.
  - **Open item.** Proposed default: balls attach to the 7v8 loser and the 9/10 seeds (by regular-season record), and a team that wins into the playoffs keeps its ball(s). Flagged on M_Lottery2027.
- **Restrictions** (NBA.com, ESPN and Hoops Rumors agree):
  - A team's own pick cannot be #1 in two consecutive drafts, and cannot be top-5 in three consecutive drafts.
  - The 2025 and 2026 drafts count retroactively.
  - They apply to the pick regardless of trade. NBA.com says so explicitly, and ESPN's example is UTA's 2027 pick, owned by MEM, which can be no higher than 6th.
  - CBS says it is unclear whether acquired picks are covered. I am following the NBA.com/ESPN wording: the restriction travels with the original team's pick.
- **Mechanics gap:**
  - No source states the number or sequence of draws, or what happens when a restricted team's ball is drawn at a blocked slot.
  - A third-party simulator (hoopsjunkie) says the pick moves down to the next valid slot.
  - Default proposal: draw sequentially for picks 1–16 without replacement, and if a restricted team's ball would take a barred slot, redraw. This is an assumption and is flagged.
- **Applicable to the 2027 draft:**
  - WAS (won the 2026 #1) cannot get #1. UTA (2025 #5, 2026 #2) is barred from the top 5. Per ESPN, UTA is the only top-5 case.
  - 2025 top-5 holders: DAL, SAS, PHI, CHA, UTA. 2026 top-5 holders: WAS, UTA, MEM, CHI, LAC.
  - bbref lists the team that made the pick, not the original owner. Checking original owners of the 2025/26 top-5 picks is an open item.
- Newly traded picks cannot carry top-12 to top-15 protections; existing protections stand. The league may cut odds, shift position or fine teams for tanking.
- **Trade deadline:** Thursday **Feb 11, 2027, 3:00 pm ET** (NBA.com key dates give Feb 11; the time is from Hoops Rumors citing the NBA).
- **Other dates:**
  - Season: Oct 20 → Apr 11.
  - Cup: group play Oct 30–Nov 27, quarterfinals Dec 4–5, semifinals Dec 8/9, final Dec 11 in Indianapolis.
  - All-Star: Feb 19–21.
  - Play-in: Apr 13–16.

## 2. Source-status table
| Source | Endpoint | Rows | Date range | Status | Fallback used |
|---|---|---|---|---|---|
| Lottery rules | nba.com board-of-governors release, ESPN, Hoops Rumors, CBS | text | 2026-05-28 | OK (3 sources) | – |
| Key dates / deadline | nba.com/news/key-dates; Yardbarker/Hoops Rumors | text | 2026-27 | OK | – |
| Odds | user CSV | 687 | 2026-10-15 | OK; flags kept (8 BACKFILL_PDF1, 3 BACKFILL_PDF_TEXT, 4 IMPUTED_20C_LADDER) | – |
| Rosters 2026-27 | ESPN site API `/teams/{id}/roster` | 627 players, 30 teams (18–24 each) | as of 10/15 | OK | **nba_api CommonTeamRoster blocked** → ESPN (bbref 2027 pages not yet populated) |
| Schedule 2026-27 | bbref `NBA_2027_games-{month}` + ESPN `/teams/{id}/schedule` | 1,200 games each, identical on date/home/away | 2026-10-20 → 2027-04-11 | OK but partial (§0.1) | **cdn.nba.com 403** → bbref; ESPN as cross-check |
| Injuries | ESPN `/injuries` | 135 (23 Out, 112 Day-To-Day) | as of 10/15 | OK | bbref injuries page not needed |
| Pick ownership 2027 | Hoops Rumors tracker (RealGM-based); OverTheApron partial; ESPN (UTA) | 30 teams | Sep 2026 | Partial verification | Tankathon 404; ProSportsTransactions 403 |
| Draft / lottery history | bbref draft pages 2013–2026 | 840 (60 per year) | 2013–2026 | OK (pick holder, not original owner) | NBA.com lottery page not fetched |
| Player RS totals / advanced (BPM, VORP, WS) / per-100 / play-by-play (on-off) | bbref `leagues/NBA_{y}_*` | 8,870 / 8,870 / 8,870 / 8,857 | 2013-14 → 2025-26 | OK | **nba_api LeagueDash* blocked** → bbref; no Misc/Defense/Hustle |
| Player playoffs totals / advanced | bbref `playoffs/NBA_{y}_*` | 2,817 each | 2013-14 → 2025-26 | OK | same |
| Team ratings history | bbref `leagues/NBA_{y}.html` (SRS, ORtg, DRtg, pace) | 30 × 13 | 2013-14 → 2025-26 | OK | nba_api TeamEstimatedMetrics blocked → bbref |
| Game results history | bbref monthly schedule pages | 971–1,323 per season (2020: 1,143; 2021: 1,171 after adding the bubble/July pages) | 2013-14 → 2025-26 | OK | nba_api LeagueGameLog blocked → bbref |
| RAPM / DPM | darko.app leaderboard via browser pane | 530 | through Jun 3, 2026 | Partial: one snapshot, no history | no free RAPM CSV; in-house RAPM infeasible (no play-by-play source) |
| Draft class + college | bbref draft pages; barttorvik `getadvstats.php?year=Y&csv=1` | 4,696–5,060 rows per year | 2014–2026 | OK; CSV is headerless, so column order (Torvik convention) must be verified in G2 against known players | – |
| Award voting | bbref `awards/awards_{y}.html` (MVP 368 rows, DPOY 439, ROY 202; MIP/SMOY/COY/Clutch tables cached) | – | 2000–2026 | OK | – |
| Stat-leader qualifiers | nba.com/stats/help/statminimums | text | undated | OK: 58 GP (70%) with a total-based exception; no TPG qualifier | – |
| Coaches (display only) | bbref `NBA_2027_coaches.html` | 30 | 2026-27 | OK, cached; uses bbref codes BRK/CHO/PHO | – |

Note: bbref's "2026" season tables are the 2025-26 season. No 2026-27 in-season data exists yet.

## 3. Validation results
- **numba:** the JIT (prange, parallel) works on Python 3.13.15 / numba 0.68.0 / numpy 2.5.4, so no fallback is needed (`src/verify/numba_smoke.py`).
- **Schedule** (`data/clean/schedule_validation.json`):
  - 1,200 games, with every team at exactly 80.
  - 60 Cup group games flagged, exactly 4 per team.
  - Back-to-back pairs per team range 13–16 (mean 14.2, calendar-date basis).
  - bbref and ESPN match on 1,200 of 1,200 (date, home, away), with 0 games in only one source.
- **Cup groups vs the book's `CUP_*` markets:** the schedule's 6 connected components (5 teams each) exactly equal the book's CUP_EAST_A/B/C and CUP_WEST_A/B/C groups (`cup_groups_validation.json`). No mismatch.
- **Name map** (`data/clean/name_map.csv`):
  - All 176 distinct player names in the book's odds file match a roster player: 173 exact after normalization and 3 explicit aliases (Kelel Ware → Kel'el Ware, DeAaron Fox → De'Aaron Fox, Luguentz Dort).
  - Hyphen and period variants are handled by normalization, e.g. "Karl Anthony Towns" and "Shai Gilgeous Alexander".
  - "Alperen Segun" does not appear in the file; the alias to Alperen Sengun is retained.
  - 0 unmatched book names, and no fuzzy guesses were accepted.
  - **DARKO → roster:** 462 exact, 7 alias (Alexandre Sarr → Alex Sarr, Carlton Carrington → Bub Carrington, Nicolas Claxton → Nic Claxton, Nah'Shon Hyland → Bones Hyland, plus the 3 book aliases), and **61 unmatched**. The unmatched are DARKO names not on a current ESPN roster (waived, FA, retired or unsigned, e.g. Westbrook, Lowry, Love, Jeff Green, Gary Harris, Seth Curry, Plumlee). Mouhamadou Gueye (CHI) is a different player from Mouhamed Gueye (ATL) and is left unmapped. The full list is in name_map.csv.
- **Roster → bbref ID** (`data/clean/player_ids.csv`):
  - 509 of 627 matched one-to-one; 118 have no ID.
  - Of the 118, 53 are 2026 draftees (rookie model) and 51 have no NBA stats yet (undrafted, two-way or camp players).
  - 14 have prior NBA seasons but no match: Joiner, R. Holland II, B. Williams, Toohey, Kaluma, RJ Davis, Key, and others. These are bbref name/ID variants, to be fixed by hand at the start of G2.
  - 53 of the 60 2026 draftees are on rosters. The 7 who are not are second-rounders: Saunders, Kayil, L. Jones, Ishchenko, Ngoy, Kaufman-Renn, Lewis.
- **2027 1st-round pick owner for every team:** 30 of 30 rows in `data/clean/picks_2027.csv`. Protections are stored as text; G3 will encode them as rules.
- **Odds flags preserved:** the file is copied unchanged to `data/raw/odds/`, with the `flag` column intact (15 flagged rows) for the G5 orange fills.

## 4. Fallback and quality notes
- **Encoding:** the first bbref pulls were saved with latin-1 decoding (the requests default), which garbled accents. The clean parquets were repaired with a utf-8 round-trip (about 5k cells), and `polite_get` now forces utf-8 for new pulls. The first-pull raw HTML under `data/raw/` is still garbled; the parsers and repair handle it.
- **Politeness:** bbref gap 4.2 s (≤15 requests/min), ESPN 0.5 s, barttorvik 2 s. Five expected 404s (months that don't exist) are logged.
- **Injuries:** ESPN lists 112 Day-To-Day entries that are mostly preseason "Rest". These are not real absences, so use only the "Out" entries plus an overrides column.
- **ESPN roster:** 627 players includes camp and two-way players. The final 15-man rosters plus two-ways are not determined yet.
- **Book coverage:** TOR, GSW and LAC have no playoff lines (noted for G5).

## 5. Not done / deferred
- Original-owner check of the 2025/26 top-5 picks, and machine-parsing of pick protections (G3).
- The 14 prior-NBA players without a bbref ID, and barttorvik column-order verification (G2).
- Hustle/Defense tracking and the nba_api feeds (blocked), and in-house RAPM.
- Re-verify pick ownership and injuries on Oct 18–19, before the Bet Card.

Awaiting "approve G1".
