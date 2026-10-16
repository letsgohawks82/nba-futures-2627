"""G4 player-market pricing: de-vig (Shin, S=1) each outright market, join the simulated probabilities (point + 80% season-block-bootstrap interval + scenarios),
EV, shrunk-edge test, longshot control, robustness scenarios, and the same Tier 1 gate as the team card (shrink 0.75, fair >= 5%, named driver).
Stakes: single-bet fractional Kelly on the shrunk probability within a market (mutually exclusive outcomes -> multi-outcome Kelly), 0.25 fraction, capped with the team Tier 1 exposure."""
import json, os
import numpy as np, pandas as pd
from scipy.optimize import minimize
from .price import load_odds, add_devig
from ..data.namemap import norm

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
C = lambda f: os.path.join(ROOT, "data", "clean", f)
PLAYER_MARKETS = ["LDR_PPG", "LDR_RPG", "LDR_APG", "LDR_SPG", "LDR_BPG", "LDR_TPG", "MVP", "DPOY", "ROY"]
DISPLAY = ["MIP", "SMOY", "COY", "CLUTCH", "CUP_MVP"]
A = dict(shrink=0.5, shrink_t1=0.75, min_ev=0.03, fair_min=0.05, kelly_fraction=0.25, tier1_cap=0.10, market_cap=0.03)
STAT = {"LDR_PPG": "PPG", "LDR_RPG": "RPG", "LDR_APG": "APG", "LDR_SPG": "SPG", "LDR_BPG": "BPG", "LDR_TPG": "TPG"}


def multi_kelly(p, dec, frac):
    """Full-Kelly stakes for mutually exclusive outcomes (one winner or none): maximise sum p_i log(1 + f_i (dec_i - 1) - sum_{j != i} f_j) + p_0 log(1 - sum f)."""
    n = len(p); p0 = max(1 - p.sum(), 0.0)
    def neg(f):
        tot = f.sum(); g = 0.0; gr = np.zeros(n)
        for i in range(n):
            w = 1 + f[i] * (dec[i] - 1) - (tot - f[i]); g += p[i] * np.log(max(w, 1e-9)); gr += p[i] * (-1.0 / max(w, 1e-9)) * np.ones(n); gr[i] += p[i] * (dec[i] / max(w, 1e-9))
        if p0 > 0: g += p0 * np.log(max(1 - tot, 1e-9)); gr += p0 * (-1.0 / max(1 - tot, 1e-9))
        return -g, -gr
    r = minimize(neg, np.zeros(n), jac=True, method="L-BFGS-B", bounds=[(0, 0.5)] * n); return np.clip(r.x, 0, None) * frac


def main():
    o = load_odds(); o = o[o.market.isin(PLAYER_MARKETS + DISPLAY)].copy().reset_index(drop=True); o = add_devig(o, "Shin")
    nm = pd.read_csv(C("name_map.csv")); nm = nm[nm.source == "odds_book"].set_index("source_name").canonical
    o["key"] = [norm(nm.get(s) if isinstance(nm.get(s), str) else s) for s in o.selection]; o["mkey"] = o.market + "|" + o["key"]
    pr = pd.read_csv(C("player_market_probs.csv")); pr["mkey"] = pr.market + "|" + pr.key
    # stat-leader sharpening: leave-one-season-out CV (src/players/sharpen_cv.py) shows the lognormal engine overstates longshots and understates favourites even after the SD fix;
    # p^gamma renormalised per market restores calibration. Production = pooled gamma; Tier 1 must also survive the gamma 80% CI bounds. Awards are not sharpened.
    sh = json.load(open(C("g4_leader_sharpen.json"))); gam = sh["gamma"]; ld = pr.market.str.startswith("LDR_"); PCOLS = ["p", "p_lo", "p_hi", "p_sd_lo", "p_sd_hi", "p_no65", "p_mpg_lo"]
    def sharpen(pr0, gm):
        q = pr0.copy()
        for mk, g in q[q.market.str.startswith("LDR_")].groupby("market"):
            Z = (g.p ** gm).sum()
            for c in PCOLS: q.loc[g.index, c] = (g[c] ** gm) / Z
        return q.drop_duplicates("mkey").set_index("mkey")
    pr_raw = pr; pr = sharpen(pr_raw, gam); pr_alt = {"lo": sharpen(pr_raw, sh["gamma_ci80"][0]), "hi": sharpen(pr_raw, sh["gamma_ci80"][1])}

    for c in ["p", "p_lo", "p_hi", "p_sd_lo", "p_sd_hi", "p_no65", "p_mpg_lo", "proj_mpg", "proj_gp", "rating", "pg_PPG", "pg_RPG", "pg_APG", "pg_SPG", "pg_BPG", "pg_TPG"]:
        o[c] = o.mkey.map(pr[c]) if c in pr else np.nan
    o["modelled"] = o.market.isin(PLAYER_MARKETS); o["display_only"] = o.market.isin(DISPLAY)
    on_pool = o.modelled & o.p.isna(); o.loc[on_pool, ["p", "p_lo", "p_hi", "p_sd_lo", "p_sd_hi", "p_no65", "p_mpg_lo"]] = 0.0     # not once in 100k sims
    o["model_prob"] = o.p
    ev = lambda p, s: ((1 - s) * p + s * o.fair) * o.dec - 1
    o["ev"] = o.p * o.dec - 1; o["ev_lo"] = o.p_lo * o.dec - 1
    o["ev_s"] = ev(o.p, A["shrink"]); o["ev_lo_s"] = ev(o.p_lo, A["shrink"])
    o["ev75"] = ev(o.p, A["shrink_t1"]); o["ev_lo75"] = ev(o.p_lo, A["shrink_t1"])
    scen = {k: ev(o[c], A["shrink"]) for k, c in dict(sd_lo="p_sd_lo", sd_hi="p_sd_hi", mpg_lo="p_mpg_lo").items()}
    scen["no65"] = ev(o.p_no65, A["shrink"]); scen_min = pd.concat(scen.values(), axis=1).min(1)
    o["ev_s_worst_scenario"] = scen_min
    o["robust_ok"] = scen_min >= A["min_ev"]
    o["fair_ge_5"] = o.fair >= A["fair_min"]
    o["longshot_ok"] = np.where(o.fair < 0.05, scen["sd_hi"] >= A["min_ev"], True)
    ok = o.modelled & (o.ev_s >= A["min_ev"]) & (o.ev_lo_s > 0)
    o["tier2"] = ok & o.robust_ok & o.longshot_ok
    # driver text: the projection facts behind each probability
    pool = pd.read_csv(C("g4_pool.csv")).set_index("key")
    P = pd.read_csv(C("player_projection_2027.csv")); P["key"] = P.name.map(norm); P = P.drop_duplicates("key").set_index("key")
    roy_lines = {x["player"].replace(" Jr.", ""): x for x in json.load(open(C("g4_jokic_rookie.json")))["roy_candidates"]}
    roy_lines.update({x["player"]: x for x in json.load(open(C("g4_jokic_rookie.json")))["roy_candidates"]})
    def driver(r):
        if not r.modelled or pd.isna(r.p) or r.p <= 0: return ""
        k = r["key"]; t = []
        if r.market in STAT:
            s = STAT[r.market]; mine = r["pg_" + s]
            comp = pr[(pr.market == r.market)].sort_values("p", ascending=False).head(4)
            t.append(f"proj {s} {mine:.1f} in {r.proj_mpg:.0f} mpg; {r.proj_gp:.0f} games projected")
            top = comp[comp.key != k].head(1)
            if len(top): t.append(f"model rival {top.player.iloc[0]} {top['pg_' + s].iloc[0]:.1f} (p={top.p.iloc[0]:.0%})")
        elif r.market == "ROY" and r["selection"] in roy_lines:
            x = roy_lines[r["selection"]]; t.append(f"pick {x['pick']:.0f}, age {x['age']:.0f}: {x['proj_mpg_minutes_model']:.0f} mpg (slot/age fit {x['mpg_from_slot_age_fit']:.0f}) x {x['pts36_fit']:.1f} pts/36 = {x['ppg_with_minutes_model']:.1f} ppg; {r.proj_gp:.0f} games projected; last 5 ROY winners averaged 18.5 ppg in 31.8 mpg")
        else:
            t.append(f"rating {r.rating:+.1f}; proj {r.pg_PPG:.1f}p/{r.pg_RPG:.1f}r/{r.pg_APG:.1f}a/{r.pg_SPG:.1f}s/{r.pg_BPG:.1f}b in {r.proj_mpg:.0f} mpg; {r.proj_gp:.0f} games")
        return "; ".join(t)
    o["driver"] = [driver(r) for r in o.itertuples()] if False else [driver(r) for _, r in o.iterrows()]
    def t1_at(prx):
        pp = o.mkey.map(prx.p).fillna(0.0); pl = o.mkey.map(prx.p_lo).fillna(0.0)
        wc = pd.concat([ev(o.mkey.map(prx[c]).fillna(0.0), A["shrink"]) for c in ("p_sd_lo", "p_sd_hi", "p_mpg_lo", "p_no65")], axis=1).min(axis=1)
        return o.modelled & (ev(pp, A["shrink_t1"]) >= A["min_ev"]) & (ev(pl, A["shrink_t1"]) > 0) & (wc >= A["min_ev"])
    o["tier1_gamma_lo"] = t1_at(pr_alt["lo"]); o["tier1_gamma_hi"] = t1_at(pr_alt["hi"])
    o["tier1"] = o.tier2 & (o.ev75 >= A["min_ev"]) & (o.ev_lo75 > 0) & o.fair_ge_5 & o.tier1_gamma_lo & o.tier1_gamma_hi
    # stakes
    o["stake_t2"] = 0.0; o["stake_t1"] = 0.0
    for mk, g in o[o.tier2].groupby("market"):
        f = multi_kelly(((1 - A["shrink"]) * g.p + A["shrink"] * g.fair).values, g.dec.values, A["kelly_fraction"]); o.loc[g.index, "stake_t2"] = np.minimum(f, A["market_cap"])
    for mk, g in o[o.tier1].groupby("market"):
        f = multi_kelly(((1 - A["shrink_t1"]) * g.p + A["shrink_t1"] * g.fair).values, g.dec.values, A["kelly_fraction"]); o.loc[g.index, "stake_t1"] = np.minimum(f, A["market_cap"])
    ps_ = (1 - A["shrink_t1"]) * o.p + A["shrink_t1"] * o.fair; dm = 1.0 / ps_.clip(lower=1e-9); o["min_price"] = np.where(dm >= 2, (dm - 1) * 100.0, -100.0 / (dm - 1.0 + 1e-12))
    o.to_csv(C("player_pricing_table.csv"), index=False)
    return o


if __name__ == "__main__":
    o = main(); pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 120)
    cols = ["market", "selection", "american", "fair", "model_prob", "p_lo", "p_hi", "ev", "ev_s", "ev_lo_s", "ev75", "ev_s_worst_scenario", "stake_t1", "stake_t2"]
    print("Tier2:", int(o.tier2.sum()), "Tier1:", int(o.tier1.sum()))
    print(o[o.tier2].sort_values("ev_s", ascending=False)[cols].round(3).to_string())
    print("\n".join(f"- {r.market} {r.selection}: {r.driver}" for _, r in o[o.tier1].iterrows()))
    # largest model-vs-market gaps overall
    g = o[o.modelled].assign(gap=lambda d: d.model_prob - d.fair).sort_values("gap")
    print(g[["market", "selection", "american", "fair", "model_prob", "p_lo", "p_hi", "ev"]].head(8).round(3).to_string()); print(g[["market", "selection", "american", "fair", "model_prob", "p_lo", "p_hi", "ev"]].tail(12).round(3).to_string())
