"""Season Monte Carlo (numba). One simulated season = true-strength draw -> games (with player availability, B2B, HCA) ->
Cup (groups, knockout, 30 Cup-dependent games) -> trade-deadline tank module -> standings (full NBA tiebreakers) -> play-in -> playoffs -> lottery.
Teams are indexed 0..29 in alphabetical abbreviation order. Conference 0 = East, 1 = West.

par[] layout (float64):
 0 HCA  1 b2b_home  2 b2b_away  3 sigma_game  4 HCA_po  5 sigma_po  6 mean_total  7 sd_total  8 sigma_team  9 repl_rating  10 b_team
 11 avail_concentration  12 po_lambda  13 po_inj_prob  14 tank_kappa  15 tank_deterrent  16 tank_on  17 cup_cross_games  18 cup_semis_neutral
 19 n_draws  20 floor_pick  21 ot_margin  22 tank_boost  23 tank_REF  24 avail_on  25 deadline_noise (1=include)  26 po_srs_weight(unused) 27 effort_floor
"""
import math
import numpy as np
from numba import njit, prange
from .lottery import _one as lottery_draw, BALLS

NT = 30


@njit(cache=True)
def phi(x):
    return 0.5 * (1.0 + math.erf(x / 1.4142135623730951))


# ----------------------------------------------------------------------------- tiebreaks
@njit(cache=True)
def pct_vs(i, mask, W, G):
    w = 0.0
    g = 0.0
    for j in range(NT):
        if mask[j] and j != i:
            w += W[i, j]
            g += G[i, j]
    if g == 0:
        return 0.5
    return w / g


@njit(cache=True)
def tb_metric(i, level, tied, W, G, div, conf, elig, pdiff, divwin):
    """Metric value for team i at criterion `level`. 1=H2H among tied, 2=division winner, 3=division %, 4=conf %, 5=vs eligible own conf, 6=vs eligible other, 7=point diff."""
    if level == 1:
        return pct_vs(i, tied, W, G)
    if level == 2:
        return 1.0 if divwin[i] else 0.0
    if level == 3:
        m = np.zeros(NT, np.bool_)
        for j in range(NT):
            m[j] = div[j] == div[i]
        return pct_vs(i, m, W, G)
    if level == 4:
        m = np.zeros(NT, np.bool_)
        for j in range(NT):
            m[j] = conf[j] == conf[i]
        return pct_vs(i, m, W, G)
    if level == 5:
        m = np.zeros(NT, np.bool_)
        for j in range(NT):
            m[j] = conf[j] == conf[i] and elig[j]
        return pct_vs(i, m, W, G)
    if level == 6:
        m = np.zeros(NT, np.bool_)
        for j in range(NT):
            m[j] = conf[j] != conf[i] and elig[j]
        return pct_vs(i, m, W, G)
    return pdiff[i]


@njit(cache=True)
def sort_tied(S, n, W, G, div, conf, elig, pdiff, divwin, use_div, rnd, out):
    """Order the n teams in S (official NBA tiebreakers incl. multi-team ties). Writes best-first into out[:n]."""
    rem = S[:n].copy()
    nr = n
    pos = 0
    while nr > 0:
        if nr == 1:
            out[pos] = rem[0]
            pos += 1
            nr = 0
            break
        cand = rem[:nr].copy()
        nc = nr
        tied = np.zeros(NT, np.bool_)
        for k in range(nc):
            tied[cand[k]] = True
        if nr == 2:
            order = (1, 2, 3, 4, 5, 6, 7)       # two-team: H2H first, then division winner
        else:
            order = (2, 1, 3, 4, 5, 6, 7)       # multi-team: division winner first, then H2H among all tied
        for lv in order:
            if nc == 1:
                break
            if lv == 2 and not use_div:
                continue
            if lv == 3:
                same = True
                for k in range(nc):
                    if div[cand[k]] != div[cand[0]]:
                        same = False
                if not same:
                    continue
            best = -1e18
            for k in range(nc):
                v = tb_metric(cand[k], lv, tied, W, G, div, conf, elig, pdiff, divwin)
                if v > best:
                    best = v
            keep = np.zeros(nc, np.bool_)
            nk = 0
            for k in range(nc):
                v = tb_metric(cand[k], lv, tied, W, G, div, conf, elig, pdiff, divwin)
                if v > best - 1e-9:
                    keep[k] = True
                    nk += 1
            if nk < nc:
                nc2 = 0
                tmp = np.zeros(nk, np.int64)
                for k in range(nc):
                    if keep[k]:
                        tmp[nc2] = cand[k]
                        nc2 += 1
                cand = tmp
                nc = nk
                if lv == 1:
                    # after H2H narrowing keep `tied` for later levels' H2H-less criteria untouched
                    pass
        # still tied -> random
        if nc > 1:
            bi = 0
            br = -1.0
            for k in range(nc):
                if rnd[cand[k]] > br:
                    br = rnd[cand[k]]
                    bi = k
            winner = cand[bi]
        else:
            winner = cand[0]
        out[pos] = winner
        pos += 1
        # remove winner
        nn = 0
        for k in range(nr):
            if rem[k] != winner:
                rem[nn] = rem[k]
                nn += 1
        nr = nn


@njit(cache=True)
def conference_order(c, W, G, div, conf, pdiff, rnd, order_out, divwin_out):
    """order_out[0..14] = team ids best-first for conference c; divwin_out[t]=True for division winners."""
    wins = np.zeros(NT)
    for t in range(NT):
        s = 0.0
        for j in range(NT):
            s += W[t, j]
        wins[t] = s
    members = np.zeros(15, np.int64)
    m = 0
    for t in range(NT):
        if conf[t] == c:
            members[m] = t
            m += 1
    # preliminary order by wins then random -> eligible set (top 10)
    keys = np.zeros(15)
    for k in range(15):
        keys[k] = wins[members[k]] + 1e-6 * rnd[members[k]]
    idx = np.argsort(-keys)
    elig = np.zeros(NT, np.bool_)
    for k in range(10):
        elig[members[idx[k]]] = True
    # eligible set must cover both conferences for criterion 6; fill other conference similarly
    for cc in range(2):
        if cc == c:
            continue
        mem2 = np.zeros(15, np.int64)
        m2 = 0
        for t in range(NT):
            if conf[t] == cc:
                mem2[m2] = t
                m2 += 1
        k2 = np.zeros(15)
        for k in range(15):
            k2[k] = wins[mem2[k]] + 1e-6 * rnd[mem2[k]]
        i2 = np.argsort(-k2)
        for k in range(10):
            elig[mem2[i2[k]]] = True
    nodiv = np.zeros(NT, np.bool_)
    out = np.zeros(15, np.int64)
    S = np.zeros(15, np.int64)
    # division winners
    for d in range(6):
        ns = 0
        bw = -1.0
        for t in range(NT):
            if div[t] == d and conf[t] == c and wins[t] > bw:
                bw = wins[t]
        for t in range(NT):
            if div[t] == d and conf[t] == c and wins[t] == bw:
                S[ns] = t
                ns += 1
        if ns == 0:
            continue
        sort_tied(S, ns, W, G, div, conf, elig, pdiff, nodiv, False, rnd, out)
        divwin_out[out[0]] = True
    # conference order: group by wins desc
    pos = 0
    wv = np.sort(np.unique(wins[members]))[::-1]
    for v in wv:
        ns = 0
        for k in range(15):
            if wins[members[k]] == v:
                S[ns] = members[k]
                ns += 1
        sort_tied(S, ns, W, G, div, conf, elig, pdiff, divwin_out, True, rnd, out)
        for k in range(ns):
            order_out[pos] = out[k]
            pos += 1


# ----------------------------------------------------------------------------- games
@njit(cache=True)
def game_margin(h, a, rt, adj, b2bh, b2ba, hca, par, site_neutral):
    mean = (rt[h] + adj[h]) - (rt[a] + adj[a])
    if not site_neutral:
        mean += hca
    mean += par[1] * b2bh + par[2] * b2ba
    return mean


@njit(cache=True)
def draw_avail(pw, pa, av_conc, arate, par, avail_on, n_top):
    """Per-sim player availability rate a ~ Beta(mean pa, concentration)."""
    for t in range(NT):
        for k in range(n_top):
            if avail_on > 0.5:
                m = min(max(pa[t, k], 0.03), 0.97)
                arate[t, k] = np.random.beta(m * av_conc, (1.0 - m) * av_conc)
            else:
                arate[t, k] = pa[t, k]


@njit(cache=True)
def team_adj(t, pw, pa, arate, gp_pl, n_top, avail_on, count):
    s = 0.0
    for k in range(n_top):
        present = 1.0 if np.random.random() < arate[t, k] else 0.0
        if avail_on > 0.5:
            s += (present - pa[t, k]) * pw[t, k]
        if count:
            gp_pl[t, k] += present
    return s


@njit(cache=True)
def play_one(h, a, b2bh, b2ba, rt, effort, pw, pa, arate, gp_pl, n_top, par, W, G, pdiff, neutral, count_in_season,
             cup_rec, cupW, cup_diff, cup_pts, record_players):
    """Simulate a single game, update records. Returns home-win flag."""
    adj = np.zeros(NT)
    adj[h] = team_adj(h, pw, pa, arate, gp_pl, n_top, par[24], record_players) + effort[h]
    adj[a] = team_adj(a, pw, pa, arate, gp_pl, n_top, par[24], record_players) + effort[a]
    mean = game_margin(h, a, rt, adj, b2bh, b2ba, par[0], par, neutral)
    m = mean + par[3] * np.random.standard_normal()
    mi = np.round(m)
    ot = False
    if mi == 0.0:
        ot = True
        hw = np.random.random() < phi(0.32274861218395140 * mean / par[3])   # OT: 5 of 48 minutes -> edge scales with sqrt(5/48)
        mrec = par[21] if hw else -par[21]
    else:
        hw = mi > 0
        mrec = mi
    if count_in_season:
        if hw:
            W[h, a] += 1
        else:
            W[a, h] += 1
        G[h, a] += 1
        G[a, h] += 1
        pdiff[h] += mrec
        pdiff[a] -= mrec
    if cup_rec:
        tot = par[6] + par[7] * np.random.standard_normal()
        d = 0.0 if ot else mi
        if hw:
            cupW[h, a] += 1
        else:
            cupW[a, h] += 1
        cup_diff[h] += d
        cup_diff[a] -= d
        cup_pts[h] += (tot + d) / 2.0
        cup_pts[a] += (tot - d) / 2.0
    return hw


# ----------------------------------------------------------------------------- cup
@njit(cache=True)
def cup_rank(cands, nc, key_w, cupW, cup_diff, cup_pts, prevw, rnd, use_h2h, out):
    """Order cands best-first by Cup group rules: wins, H2H among tied (if use_h2h), point diff, points, 2025-26 wins, random."""
    n = nc
    used = np.zeros(n, np.bool_)
    for pos in range(n):
        best = -1
        for a in range(n):
            if used[a]:
                continue
            if best < 0:
                best = a
                continue
            ta = cands[a]
            tb = cands[best]
            better = False
            if key_w[ta] != key_w[tb]:
                better = key_w[ta] > key_w[tb]
            else:
                # tied set = all unused with equal wins
                hh_a = 0.0
                hh_b = 0.0
                if use_h2h:
                    for c in range(n):
                        if (not used[c]) and key_w[cands[c]] == key_w[ta]:
                            hh_a += cupW[ta, cands[c]]
                            hh_b += cupW[tb, cands[c]]
                if hh_a != hh_b:
                    better = hh_a > hh_b
                elif cup_diff[ta] != cup_diff[tb]:
                    better = cup_diff[ta] > cup_diff[tb]
                elif cup_pts[ta] != cup_pts[tb]:
                    better = cup_pts[ta] > cup_pts[tb]
                elif prevw[ta] != prevw[tb]:
                    better = prevw[ta] > prevw[tb]
                else:
                    better = rnd[ta] > rnd[tb]
            if better:
                best = a
        used[best] = True
        out[pos] = cands[best]


@njit(cache=True)
def run_cup(rt, effort, pw, pa, arate, gp_pl, n_top, par, W, G, pdiff, conf, grp, grp_conf, cupW, cup_diff, cup_pts, prevw, rnd,
            cup_win_out, cup_grpwin_out, cup_stage_out):
    """After group play: resolve knockout and the 30 Cup-dependent regular-season games. Returns None; updates W/G/pdiff."""
    cup_w = np.zeros(NT)
    for t in range(NT):
        for j in range(NT):
            cup_w[t] += cupW[t, j]
    # rank each group
    gw = np.zeros(6, np.int64)
    second = np.zeros(6, np.int64)
    tmp = np.zeros(5, np.int64)
    out = np.zeros(5, np.int64)
    members = np.zeros((6, 5), np.int64)
    for g in range(6):
        k = 0
        for t in range(NT):
            if grp[t] == g:
                members[g, k] = t
                k += 1
        cup_rank(members[g], 5, cup_w, cupW, cup_diff, cup_pts, prevw, rnd, True, out)
        gw[g] = out[0]
        second[g] = out[1]
        cup_grpwin_out[out[0]] = 1
    qual = np.zeros(NT, np.bool_)
    seeds = np.zeros((2, 4), np.int64)
    for c in range(2):
        wl = np.zeros(3, np.int64)
        sl = np.zeros(3, np.int64)
        kk = 0
        for g in range(6):
            if grp_conf[g] == c:
                wl[kk] = gw[g]
                sl[kk] = second[g]
                kk += 1
        o3 = np.zeros(3, np.int64)
        cup_rank(sl, 3, cup_w, cupW, cup_diff, cup_pts, prevw, rnd, False, o3)
        wc = o3[0]
        o4 = np.zeros(3, np.int64)
        cup_rank(wl, 3, cup_w, cupW, cup_diff, cup_pts, prevw, rnd, False, o4)
        seeds[c, 0] = o4[0]
        seeds[c, 1] = o4[1]
        seeds[c, 2] = o4[2]
        seeds[c, 3] = wc
        for s in range(4):
            qual[seeds[c, s]] = True
            cup_stage_out[seeds[c, s]] = 1
    losers = np.zeros((2, 2), np.int64)
    finalists = np.zeros(2, np.int64)
    zero = np.zeros(NT)
    dummyW = np.zeros((NT, NT))
    dummyD = np.zeros(NT)
    for c in range(2):
        # quarterfinals: seed1 hosts seed4(WC); seed2 hosts seed3
        wins_q = np.zeros(2, np.int64)
        for q in range(2):
            h = seeds[c, q]
            a = seeds[c, 3 - q]
            hw = play_one(h, a, 0, 0, rt, effort, pw, pa, arate, gp_pl, n_top, par, W, G, pdiff, False, True, False, dummyW, dummyD, dummyD, True)
            wins_q[q] = h if hw else a
            losers[c, q] = a if hw else h
            cup_stage_out[wins_q[q]] = 2
        # semifinal: higher seed (lower index in seeds) hosts, neutral if toggled
        s_a = wins_q[0]
        s_b = wins_q[1]
        ia = 0
        ib = 0
        for s in range(4):
            if seeds[c, s] == s_a:
                ia = s
            if seeds[c, s] == s_b:
                ib = s
        h = s_a if ia < ib else s_b
        a = s_b if ia < ib else s_a
        hw = play_one(h, a, 0, 0, rt, effort, pw, pa, arate, gp_pl, n_top, par, W, G, pdiff, par[18] > 0.5, True, False, dummyW, dummyD, dummyD, True)
        finalists[c] = h if hw else a
        cup_stage_out[finalists[c]] = 3
        # QF losers play one regular-season game (higher seed hosts)
        l0 = losers[c, 0]
        l1 = losers[c, 1]
        i0 = 0
        i1 = 0
        for s in range(4):
            if seeds[c, s] == l0:
                i0 = s
            if seeds[c, s] == l1:
                i1 = s
        hh = l0 if i0 < i1 else l1
        aa = l1 if i0 < i1 else l0
        play_one(hh, aa, 0, 0, rt, effort, pw, pa, arate, gp_pl, n_top, par, W, G, pdiff, False, True, False, dummyW, dummyD, dummyD, True)
    # final (neutral, not a regular-season game)
    f0 = finalists[0]
    f1 = finalists[1]
    hw = play_one(f0, f1, 0, 0, rt, effort, pw, pa, arate, gp_pl, n_top, par, W, G, pdiff, True, False, False, dummyW, dummyD, dummyD, False)
    champ = f0 if hw else f1
    cup_win_out[champ] = 1
    cup_stage_out[champ] = 4
    # 22 non-qualifiers: 2 games each (1 home, 1 away); random cycles within conference, optional 2 cross-conference games
    cross = par[17] > 0.5
    cyc = np.zeros((2, 11), np.int64)
    for c in range(2):
        k = 0
        for t in range(NT):
            if conf[t] == c and not qual[t]:
                cyc[c, k] = t
                k += 1
        # shuffle (Fisher-Yates)
        for i in range(10, 0, -1):
            j = int(np.random.random() * (i + 1))
            tmpv = cyc[c, i]
            cyc[c, i] = cyc[c, j]
            cyc[c, j] = tmpv
    for c in range(2):
        for i in range(11):
            h = cyc[c, i]
            a = cyc[c, (i + 1) % 11]
            skip = False
            if cross and i == 10:
                skip = True      # the closing edge of each cycle is replaced by a cross-conference game
            if not skip:
                play_one(h, a, 0, 0, rt, effort, pw, pa, arate, gp_pl, n_top, par, W, G, pdiff, False, True, False, dummyW, dummyD, dummyD, True)
    if cross:
        # East closing edge was a=cyc[0,10] (home) -> cyc[0,0]; West closing edge c=cyc[1,10] -> cyc[1,0]
        a_ = cyc[0, 10]
        b_ = cyc[0, 0]
        c_ = cyc[1, 10]
        d_ = cyc[1, 0]
        play_one(a_, d_, 0, 0, rt, effort, pw, pa, arate, gp_pl, n_top, par, W, G, pdiff, False, True, False, dummyW, dummyD, dummyD, True)
        play_one(c_, b_, 0, 0, rt, effort, pw, pa, arate, gp_pl, n_top, par, W, G, pdiff, False, True, False, dummyW, dummyD, dummyD, True)


# ----------------------------------------------------------------------------- playoffs
@njit(cache=True)
def series(h, a, rt, po_adj, inj, par, wins_h_needed=4):
    """Best-of-7, h has home court (2-2-1-1-1). Returns winner."""
    pattern = (1, 1, 0, 0, 1, 0, 1)
    wh = 0
    wa = 0
    g = 0
    while wh < 4 and wa < 4:
        home_is_h = pattern[g] == 1
        mean = (rt[h] + po_adj[h] - inj[h]) - (rt[a] + po_adj[a] - inj[a])
        mean = mean + par[4] if home_is_h else mean - par[4]
        m = mean + par[5] * np.random.standard_normal()
        hwin = m > 0
        if hwin == home_is_h:
            wh += 1
        else:
            wa += 1
        g += 1
    return h if wh == 4 else a


@njit(cache=True)
def play_in_game(h, a, rt, par):
    mean = rt[h] - rt[a] + par[4]
    m = mean + par[5] * np.random.standard_normal()
    return h if m > 0 else a
