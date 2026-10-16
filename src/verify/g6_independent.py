"""G6 independent verification. Imports NO pricing/model code: raw odds CSV + engine output tables + saved sim outcomes + the built workbook's cached values.
 1. Shin / power de-vig re-derived (own bisection) for EVERY Tier 1 row's market group and for 10 random market groups, compared with the pricing tables and the workbook.
 2. EV, shrunk EV (0.75), single-bet and joint portfolio Kelly re-derived for every Tier 1 row (own projected-gradient solver on the saved sim outcome matrix).
 3. Model probabilities of team bets re-derived from the sims; Excel cached values compared to the engine.
Writes data/clean/g6_verification.json and prints a table."""
import csv, glob, json, math, os, random
import numpy as np, openpyxl

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
C = lambda f: os.path.join(ROOT, "data", "clean", f)


def dec(a): return 1 + a / 100.0 if a > 0 else 1 + 100.0 / abs(a)


def shin(pi):
    s = sum(pi)
    if s <= 1.0: return [x / s for x in pi]
    f = lambda z: sum((math.sqrt(z * z + 4 * (1 - z) * x * x / s) - z) / (2 * (1 - z)) for x in pi) - 1.0
    lo, hi = 1e-12, 0.9999
    for _ in range(200):
        mid = (lo + hi) / 2
        if f(mid) > 0: lo = mid
        else: hi = mid
    z = (lo + hi) / 2
    return [(math.sqrt(z * z + 4 * (1 - z) * x * x / s) - z) / (2 * (1 - z)) for x in pi]


def power(pi, S=1.0):
    lo, hi = 0.2, 10.0
    for _ in range(200):
        k = (lo + hi) / 2
        if sum(x ** k for x in pi) > S: lo = k
        else: hi = k
    return [x ** ((lo + hi) / 2) for x in pi]


def mult(pi, S=1.0): s = sum(pi); return [x * S / s for x in pi]


def own_min(ps):
    d = 1.0 / ps
    return (d - 1) * 100.0 if d >= 2 else -100.0 / (d - 1)


def own_consensus(r, fair_over):
    """WINS consensus re-derived from the raw inputs only: market median from the de-vigged OVER probability, compression bias, bias-adjusted gaps."""
    pr = json.load(open(os.path.join(ROOT, "params/tier1_overrides.json"))); src = json.load(open(os.path.join(ROOT, "data/consensus/sources.json")))["sources"]
    rows = list(csv.DictReader(open(os.path.join(ROOT, "data/consensus/consensus_wins_2026-10-15.csv")))); M = {x["team"]: x for x in rows}
    tp = {x["abbr"]: float(x["pred_wins"]) for x in csv.DictReader(open(C("team_projection_2027.csv")))}
    line = float(r["line"]); med = line + (fair_over - 0.5) / pr["p_per_win"]; bias = pr["comp_slope"] * (med - 41.0)
    return med, bias, tp, M, pr, src


def groups():
    rows = list(csv.DictReader(open(os.path.join(ROOT, "data/raw/odds/odds_2026-10-15.csv"), encoding="utf-8")))
    g = {}
    for i, r in enumerate(rows):
        k = (r["market"], r["selection"], r["line"]) if r["market"] == "WINS" else ((r["market"], r["selection"]) if r["market"] == "PLAYOFFS" else (r["market"],))
        g.setdefault(k, []).append((i, r))
    return rows, g


def kelly_solver(X, dec_, p_stake, frac=0.25, cap=0.10, iters=4000, ub=None, fixed=None):
    """Own implementation: exponential-tilt the sims to the target marginals (Newton on the dual), then maximise E_w[log(1+R f)] by projected gradient ascent with backtracking."""
    n, m = X.shape; Xf = X.astype(float); lam = np.zeros(m)
    for _ in range(100):
        a = Xf @ lam; w = np.exp(a - a.max()); w /= w.sum(); mu = Xf.T @ w; gvec = mu - p_stake
        if np.abs(gvec).max() < 1e-10: break
        cov = (Xf * w[:, None]).T @ Xf - np.outer(mu, mu) + 1e-12 * np.eye(m); lam -= np.linalg.solve(cov, gvec)
    a = Xf @ lam; w = np.exp(a - a.max()); w /= w.sum()
    R = np.where(X, dec_ - 1.0, -1.0); f = np.full(m, 0.001); hi = np.full(m, 0.6) if ub is None else np.minimum(0.6, ub / frac); lo = np.zeros(m)
    for j, v in (fixed or {}).items(): lo[j] = hi[j] = v / frac; f[j] = v / frac
    obj = lambda f: float((w * np.log(np.maximum(1 + R @ f, 1e-12))).sum())
    for _ in range(iters):
        g = (R * (w / (1 + R @ f))[:, None]).sum(0); step = 0.05; o0 = obj(f)
        while step > 1e-12:
            fn = np.clip(f + step * g, lo, hi)
            if obj(fn) > o0: break
            step /= 2
        if step <= 1e-12 or np.abs(fn - f).max() < 1e-11: f = fn; break
        f = fn
    full = f * frac; tot = full.sum(); return full * (min(1.0, cap / tot) if tot > 0 else 1.0), w, (Xf.T @ w)


def main():
    rows, grp = groups(); out = {}
    T = list(csv.DictReader(open(C("pricing_table.csv"), encoding="utf-8"))); P = list(csv.DictReader(open(C("player_pricing_table.csv"), encoding="utf-8")))
    t1 = [r for r in T if r["tier1"] == "True"]; p1 = [r for r in P if r["tier1"] == "True"]
    wbp = sorted(glob.glob(os.path.join(ROOT, "output", "NBA_Futures_Model_v1_*_MS.xlsx")))[-1]; wb = openpyxl.load_workbook(wbp, data_only=True)
    # --- de-vig of every Tier 1 market group + 10 random groups
    def group_for(r):
        m = r["market"]
        for k, v in grp.items():
            if k[0] != m: continue
            if m == "WINS" and (k[1] != r["selection"] or k[2] != r["line"]): continue
            if m == "PLAYOFFS" and k[1] != r["selection"]: continue
            return k, v
    checks = []
    def devig_group(k, v):
        pi = [1 / dec(float(r["american"])) for _, r in v]; S = 4.0 if k[0].startswith("PLAYIN") else 1.0
        return (shin(pi) if S == 1.0 else power(pi, S)), mult(pi, S), power(pi, S), v
    def compare(r, k, v, own):
        i = [ii for ii, rr in v if rr["selection"] == r["selection"] and rr["side"] == r["side"]]
        pos = [j for j, (ii, rr) in enumerate(v) if rr["selection"] == r["selection"] and rr["side"] == r["side"]][0]
        return own[pos]
    for r in t1:
        k, v = group_for(r); sh, mu, pw, vv = devig_group(k, v); own = compare(r, k, v, sh)
        checks.append(dict(bet=f'{r["market"]} {r["selection"]} {r["side"]}', n_group=len(v), own_fair=own, table_fair=float(r["fair"]), abs_diff=abs(own - float(r["fair"]))))
    for r in p1:
        v = grp[(r["market"],)]; sh, mu, pw, vv = devig_group((r["market"],), v); pos = [j for j, (ii, rr) in enumerate(v) if rr["selection"] == r["selection"]][0]
        checks.append(dict(bet=f'{r["market"]} {r["selection"]}', n_group=len(v), own_fair=sh[pos], table_fair=float(r["fair"]), abs_diff=abs(sh[pos] - float(r["fair"]))))
    random.seed(2026); keys = random.sample(sorted(grp, key=str), 10); rnd = []
    Tt = {(r["market"], r["selection"], r["side"], r["line"]): r for r in T}
    for k in keys:
        v = grp[k]; sh, mu, pw, vv = devig_group(k, v); md = 0.0
        for j, (ii, rr) in enumerate(v):
            t = Tt.get((rr["market"], rr["selection"], rr["side"], rr["line"] if rr["line"] != "" else ""))
            if t is None: t = next((x for x in T if x["row_id"] == str(ii)), None)
            if t is not None:
                md = max(md, abs(sh[j] - float(t["fair_shin"])), abs(mu[j] - float(t["fair_mult"])), abs(pw[j] - float(t["fair_power"])))
        rnd.append(dict(group=str(k), n=len(v), sum_shin=sum(sh), max_abs_diff_vs_table_3methods=md))
    # --- EV / Kelly for every Tier 1 row
    Xs = np.load(C("joint_X.npy")); labels = [r for r in t1] + [r for r in p1]
    # order in joint.py: team (pricing_table order, tier1) then player; reproduce
    dec_ = np.array([dec(float(r["american"])) for r in labels]); fair_own = np.array([c["own_fair"] for c in checks])
    pm = np.array([float(r["model_prob"]) for r in labels]); p_stake = 0.25 * pm + 0.75 * fair_own
    jt = json.load(open(C("joint_summary.json"))); eng = np.array(list(jt["stakes"].values())); eng0 = np.array(list(jt["uncapped_joint"].values()))
    pr_ = json.load(open(os.path.join(ROOT, "params/tier1_overrides.json")))
    f0, w, mu_t = kelly_solver(Xs, dec_, p_stake)                                           # (a) no caps / multipliers
    ub = np.full(len(labels), np.inf); fixed = {}
    for j, r in enumerate(labels):
        if r["market"] == "WINS": ub[j] = pr_["wins_stake_cap"] * (pr_["lowcont_mult"] if float(r["continuity"]) < pr_["lowcont_thr"] else 1.0)
        if r["market"] == "ROY": fixed[j] = pr_["roy_stake_mult"] * f0[j]
    f, w, mu_t = kelly_solver(Xs, dec_, p_stake, ub=ub, fixed=fixed)                       # (b) WINS capped, ROY fixed at the multiplied stake
    ev = pm * dec_ - 1; ev75 = p_stake * dec_ - 1
    # team bets: model probability from the sims directly
    Z = np.load(os.path.join(ROOT, "sims/season_sims.npz")); teams = list(Z["teams"])
    team_rows = []
    for j, r in enumerate(t1):
        team_rows.append(dict(bet=f'{r["market"]} {r["selection"]} {r["side"]}', sim_marginal=float(Xs[:, j].mean()), table_model=float(r["model_prob"]), abs_diff=abs(float(Xs[:, j].mean()) - float(r["model_prob"]))))
    # --- Excel cached values
    xl = {}
    ws = wb["Tier1_Card"]
    for rr in range(8, 30):
        if ws.cell(rr, 2).value and ws.cell(rr, 3).value:
            xl[(ws.cell(rr, 2).value, ws.cell(rr, 3).value)] = dict(fair=ws.cell(rr, 11).value, model=ws.cell(rr, 12).value, ev=ws.cell(rr, 13).value, stake=ws.cell(rr, 15).value, minp=ws.cell(rr, 8).value, cons=ws.cell(rr, 17).value)
    table = []
    for j, r in enumerate(labels):
        x = xl.get((r["market"], r["selection"])) or xl.get((r["market"], r["selection"].replace("Shai Gilgeous Alexander", "Shai Gilgeous-Alexander")))
        table.append(dict(bet=f'{r["market"]} {r["selection"]} {r.get("side", "")}'.strip(), american=float(r["american"]), own_fair=float(fair_own[j]), engine_fair=float(r["fair"]), model=float(pm[j]), own_ev=float(ev[j]), own_ev_shrunk75=float(ev75[j]),
                          own_single_kelly=float(0.25 * max(ev75[j], 0) / (dec_[j] - 1)), own_joint_stake=float(f[j]), engine_joint_stake=float(eng[j]), xl_fair=x and x["fair"], xl_model=x and x["model"], xl_ev=x and x["ev"], xl_stake=x and x["stake"], xl_min_price=x and x["minp"], xl_cons=x and x["cons"], own_min_price=own_min(p_stake[j])))
    # independent consensus + min price for every Tier 1 row; WINS rows re-derive the consensus from raw inputs
    from_abbr = {}
    for x in csv.DictReader(open(C("pricing_table.csv"), encoding="utf-8")): from_abbr[x["selection"]] = x["team"]
    cons_rows = []
    for j, r in enumerate(t1):
        if r["market"] != "WINS": continue
        k, v = group_for(r); sh, mu, pw, vv = devig_group(k, v); over_pos = [jj for jj, (ii, rr) in enumerate(v) if rr["side"] == "OVER"][0]
        med, bias, tp, M, pr, src = own_consensus(r, sh[over_pos]); t = r["team"]; sign = 1 if r["side"] == "OVER" else -1
        g_model = (tp[t] - med) - bias; stat = [x["id"] for x in src if x["type"] == "STAT_MODEL"]; g_stat = {i: (float(M[t][i]) - med) - bias for i in stat}
        ok = sign * g_model >= pr["cons_min"] and any(sign * g >= pr["cons_min"] for g in g_stat.values())
        xv = xl.get((r["market"], r["selection"]), {}).get("cons")
        cons_rows.append(dict(bet=f'{r["selection"]} {r["side"]}', market_median=med, bias=bias, gap_model=g_model, gap_stat=g_stat, own_pass=ok, excel=xv, match=(xv == ("PASS" if ok else "FAIL"))))
    res = dict(consensus_check=cons_rows, devig_tier1=checks, devig_random10=rnd, bets=table, team_model_from_sims=team_rows,
               max_fair_diff=max(c["abs_diff"] for c in checks), max_random_devig_diff=max(r["max_abs_diff_vs_table_3methods"] for r in rnd),
               max_stake_diff=float(np.abs(f - eng).max()), max_uncapped_stake_diff=float(np.abs(f0 - eng0).max()), total_stake_own=float(f.sum()), total_uncapped_own=float(f0.sum()), total_stake_engine=float(eng.sum()),
               max_xl_min_price_diff=max((abs(t["xl_min_price"] - t["own_min_price"]) for t in table if t["xl_min_price"] is not None), default=None), consensus_all_match=all(c["match"] for c in cons_rows),
               max_xl_fair_diff=max((abs(t["xl_fair"] - t["own_fair"]) for t in table if t["xl_fair"] is not None), default=None),
               max_xl_stake_diff=max((abs(t["xl_stake"] - t["engine_joint_stake"]) for t in table if t["xl_stake"] is not None), default=None),
               n_xl_matched=sum(t["xl_fair"] is not None for t in table))
    json.dump(res, open(C("g6_verification.json"), "w"), indent=1, default=float); return res


if __name__ == "__main__":
    r = main()
    for t in r["bets"]: print({k: (round(v, 5) if isinstance(v, float) else v) for k, v in t.items()})
    print({k: v for k, v in r.items() if k.startswith("max") or k.startswith("total") or k == "n_xl_matched"}); print([ (x["bet"][:30], round(x["abs_diff"], 4)) for x in r["team_model_from_sims"]])
