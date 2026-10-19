"""reports/alpha_validation.md: what is and is not demonstrated about betting alpha, and the sample the live log needs. Measures only; no model change; no external data.
Inputs: backtest_metrics_firstroster.json, benchmark_model_vs_book_wins.csv, release/final_card.csv. python -m src.pricing.alpha_validation"""
import json, math, os
import numpy as np, pandas as pd
from scipy.stats import norm
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
Z = norm.ppf(0.95) + norm.ppf(0.80)          # one-sided 5% test, 80% power


def main():
    bt = json.load(open(os.path.join(ROOT, "data", "clean", "backtest_metrics_firstroster.json"))); b = pd.read_csv(os.path.join(ROOT, "data", "clean", "benchmark_model_vs_book_wins.csv")); card = pd.read_csv(os.path.join(ROOT, "release", "final_card.csv"))
    gap = b.model_minus_line.abs()
    L = ["# Alpha validation", "",
         "## Verdict: **ALPHA REMAINS UNPROVEN** (expected alpha > 0 is a hypothesis; no lower confidence bound > 0 can be computed from anything in this repository).", "",
         "Scope: measurement only. No model, parameter, bet or stake was changed, and no data was added or invented for this report.", "",
         "## What the repository can and cannot show", "",
         "| Evidence the auditor asked for | Available? | Why |", "|---|---|---|",
         "| Historical market lines + odds for every backtest observation | **No** | No free historical win-total / futures price archive was found (G2 report); the only prices held are the 10/15/2026 book transcription and a 10/16 external consensus. Buying or reconstructing an archive is a data task, not something to estimate. |",
         "| ROI, CLV, Brier / log loss vs the sportsbook, calibration vs the sportsbook, hit rate vs the sportsbook | **No** | All need historical prices. Without them, any 'historical ROI' would be fabricated. |",
         "| Model vs no-bet / equal-weight / highest-odds baselines on historical bets | **No** | Same reason. |",
         f"| Out-of-sample forecast accuracy vs naive baselines | Yes | First-team roster proxy RMSE {bt['model']['rmse']:.2f} wins [{bt['model']['rmse_ci'][0]:.2f}, {bt['model']['rmse_ci'][1]:.2f}] vs strongest naive baseline about 10.2 (2019-2026). This is a forecasting result, not a betting result: it is silent on whether the model beats the market. |",
         "| Live CLV on timestamped picks | **Not yet** | Logging started 2026-10-19 (`live/`); closing prices come after the lock. |", "",
         "## Why the backtest does not establish alpha",
         "- A model can beat last-year's-wins baselines and still be worse than the market, which already uses rosters, injuries and trades. There is no market-line benchmark here, so the comparison that matters was never run.",
         f"- This season's model differs from the book's win totals by a mean of **{gap.mean():.2f} wins** (median {gap.median():.2f}, max {gap.max():.2f}) across {len(b)} teams. If the market were no worse than the model, most of those gaps would be model error; an edge exists only if the gaps are the market's errors. The data cannot separate the two.",
         "- The backtest uses a roster proxy that knows offseason moves; with no moves known the model is no better than the baselines (RMSE 10.30). Skill depends on knowing the moves, which the market also knows.",
         "- DARKO (weight 0.5 in production) never entered the backtest; the 2026-27 numbers are not covered by it.",
         "- The 4-bet card is a sample of one season, and the bets are correlated (three WINS bets and a playoffs bet), so it cannot prove anything on its own.", "",
         "## What it would take (power calculation, one-sided 5% test, 80% power)",
         "n = (z_alpha + z_beta)^2 * sigma^2 / mu^2. sigma for CLV per bet is an ASSUMPTION (no live data yet); recompute from `live/clv_ledger.csv` once 20+ closes exist.", "",
         "| True mean CLV (implied pp) | n if sd = 1.5 pp | n if sd = 2.5 pp | n if sd = 4 pp |", "|---|---|---|---|"]
    for mu in (0.5, 1.0, 2.0, 3.0): L.append(f"| {mu:.1f} | {math.ceil(Z ** 2 * 1.5 ** 2 / mu ** 2)} | {math.ceil(Z ** 2 * 2.5 ** 2 / mu ** 2)} | {math.ceil(Z ** 2 * 4 ** 2 / mu ** 2)} |")
    L += ["", "Outcome-based ROI is far slower. For the released card, per-unit return SD is dec x sqrt(p(1-p)) at the model probability:", "", "| Bet | Book dec | Model p | Return SD / unit | Edge needed for 80% power at n=100 | n for a 5-pp ROI edge |", "|---|---|---|---|---|---|"]
    for r in card.itertuples():
        dec = r.american / 100 + 1 if r.american > 0 else 100 / -r.american + 1; sd = dec * math.sqrt(r.model_prob * (1 - r.model_prob))
        L.append(f"| {r.market} {r.selection} {r.side} | {dec:.3f} | {r.model_prob:.3f} | {sd:.2f} | {100 * Z * sd / 10:.1f} pp ROI | {math.ceil(Z ** 2 * sd ** 2 / 0.05 ** 2)} |")
    L += ["", "A single season of futures settles about 4 independent-ish outcomes. Even 50 independent bets of return SD about 1 have 80% power only for ROI edges above roughly 35 pp, so ROI cannot confirm a realistic edge within a season; CLV can start to within one season only if the sample is wide (the shadow log of TIER2 / HELD / NOT_BET sides, not just the card).", "",
          "## Decision rule fixed in advance (proposed; change before the first close or not at all)",
          "1. Primary metric: mean CLV (implied pp, same side, first logged price to closing price) on **all non-DISPLAY_ONLY, non-IMPUTED logged sides with model EV > 0**, not just placed bets.",
          "2. 'Alpha supported' needs the lower 95% bound of mean CLV > 0 with n >= 100 logged sides (bootstrap by team and market to respect correlation).",
          "3. 'Alpha refuted' if the upper bound < 0 at any n >= 100, or the CARD sides' mean CLV is below the NOT_BET sides' (the selection rule then adds no value).",
          "4. Anything else: **unproven**; stakes stay at the released level and are not scaled up.",
          "5. A market-line archive, if acquired, replaces this with the historical test in the auditor's list (ROI, Brier, log loss, calibration vs book).", ""]
    open(os.path.join(ROOT, "reports", "alpha_validation.md"), "w", encoding="utf-8", newline="\n").write("\n".join(L)); print("\n".join(L))


if __name__ == "__main__":
    main()
