"""Calibrate kappa (post-deadline effort suppression) by dose-response diff-in-diff on 2018-19..2025-26 using the OLD (2019-2026) lottery system.
   Delta_ts = post-deadline minus pre-deadline opponent-adjusted margin; regress on season FE + pre-deadline level + normalized old-system incentive.
   kappa = -beta (net-rating points per unit normalized incentive)."""
import json, os, datetime, math
import numpy as np, pandas as pd
from numba import njit
from ..ratings.prep import team_seasons
from .fit_game_model import games_frame, add_rest
from .inputs import fit_pick_value, ROOT

DEADLINE = {2019: "2019-02-07", 2020: "2020-02-06", 2021: "2021-03-25", 2022: "2022-02-10", 2023: "2023-02-09", 2024: "2024-02-08", 2025: "2025-02-06", 2026: "2026-02-05"}
OLD_COMBOS = np.array([140, 140, 140, 125, 105, 90, 75, 60, 45, 30, 20, 15, 10, 5], float)


@njit(cache=True)
def _old_draw(combos, n, seed):
    np.random.seed(seed)
    P = np.zeros((14, 14))
    for s in range(n):
        taken = np.zeros(14, np.bool_)
        pick = np.zeros(14, np.int64)
        for k in range(4):
            tot = 0.0
            for t in range(14):
                if not taken[t]:
                    tot += combos[t]
            r = np.random.random() * tot
            acc = 0.0
            ch = -1
            for t in range(14):
                if not taken[t]:
                    acc += combos[t]
                    if r < acc:
                        ch = t
                        break
            taken[ch] = True
            pick[ch] = k
        nxt = 4
        for t in range(14):
            if not taken[t]:
                pick[t] = nxt
                nxt += 1
        for t in range(14):
            P[t, pick[t]] += 1
    return P / n


def old_matrix(n=400_000):
    return _old_draw(OLD_COMBOS, n, 5)


def state_value_old(Wv, conf, i, Pold, pickval, play_in):
    """Expected pick value of team i's own pick under the old system if final wins were Wv."""
    cr = 1 + sum(1 for j in range(30) if j != i and conf[j] == conf[i] and (Wv[j] + 1e-4 * j) > (Wv[i] + 1e-4 * i))
    crs = [1 + sum(1 for k in range(30) if k != j and conf[k] == conf[j] and (Wv[k] + 1e-4 * k) > (Wv[j] + 1e-4 * j)) for j in range(30)]
    cut = 8
    if cr > cut:
        pos = 1 + sum(1 for j in range(30) if j != i and crs[j] > cut and (Wv[j] + 1e-4 * j) < (Wv[i] + 1e-4 * i))
        V = float((Pold[pos - 1] * pickval[1:15]).sum())
    else:
        p = 1 + sum(1 for j in range(30) if j != i and crs[j] <= cut and (Wv[j] + 1e-4 * j) < (Wv[i] + 1e-4 * i))
        V = float(pickval[min(30, 14 + math.ceil(p * 16 / 16))])
    race = 1.0 if cr <= (10 if play_in else 8) else 0.0
    return V, race


def incentive_table(save=True):
    ts = team_seasons().set_index(["season", "abbr"]); g = add_rest(games_frame())
    val, _ = fit_pick_value(save=False); Pold = old_matrix()
    nodes = np.array([-math.sqrt(3), 0.0, math.sqrt(3)]); wts = np.array([1 / 6, 2 / 3, 1 / 6])
    srs = ts.srs.to_dict()
    HCA = 1.9; rows = []
    for s, dl in DEADLINE.items():
        d = g[(g.season == s) & (~g.post)].copy()
        dl = pd.Timestamp(dl)
        teams = sorted(set(d.home) | set(d.away)); ti = {t: i for i, t in enumerate(teams)}
        conf = np.array([ts.loc[(s, t)].conf == "W" for t in teams], int)
        n_g = d.groupby("home").size().add(d.groupby("away").size(), fill_value=0)
        total_games = {t: int(n_g[t]) for t in teams}
        pre = d[d.date <= dl]; post = d[d.date > dl]
        def stats(x):
            m = {t: [] for t in teams}
            for r in x.itertuples():
                m[r.home].append(r.margin - HCA - srs[(s, r.away)]); m[r.away].append(-r.margin + HCA - srs[(s, r.home)])
            return m
        mp, mq = stats(pre), stats(post)
        wins_pre = {t: 0 for t in teams}; g_pre = {t: 0 for t in teams}
        for r in pre.itertuples():
            wins_pre[r.home] += r.margin > 0; wins_pre[r.away] += r.margin < 0; g_pre[r.home] += 1; g_pre[r.away] += 1
        full = 82 if s not in (2020, 2021) else (72 if s == 2021 else 67)
        E = np.zeros(len(teams)); sd = np.zeros(len(teams))
        for t in teams:
            i = ti[t]; rem = max(total_games[t] - g_pre[t], 0)
            phat = (wins_pre[t] + 10) / (g_pre[t] + 20); E[i] = wins_pre[t] + rem * phat; sd[i] = math.sqrt(0.25 * rem + 4)
        # pad to 30 for the helper (all seasons have 30 teams)
        for t in teams:
            i = ti[t]; inc = 0.0; race = 0.0; Wv = E.copy()
            for n_, w_ in zip(nodes, wts):
                x = E[i] + sd[i] * n_; Wv[i] = x; V0, r0 = state_value_old(Wv, conf, i, Pold, val, s >= 2021)
                Wv[i] = x - 1; V1, _ = state_value_old(Wv, conf, i, Pold, val, s >= 2021)
                inc += w_ * (V1 - V0); race += w_ * r0
            rows.append(dict(season=s, team=t, g_pre=g_pre[t], g_post=len(mq[t]), pre_adj=np.mean(mp[t]) if mp[t] else np.nan, post_adj=np.mean(mq[t]) if mq[t] else np.nan,
                             dV=inc, race=race, inc_raw=inc * (1 - race)))
    T = pd.DataFrame(rows); T["delta"] = T.post_adj - T.pre_adj
    ref = float(np.percentile(T.inc_raw[T.inc_raw > 0], 90)); T["inc_norm"] = T.inc_raw / ref
    if save:
        T.to_csv(os.path.join(ROOT, "data/clean/tank_did_table.csv"), index=False)
    return T, ref


def fit_kappa(T, ref, B=4000, seed=3):
    rng = np.random.default_rng(seed)
    T = T.dropna(subset=["delta"]).copy()
    seasons = sorted(T.season.unique())
    def est(D):
        X = np.column_stack([D.inc_norm.values, D.pre_adj.values] + [(D.season == s).astype(float).values for s in seasons])
        w = D.g_post.values.astype(float)
        beta = np.linalg.lstsq(X * np.sqrt(w)[:, None], D.delta.values * np.sqrt(w), rcond=None)[0]
        return beta[0], beta[1]
    b, gam = est(T)
    bs = []
    teams = T.team.unique()
    for _ in range(B):
        pick = rng.choice(teams, len(teams))      # cluster bootstrap by franchise
        D = pd.concat([T[T.team == t] for t in pick])
        try: bs.append(est(D)[0])
        except Exception: pass
    bs = np.array(bs)
    # simple DiD: incentive>0.1 vs incentive==0 on season-demeaned deltas
    T["dd"] = T.delta - T.groupby("season").delta.transform("mean")
    treat = T[T.inc_norm > 0.1]; ctrl = T[T.inc_norm <= 0.1]
    did = float(treat.dd.mean() - ctrl.dd.mean())
    return dict(beta_per_unit=float(b), kappa=float(-b), kappa_ci80=[float(-np.percentile(bs, 90)), float(-np.percentile(bs, 10))], pre_level_coef=float(gam),
                se_boot=float(bs.std()), n=int(len(T)), n_treated=int(len(treat)), did_treated_minus_control=did, ref_dV=float(ref))


if __name__ == "__main__":
    T, ref = incentive_table(); r = fit_kappa(T, ref); print(json.dumps(r, indent=1))
    print(T.groupby('season').agg(inc=('inc_norm','mean'), n_pos=('inc_norm', lambda x:(x>0.1).sum()), d=('delta','mean')).round(3))
    json.dump(r, open(os.path.join(ROOT, "data/clean/tank_kappa_fit.json"), "w"), indent=1)
