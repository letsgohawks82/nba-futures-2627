"""python run.py repro [--n 20000] [--seed 2026] [--with-backtest]
Excel-free reproduction: ratings -> simulation -> pricing (team + player + joint Kelly), then reports/repro_check.md comparing the rebuilt outputs with the committed ones
(snapshotted into repro/baseline/ before anything is overwritten). Exit code 1 if any stage fails or any difference exceeds Monte Carlo error. Never touches the network."""
import argparse, datetime, json, math, os, shutil, subprocess, sys, time
import numpy as np, pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PY = sys.executable
C = lambda f: os.path.join(ROOT, "data", "clean", f)
REPRO = os.path.join(ROOT, "repro"); BASE = os.path.join(REPRO, "baseline")
SNAP = ["data/clean/sim_team_summary.csv", "data/clean/pricing_table.csv", "data/clean/player_pricing_table.csv", "data/clean/team_projection_2027.csv", "data/clean/player_projection_2027.csv",
        "data/clean/joint_summary.json", "data/clean/sim_run_meta.json", "release/final_card.csv"]
Z = 4.0           # tolerance in Monte Carlo standard errors


def run(cmd, log, env=None):
    t = time.time(); os.makedirs(os.path.dirname(log), exist_ok=True)
    with open(log, "w") as f: rc = subprocess.call(cmd, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT, env=env)
    return dict(cmd=" ".join(os.path.basename(c) if os.path.sep in c else c for c in cmd[1:]), exit=rc, seconds=round(time.time() - t, 1), log=os.path.relpath(log, ROOT).replace(os.sep, "/"))


def snapshot():
    os.makedirs(BASE, exist_ok=True)
    for f in SNAP:
        src = os.path.join(ROOT, f); dst = os.path.join(BASE, f.replace("/", "__"))
        if os.path.exists(src) and not os.path.exists(dst): shutil.copy2(src, dst)


def numba_compile_seconds():
    """Time a tiny simulation first: dominated by the numba JIT compile of the engine (cache cleared by the caller if a cold number is wanted)."""
    code = ("import time,sys; sys.path.insert(0,r'%s'); t=time.time()\n"
            "from src.sim.inputs import build, lottery_tables\nfrom src.sim.runner import simulate\n"
            "lt=lottery_tables(16,2000); inp=build({'_lottery_tables':lt,'_calibrate':False}); t1=time.time(); simulate(inp,64,1,verbose=False); print(round(time.time()-t1,1))") % ROOT
    import tempfile
    env = dict(os.environ, NUMBA_CACHE_DIR=tempfile.mkdtemp(prefix="numba_cold_"))       # fresh cache dir: the number below is a COLD compile
    out = subprocess.run([PY, "-W", "ignore", "-c", code], capture_output=True, text=True, cwd=ROOT, env=env)
    try: return float(out.stdout.strip().splitlines()[-1])
    except Exception: return float("nan")


def compare(n, seed):
    from . import checks as K
    B = lambda f: os.path.join(BASE, f.replace("/", "__"))
    n0 = int(pd.read_csv(B("data/clean/sim_team_summary.csv")).n_sims.iloc[0]); m0 = json.load(open(B("data/clean/sim_run_meta.json"))); same = (n == n0 and seed == m0["seed"])
    out = dict(n=n, n0=n0, seed=seed, seed0=m0["seed"], strict=same); rows = []; bad = []
    tp0 = pd.read_csv(B("data/clean/team_projection_2027.csv")).set_index("abbr"); tp1 = pd.read_csv(C("team_projection_2027.csv")).set_index("abbr")
    rat = float(np.abs(tp0.pred_wins - tp1.pred_wins.reindex(tp0.index)).max()); out["ratings_max_abs_diff_wins"] = rat
    if rat > 1e-6: bad.append(f"ratings differ from the committed projection (max |diff| {rat:.2e} wins)")
    S0 = pd.read_csv(B("data/clean/sim_team_summary.csv")).set_index("team"); S1 = pd.read_csv(C("sim_team_summary.csv")).set_index("team")
    cols = ["team", "market", "selection", "side", "line", "dec", "fair", "model_prob"]
    def both(team_path, player_path):
        t = pd.read_csv(team_path)[cols]; q = pd.read_csv(player_path); q["side"] = "YES"; q["line"] = np.nan
        return pd.concat([t, q[cols]], ignore_index=True)
    P0 = both(B("data/clean/pricing_table.csv"), B("data/clean/player_pricing_table.csv")); P1 = both(C("pricing_table.csv"), C("player_pricing_table.csv"))
    w0 = P0[(P0.market == "WINS") & (P0.side == "OVER")].set_index("team"); w1 = P1[(P1.market == "WINS") & (P1.side == "OVER")].set_index("team"); zmax = 0.0
    for t in S0.index:
        se_w = S0.wins_sd[t] * math.sqrt(1 / n + 1 / n0); dw = S1.wins_mean[t] - S0.wins_mean[t]
        p0, p1 = w0.model_prob[t], w1.model_prob[t]; se_p = math.sqrt(max(p0 * (1 - p0), 1e-6) * (1 / n + 1 / n0))
        q0, q1 = S0.p_bracket[t], S1.p_bracket[t]; se_q = math.sqrt(max(q0 * (1 - q0), 1e-6) * (1 / n + 1 / n0))
        z = [abs(dw) / se_w, abs(p1 - p0) / se_p, abs(q1 - q0) / se_q]; zmax = max(zmax, *z)
        rows.append(dict(team=t, wins0=S0.wins_mean[t], wins1=S1.wins_mean[t], dz_wins=z[0], pover0=p0, pover1=p1, dz_pover=z[1], ptop8_0=q0, ptop8_1=q1, dz_top8=z[2]))
        lim = 1e-6 if same else Z
        if (same and (abs(dw) > 1e-6 or abs(p1 - p0) > 1e-6 or abs(q1 - q0) > 1e-6)) or (not same and max(z) > lim): bad.append(f"{t}: z(wins,P(over),P(top8)) = {[round(x, 2) for x in z]}")
    out["team_rows"] = rows; out["z_max_team"] = zmax
    rb = os.path.join(REPRO, "rebuilt_card.csv"); card0 = pd.read_csv(B("release/final_card.csv")); card1 = pd.read_csv(rb) if os.path.exists(rb) else K.card_from_tables(); crow = []     # the card file written by the write_card stage
    key = lambda d: set(zip(d.market, d.selection, d.side))
    miss = key(card0) ^ key(card1)
    for r in card0.itertuples():
        m = card1[(card1.market == r.market) & (card1.selection == r.selection) & (card1.side == r.side)]
        o = P1[(P1.market == r.market) & (P1.selection == r.selection) & (P1.side == r.side)]
        o = o.iloc[0] if len(o) else None
        if o is None: bad.append(f"card bet missing from rebuilt pricing table: {r.market} {r.selection}"); continue
        dec = float(o.dec); se_p = math.sqrt(max(r.model_prob * (1 - r.model_prob), 1e-6) * (1 / n + 1 / n0)); ev1 = float(o.model_prob) * dec - 1
        z_ev = abs(ev1 - r.ev) / (dec * se_p); sh1 = (0.25 * float(o.model_prob) + 0.75 * float(o.fair)) * dec - 1; marginal = abs(r.ev_shrunk75 - 0.03) <= Z * 0.25 * dec * se_p
        stake1 = float(m.stake_frac.iloc[0]) if len(m) else 0.0; in1 = len(m) > 0
        crow.append(dict(bet=f"{r.market} {r.selection} {r.side}", ev0=r.ev, ev1=ev1, z_ev=z_ev, ev75_0=r.ev_shrunk75, ev75_1=sh1, stake0=r.stake_frac, stake1=stake1, in_rebuilt_card=in1, marginal=marginal))
        if same:
            if not in1 or abs(stake1 - r.stake_frac) > 1e-6 or abs(ev1 - r.ev) > 1e-6: bad.append(f"card bet differs at identical N/seed: {r.market} {r.selection}")
        else:
            if z_ev > Z: bad.append(f"card EV differs by {z_ev:.1f} MC SE: {r.market} {r.selection}")
            if not in1 and not marginal: bad.append(f"card bet absent from the rebuilt card (not marginal): {r.market} {r.selection}")
            if in1 and abs(stake1 - r.stake_frac) > 0.0010: bad.append(f"stake differs by {abs(stake1 - r.stake_frac):.4f}: {r.market} {r.selection}")
    extra = key(card1) - key(card0)
    for e in extra:
        r1 = card1[(card1.market == e[0]) & (card1.selection == e[1]) & (card1.side == e[2])].iloc[0]
        if same or abs(r1.ev_shrunk75 - 0.03) > Z * 0.25 * (1 + r1.american / 100 if r1.american > 0 else 1 + 100 / abs(r1.american)) * math.sqrt(0.2 * (1 / n + 1 / n0)): bad.append(f"rebuilt card has an extra bet: {e}")
    out["card_rows"] = crow; out["card_extra"] = sorted(extra); out["problems"] = bad
    return out


def report(res, status, compile_s):
    L = ["# repro_check", "", f"Generated {datetime.datetime.now():%Y-%m-%d %H:%M}. Rebuilt with N = {res['n']:,}, seed {res['seed']} (committed outputs: N = {res['n0']:,}, seed {res['seed0']}); "
         f"{'IDENTICAL N and seed: strict comparison (1e-6)' if res['strict'] else f'tolerance = {Z:.0f} Monte Carlo standard errors of the difference (sqrt(1/N + 1/N0))'}.", "",
         f"**Result: {'PASS' if not res['problems'] else 'FAIL'}.** Numba COLD compile time (first 64-sim run, empty cache): **{compile_s:.1f} s**. Ratings reproduced to max |diff| {res['ratings_max_abs_diff_wins']:.2e} wins (deterministic).", "",
         "## Stages", "| Stage | Exit | Seconds | Log |", "|---|---|---|---|"]
    L += [f"| {s['cmd']} | {s['exit']} | {s['seconds']} | `{s['log']}` |" for s in status]
    L += ["", f"## Teams (max z over all 30 teams and 3 statistics: {res['z_max_team']:.2f})", "| Team | Mean wins (committed) | Mean wins (rebuilt) | z | P(over line) committed | rebuilt | z | P(top-8) committed | rebuilt | z |", "|---|---|---|---|---|---|---|---|---|---|"]
    L += [f"| {r['team']} | {r['wins0']:.2f} | {r['wins1']:.2f} | {r['dz_wins']:.2f} | {r['pover0']:.3f} | {r['pover1']:.3f} | {r['dz_pover']:.2f} | {r['ptop8_0']:.3f} | {r['ptop8_1']:.3f} | {r['dz_top8']:.2f} |" for r in res["team_rows"]]
    L += ["", "## Card bets", "| Bet | EV committed | EV rebuilt | z | EV at 0.75 shrink committed | rebuilt | Stake committed | rebuilt | On rebuilt card | Marginal |", "|---|---|---|---|---|---|---|---|---|---|"]
    L += [f"| {r['bet']} | {r['ev0']:+.3f} | {r['ev1']:+.3f} | {r['z_ev']:.2f} | {r['ev75_0']:+.3f} | {r['ev75_1']:+.3f} | {r['stake0']:.4f} | {r['stake1']:.4f} | {r['in_rebuilt_card']} | {r['marginal']} |" for r in res["card_rows"]]
    if res["card_extra"]: L += ["", f"Extra bets on the rebuilt card: {res['card_extra']}"]
    L += ["", "## Problems"] + ([f"- {p}" for p in res["problems"]] or ["- none"])
    path = os.path.join(ROOT, "reports", "repro_check.md"); open(path, "w", encoding="utf-8").write("\n".join(L) + "\n"); return path


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=20000); ap.add_argument("--seed", type=int, default=2026); ap.add_argument("--with-backtest", action="store_true"); ap.add_argument("--skip-sim", action="store_true")
    a = ap.parse_args(argv); snapshot(); os.makedirs(REPRO, exist_ok=True); status = []; L = lambda n: os.path.join(REPRO, "logs", n + ".log")
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    steps = [([PY, "-W", "ignore", os.path.join(ROOT, "scripts", "verify_inputs.py")], "verify_inputs")]
    if a.with_backtest: steps.append(([PY, "-W", "ignore", "-m", "src.ratings.backtest"], "ratings_backtest"))
    steps.append(([PY, "-W", "ignore", "-m", "src.ratings.project_2027"], "ratings_project"))
    compile_s = numba_compile_seconds(); print(f"[repro] numba COLD compile time (first 64-sim run, empty cache): {compile_s:.1f} s", flush=True)
    steps += [([PY, "-W", "ignore", "-m", "src.sim.run_sim", str(a.n), str(a.seed)], "sim"), ([PY, "-W", "ignore", "-m", "src.pricing.run_pricing"], "price_teams"), ([PY, "-W", "ignore", "-m", "src.pricing.tier1"], "price_tier1"),
              ([PY, "-W", "ignore", "-m", "src.players.run_g4"], "players_sim"), ([PY, "-W", "ignore", "-m", "src.pricing.price_players"], "price_players"), ([PY, "-W", "ignore", "-m", "src.pricing.joint"], "joint_kelly"),
              ([PY, "-W", "ignore", os.path.join(ROOT, "scripts", "write_final_card.py"), os.path.join(REPRO, "rebuilt_card.csv")], "write_card")]
    for cmd, name in steps:
        if a.skip_sim and name in ("sim", "players_sim"): continue
        s = run(cmd, L(name), env); s["name"] = name; status.append(s); print(f"[repro] {name}: exit {s['exit']} ({s['seconds']} s)", flush=True)
        if s["exit"]: break
    json.dump(dict(n=a.n, seed=a.seed, numba_compile_s=compile_s, stages=status, finished=datetime.datetime.now().isoformat(timespec="seconds")), open(os.path.join(REPRO, "run_status.json"), "w"), indent=1)
    if any(s["exit"] for s in status): print("[repro] FAILED: a stage exited non-zero"); return 1
    res = compare(a.n, a.seed); path = report(res, status, compile_s); print("[repro] wrote", path)
    for p in res["problems"]: print("[repro] PROBLEM:", p)
    return 0 if not res["problems"] else 1


if __name__ == "__main__":
    sys.exit(main())
