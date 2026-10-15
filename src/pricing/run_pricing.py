"""python -m src.pricing.run_pricing : builds data/clean/pricing_table.csv, bet_card.csv and portfolio outputs."""
import json, math, os, sys
import numpy as np, pandas as pd
from .price import *
from . import robust as RB
from ..sim.inputs import TEAM_LIST, IDX


PLAYOFFS_DEF = "Bracket"      # "Bracket" (16-team playoffs, implied by the book prices) or "Top10" (spec reading: play-in counts)


def prob_vector(o, src, po_def=None):
    po_def = po_def or PLAYOFFS_DEF
    """src: dict of arrays title/conference/division/cup/cup_group/playoffs [30], confrank [30,15], pmf [30,83]."""
    p = np.full(len(o), np.nan)
    for i, r in enumerate(o.itertuples()):
        m = r.market
        if m not in MODELLED:
            continue
        t = IDX[r.team]
        if m == "TITLE": p[i] = src["title"][t]
        elif m in ("CONF_EAST", "CONF_WEST"): p[i] = src["conference"][t]
        elif m in DIVMAP: p[i] = src["division"][t]
        elif m == "CUP": p[i] = src["cup"][t]
        elif m.startswith("CUP_"): p[i] = src["cup_group"][t]
        elif m in ("PLAYIN_EAST", "PLAYIN_WEST"): p[i] = src["confrank"][t, 6:10].sum()
        elif m == "PLAYOFFS":
            q = src["bracket"][t] if po_def == "Bracket" else src["playoffs"][t]
            p[i] = q if r.side == "YES" else 1 - q
        elif m == "WINS": p[i] = wins_prob(src["pmf"][t], r.line, r.side)
    return p


def base_source(summary, pmf):
    S = summary.set_index("team").loc[TEAM_LIST]
    return dict(title=S.p_title.values, conference=S.p_conference.values, division=S.p_division.values, cup=S.p_cup.values, cup_group=S.p_cup_group.values,
                playoffs=S.p_playoffs.values, bracket=S.p_bracket.values, confrank=S[[f"p_confrank_{k}" for k in range(1, 16)]].values, pmf=pmf)


def scenario_sources():
    R = pd.read_csv(C("sim_robust_summary.csv")); H = pd.read_csv(C("sim_robust_wins_hist.csv")); out = {}
    for sc, g in R.groupby("scenario"):
        pm = np.stack([H[(H.scenario == sc) & (H.team == t)].sort_values("wins").p.values for t in TEAM_LIST])
        out[sc] = base_source(g, pm)
    return out


RULES = {"WINS": "All 82 games must be played for action; play-in games do not count; lines are x.5 (no push)",
         "PLAYOFFS": "Play-in counts as playoffs (YES = top-10 in conference); action requires 82 games unless already determined",
         "PLAYIN": "Interpreted as team participates in the play-in (finishes 7-10); implied probs sum to ~4.4 per conference with 4 slots - INTERPRETATION FLAGGED",
         "TITLE": "All wagers action", "CONF": "All wagers action", "DIV": "All wagers action; division tiebreakers per NBA rules", "CUP": "All wagers action (Cup final does not count in the standings)"}


def rule(m):
    for k, v in RULES.items():
        if m.startswith(k):
            return v
    return "All in, no refunds; dead-heat rules apply to stat leaders"


def main(assume=ASSUME):
    o = load_odds(); o = add_devig(o, assume["devig"])
    sc = scenario_sources()
    Zp = np.load(os.path.join(ROOT, "sims/season_sims.npz")); N_ = Zp["wins"].shape[0]
    pmf_prod = np.stack([np.bincount(Zp["wins"][:, i], minlength=83) / N_ for i in range(30)])
    src = base_source(pd.read_csv(C("sim_team_summary.csv")), pmf_prod)          # production run is the base case
    o["model_prob"] = prob_vector(o, src)
    o["modelled"] = o.market.isin(MODELLED); o["display_only"] = o.market.isin(DISPLAY_ONLY); o["g4_pending"] = o.market.isin(PLAYER_G4)
    o["model_fair_dec"] = 1 / o.model_prob; o["model_fair_american"] = american_from_dec(o.model_fair_dec)
    o["ev"] = o.model_prob * o.dec - 1
    D = np.load(C("param_draws.npz")); M = D["title"].shape[0]; evs = np.zeros((M, len(o)))
    for d in range(M):
        s = dict(title=D["title"][d], conference=D["conference"][d], division=D["division"][d], cup=D["cup"][d], cup_group=D["cup_group"][d],
                 playoffs=D["playoffs"][d], bracket=D["bracket"][d], confrank=D["confrank"][d], pmf=D["wins_pmf"][d])
        evs[d] = prob_vector(o, s) * o.dec.values - 1
    lo_q, hi_q = (1 - assume["ci_level"]) / 2 * 100, (1 + assume["ci_level"]) / 2 * 100
    o["ev_lo"] = np.nanpercentile(evs, lo_q, axis=0); o["ev_hi"] = np.nanpercentile(evs, hi_q, axis=0); o["p_ev_pos"] = (evs > 0).mean(0)
    o["n_draws"] = M
    for name in ("kappa_0", "kappa_hi", "sigma_lo", "sigma_hi"):
        o["ev_" + name] = prob_vector(o, sc[name]) * o.dec.values - 1
    meta = json.load(open(C("sim_robust_meta.json"))); o["bottom10"] = o.team.isin(meta["bottom10_projected"])
    o["robust_ok"] = True; o["robust_reason"] = "ok"
    for i, r in o.iterrows():
        if r.modelled:
            ok, why = RB.passes(r.team, {k: r["ev_" + k] for k in ("kappa_0", "kappa_hi", "sigma_lo", "sigma_hi")})
            o.loc[i, "robust_ok"] = ok; o.loc[i, "robust_reason"] = why
    alt = "Top10" if PLAYOFFS_DEF == "Bracket" else "Bracket"
    o["model_prob_alt"] = prob_vector(o, src, alt); o["ev_alt"] = o.model_prob_alt * o.dec - 1
    evs_alt = np.zeros((M, len(o)))
    for d in range(M):
        s_ = dict(title=D["title"][d], conference=D["conference"][d], division=D["division"][d], cup=D["cup"][d], cup_group=D["cup_group"][d],
                  playoffs=D["playoffs"][d], bracket=D["bracket"][d], confrank=D["confrank"][d], pmf=D["wins_pmf"][d])
        evs_alt[d] = prob_vector(o, s_, alt) * o.dec.values - 1
    o["ev_lo_alt"] = np.nanpercentile(evs_alt, lo_q, axis=0); o["ev_hi_alt"] = np.nanpercentile(evs_alt, hi_q, axis=0)
    o["playoffs_def_primary"] = PLAYOFFS_DEF
    o["p_stake"] = (1 - assume["shrink"]) * o.model_prob + assume["shrink"] * o.fair
    b = o.dec - 1
    o["kelly_full"] = np.clip((o.p_stake * o.dec - 1) / b, 0, None); o["kelly_naive"] = o.kelly_full * assume["kelly_fraction"]
    o["rule_text"] = o.market.map(rule)
    sched = pd.read_csv(C("schedule_games.csv")); first = {}
    for r in sched.sort_values(["date", "game_no"]).itertuples():
        for t in (r.home, r.away):
            if t not in first:
                first[t] = (r.date, r.start_et)

    def lock(r):
        if r.market in ("WINS", "PLAYOFFS") and r.team in first:
            d, st = first[r.team]; hh = int(st.split(":")[0]); mm = int(st.split(":")[1][:2]); pm = st.endswith("p")
            h24 = (hh % 12) + (12 if pm else 0)
            t = pd.Timestamp(d) + pd.Timedelta(hours=h24 - 1, minutes=mm + 10)       # ET -> CST (-1h); +10 min after tip (BOS/DET opener = 2:10 PM CST)
            return t.strftime("%a %m/%d %I:%M %p CST")
        return "Tue 10/20 02:10 PM CST"
    o["lock_cst"] = [lock(r) for r in o.itertuples()]
    o["imputed"] = o.flag.eq("IMPUTED_20C_LADDER")
    cand = o.modelled & ~o.imputed
    o["rule_confirmed"] = ~o.market.eq("PLAYOFFS")        # PLAYOFFS definition (top-8 pricing vs top-10 rule text) is UNCONFIRMED -> no bets until Max confirms
    o["qualifies"] = cand & (o.ev >= assume["min_ev"]) & (o.ev_lo > 0) & o.robust_ok & o.rule_confirmed
    o["qualifies_if_confirmed"] = cand & (o.ev >= assume["min_ev"]) & (o.ev_lo > 0) & o.robust_ok
    Q = o[o.qualifies].copy()
    Z = np.load(os.path.join(ROOT, "sims/season_sims.npz")); flags = Z["flags"]; wins = Z["wins"]; cr = Z["conf_rank"]

    def outcome(r):
        t = IDX[r.team]; m = r.market
        if m == "TITLE": return (flags[:, t] & 16) > 0
        if m in ("CONF_EAST", "CONF_WEST"): return (flags[:, t] & 8) > 0
        if m in DIVMAP: return (flags[:, t] & 4) > 0
        if m == "CUP": return (flags[:, t] & 64) > 0
        if m.startswith("CUP_"): return (flags[:, t] & 32) > 0
        if m in ("PLAYIN_EAST", "PLAYIN_WEST"): return (cr[:, t] >= 7) & (cr[:, t] <= 10)
        if m == "PLAYOFFS": return (cr[:, t] <= 10) if r.side == "YES" else (cr[:, t] > 10)
        thr = int(math.floor(r.line)) + 1
        return (wins[:, t] >= thr) if r.side == "OVER" else (wins[:, t] < thr)
    o["kelly_portfolio"] = 0.0
    if len(Q):
        X = np.stack([outcome(r) for r in Q.itertuples()], 1)
        f_port, f_full, w = portfolio_kelly(X, Q.dec.values, Q.p_stake.values, assume["kelly_fraction"], assume["max_exposure"])
        o.loc[Q.index, "kelly_portfolio"] = f_port
        R = np.where(X, (Q.dec.values - 1)[None, :], -1.0); pnl = R @ f_port
        corr = np.corrcoef(X.astype(float).T) if X.shape[1] > 1 else np.ones((1, 1))
        summ_ = dict(n_bets=int(len(Q)), total_stake_frac=float(f_port.sum()), exp_return_frac=float(pnl.mean()), p_profit=float((pnl > 0).mean()), median=float(np.median(pnl)),
                     p05=float(np.percentile(pnl, 5)), p95=float(np.percentile(pnl, 95)), worst=float(pnl.min()), p01=float(np.percentile(pnl, 1)),
                     exp_return_tilted=float((w * pnl).sum()), full_kelly_sum=float(f_full.sum()))
        by_team = Q.assign(stake=f_port).groupby("team").stake.sum().to_dict()
        json.dump(dict(summary=summ_, by_team=by_team), open(C("portfolio_summary.json"), "w"), indent=1)
        lab = (Q.market + "|" + Q.selection + "|" + Q.side).values
        pd.DataFrame(corr, index=lab, columns=lab).to_csv(C("portfolio_corr.csv"))
        np.save(C("portfolio_pnl.npy"), pnl.astype(np.float32))
    o.to_csv(C("pricing_table.csv"), index=False)
    o[o.qualifies].sort_values("ev", ascending=False).to_csv(C("bet_card.csv"), index=False)
    return o


if __name__ == "__main__":
    o = main(); Q = o[o.qualifies]
    print("rows", len(o), "modelled", int(o.modelled.sum()), "qualifying", len(Q))
    print(Q.sort_values("ev", ascending=False)[["market", "selection", "side", "line", "american", "model_prob", "fair", "ev", "ev_lo", "ev_hi", "kelly_naive", "kelly_portfolio"]].round(4).to_string())
    print("EV>=3% but CI lower bound <=0:", int((o.modelled & ~o.imputed & (o.ev >= ASSUME["min_ev"]) & ~(o.ev_lo > 0)).sum()), "| fail robustness:", int((o.modelled & (o.ev >= ASSUME["min_ev"]) & (o.ev_lo > 0) & ~o.robust_ok).sum()))
