"""G4 driver: simulate stat leaders, MVP, DPOY, ROY on the production season sims (team wins + per-player games from sims/season_sims.npz)
and write data/clean/player_market_probs.csv (point probability + season-block-bootstrap draws) and g4_summary.json."""
import json, os, sys, time
import numpy as np, pandas as pd
from ..data.namemap import norm
from . import pool as PL, leaders as L, awards as A, rookies as RK, simgp
from .rates import C, STATS

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MARKETS = ["LDR_PPG", "LDR_RPG", "LDR_APG", "LDR_SPG", "LDR_BPG", "LDR_TPG", "MVP", "DPOY", "ROY"]
ASSUME = dict(awards_65_game_rule=True, award_min_games=65, award_min_mpg=20.0, qual_games=58, rookie_mpg_sd=None, bpm_sd=None, dbpm_sd=None)


def prep_pool():
    P, ps = PL.build(); o = PL.odds_names()
    pool = P[P.slotted | P.key.isin(set(o.key))].reset_index(drop=True)
    a = pd.read_parquet(C("award_voting.parquet"))
    for c in ["season", "award_share"]: a[c] = pd.to_numeric(a[c], errors="coerce")
    for aw in ("mvp", "dpoy"):
        sh = a[(a.award == aw) & (a.season == 2026)].set_index("bbref_id").award_share; sh = sh[~sh.index.duplicated()]
        pool["prev_" + aw] = pool.bbref_id.map(sh).fillna(0.0)
    dr = pd.read_parquet(C("draft_picks.parquet")); dr["k"] = dr.player.map(norm); dr = dr[dr.draft_year.astype(int) == 2026]
    pool = pool.merge(dr[["k", "pick_overall"]].rename(columns={"k": "key"}).drop_duplicates("key"), on="key", how="left")
    pool["draft26"] = pool.pick_overall.notna(); pool["pick"] = pd.to_numeric(pool.pick_overall).fillna(61.0)
    return pool


def tdef_model(m):
    """Team defence rating (z, lower = better) of a candidate's team as a function of team win%, own DBPM, big flag - used so the DPOY features in sims have a team-defence term."""
    d = m[(m.mp >= 1000) & (m.games >= 40) & m.dbpm.notna()]
    X = np.column_stack([np.ones(len(d)), d.win, d.dbpm, d.big]); b, *_ = np.linalg.lstsq(X, d.tdef.values, rcond=None); res = d.tdef.values - X @ b
    return dict(coef=b.tolist(), sd=float(res.std()))


def run_sims(pool, gp, wins_p, cal, coefs, rookie_fit, tdef_fit, bpm_fit, dbpm_fit, rng, sd_scale=1.0, toggle65=True, mpg_sd=0.32, cap=None):
    """One batch of n sims given gp (n,m) and team win fraction (n,m). Returns dict market -> (m,) mean win credit."""
    n, m = gp.shape; out = {}
    st = L.draw_stats(pool, cal, n, rng, sd_scale)
    for sn in L.SN:
        out["LDR_" + sn] = L.leader_credit(st[sn], gp, total_alt=L.TOTAL_ALT[sn])
        if cap is not None: cap["LDR_" + sn] = L.leader_winner(st[sn], gp, rng, L.TOTAL_ALT[sn])
    # award eligibility: >= 65 games and >= 20 mpg in the SIMULATED season (minutes noise: rookies mpg_sd, veterans 0.12 = LOSO RMSE ~2.2 mpg on 30), so low-projected-minute players keep a real chance
    sd_m = np.where(pool.rookie.values, mpg_sd, 0.12)[None, :]
    mpg_sim = pool.proj_mpg.values[None, :] * np.exp(sd_m * rng.standard_normal((n, m)) - 0.5 * sd_m ** 2)
    elig = (gp >= ASSUME["award_min_games"]) & (mpg_sim >= ASSUME["award_min_mpg"]) if toggle65 else np.ones_like(gp, bool)
    gum = lambda: rng.gumbel(size=(n, m)).astype(np.float32)
    # MVP
    bpm = pool.rating.values[None, :] + bpm_fit["sd"] * rng.standard_normal((n, m)).astype(np.float32)
    F = dict(bpm=bpm, ppg=st["PPG"], win=wins_p, gp=gp.astype(np.float32), prev_mvp=np.repeat(pool.prev_mvp.values[None, :], n, 0))
    u = sum(coefs["MVP"][f] * A.zf(f, F[f]) for f in A.FEATS["MVP"]) + gum()
    u = np.where(elig & (pool.rookie.values[None, :] | True), u, -np.inf); out["MVP"] = _argmax_credit(u)
    if cap is not None: cap["MVP"] = np.where(np.isfinite(u.max(1)), u.argmax(1), -1)
    # DPOY
    dbpm = pool.dbpm_hat.values[None, :] + dbpm_fit["sd"] * rng.standard_normal((n, m)).astype(np.float32)
    tb = tdef_fit["coef"]; tdef = tb[0] + tb[1] * wins_p + tb[2] * dbpm + tb[3] * pool.cls.eq("B").values[None, :] + tdef_fit["sd"] * rng.standard_normal((n, m)).astype(np.float32)
    F = dict(dbpm=dbpm, stocks=st["SPG"] + st["BPG"], blkpg=st["BPG"], win=wins_p, tdef=tdef, big=np.repeat(pool.cls.eq("B").values[None, :].astype(np.float32), n, 0), gp=gp.astype(np.float32), prev_dpoy=np.repeat(pool.prev_dpoy.values[None, :], n, 0))
    u = sum(coefs["DPOY"][f] * A.zf(f, F[f]) for f in A.FEATS["DPOY"]) + gum()
    u = np.where(elig, u, -np.inf); out["DPOY"] = _argmax_credit(u)
    if cap is not None: cap["DPOY"] = np.where(np.isfinite(u.max(1)), u.argmax(1), -1)
    # ROY (2026 draft class only): per-36 box rates from draft slot and age, minutes = projected mpg x lognormal(minutes SD)
    rk = pool.draft26.values
    mpg = mpg_sim
    pts36 = np.exp(rookie_fit["pts36"]["coef"][0] + rookie_fit["pts36"]["coef"][1] * np.log(pool.pick.values) + rookie_fit["pts36"]["coef"][2] * (pool.age.values - 20.0))[None, :] * np.exp(rookie_fit["pts36"]["sd"] * rng.standard_normal((n, m)))
    ra36 = np.exp(rookie_fit["ra36"]["coef"][0] + rookie_fit["ra36"]["coef"][1] * np.log(pool.pick.values) + rookie_fit["ra36"]["coef"][2] * (pool.age.values - 20.0))[None, :] * np.exp(rookie_fit["ra36"]["sd"] * rng.standard_normal((n, m)))
    F = dict(ppg=pts36 * mpg / 36.0, rebast=ra36 * mpg / 36.0, gp=gp.astype(np.float32), lnpick=np.repeat(np.log(pool.pick.values)[None, :], n, 0))
    u = sum(coefs["ROY"][f] * A.zf(f, F[f]) for f in A.FEATS["ROY"]) + gum()
    u = np.where(elig & rk[None, :], u, -np.inf); out["ROY"] = _argmax_credit(u)
    if cap is not None: cap["ROY"] = np.where(np.isfinite(u.max(1)), u.argmax(1), -1); cap["ROY_ppg"] = F["ppg"]; cap["ROY_mpg"] = mpg
    return out


def _argmax_credit(u):
    j = u.argmax(1); ok = np.isfinite(u.max(1)); c = np.bincount(j[ok], minlength=u.shape[1]).astype(float)
    return c / u.shape[0]


def main(n_draws=40, n_point=100_000, n_draw=10_000, seed=77):
    t0 = time.time(); rng = np.random.default_rng(seed)
    pool = prep_pool(); Z = np.load(os.path.join(ROOT, "sims/season_sims.npz")); GP = Z["gp"]; WINS = Z["wins"]; tm = list(Z["teams"])
    gp_full, ti = simgp.sim_gp(pool, {"gp": GP, "teams": Z["teams"]}, rng=rng)
    wins_full = (WINS[:, ti] / 82.0).astype(np.float32)
    N = gp_full.shape[0]; print("pool", len(pool), "gp ready", round(time.time() - t0, 1), flush=True)
    R = pd.read_csv(C("g4_rate_backtest.csv")); m, w = A.hist_frame(); P = A.pools(m, w)
    bpm_fit = A.bpm_error("bpm"); dbpm_fit = A.bpm_error("dbpm"); tdef_fit = tdef_model(m); rookie_fit, _ = RK.fit()
    point_cal = L.calib_from_backtest(R); point_coef = {k: dict(zip(A.FEATS[k], A.fit_clogit(P[k], k, 0.5))) for k in A.FEATS}
    # point estimate, 100k sims in chunks
    acc = {k: np.zeros(len(pool)) for k in MARKETS}; done = 0
    while done < N:
        k = min(20_000, N - done)
        r = run_sims(pool, gp_full[done:done + k], wins_full[done:done + k], point_cal, point_coef, rookie_fit, tdef_fit, bpm_fit, dbpm_fit, rng)
        for kk in MARKETS: acc[kk] += r[kk] * k
        done += k
    point = {k: acc[k] / N for k in MARKETS}; print("point done", round(time.time() - t0, 1), flush=True)
    # bootstrap draws: calibration (rates) + award-fit coefficients re-estimated on season-block resamples; each on a fresh random subset of sims
    seas_r = sorted(R.season.unique()); seas_a = {k: sorted(P[k].season.unique()) for k in P}
    draws = {k: [] for k in MARKETS}
    for d in range(n_draws):
        cal = L.calib_from_backtest(R, list(rng.choice(seas_r, len(seas_r), replace=True)))
        coef = {k: dict(zip(A.FEATS[k], A.fit_clogit(P[k], k, 0.5, seasons=list(rng.choice(seas_a[k], len(seas_a[k]), replace=True))))) for k in P}
        ix = np.sort(rng.choice(N, min(n_draw, N), replace=False))
        r = run_sims(pool, gp_full[ix], wins_full[ix], cal, coef, rookie_fit, tdef_fit, bpm_fit, dbpm_fit, rng)
        for kk in MARKETS: draws[kk].append(r[kk])
        if d % 10 == 9: print("draw", d + 1, round(time.time() - t0, 1), flush=True)
    # scenarios: rate residual SD x0.8 / x1.25 and 65-game rule off
    scen = {}
    for name, kw in (("sd_lo", dict(sd_scale=0.8)), ("sd_hi", dict(sd_scale=1.25)), ("no65", dict(toggle65=False)), ("mpg_lo", dict(mpg_sd=0.22))):
        ix = np.sort(rng.choice(N, min(40_000, N), replace=False))
        scen[name] = run_sims(pool, gp_full[ix], wins_full[ix], point_cal, point_coef, rookie_fit, tdef_fit, bpm_fit, dbpm_fit, rng, **kw)
    rows = []
    for kk in MARKETS:
        D = np.array(draws[kk])
        for j in range(len(pool)):
            if point[kk][j] <= 0 and D[:, j].max() <= 0: continue
            rows.append(dict(market=kk, player=pool.name[j], key=pool.key[j], team=pool.abbr[j], p=point[kk][j], p_lo=float(np.percentile(D[:, j], 10)), p_hi=float(np.percentile(D[:, j], 90)), p_boot_mean=float(D[:, j].mean()),
                             p_sd_lo=scen["sd_lo"][kk][j], p_sd_hi=scen["sd_hi"][kk][j], p_no65=scen["no65"][kk][j], p_mpg_lo=scen["mpg_lo"][kk][j],
                             proj_mpg=pool.proj_mpg[j], proj_gp=pool.proj_gp[j], rating=pool.rating[j], pg_PPG=pool.pg_PPG[j], pg_RPG=pool.pg_RPG[j], pg_APG=pool.pg_APG[j], pg_SPG=pool.pg_SPG[j], pg_BPG=pool.pg_BPG[j], pg_TPG=pool.pg_TPG[j]))
    out = pd.DataFrame(rows); out.to_csv(C("player_market_probs.csv"), index=False)
    pool.to_csv(C("g4_pool.csv"), index=False)
    json.dump(dict(n_point=N, n_draws=n_draws, n_draw_sims=n_draw, coef=point_coef, rate_calibration=point_cal, bpm_error=bpm_fit, dbpm_error=dbpm_fit, tdef_model=tdef_fit, rookie_fit=rookie_fit, assume=ASSUME, seconds=round(time.time() - t0, 1)), open(C("g4_summary.json"), "w"), indent=1, default=float)
    return out


if __name__ == "__main__":
    out = main(); pd.set_option("display.width", 220)
    for k in MARKETS: print(k, out[out.market == k].nlargest(6, "p")[["player", "p", "p_lo", "p_hi"]].round(3).values.tolist())
