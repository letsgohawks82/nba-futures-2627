"""Per-bet sizing waterfall for the released card, from data/clean/joint_stakes.csv (written by src/pricing/joint.py). Writes reports/sizing_waterfall.md.
Chain: model prob -> shrink to sizing prob (0.25 model + 0.75 book-fair, SHRINK_T1=0.75) -> single-bet full Kelly at that prob (reference) -> joint 0.25-fractional Kelly
over the whole Tier 1 portfolio on the production sims (no caps) -> hard cap (WINS 0.75% / 0.50% low-continuity; none on PLAYOFFS) -> final stake. python -m src.pricing.sizing_doc"""
import os, pandas as pd
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def main():
    J = pd.read_csv(os.path.join(ROOT, "data", "clean", "joint_stakes.csv")); card = pd.read_csv(os.path.join(ROOT, "release", "final_card.csv"))
    L = ["# Sizing waterfall (released card)", "",
         "Policy: Kelly fraction **0.25**; probability used for sizing is **shrunk 75% toward the book's de-vigged fair price** (p_stake = 0.25 x model + 0.75 x fair); stakes are the joint solution over the whole portfolio on the same simulations (correlated bets share risk); then a hard per-bet cap (WINS 0.75%, or 0.50% when roster continuity < 0.55; PLAYOFFS uncapped; portfolio cap 10%). Stakes are a fraction of bankroll. `joint_uncapped` is already the 0.25-fraction.", "",
         "| Bet | Book dec | Model p | Fair p | Sizing p | Full Kelly @ model p | Full Kelly @ sizing p | Joint 0.25 Kelly, uncapped | Cap | Final stake | Binding step |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in J.itertuples():
        b = r.dec - 1; kfm = max(0, (r.model * r.dec - 1) / b); kfs = max(0, (r.p_stake * r.dec - 1) / b); atcap = str(r.cap) != 'inf' and abs(r.stake - float(r.cap)) < 1e-9
        L.append(f"| {r.bet} | {r.dec:.3f} | {r.model:.3f} | {r.fair:.3f} | {r.p_stake:.3f} | {100 * kfm:.2f}% | {100 * kfs:.2f}% | {100 * r.joint_uncapped:.2f}% | {'none' if r.cap == float('inf') or str(r.cap) == 'inf' else f'{100 * float(r.cap):.2f}%'} | **{100 * r.stake:.2f}%** | {'at cap' if atcap else 'joint Kelly re-solved after other stakes were capped'} |")
    L += ["", f"Total staked: **{100 * J.stake.sum():.2f}%** of bankroll. A stake can be reproduced from the table: shrink -> joint 0.25 Kelly (needs the sims, `src/pricing/joint.py`) -> min(cap, Kelly). Full Kelly at the raw model probability is shown only to make the haircut visible (20-50% of bankroll per bet, 8-70x the final stakes). The final column can differ from the uncapped joint Kelly in either direction: the joint problem is solved again with the capped stakes held fixed (src/pricing/joint.py), so an uncapped bet (MIN) is re-sized and a capped bet can sit at its cap even when its own uncapped Kelly is slightly below it (POR 0.48% -> 0.50%, the WINS low-continuity cap).",
          "", "The recommended stake is **not** raised if the model's probability is raised; the only inputs that move a stake are the book price, the fair price and the model probability through the 25% weight."]
    open(os.path.join(ROOT, "reports", "sizing_waterfall.md"), "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n"); print("\n".join(L))


if __name__ == "__main__":
    main()
