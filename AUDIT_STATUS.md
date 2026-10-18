# AUDIT_STATUS

Verdict: **REPRODUCIBLE WITH LIMITATIONS** (not "audit-cleared" for model skill). Evidence: `reports/audit_evidence.md`. Validated commit: `e10de95` (fresh clone, network blocked).

## Passed (with command output in the evidence file)
- Clean-room command (README) runs end to end: ALL STEPS PASSED, network attempts 0, every stage exit 0.
- Frozen input archive and history archive verify by SHA-256 against their manifests and `data/manifest.csv`; assets on release `v1.0-preseason.1` match the committed hashes.
- Ratings and team/player projections reproduce byte-identically (deterministic). Monte Carlo outputs reproduce within 4 SE at N=20,000.
- Rebuilt card = committed card (same 4 bets, same prices; MIN stake differs within Monte Carlo error). Workbook: 4 Tier 1 rows, stakes agree with the card, no FLAG/CHECK/STALE cells, metadata agree.
- 17 tests pass; 10 negative controls fail closed (`reports/negative_controls.md`).
- All 12 historical tables re-derived from the raw pages agree cell by cell.

## Open limitations
1. Original parsers for team, awards, draft, roster-check tables and the mojibake repair were never committed; they are covered only by an independent re-derivation (`src/data/rederive_history.py`).
2. Tag `v1.0-preseason.1-history` has the 33.6 MB history archive in its tree. It is not moved or rewritten; master and the addendum tag `v1.0-preseason.1-history.1` do not contain it. The release asset is canonical.
3. Validated on Windows with Excel only; the Linux/no-Excel path is implemented but not run end to end.
4. The reduced run reuses committed parameter draws and robustness scenarios; a full N=100,000 rerun and the planned sensitivity runs were not performed.
5. No market benchmark shows the model beats the book; DARKO 0.5 blend is an UNVALIDATED scenario input; three bets need book-rule confirmation; imputed prices are never bet.

## Auditor reproduction
```bash
git clone https://github.com/letsgohawks82/nba-futures-2627 && cd nba-futures-2627 && git checkout v1.0-preseason.1-history.1
gh release download v1.0-preseason.1 -p "nba_futures_*.tar.gz" -D dist
# then follow the clean-room command in README.md, and:
python scripts/verify_history_archive.py --restore --rederive
```
