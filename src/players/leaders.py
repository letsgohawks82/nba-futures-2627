"""G4 stat-leader markets (PPG/RPG/APG/SPG/BPG/TPG): per-sim season averages = calibrated per-game projection x lognormal residual, qualification = >=58 games
(NBA.com rule; TPG uses the same rule by user default), values rounded to 0.1 and ties dead-heated (1/k credit).
Parameter uncertainty: calibration (slope, intercept, residual SD) re-estimated on season-block bootstrap resamples of the 2019-2026 backtest."""
import json, os
import numpy as np, pandas as pd
from .rates import STATS, C

QUAL_GAMES = 58
TOTAL_ALT = {"PPG": 1400, "RPG": 800, "APG": 400, "SPG": 125, "BPG": 100, "TPG": np.inf}      # NBA.com minimums: 58 GP OR season total at least this (no official TPG qualifier -> 58 GP default)
SN = list(STATS)


TOP_K = 15          # contender group the calibration/SD is estimated on (top-15 predicted per stat-season; the pooled top-30 over-states the SD for leaders, see g4_variance_check.json)


def calib_from_backtest(R, seasons=None, top_k=None):
    """Per stat: (slope, intercept, rel_sd of act/cal_pred, pred_lo) fit on the top-30 predicted players of the given seasons."""
    out = {}
    for sn in SN:
        g = R[R.stat == sn]
        g = g[g.groupby("season").pred.rank(ascending=False) <= (top_k or TOP_K)]
        if seasons is not None: g = pd.concat([g[g.season == s] for s in seasons])
        b = np.polyfit(g.pred, g.act, 1); cal = np.polyval(b, g.pred)
        lr = np.log(g.act.clip(lower=0.05) / cal)
        out[sn] = dict(slope=float(b[0]), intercept=float(b[1]), sd=float(lr.std()), pred_lo=float(g.pred.min()), bias=float(lr.mean()))
    return out


def bootstrap_calibs(R, n, rng):
    seas = sorted(R.season.unique()); draws = [calib_from_backtest(R)]
    for _ in range(n):
        draws.append(calib_from_backtest(R, list(rng.choice(seas, len(seas), replace=True))))
    return draws


def calibrated_pred(pred, cal):
    """Apply the top-candidate calibration only inside the range it was fit on; below it, a continuity blend to the raw prediction."""
    lo = cal["pred_lo"]; full = cal["intercept"] + cal["slope"] * pred
    w = np.clip((pred - 0.5 * lo) / (0.5 * lo), 0, 1)
    return w * full + (1 - w) * pred


def draw_stats(pool, cal, n, rng, sd_scale=1.0):
    """Season per-game averages for every pool player: arrays (n, m) per stat. lognormal with mean = calibrated pred."""
    out = {}; m = len(pool)
    for sn in SN:
        mu = calibrated_pred(pool["pg_" + sn].values, cal[sn]); sd = cal[sn]["sd"] * sd_scale
        out[sn] = (mu * np.exp(sd * rng.standard_normal((n, m)).astype(np.float32) - 0.5 * sd * sd)).astype(np.float32)
    return out


def leader_credit(vals, gp, qual=QUAL_GAMES, total_alt=np.inf):
    """vals, gp: (n, m). Returns (m,) mean win credit with 0.1 rounding and dead-heat 1/k. Qualifies with >= qual games or season total >= total_alt."""
    ok = (gp >= qual) | (vals * gp >= total_alt)
    v = np.where(ok, np.round(vals, 1), -1.0)
    mx = v.max(1, keepdims=True); win = (v == mx) & (mx > 0)
    k = win.sum(1, keepdims=True).clip(min=1)
    return (win / k).mean(0)


def run(pool, gp, cal, n_chunk=20_000, seed=3, sd_scale=1.0):
    """gp: (N, m) simulated games for every pool player. Returns DataFrame (m x 6) of leader probabilities."""
    rng = np.random.default_rng(seed); N = gp.shape[0]; acc = {sn: np.zeros(gp.shape[1]) for sn in SN}; done = 0
    while done < N:
        k = min(n_chunk, N - done); st = draw_stats(pool, cal, k, rng, sd_scale)
        for sn in SN: acc[sn] += leader_credit(st[sn], gp[done:done + k], total_alt=TOTAL_ALT[sn]) * k
        done += k
    return pd.DataFrame({sn: acc[sn] / N for sn in SN}, index=pool.index)


def leader_winner(vals, gp, rng, total_alt=np.inf):
    """Per-sim winning player index (-1 if nobody qualifies); ties at the 0.1-rounded value broken at random (expected value equals the dead-heat 1/k credit)."""
    ok = (gp >= QUAL_GAMES) | (vals * gp >= total_alt)
    v = np.where(ok, np.round(vals, 1), -1.0) + rng.random(vals.shape) * 1e-3
    j = v.argmax(1); return np.where(v.max(1) > 0, j, -1)
