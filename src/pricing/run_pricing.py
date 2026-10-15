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
         "PLAYOFFS": "Makes the 16-team playoff field, including via the play-in (top-8 per conference; user-confirmed from implied sums ~8.7/conf) - CONFIRM WITH BOOK; action requires 82 games unless already determined",
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
    o["rule_confirmed"] = True            # PLAYOFFS = 16-team field (Bracket), confirmed by the user from the implied sums; still flagged CONFIRM WITH BOOK
    # --- zero-sum filter: rescale model win means so the league sums to the book's 1,241 (shift every team by delta wins) and keep only WINS bets that survive
    wl = o[(o.market == "WINS") & (o.side == "OVER")]
    delta = (wl.line.sum() - 1230.0) / 30.0
    o["zs_delta"] = delta
    o["p_zs"] = np.nan; evz = np.full((M, len(o)), np.nan)
    for i, r in o.iterrows():
        if r.market == "WINS":
            t = IDX[r.team]; o.loc[i, "p_zs"] = wins_prob_shift(src["pmf"][t], r.line, r.side, delta)
            for d in range(M):
                evz[d, i] = wins_prob_shift(D["wins_pmf"][d][t], r.line, r.side, delta) * r.dec - 1
    o["ev_zs"] = o.p_zs * o.dec - 1; o["ev_lo_zs"] = np.nanpercentile(evz, lo_q, axis=0)
    o["zs_ok"] = np.where(o.market == "WINS", (o.ev_zs >= assume["min_ev"]) & (o.ev_lo_zs > 0), True) if assume.get("zero_sum_filter", True) else True
    # --- shrunk-edge test: the edge must survive when the model is shrunk toward the market (EV is linear in p, so the CI shifts exactly)
    def shrunk(s_):
        ev_s = ((1 - s_) * o.model_prob + s_ * o.fair) * o.dec - 1
        lo_s = (1 - s_) * o.ev_lo + s_ * (o.fair * o.dec - 1)
        return ev_s, lo_s
    o["ev_s"], o["ev_lo_s"] = shrunk(assume["shrink"]); ev25, lo25 = shrunk(0.25)
    # ---------------- filter waterfall (each step applied in this order)
    ev_ok = (o.ev >= assume["min_ev"]) & (o.ev_lo > 0)
    r0 = cand & ev_ok & ~o.market.eq("PLAYOFFS")                                  # raw: positive EV, CI low > 0, not imputed (PLAYOFFS still blocked)
    r1 = cand & ev_ok                                                             # + PLAYOFFS priced as the 16-team field (user-confirmed)
    r2 = r1 & o.zs_ok                                                             # + WINS survive rescale to the book's sum (zero-sum)
    r3 = r2 & (o.ev_s >= assume["min_ev"]) & (o.ev_lo_s > 0)                      # + edge survives shrink toward the market
    r4 = r3 & o.robust_ok                                                         # + robustness (bottom-10: kappa 0/hi, sigma -/+10%)
    # longshot control: fair<5% must survive shrink + sigma_team -10%; and EV-miscalibrated fair-probability buckets are excluded
    bins = [0, 0.02, 0.05, 0.15, 0.50, 1.01]; labs = ["<2%", "2-5%", "5-15%", "15-50%", ">50%"]
    o["fair_bucket"] = pd.cut(o.fair, bins, labels=labs, right=False)
    mod = o[o.modelled & ~o.imputed]
    bk = mod.groupby("fair_bucket", observed=False).ev.agg(["count", "median", lambda x: x.quantile(0.25), lambda x: x.quantile(0.75)]); bk.columns = ["n", "median_ev", "p25_ev", "p75_ev"]
    bad_buckets = [b for b, r in bk.iterrows() if r["n"] > 0 and r["median_ev"] > 0.20]
    o["bucket_excl"] = o.fair_bucket.astype(str).isin(bad_buckets) & o.modelled
    ev_s_slo = ((1 - assume["shrink"]) * (o.ev_sigma_lo + 1) / o.dec + assume["shrink"] * o.fair) * o.dec - 1
    o["longshot_ok"] = np.where(o.fair < 0.05, ev_s_slo >= assume["min_ev"], True) & ~o.bucket_excl
    r5 = r4 & o.longshot_ok
    # low-continuity teams: wins / playoffs / division edges must survive shrink 0.75
    cont = pd.read_csv(C("team_projection_2027.csv")).set_index("abbr").continuity
    o["continuity"] = o.team.map(cont); low = o.continuity < 0.55
    ev75 = (0.25 * o.model_prob + 0.75 * o.fair) * o.dec - 1; lo75 = 0.25 * o.ev_lo + 0.75 * (o.fair * o.dec - 1)
    fam = o.market.isin(["WINS", "PLAYOFFS"]) | o.market.str.startswith("DIV_")
    o["continuity_ok"] = ~(low & fam) | ((ev75 >= assume["min_ev"]) & (lo75 > 0))
    r6 = r5 & o.continuity_ok
    # compression rule (applies only if the post-fix compression test is significantly negative): no wins unders on market top-5, no overs on market bottom-5 unless a verified driver exists
    comp = json.load(open(C("compression_test.json"))) if os.path.exists(C("compression_test.json")) else {"apply_rule": False}
    o["comp_block"] = False
    if comp.get("apply_rule"):
        W_ = pd.read_csv(C("model_vs_market_wins_table.csv"), index_col=0); top5 = W_.sort_values("mkt_median", ascending=False).head(5).index.tolist(); bot5 = W_.sort_values("mkt_median").head(5).index.tolist()
        ver = pd.read_csv(os.path.join(ROOT, "params/verified_drivers.csv")) if os.path.exists(os.path.join(ROOT, "params/verified_drivers.csv")) else pd.DataFrame(columns=["team", "market", "fact"])
        okteams = set(ver[ver.market == "WINS"].team)
        o["comp_block"] = (o.market == "WINS") & (((o.side == "UNDER") & o.team.isin(top5)) | ((o.side == "OVER") & o.team.isin(bot5))) & ~o.team.isin(okteams)
    r7 = r6 & ~o.comp_block
    o["static_block"] = o.bucket_excl | o.comp_block
    o["qualifies"] = r7; o["qualifies_if_confirmed"] = r7
    ev25 = ((0.75 * o.model_prob + 0.25 * o.fair) * o.dec - 1); lo25 = 0.75 * o.ev_lo + 0.25 * (o.fair * o.dec - 1)
    o["qualifies_shrink025"] = r2 & (ev25 >= assume["min_ev"]) & (lo25 > 0) & o.robust_ok & o.longshot_ok & o.continuity_ok & ~o.comp_block
    json.dump(dict(raw=int(r0.sum()), playoff_fix=int(r1.sum()), zero_sum=int(r2.sum()), shrink=int(r3.sum()), robustness=int(r4.sum()), longshot=int(r5.sum()), continuity=int(r6.sum()), compression_rule=int(r7.sum()),
                   final=int(r7.sum()), shrink_final=assume["shrink"], zs_delta=float(delta), bad_buckets=bad_buckets, shrink025_alt_final=int(o.qualifies_shrink025.sum()),
                   wins_by_step={k: int((v & (o.market == "WINS")).sum()) for k, v in dict(raw=r0, playoff_fix=r1, zero_sum=r2, shrink=r3, robustness=r4, longshot=r5, continuity=r6, final=r7).items()},
                   ev_by_bucket=bk.round(4).reset_index().astype({"fair_bucket": str}).to_dict("records")), open(C("qualification_waterfall.json"), "w"), indent=1)
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
        if m == "PLAYOFFS":
            inn = ((flags[:, t] & 128) > 0) if PLAYOFFS_DEF == "Bracket" else (cr[:, t] <= 10)
            return inn if r.side == "YES" else ~inn
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
