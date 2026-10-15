# G2 Addendum — leakage audit, stronger baseline, calibration (2026-10-15)

Responds to the six G2 approval conditions. **The headline G2 backtest number changes: 8.92, not 8.44** (see §2). The G2 report's 8.44 stands only as the optimistic bound.

## 1. Lottery draws = 16 (source-confirmed)
`lottery_n_draws` = 16 in `params/assumptions.json`, typed *documented fact* (NBA.com, Tankathon, Hoops Rumors). The 2/6-draw sensitivity is removed. Exact-sim validation, `data/clean/lottery_validation.json`:
- Simulated P(#1) is 5.40% / 8.12% / 2.73% for 2 / 3 / 1 balls, versus NBA.com's published 5.4% / 8.1% / 2.7%.
- Max error vs exact P(pick 1) is 0.09 pp, and vs exact P(pick 2) is 0.06 pp (1M sims).
- The #12 floor for the three worst records is never violated.
- A team barred from #1 or top-5 never lands there.
- NBA.com publishes no full odds table beyond the #1 odds, so there is no further official example to test against.

## 2. Cup rules
NBA.com's official version is implemented: semifinals at the higher seed's home, and 2 of the 22 non-qualifier games cross-conference. Both are recorded in `params/assumptions.json` and CLAUDE.md. The cup module itself is built in G3.

## 3. Leakage audit (the blocking item)
**DARKO:** it never entered any backtest season. The backtest code (`src/ratings/backtest.py` → `model.py`) imports no DARKO data, and DARKO is read only in `project_2027.py`. So the 8.44 was **not invalidated by DARKO**. The backtest is box-prior only already.

**Exact player-impact inputs for test season t** (t = 2019…2026):
- **Impact:** bbref BPM (and for O/D, OBPM/DBPM) from seasons t−1, t−2, t−3 only, with decay λ and reliability M0 chosen by grid search on target seasons ≤ t−1.
- **Aging curve:** the age terms are fit on target seasons ≤ t−1, and the age of the player in season t (a Feb-1 age, known in the preseason).
- **Rookies:** draft-slot model fit on rookies with rookie season ≤ t−1. The pick number is known at the preseason.
- **Minutes and availability:** decayed minutes and games from seasons < t, and availability coefficients fit on seasons ≤ t−1.
- **Team layer** (coefficients, k_wins, σ): fit on team-seasons 2016…t−1 only. Each training season s uses a player model fit only on seasons < s.
- **Prior SRS and continuity:** from season t−1.
- **Baselines:** trained on seasons < t.

**The only point-in-time weakness is roster membership** (who is on which team in season t):
- The original run used actual season-t stints (including in-season trades, a leak). I measured three definitions.

| Roster definition for season t | Model RMSE (80% CI) | Beats best baseline? |
|---|---|---|
| Actual full-season stints (G2 report; **leaky**, optimistic) | 8.44 [7.97, 8.90] | yes (−1.76 [−2.15, −1.36]) |
| **First team listed for each player in season t (no in-season-trade leakage)** | **8.92 [8.42, 9.42]** | yes (−1.28 [−1.61, −0.94]) |
| Players who ended season t−1 on the team (no offseason moves; pessimistic) | 10.30 [9.67, 10.93] | no (+0.09, CI touches zero) |

- **The honest headline is 8.92.** The first-team roster still includes late signings of veterans, which is a small residual leak.
- **Skill rests on knowing offseason roster moves.** With no moves known the model is no better than the baselines.
- For 2026-27 the offseason moves are known (current ESPN rosters), which is the information the 8.92 variant uses legitimately.
- The paired comparison still excludes zero for the 8.92 variant. This is *not* a market benchmark; there is none (no free archive).

**Production DARKO weight:** because DARKO has no point-in-time history, the weight is a documented rule, **50/50**, flagged untested on Assumptions (`w_darko` = 0.5). It was 0.35 in the G2 report. Sensitivity (`data/clean/sensitivity_w_darko.csv`), win change vs the 50/50 blend:
- At weight 0: mean |Δ| 1.58 wins, max 3.67.
- At weight 1: mean |Δ| 1.58, max 3.67.
- OKC moves ±2.7 (58.8 at 50/50, 61.6 at 0, 56.1 at 1), SAS ±1.7, HOU ±2.2, DEN ±2.2.

## 4. Baselines
- **B1:** OLS of wins on prior-season wins, trained on seasons < t, re-centered to 1,230.
- **B2:** OLS of SRS on prior SRS, converted to wins with the model's k.
- **B3:** prior wins, centered.
- **B4 (new, stronger):** prior SRS regressed 1/3 to the mean, with a continuity adjustment: `SRS_hat = (2/3)·prev_SRS·(1+κ(continuity − mean))`, κ fit on training seasons, converted to wins with the model's k.
- B4 RMSE is 10.21, the same as B2 (10.21) and B1 (10.23). Regressing prior SRS gains nothing more.
- **Beating naive prior wins was never the bar; the bar is B4** (paired RMSE −1.28 for the 8.92 variant, CI excludes zero).

## 5. Probability calibration (per season, with 80% CIs)
Primary variant: first-team roster. Full tables are in `data/clean/backtest_calibration_firstroster.json`.
- **P(over the median projection line):** Brier 0.249 [0.248, 0.251] vs 0.25. This is 0.25 *by construction*, because every probability sits near 0.5, so it validates nothing.
- **P(over a market-proxy line):** the lines are the B4 projection rounded to .5, as a stand-in for a book line. Brier **0.214 [0.202, 0.227]** vs 0.25. Per season: 0.232, 0.197, 0.201, 0.255, 0.166, 0.205, 0.245, 0.211 (2019…2026). In 2022 and 2025 it is no better than a coin flip.
- **Information in the disagreement:** the slope of actual-minus-B4 wins on model-minus-B4 wins is **1.16 [0.99, 1.33]**. The model's deviation from B4 is at least fully real, with no shrinkage needed.
- **P(top-10 in conference):** Brier 0.149 [0.132, 0.167] vs 0.222 climatology; per season 0.156, 0.170, 0.195, 0.178, 0.115, 0.111, 0.122, 0.146.
- **P(top-6 in conference):** Brier 0.158 [0.144, 0.174] vs 0.240; per season 0.119, 0.098, 0.178, 0.183, 0.181, 0.190, 0.184, 0.135.
- **Reliability** (in the JSON): bins track the diagonal within sampling error; the over-line probabilities in the 5–15% bin run a little low (freq. above prediction).
- **Caveat:** none of this tests against the market, which is typically sharper than B4.

## 6. LAC/TOR pick toggle
- **The conflict was timing only.** The LAC–TOR agreement (Kawhi Leonard to TOR) was agreed 6/30/2026 and completed 9/14/2026, which RealGM dates. Hoops Rumors' 9/11 snapshot already described the TOR→LAC swap.
- **Text matches:** RealGM's full text matches Hoops Rumors: the LAC can swap its pick, OKC's or DEN's (top-5 protected) for TOR's.
- **Penalty check:** the NBA's 9/2/2026 penalty took the Clippers' **2029–2033** firsts, not 2027, so no 2027 pick is affected.
- **Resolution:** no unresolved conflict remains, and `tank_incentive_toggle_teams` is cleared.
- **Win delta of the toggle states:** this needs the tank module, which is built in G3. I will report it in the G3 report. If the delta exceeds 1.5 wins for either team I will flag it no-bet at that point.

## Files changed
`src/ratings/{model,backtest,calib,project_2027}.py`, `src/verify/lottery_validation.py` (replaces `lottery_sens.py`), `params/{assumptions,provenance}.json`, `data/clean/{backtest_*,sensitivity_w_darko,lottery_validation}.*`.

Proceeding to G3 (simulation engine + calibration). The first piece is the Cup module and the 3-2-1 tank module.
