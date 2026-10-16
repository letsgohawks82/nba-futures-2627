"""Tier 1 card: the conservative subset of the Bet Card. Filters (all must hold):
 1. edge survives shrink 0.75 (model weight 0.25): EV >= min EV and shrunk CI low > 0
 2. market fair probability >= 5%
 3. not against a market top-5 team (wins UNDER, PLAYOFFS NO) and not backing a market bottom-5 team (wins OVER, PLAYOFFS/DIV/CONF/TITLE YES)
 4. a named driver: the team-level model-vs-market gap is explained (>= 50%) by 1-3 identifiable player / roster facts
 5. total Tier 1 exposure capped at 10% of bankroll (portfolio Kelly re-solved on the Tier 1 set)
Everything else on the Bet Card is Tier 2 (no stake by default)."""
import json, math, os
import numpy as np, pandas as pd
from .price import portfolio_kelly, DIVMAP
from . import consensus as CS
from ..ratings.prep import player_seasons
from ..sim.inputs import IDX, B_TEAM, R_REPL, TEAM_LIST

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
C = lambda f: os.path.join(ROOT, "data", "clean", f)
SHRINK_T1 = 0.75; CAP_T1 = 0.10; FAIR_MIN = 0.05; COVER_MIN = 0.6; MIN_FACT = 1.0      # named driver: verifiable arrival / departure / availability facts of >= 1.0 SRS covering >= 60% of the gap


def team_facts(k_wins):
    P = pd.read_csv(C("player_projection_2027.csv")); W = pd.read_csv(C("model_vs_market_wins_table.csv"), index_col=0)
    ps, st = player_seasons(); ps26 = ps[ps.season == 2026].drop_duplicates("bbref_id").set_index("bbref_id"); st26 = st[(st.season == 2026) & st.bbref_id.notna()]
    tot26 = st26.groupby("team").mp_team.sum()
    out = {}
    for t in TEAM_LIST:
        d = P[P.abbr == t].copy(); gap_wins = float(W.loc[t, "diff"]) if t in W.index else 0.0; gap_srs = abs(gap_wins) / k_wins; sign = 1 if gap_wins >= 0 else -1
        d["c27"] = B_TEAM * d.proj_min / (19680 / 5) * d.rating
        prev = st26[st26.team == t].set_index("bbref_id").mp_team
        d["c26"] = [B_TEAM * float(prev.get(b, 0.0)) / (tot26.get(t, 19680) / 5) * float(ps26.bpm.get(b, 0.0) if b in ps26.index and pd.notna(ps26.bpm.get(b)) else 0.0) if isinstance(b, str) else 0.0 for b in d.bbref_id]
        d["delta"] = d.c27 - d.c26
        # departed players (not on the roster now): negative contribution change
        cur = set(d.bbref_id.dropna())
        dep = []
        for b, m in prev.items():
            if b not in cur and m >= 600 and b in ps26.index:
                c = B_TEAM * m / (tot26.get(t, 19680) / 5) * float(ps26.bpm.get(b, 0.0) if pd.notna(ps26.bpm.get(b)) else 0.0)
                dep.append(dict(name=ps26.loc[b, "name_display"], delta=-c, kind="departed", rating=float(ps26.bpm.get(b, 0.0)), mp=float(m)))
        facts = []
        for _, r in d.iterrows():
            tag = "new" if (r.c26 == 0 and r.proj_min > 600) else ("returning" if r.c26 != 0 else None)
            if abs(r.delta) >= 0.15 and r.proj_min > 400:
                dpm = f"DARKO {r.dpm:+.1f}" if pd.notna(r.dpm) else "no DARKO"
                facts.append(dict(name=r["name"], delta=float(r.delta), kind=("arrival" if tag == "new" else "role/rating change"),
                                  text=f"{r['name']} rated {r.rating:+.1f} ({dpm}), {r.proj_mpg:.0f} mpg, {r.proj_gp:.0f} g ({'new to team' if tag == 'new' else 'returning'}; {r.delta:+.1f} SRS vs 2025-26)"))
        for x in dep:
            if abs(x["delta"]) >= 0.15:
                facts.append(dict(name=x["name"], delta=float(x["delta"]), kind="departure", text=f"{x['name']} gone ({x['mp']:.0f} min at {x['rating']:+.1f} BPM last year; {x['delta']:+.1f} SRS)"))
        for _, r in d.nlargest(4, "proj_min").iterrows():          # availability: top-4 players projected to miss time
            lost = B_TEAM * (r.proj_mpg / 48) * max(r.rating - R_REPL, 0) * (1 - r.gfrac_hat_raw)
            if r.gfrac_hat_raw < 0.70 and lost >= 0.3:
                facts.append(dict(name=r["name"], delta=float(-lost), kind="availability", text=f"{r['name']} projected {r.proj_gp:.0f} games (injury/age history; costs {lost:.1f} SRS vs full health)"))
        top4 = set(d.nlargest(4, "proj_min")["name"])
        ok_kind = lambda f: f["kind"] in ("arrival", "departure", "availability") and abs(f["delta"]) >= MIN_FACT and (f["kind"] != "arrival" or f["name"] in top4)
        aligned = sorted([f for f in facts if f["delta"] * sign > 0 and ok_kind(f)], key=lambda f: -abs(f["delta"]))[:3]
        cover = sum(abs(f["delta"]) for f in aligned) / gap_srs if gap_srs > 0 else 0.0
        named = bool(aligned) and cover >= COVER_MIN
        out[t] = dict(team=t, gap_wins=gap_wins, gap_srs=gap_srs, direction=sign, coverage=cover, named=named, facts=[f["text"] for f in aligned], fact_effects=[round(f["delta"], 2) for f in aligned])
    return out


def run(table="pricing_table.csv"):
    o = pd.read_csv(C(table)); k = json.load(open(os.path.join(ROOT, "params/provenance.json")))["k_wins_per_srs"]["value"]
    W = pd.read_csv(C("model_vs_market_wins_table.csv"), index_col=0)
    top5 = W.sort_values("mkt_median", ascending=False).head(5).index.tolist(); bot5 = W.sort_values("mkt_median").head(5).index.tolist()
    facts = team_facts(k)
    ev75 = (0.25 * o.model_prob + 0.75 * o.fair) * o.dec - 1; lo75 = 0.25 * o.ev_lo + 0.75 * (o.fair * o.dec - 1)
    o["t1_shrink75"] = (ev75 >= 0.03) & (lo75 > 0); o["ev75"] = ev75; o["ev_lo75"] = lo75
    o["t1_fair5"] = o.fair >= FAIR_MIN
    fam = o.market.isin(["WINS", "PLAYOFFS", "TITLE", "CONF_EAST", "CONF_WEST"]) | o.market.str.startswith("DIV_")
    against_top = fam & o.team.isin(top5) & (((o.market == "WINS") & (o.side == "UNDER")) | ((o.market == "PLAYOFFS") & (o.side == "NO")))
    for_bottom = fam & o.team.isin(bot5) & (((o.market == "WINS") & (o.side == "OVER")) | ((o.market != "WINS") & (o.side == "YES")))
    o["t1_direction"] = ~(against_top | for_bottom)
    o["t1_named"] = o.team.map(lambda t: bool(facts[t]["named"]) if t in facts else False)
    o["t1_driver"] = o.team.map(lambda t: " | ".join(facts[t]["facts"]) if t in facts else "")
    # WINS: the consensus rule replaces the named-driver rule
    T, summ = CS.table(o); cons = []; basis = []
    for r in o.itertuples():
        if r.market != "WINS" or r.team not in T.index: cons.append("n/a"); basis.append(""); continue
        t = T.loc[r.team]; ok = bool(t.pass_over if r.side == "OVER" else t.pass_under); cons.append("PASS" if ok else "FAIL")
        ra = "; ".join(f"{k} {t['res_' + k]:+.1f}" for k in ("ours", "PredictionEngine")); rb = "; ".join(f"{k} {t['res_' + k]:+.1f}" for k in summ if summ[k]["method"] == "results_based")
        dsp = "; ".join(f"{k} {t['res_' + k]:+.1f}" for k in summ if summ[k]["type"] in ("MARKET_INFORMED", "EXPERT"))
        basis.append(f"residuals vs market median {t['median']:.1f}: roster-aware [{ra}]; results-based {'(counted)' if t.rb_eligible else '(ignored: ' + t.rb_reason + ')'} [{rb}]; display [{dsp}]")
    o["t1_cons"] = cons; o["t1_cons_basis"] = basis
    isw = o.market == "WINS"; o["t1_named"] = np.where(isw, o.t1_cons == "PASS", o.t1_named); o["t1_driver"] = np.where(isw, o.t1_cons_basis, o.t1_driver)
    ps_ = (0.25 * o.model_prob + 0.75 * o.fair); dm = 1.0 / ps_.clip(lower=1e-9)
    o["min_price"] = np.where(dm >= 2, (dm - 1) * 100.0, -100.0 / (dm - 1.0 + 1e-12))
    o["t1_gap_srs"] = o.team.map(lambda t: facts[t]["gap_srs"] if t in facts else np.nan); o["t1_cover"] = o.team.map(lambda t: facts[t]["coverage"] if t in facts else np.nan)
    ovr = json.load(open(os.path.join(ROOT, "params/tier1_overrides.json")))
    o["t1_excluded"] = False; o["t1_scenario_ok"] = True; o["t1_scenario_ev75"] = np.nan; o["t1_scenario_lo75"] = np.nan
    for e in ovr.get("exclude", []) + ovr.get("hold", []):
        if "team" in e: o.loc[(o.market == e["market"]) & (o.team == e["team"]), "t1_excluded"] = True
    g = ovr.get("scenario_gate")
    if g and os.path.exists(C(g["file"])):
        sc = json.load(open(C(g["file"]))); base_lo = {}
        for i, r in o[(o.team == g["team"]) & o.market.isin(g["markets"])].iterrows():
            p_s = sc["point"][g["point_keys"][r.market]]; p_lo = sc["ci"][g["ci_keys"][r.market]]
            ev_s = (0.25 * p_s + 0.75 * r.fair) * r.dec - 1; lo_s = (0.25 * p_lo + 0.75 * r.fair) * r.dec - 1
            o.loc[i, ["t1_scenario_ev75", "t1_scenario_lo75"]] = [ev_s, lo_s]; o.loc[i, "t1_scenario_ok"] = bool(ev_s >= 0.03 and lo_s > 0)
    o["t1_static_ok"] = o.t1_direction & o.t1_named & ~o.t1_excluded & o.t1_scenario_ok          # engine-side static part; shrink/fair tests are live in the workbook
    o["tier1"] = o.qualifies & o.t1_shrink75 & o.t1_fair5 & o.t1_static_ok
    wf = dict(tier2_all=int(o.qualifies.sum()), shrink075=int((o.qualifies & o.t1_shrink75).sum()), fair_ge_5pct=int((o.qualifies & o.t1_shrink75 & o.t1_fair5).sum()),
              direction_rule=int((o.qualifies & o.t1_shrink75 & o.t1_fair5 & o.t1_direction).sum()), named_driver=int(o.tier1.sum()))
    o["tier1_kelly"] = 0.0
    Z = np.load(os.path.join(ROOT, "sims/season_sims.npz")); flags = Z["flags"]; wins = Z["wins"]; cr = Z["conf_rank"]
    Q = o[o.tier1]
    if len(Q):
        def outcome(r):
            t = IDX[r.team]; m = r.market
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
        X = np.stack([outcome(r) for r in Q.itertuples()], 1)
        p_stake = 0.25 * Q.model_prob.values + 0.75 * Q.fair.values            # Tier 1 stakes use the 0.75 shrink
        f, _, _ = portfolio_kelly(X, Q.dec.values, p_stake, 0.25, CAP_T1)
        o.loc[Q.index, "tier1_kelly"] = f
        R = np.where(X, (Q.dec.values - 1)[None, :], -1.0); pnl = R @ f
        wf.update(total_stake_frac=float(f.sum()), exp_return_model=float(pnl.mean()), p_profit=float((pnl > 0).mean()), p05=float(np.percentile(pnl, 5)), worst=float(pnl.min()))
    json.dump(dict(waterfall=wf, top5=top5, bottom5=bot5, team_facts={t: {k_: v for k_, v in f.items()} for t, f in facts.items()}), open(C("tier1_summary.json"), "w"), indent=1, default=str)
    o.to_csv(C("pricing_table.csv"), index=False)
    o[o.tier1].sort_values("tier1_kelly", ascending=False).to_csv(C("tier1_card.csv"), index=False)
    return o, wf, facts


if __name__ == "__main__":
    o, wf, facts = run(); pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 200)
    print(wf)
    T = o[o.tier1].sort_values("tier1_kelly", ascending=False)
    print(T[["market", "selection", "side", "line", "american", "model_prob", "fair", "ev", "ev75", "ev_lo75", "tier1_kelly", "t1_cover"]].round(4).to_string())
    for _, r in T.iterrows(): print(f"- {r.market} {r.selection} {r.side} {'' if pd.isna(r.line) else r.line}: {r.t1_driver}")
    print("\nteams with named drivers:", [t for t, f in facts.items() if f["named"]]); print("diffuse:", [t for t, f in facts.items() if not f["named"]])
