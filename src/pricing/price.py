"""Pricing: de-vig (multiplicative / power / Shin), model probabilities from the sims, EV, Kelly, parameter-posterior edge CI, robustness, portfolio Kelly.
Outputs data/clean/pricing_table.csv, bet_card.csv, portfolio_*.csv. Market odds are NEVER a model input (only de-vig, edges and the staking shrink)."""
import json, math, os
import numpy as np, pandas as pd
from scipy.optimize import brentq, minimize
from ..data.teams import NAME2ABBR, TEAMS
from ..sim.inputs import TEAM_LIST, IDX

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
C = lambda f: os.path.join(ROOT, "data", "clean", f)
DIVMAP = {"DIV_ATLANTIC": "Atlantic", "DIV_CENTRAL": "Central", "DIV_SOUTHEAST": "Southeast", "DIV_NORTHWEST": "Northwest", "DIV_PACIFIC": "Pacific", "DIV_SOUTHWEST": "Southwest"}
MODELLED = {"TITLE", "CONF_EAST", "CONF_WEST", "CUP", "PLAYIN_EAST", "PLAYIN_WEST", "PLAYOFFS", "WINS"} | set(DIVMAP) | {f"CUP_{c}_{g}" for c in ("EAST", "WEST") for g in "ABC"}
DISPLAY_ONLY = {"MIP", "SMOY", "COY", "CLUTCH", "CUP_MVP"}            # market de-vig + fair price only, no model probability, no bets
PLAYER_G4 = {"MVP", "DPOY", "ROY", "LDR_PPG", "LDR_RPG", "LDR_APG", "LDR_SPG", "LDR_BPG", "LDR_TPG"}   # modelled in G4

ASSUME = dict(devig="Shin", kelly_fraction=0.25, min_ev=0.03, ci_level=0.80, max_bet=1000.0, max_exposure=0.25, shrink=0.25)


def dec_from_american(a):
    a = np.asarray(a, float)
    return np.where(a > 0, 1 + a / 100.0, 1 + 100.0 / np.abs(a))


def american_from_dec(d):
    d = np.asarray(d, float)
    return np.where(d >= 2, (d - 1) * 100.0, -100.0 / (d - 1))


# ----------------------------------------------------------------------------- de-vig
def devig_mult(pi, S=1.0):
    pi = np.asarray(pi, float); return pi * S / pi.sum()


def devig_power(pi, S=1.0):
    pi = np.asarray(pi, float)
    f = lambda k: (pi ** k).sum() - S
    lo, hi = 0.2, 10.0
    if f(lo) < 0 or f(hi) > 0:
        return devig_mult(pi, S)
    k = brentq(f, lo, hi, xtol=1e-12)
    return pi ** k


def devig_shin(pi, S=1.0):
    """Shin (1993) for S=1; for S != 1 (the play-in 4-slot market) the model is undefined -> power method."""
    pi = np.asarray(pi, float)
    if abs(S - 1.0) > 1e-9:
        return devig_power(pi, S)
    Pi = pi.sum()
    if Pi <= 1.0:
        return pi / Pi
    g = lambda z: ((np.sqrt(z * z + 4 * (1 - z) * pi * pi / Pi) - z) / (2 * (1 - z))).sum() - 1.0
    z = brentq(g, 1e-12, 0.9999, xtol=1e-13)
    return (np.sqrt(z * z + 4 * (1 - z) * pi * pi / Pi) - z) / (2 * (1 - z))


DEVIG = {"Multiplicative": devig_mult, "Power": devig_power, "Shin": devig_shin}


def load_odds():
    o = pd.read_csv(os.path.join(ROOT, "data/raw/odds/odds_2026-10-15.csv")); o["row_id"] = np.arange(len(o))
    o["team"] = o.selection.map(NAME2ABBR)
    o["dec"] = dec_from_american(o.american); o["implied"] = 1 / o.dec
    key = []
    for r in o.itertuples():
        if r.market in ("WINS", "PLAYOFFS"):
            key.append(f"{r.market}|{r.selection}" + (f"|{r.line}" if r.market == "WINS" else ""))
        else:
            key.append(r.market)
    o["key"] = key
    o["S"] = np.where(o.market.isin(["PLAYIN_EAST", "PLAYIN_WEST"]), 4.0, 1.0)
    return o


def add_devig(o, method="Shin"):
    for name, fn in DEVIG.items():
        col = "fair_" + {"Multiplicative": "mult", "Power": "power", "Shin": "shin"}[name]
        o[col] = np.nan
        for k, g in o.groupby("key"):
            o.loc[g.index, col] = fn(g.implied.values, g.S.iloc[0])
    o["fair"] = o["fair_" + {"Multiplicative": "mult", "Power": "power", "Shin": "shin"}[method]]
    o["overround"] = o.groupby("key").implied.transform("sum") / o.S - 1
    return o


# ----------------------------------------------------------------------------- model probabilities
def team_prob_table(summary, wins_pmf=None, confrank=None):
    """summary: sim_team_summary.csv indexed by team. Returns functions giving probability for an odds row."""
    S = summary.set_index("team")
    def p(row):
        t = row.team
        m = row.market
        if m == "TITLE": return S.loc[t, "p_title"]
        if m in ("CONF_EAST", "CONF_WEST"): return S.loc[t, "p_conference"]
        if m in DIVMAP: return S.loc[t, "p_division"]
        if m == "CUP": return S.loc[t, "p_cup"]
        if m.startswith("CUP_") and m != "CUP_MVP": return S.loc[t, "p_cup_group"]
        if m in ("PLAYIN_EAST", "PLAYIN_WEST"): return float(sum(S.loc[t, f"p_confrank_{k}"] for k in range(7, 11)))
        if m == "PLAYOFFS": return S.loc[t, "p_playoffs"] if row.side == "YES" else 1 - S.loc[t, "p_playoffs"]
        return np.nan
    return p


def wins_prob(pmf_row, line, side):
    """pmf_row: P(wins = w), w=0..82; lines are x.5."""
    thr = int(math.floor(line)) + 1
    over = pmf_row[thr:].sum()
    return over if side == "OVER" else 1 - over


# ----------------------------------------------------------------------------- portfolio Kelly
def tilt_weights(X, p_target, iters=200):
    """Exponential tilt of equally weighted sims so that E_w[X_i] = p_target_i (preserves the joint structure)."""
    n, m = X.shape; Xf = X.astype(float)
    def f(lmb):
        a = Xf @ lmb; mx = a.max(); w = np.exp(a - mx); Z = w.sum()
        val = mx + np.log(Z / n) - lmb @ p_target
        grad = (Xf * (w / Z)[:, None]).sum(0) - p_target
        return val, grad
    res = minimize(f, np.zeros(m), jac=True, method="L-BFGS-B", options=dict(maxiter=iters))
    a = Xf @ res.x; w = np.exp(a - a.max()); return w / w.sum(), res


def portfolio_kelly(X, dec, p_stake, kelly_fraction=0.25, max_exposure=0.25):
    """Full-Kelly stakes (fractions of bankroll) maximizing E_w[log(1 + sum f_i r_i)] over tilted sims; then fractional scaling and exposure cap."""
    w, _ = tilt_weights(X, p_stake)
    R = np.where(X, (dec - 1.0)[None, :], -1.0)
    def f(fr):
        g = 1.0 + R @ fr
        if (g <= 1e-9).any(): return 1e6, np.zeros_like(fr)
        return -(w * np.log(g)).sum(), -((R * (w / g)[:, None]).sum(0))
    m = X.shape[1]
    res = minimize(f, np.full(m, 0.001), jac=True, method="L-BFGS-B", bounds=[(0, 0.6)] * m, options=dict(maxiter=500))
    full = res.x * kelly_fraction
    tot = full.sum()
    scale = min(1.0, max_exposure / tot) if tot > 0 else 1.0
    return full * scale, res.x, w
