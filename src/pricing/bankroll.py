"""Bankroll simulation for the released Tier 1 card (release/final_card.csv) on the production season sims (sims/season_sims.npz, same sims that priced the card).
Scenarios change the TRUE win probabilities by exponential tilting (joint structure kept): model = model_prob; shrunk = 0.25 model + 0.75 fair (the sizing probability);
half = halfway between fair and shrunk; fair = no edge (book fair price is right). Reports one-season outcome and 10 compounded independent seasons per scenario and stake multiplier.
Writes reports/bankroll_sim.md and data/clean/bankroll_sim.json.  Usage: python -m src.pricing.bankroll"""
import json, os
import numpy as np, pandas as pd
from .price import tilt_weights
from .joint import team_outcome
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SEASONS = 10; PATHS = 20000


def main(seed=2026):
    card = pd.read_csv(os.path.join(ROOT, "release", "final_card.csv")); T = pd.read_csv(os.path.join(ROOT, "data", "clean", "pricing_table.csv"))
    Z = np.load(os.path.join(ROOT, "sims", "season_sims.npz")); Zd = {k: Z[k] for k in ("flags", "wins", "conf_rank")}; N = Zd["wins"].shape[0]
    rows = []
    for c in card.itertuples():
        m = (T.market == c.market) & (T.selection == c.selection) & (T.side == c.side)
        if not np.isnan(c.line): m &= (T.line == c.line)
        assert m.sum() == 1, (c.market, c.selection); rows.append(T[m].iloc[0])
    S = pd.DataFrame(rows).reset_index(drop=True)
    X = np.stack([team_outcome(r, Zd) for r in S.itertuples()], 1); dec = S.dec.values; f = card.stake_frac.values
    fair = S.fair.values; pm = S.model_prob.values; psh = 0.25 * pm + 0.75 * fair
    sc = {"model right": pm, "shrunk (sizing prob)": psh, "half of shrunk edge": fair + 0.5 * (psh - fair), "no edge (book fair)": fair}
    R = np.where(X, (dec - 1.0)[None, :], -1.0); rng = np.random.default_rng(seed); out = {}; L = []
    for mult in (1, 2, 4):
        for name, p in sc.items():
            w, _ = tilt_weights(X, p); pnl = (R @ (f * mult)); idx = rng.choice(N, size=(PATHS, SEASONS), p=w)
            g = np.log1p(pnl[idx]); eq = np.exp(np.cumsum(g, 1)); peak = np.maximum.accumulate(np.concatenate([np.ones((PATHS, 1)), eq], 1), 1)[:, 1:]; dd = (1 - eq / peak).max(1)
            one = np.sort(pnl); cw = np.cumsum(w[np.argsort(pnl)])
            q = lambda a: float(one[np.searchsorted(cw, a)])
            res = dict(stake_mult=mult, scenario=name, total_stake=float(f.sum() * mult), exp_season_return=float((w * pnl).sum()), p_season_profit=float(w[pnl > 0].sum()), p05=q(0.05), median=q(0.5), worst=float(pnl.min()),
                       p_lose_all=float(w[(X.sum(1) == 0)].sum()), median_cagr10=float(np.median(eq[:, -1] ** (1 / SEASONS) - 1)), p05_cagr10=float(np.quantile(eq[:, -1] ** (1 / SEASONS) - 1, 0.05)),
                       p_dd20=float((dd > 0.2).mean()), p_dd40=float((dd > 0.4).mean()), p_ruin=float((eq.min(1) < 0.1).mean()))
            out[f"x{mult}|{name}"] = res; L.append(res)
    json.dump(dict(n_sims=int(N), seasons=SEASONS, paths=PATHS, seed=seed, bets=[f"{r.market} {r.selection} {r.side}" for r in S.itertuples()], stakes=f.tolist(), results=L), open(os.path.join(ROOT, "data", "clean", "bankroll_sim.json"), "w"), indent=1)
    pc = lambda x: f"{100 * x:.2f}%"
    md = ["# Bankroll simulation - released Tier 1 card", "",
          f"Card: {', '.join(out_b + f' ({100 * s:.2f}%)' for out_b, s in zip([f'{r.market} {r.selection} {r.side}' for r in S.itertuples()], f))}; total {pc(f.sum())} of bankroll. Outcomes from the {N:,} production season sims that priced the card; each scenario re-weights the sims (exponential tilt, joint structure kept) so the four marginals equal the scenario's TRUE probabilities. Seasons are independent draws, compounded {SEASONS} times ({PATHS:,} paths). Futures settle once per season, so 'drawdown' is measured at season ends; a path ruin means equity < 10% of start.", "",
          "Scenarios: **model right** = model_prob; **shrunk** = 0.25 model + 0.75 book-fair (the probability the stakes are sized on); **half** = half of the shrunk edge; **no edge** = the book's fair price is right (vig still paid).", "",
          "| Stake x | True probabilities | Season E[return] | P(profit) | 5th pct | Median | Worst | P(lose all 4) | 10-season median CAGR | 5th pct CAGR | P(DD>20%) | P(DD>40%) | P(ruin) |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in L: md.append(f"| {r['stake_mult']}x ({pc(r['total_stake'])}) | {r['scenario']} | {pc(r['exp_season_return'])} | {pc(r['p_season_profit'])} | {pc(r['p05'])} | {pc(r['median'])} | {pc(r['worst'])} | {pc(r['p_lose_all'])} | {pc(r['median_cagr10'])} | {pc(r['p05_cagr10'])} | {pc(r['p_dd20'])} | {pc(r['p_dd40'])} | {pc(r['p_ruin'])} |")
    md += ["", "Reading it: the card risks at most its total stake in a season (all four lose). Under 'no edge' the expected loss is the vig on the four prices; the gap between that row and the 'shrunk' row is what the sizing assumes the model is worth. A live CLV / calibration record (live/) is what decides which row is real."]
    open(os.path.join(ROOT, "reports", "bankroll_sim.md"), "w", encoding="utf-8", newline="\n").write("\n".join(md) + "\n"); print("\n".join(md))


if __name__ == "__main__":
    main()
