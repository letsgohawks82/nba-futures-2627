"""Production run: python -m src.sim.run_sim [N] -> sims/*.npz + data/clean/sim_team_summary.csv + sims/run_meta.json"""
import hashlib, json, os, sys, time, datetime
import numpy as np, pandas as pd
from .inputs import build, PAR_NAMES, lottery_tables
from .runner import simulate, FLAGS

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def assumptions_hash(inp):
    h = hashlib.sha256()
    h.update(inp["par"].tobytes()); h.update(inp["rating"].tobytes()); h.update(inp["pw"].tobytes()); h.update(inp["pa"].tobytes())
    h.update(inp["kprot"].tobytes()); h.update(inp["fover"].tobytes())
    for f in ("params/pick_ownership_rules.csv", "params/overrides_players.csv", "params/assumptions.json"):
        h.update(open(os.path.join(ROOT, f), "rb").read())
    return h.hexdigest()[:16]

def summarize(r, inp):
    n = r["wins"].shape[0]; T = r["teams"]; rows = []
    fl = r["flags"]
    for i, t in enumerate(T):
        w = r["wins"][:, i]; row = dict(team=t, n_sims=n, wins_mean=w.mean(), wins_sd=w.std(), wins_p10=np.percentile(w, 10), wins_p50=np.percentile(w, 50), wins_p90=np.percentile(w, 90))
        for k, bit in FLAGS.items():
            p = ((fl[:, i] & bit) > 0).mean(); row[f"p_{k}"] = p; row[f"se_{k}"] = np.sqrt(p * (1 - p) / n)
        pk = r["pick"][:, i]; lp = r["lotpos"][:, i]
        row.update(p_lottery=(lp > 0).mean(), p_pick1=(pk == 1).mean(), p_top4=(pk <= 4).mean(), p_top5=(pk <= 5).mean(), pick_mean=pk.mean(),
                   p_cup_qf=(r["cupstage"][:, i] >= 1).mean(), p_cup_final=(r["cupstage"][:, i] >= 3).mean())
        seeds = r["conf_rank"][:, i]
        for s_ in range(1, 16): row[f"p_confrank_{s_}"] = (seeds == s_).mean()
        for k_ in (35, 40, 45, 50, 55): row[f"p_wins_ge_{k_}"] = (w >= k_).mean()
        rows.append(row)
    return pd.DataFrame(rows)

def main(N=100_000, seed=2026):
    lt = lottery_tables(16, 300_000)
    inp = build({"_lottery_tables": lt}); t = time.time()
    r = simulate(inp, N, seed)
    os.makedirs(os.path.join(ROOT, "sims"), exist_ok=True)
    np.savez_compressed(os.path.join(ROOT, "sims", "season_sims.npz"), wins=r["wins"], conf_rank=r["conf_rank"], flags=r["flags"], pick=r["pick"], gp=r["gp"], cupstage=r["cupstage"], lotpos=r["lotpos"], srs=r["srs"], teams=np.array(r["teams"]))
    S = summarize(r, inp); S.to_csv(os.path.join(ROOT, "data/clean/sim_team_summary.csv"), index=False)
    pl = pd.DataFrame([(inp["teams"][i], k, inp["pnames"][i][k], inp["pids"][i][k], float(r["gp"][:, i, k].mean()), float((r["gp"][:, i, k] >= 65).mean())) for i in range(30) for k in range(inp["pw"].shape[1])],
                      columns=["team", "slot", "player", "bbref_id", "games_mean", "p_ge_65_games"])
    pl.to_csv(os.path.join(ROOT, "data/clean/sim_player_games.csv"), index=False)
    meta = dict(n_sims=N, seed=seed, run_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), assumptions_hash=assumptions_hash(inp),
                par={k: float(v) for k, v in zip(PAR_NAMES, inp["par"])}, runtime_s=round(time.time() - t, 1))
    json.dump(meta, open(os.path.join(ROOT, "sims", "run_meta.json"), "w"), indent=1)
    json.dump(meta, open(os.path.join(ROOT, "data/clean/sim_run_meta.json"), "w"), indent=1)
    return S, meta

if __name__ == "__main__":
    S, meta = main(int(sys.argv[1]) if len(sys.argv) > 1 else 100_000, int(sys.argv[2]) if len(sys.argv) > 2 else 2026)
    print(json.dumps(meta, indent=1)); print(S[["team", "wins_mean", "p_playoffs", "p_division", "p_conference", "p_title", "p_cup_group", "p_cup", "p_pick1", "p_top4"]].round(3).sort_values("p_title", ascending=False).to_string())
