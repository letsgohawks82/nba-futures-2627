"""Joint Tier 1 portfolio: team bets (tier1 flag in pricing_table.csv) + player bets (tier1 in player_pricing_table.csv) on the SAME 100k season sims.
Player outcomes come from re-running the G4 player simulation on the production team sims (wins and games shared); Kelly is solved on exponentially tilted sims so the marginals equal
the shrunk (model weight 0.25) probabilities. Outputs: joint_summary.json, joint_corr.csv, joint_stakes.csv; overwrites tier1_kelly (team) and stake_t1 (player)."""
import json, math, os
import numpy as np, pandas as pd
from scipy.optimize import minimize
from .price import portfolio_kelly, DIVMAP, tilt_weights
from . import consensus as CS
from ..sim.inputs import IDX
from ..players import run_g4 as G, leaders as L, awards as A, rookies as RK, simgp
from ..players.rates import C as CP
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
C = lambda f: os.path.join(ROOT, "data", "clean", f)
SHRINK_T1 = 0.75; CAP = 0.10; KF = 0.25


def team_outcome(r, Z):
    flags, wins, cr = Z["flags"], Z["wins"], Z["conf_rank"]; t = IDX[r.team]; m = r.market
    if m == "TITLE": return (flags[:, t] & 16) > 0
    if m in ("CONF_EAST", "CONF_WEST"): return (flags[:, t] & 8) > 0
    if m in DIVMAP: return (flags[:, t] & 4) > 0
    if m == "CUP": return (flags[:, t] & 64) > 0
    if m.startswith("CUP_"): return (flags[:, t] & 32) > 0
    if m.startswith("PLAYIN"): return (cr[:, t] >= 7) & (cr[:, t] <= 10)
    if m == "PLAYOFFS":
        inn = (flags[:, t] & 128) > 0; return inn if r.side == "YES" else ~inn
    thr = int(math.floor(r.line)) + 1
    return (wins[:, t] >= thr) if r.side == "OVER" else (wins[:, t] < thr)


def main(seed=909):
    rng = np.random.default_rng(seed)
    T = pd.read_csv(C("pricing_table.csv")); T = T[T.tier1].copy(); PT = pd.read_csv(C("player_pricing_table.csv")); Pl = PT[PT.tier1].copy()
    Z = np.load(os.path.join(ROOT, "sims/season_sims.npz")); Zd = {k: Z[k] for k in ("flags", "wins", "conf_rank")}
    N = Zd["wins"].shape[0]
    Xt = np.stack([team_outcome(r, Zd) for r in T.itertuples()], 1) if len(T) else np.zeros((N, 0), bool)
    pool = G.prep_pool(); gp, ti = simgp.sim_gp(pool, {"gp": Z["gp"], "teams": Z["teams"]}, rng=rng); wp = (Zd["wins"][:, ti] / 82.0).astype(np.float32)
    R = pd.read_csv(CP("g4_rate_backtest.csv")); m, w = A.hist_frame(); P = A.pools(m, w)
    bpm_fit = A.bpm_error("bpm"); dbpm_fit = A.bpm_error("dbpm"); tdef_fit = G.tdef_model(m); rookie_fit, _ = RK.fit()
    cal = L.calib_from_backtest(R); coef = {k: dict(zip(A.FEATS[k], A.fit_clogit(P[k], k, 0.5))) for k in A.FEATS}
    keys = pool.key.values; cols = {}
    need = {(r.market, r.key) for r in Pl.itertuples()}
    win = {mk: np.full(N, -1) for mk, _ in need}
    for a in range(0, N, 20_000):
        cap = {}; G.run_sims(pool, gp[a:a + 20_000], wp[a:a + 20_000], cal, coef, rookie_fit, tdef_fit, bpm_fit, dbpm_fit, rng, cap=cap)
        for mk in win: win[mk][a:a + 20_000] = cap[mk]
    Xp = np.stack([win[r.market] == int(np.where(keys == r.key)[0][0]) for r in Pl.itertuples()], 1) if len(Pl) else np.zeros((N, 0), bool)
    X = np.concatenate([Xt, Xp], 1); dec = np.concatenate([T.dec.values, Pl.dec.values]); fair = np.concatenate([T.fair.values, Pl.fair.values]); pm = np.concatenate([T.model_prob.values, Pl.model_prob.values])
    p_stake = (1 - SHRINK_T1) * pm + SHRINK_T1 * fair
    f0, f_full, wt = portfolio_kelly(X, dec, p_stake, KF, CAP)                     # (a) joint Kelly with no caps / multipliers
    pr = CS.params(); n_t = len(T); CT = CS.table(pd.read_csv(C("pricing_table.csv")))[0]
    cont = T.continuity.fillna(1.0).values if "continuity" in T else np.ones(n_t)
    caps = np.full(len(dec), np.inf)
    for j, r in enumerate(T.itertuples()):
        if r.market == "WINS": caps[j] = (pr["wins_stake_base"] if bool(CT.strong[r.team]) else pr["wins_stake_low"]) * (pr["lowcont_mult"] if r.continuity < pr["lowcont_thr"] else 1.0)
    roy = [n_t + j for j, r in enumerate(Pl.itertuples()) if r.market == "ROY"]
    fixed = {j: pr["roy_stake_mult"] * f0[j] for j in roy}                          # (b) ROY stake fixed at mult x joint stake
    Rm_ = np.where(X, (dec - 1.0)[None, :], -1.0); m_ = len(dec)
    def neg(g):
        w_ = 1.0 + Rm_ @ g
        if (w_ <= 1e-9).any(): return 1e6, np.zeros_like(g)
        return -(wt * np.log(w_)).sum(), -((Rm_ * (wt / w_)[:, None]).sum(0))
    bnds = []
    for j in range(m_):
        if j in fixed: bnds.append((fixed[j] / KF, fixed[j] / KF))
        else: bnds.append((0.0, min(0.6, caps[j] / KF)))
    g0 = np.array([min(b_[1], 0.001) if b_[0] == 0 else b_[0] for b_ in bnds])
    res = minimize(neg, g0, jac=True, method="L-BFGS-B", bounds=bnds, options=dict(maxiter=1000)); f = res.x * KF
    if f.sum() > CAP: free = [j for j in range(m_) if j not in fixed]; f[free] *= max(CAP - sum(fixed.values()), 0) / max(f[free].sum(), 1e-12)
    Rm = np.where(X, (dec - 1)[None, :], -1.0); pnl = Rm @ f; pnl0 = Rm @ f0
    lab = [f"{r.market} {r.selection} {getattr(r, 'side', '')}".strip() for r in T.itertuples()] + [f"{r.market} {r.selection}" for r in Pl.itertuples()]
    corr = np.corrcoef(X.astype(float).T); pd.DataFrame(corr, index=lab, columns=lab).to_csv(C("joint_corr.csv"))
    summ = dict(uncapped_joint=dict(zip(lab, map(float, f0))), uncapped_total=float(f0.sum()), uncapped_exp_return=float(pnl0.mean()), caps={l: (None if not np.isfinite(c) else float(c)) for l, c in zip(lab, caps)}, roy_mult=pr["roy_stake_mult"],
                n_bets=int(X.shape[1]), n_team=int(len(T)), n_player=int(len(Pl)), total_stake_frac=float(f.sum()), exp_return_model=float(pnl.mean()), exp_return_tilted=float((wt * pnl).sum()), p_profit=float((pnl > 0).mean()), p05=float(np.percentile(pnl, 5)), worst=float(pnl.min()),
                stakes=dict(zip(lab, map(float, f))), observed_marginals=dict(zip(lab, map(float, X.mean(0)))), cap=CAP, kelly_fraction=KF)
    json.dump(summ, open(C("joint_summary.json"), "w"), indent=1); np.save(C("joint_X.npy"), X)
    # write stakes back
    full = pd.read_csv(C("pricing_table.csv")); full["tier1_kelly"] = 0.0; full.loc[T.index, "tier1_kelly"] = f[:len(T)]; full["tier1_joint_uncapped"] = 0.0; full.loc[T.index, "tier1_joint_uncapped"] = f0[:len(T)]; full.to_csv(C("pricing_table.csv"), index=False)
    PT["stake_t1"] = 0.0; PT.loc[Pl.index, "stake_t1"] = f[len(T):]; PT["stake_t1_premult"] = 0.0; PT.loc[Pl.index, "stake_t1_premult"] = f0[len(T):]; PT.to_csv(C("player_pricing_table.csv"), index=False)
    pd.DataFrame(dict(bet=lab, dec=dec, fair=fair, model=pm, p_stake=p_stake, sim_marginal=X.mean(0), joint_uncapped=f0, cap=caps, stake=f)).to_csv(C("joint_stakes.csv"), index=False)
    return summ, corr, lab


if __name__ == "__main__":
    s, c, lab = main(); pd.set_option("display.width", 250)
    print({k: v for k, v in s.items() if k not in ("stakes", "observed_marginals")}); print(pd.Series(s["stakes"]).round(4).to_string())
    print(pd.DataFrame(c, index=[l[:22] for l in lab], columns=[str(i) for i in range(len(lab))]).round(2).to_string())
