# G5 Addendum — Tier 1 card (2026-10-15)

**Tier 1 = 4 bets, 2.0% of bankroll in total (cap 10%, not binding).** The full 52-bet card stays on `Bet_Card` as **Tier 2 with no stake by default** (`Assumptions!tier2_staking_on` = 0). Tier 1 lives on the new `Tier1_Card` tab; Dashboard and Exposure now report Tier 1.

## Funnel (from the 52-bet Tier 2 card)
| Filter | Bets left |
|---|---|
| Tier 2 card | 52 |
| Edge survives shrink 0.75 (EV ≥ 3% and shrunk CI low > 0 at model weight 0.25) | 27 |
| Market fair probability ≥ 5% | 20 |
| Not against a market top-5 team / not for a market bottom-5 team (wins, playoffs, division, conference, title) | 19 |
| **Named driver** (verifiable arrival / departure / availability facts of ≥ 1.0 SRS covering ≥ 60% of the model-vs-market gap) | **4** |

- Market top 5 by fair win median: OKC, SAS, NYK, BOS, PHI. Bottom 5: SAC, BKN, MIL, LAC, NOP.
- The named-driver test is strict on purpose. A looser version (any 0.15+ SRS change in any rotation player) passed 19 of 20, which says nothing: nearly every team has some roster change. Teams that fail it have a diffuse gap, with no single verifiable roster fact behind it: MEM, WAS, GSW, UTA, POR, HOU, MIA (Giannis's availability and Ware's departure cover only 52% of its gap, just under the 60% bar), NYK, PHI, SAS and others. Those bets stay in Tier 2.

## The Tier 1 bets
Stakes are portfolio Kelly at model weight 0.25 (shrink 0.75), re-solved on the Tier 1 set and capped at 10% (cap not reached). EV is shown at the model's own probability; the shrunk-EV column is what the filter tested.

| # | Bet | Book | Fair | Model | EV (model) | EV at shrink 0.75 | Stake (% bankroll) | Named driver |
|---|---|---|---|---|---|---|---|---|
| 1 | **TOR to win Atlantic** | +650 | 10.5% | 33.4% | +151% | +21.9% | **0.83%** | **Kawhi Leonard** acquired: rated +6.1 (DARKO +6.3), ~30 mpg, projected 56 games, worth +2.8 SRS vs the 2025-26 Raptors roster. **Gradey Dick** gone (1,067 min at −3.6 BPM, +1.0 SRS). The book's TOR win total (45.5) is 4.6 wins below the model's 50.1 |
| 2 | **CHI in the East play-in (finish 7–10)** | +800 | 9.3% | 25.4% | +129% | +20.0% | **0.62%** | **Rob Dillingham** gone (644 min at −7.3 BPM last year, +1.3 SRS). *Weak driver: a bench player, and the whole case is that the Bulls are better without a very bad player; treat with caution* |
| 3 | **MIN misses the 16-team playoff field (PLAYOFFS NO)** | +550 | 12.5% | 31.8% | +107% | +12.4% | **0.56%** | **Julius Randle** gone (2,610 min at +1.5 BPM, −1.1 SRS); the model also sees Cody Williams (rated −3.8, 22 mpg) as a drag. Lock Wed 10/21 6:40 PM CST |
| 4 | **TOR to win the East** | +900 | 8.3% | 17.6% | +76% | +6.4% | **0.00%** | Same Kawhi / Dick facts as #1. Sized at zero because it is highly correlated with bet #1 and adds nothing at shrink 0.75 |

- **Staked total: 2.0% of bankroll.** Model-world expected return +2.6% of bankroll, P(profit) 66%, 5th percentile and worst case −2.0% (every bet loses).
- **Locks:** #1, #2 and #4 lock Tue 10/20 02:10 PM CST; #3 locks Wed 10/21 06:40 PM CST (MIN's first game).
- **Assumptions to know:** PLAYOFFS is the 16-team field (user-confirmed from implied sums, "confirm with book"). Bet #2 depends on the play-in interpretation (finishing 7–10).

## What this says about the model
- At the honest weight (0.25 model / 0.75 market) only **three** distinct ideas survive, and one of them (#2) rests on a bench departure. That is consistent with a model that has no proven edge over the market. The 52-bet card is better read as a list of model opinions to audit than as a betting plan.
- The Toronto idea is the clearest: a specific, verifiable acquisition (Kawhi) that the model values at +2.8 SRS and that the book prices well below the model. The market has the same information; the disagreement is how much Kawhi is worth at 56 projected games.

## In the workbook
- `Tier1_Card` is a dynamic `FILTER`/`SORTBY` view over `S_Markets` column `Tier 1 (live)`. The shrink, fair-probability, min-EV and exposure-cap thresholds are Assumptions (`tier1_shrink`, `tier1_fair_min`, `tier1_exposure_cap`); the direction rule and named driver are engine flags (`run.py price` refreshes them).
- `Bet_Card` shows a `Tier` column; Tier 2 stakes display "-" unless `tier2_staking_on` = 1.
- Excel and Python agree: **4 Tier 1 / 52 Tier 2**, 0 failing checks, 0 error cells.
- Code: `src/pricing/tier1.py`; outputs `data/clean/tier1_card.csv`, `tier1_summary.json` (all 30 teams' driver analysis).

Starting G4 (player markets) next.
