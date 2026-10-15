"""simulate_season / run: orchestrates the numba kernels in engine.py"""
import math
import numpy as np
from numba import njit, prange
from .engine import *
from .lottery import _one as lottery_draw, BALLS


@njit(cache=True)
def late_pick_and_slot(i, Wv, conf, tr_noise):
    """Return (conference rank of team i, ...) helper: rank by Wv (higher=better) with deterministic tiny noise."""
    r = 1
    for j in range(NT):
        if j != i and conf[j] == conf[i]:
            if Wv[j] + tr_noise[j] > Wv[i] + tr_noise[i]:
                r += 1
    return r


@njit(cache=True)
def pick_state(i, Wv, conf, tr_noise, pickval, Pgen, Pnf, Pnt5, no_first, no_top5, kprot):
    """Expected pick value V for team i's own pick if the season ended with win vector Wv; also P(pick <= kprot[i]) and in-race flag."""
    cr = late_pick_and_slot(i, Wv, conf, tr_noise)
    inrace = 1.0 if cr <= 10 else 0.0
    # conference ranks of everybody
    crs = np.zeros(NT, np.int64)
    for j in range(NT):
        crs[j] = late_pick_and_slot(j, Wv, conf, tr_noise)
    slot_lot = -1.0
    late = False
    if cr >= 11:
        pos = 1
        for j in range(NT):
            if j != i and crs[j] >= 11 and Wv[j] + tr_noise[j] < Wv[i] + tr_noise[i]:
                pos += 1
        slot_lot = pos
    elif cr >= 9:
        pos = 1
        for j in range(NT):
            if j != i and crs[j] >= 9 and crs[j] <= 10 and Wv[j] + tr_noise[j] < Wv[i] + tr_noise[i]:
                pos += 1
        slot_lot = 10 + pos
    # value
    V = 0.0
    ptop = 1.0
    if slot_lot > 0:
        s = int(slot_lot) - 1
        if no_first[i]:
            row = Pnf[s, s]
        elif no_top5[i]:
            row = Pnt5[s, s]
        else:
            row = Pgen[s]
        for p in range(16):
            V += row[p] * pickval[p + 1]
        if kprot[i] > 0:
            ptop = 0.0
            for p in range(min(kprot[i], 16)):
                ptop += row[p]
    else:
        # playoff-bound or 7/8 seed: late pick by record ascending among the 16 teams with conference rank <= 8
        pos = 1
        for j in range(NT):
            if j != i and crs[j] <= 8 and Wv[j] + tr_noise[j] < Wv[i] + tr_noise[i]:
                pos += 1
        lp = 16.0 + math.ceil(pos * 14.0 / 16.0)
        if lp > 30.0:
            lp = 30.0
        Vlate = pickval[int(lp)]
        if cr == 7 or cr == 8:
            q = 0.45 if cr == 7 else 0.55
            s = 14
            row = Pgen[s]
            Vl = 0.0
            for p in range(16):
                Vl += row[p] * pickval[p + 1]
            V = q * Vl + (1.0 - q) * Vlate
            if kprot[i] > 0:
                ptop = 0.0
                for p in range(min(kprot[i], 16)):
                    ptop += q * row[p]
        else:
            V = Vlate
            if kprot[i] > 0:
                ptop = 0.0
    return V, ptop, inrace


@njit(cache=True)
def tank_effort(W, G, rt, par, conf, pickval, Pgen, Pnf, Pnt5, no_first, no_top5, kprot, fover, effort):
    """Deadline step: marginal draft equity of one more loss (under 3-2-1, may be negative) -> effort suppression."""
    E = np.zeros(NT)
    sd = np.zeros(NT)
    noise = np.zeros(NT)
    for j in range(NT):
        w = 0.0
        g = 0.0
        for k in range(NT):
            w += W[j, k]
            g += G[j, k]
        rem = max(82.0 - g, 0.0)
        E[j] = w + rem * (0.5 + rt[j] * par[26] / 82.0)
        sd[j] = math.sqrt(0.25 * rem + 4.0)
        noise[j] = 1e-4 * j
    nodes = np.array([-1.7320508075688772, 0.0, 1.7320508075688772])
    wts = np.array([1.0 / 6.0, 2.0 / 3.0, 1.0 / 6.0])
    for i in range(NT):
        inc = 0.0
        race = 0.0
        Wv = E.copy()
        for n in range(3):
            x = E[i] + sd[i] * nodes[n] * par[25]
            Wv[i] = x
            V0, p0, r0 = pick_state(i, Wv, conf, noise, pickval, Pgen, Pnf, Pnt5, no_first, no_top5, kprot)
            Wv[i] = x - 1.0
            V1, p1, r1 = pick_state(i, Wv, conf, noise, pickval, Pgen, Pnf, Pnt5, no_first, no_top5, kprot)
            f = 1.0
            if fover[i] >= 0.0:
                f = fover[i]
            elif kprot[i] == 0:
                f = 0.0
            elif kprot[i] > 0:
                f = p0
            inc += wts[n] * f * (V1 - V0)
            race += wts[n] * r0
        norm = inc / par[23] * (1.0 - race)
        if norm > 0:
            effort[i] = -par[14] * norm * (1.0 - par[15])
        elif par[22] > 0.5:
            effort[i] = -par[14] * norm * (1.0 - par[15])    # sign flip: effort rises (optional)
        else:
            effort[i] = 0.0


@njit(cache=True, parallel=True)
def run_sims(n, seed, par, conf, div, grp, grp_conf, prevw, rating, pw, pa, pw_po, po_delta,
             gh, ga, gb2bh, gb2ba, gday, gcup, deadline_day, cup_ko_day,
             pickval, Pgen, Pnf, Pnt5, kprot, fover, nf_team, nt5_team,
             o_wins, o_conf_rank, o_flags, o_pick, o_gp, o_cupstage, o_lotpos, o_srs, o_games):
    n_top = pw.shape[1]
    ng = gh.shape[0]
    for sim in prange(n):
        np.random.seed(seed * 1000003 + sim)
        rnd = np.random.random(NT)
        rt = np.zeros(NT)
        z = np.random.standard_normal(NT)
        for t in range(NT):
            rt[t] = rating[t] + par[8] * z[t]
        m = rt.mean()
        for t in range(NT):
            rt[t] -= m
        arate = np.zeros((NT, n_top))
        draw_avail(pw, pa, par[11], arate, par, par[24], n_top)
        gp_pl = np.zeros((NT, n_top))
        W = np.zeros((NT, NT))
        G = np.zeros((NT, NT))
        pdiff = np.zeros(NT)
        cupW = np.zeros((NT, NT))
        cup_diff = np.zeros(NT)
        cup_pts = np.zeros(NT)
        effort = np.zeros(NT)
        cupwin = np.zeros(NT, np.int64)
        cupgrp = np.zeros(NT, np.int64)
        cupstage = np.zeros(NT, np.int64)
        cup_done = par[27] < 0.5
        tank_done = False
        no_first = np.zeros(NT, np.bool_)
        no_top5 = np.zeros(NT, np.bool_)
        if nf_team >= 0:
            no_first[nf_team] = True
        if nt5_team >= 0:
            no_top5[nt5_team] = True
        for g in range(ng):
            if (not cup_done) and gday[g] >= cup_ko_day:
                run_cup(rt, effort, pw, pa, arate, gp_pl, n_top, par, W, G, pdiff, conf, grp, grp_conf, cupW, cup_diff, cup_pts, prevw, rnd,
                        cupwin, cupgrp, cupstage)
                cup_done = True
            if (not tank_done) and gday[g] > deadline_day:
                tank_done = True
                if par[16] > 0.5:
                    tank_effort(W, G, rt, par, conf, pickval, Pgen, Pnf, Pnt5, no_first, no_top5, kprot, fover, effort)
            play_one(gh[g], ga[g], gb2bh[g], gb2ba[g], rt, effort, pw, pa, arate, gp_pl, n_top, par, W, G, pdiff, False, True, gcup[g],
                     cupW, cup_diff, cup_pts, True)
        if (not cup_done) and par[27] > 0.5:
            run_cup(rt, effort, pw, pa, arate, gp_pl, n_top, par, W, G, pdiff, conf, grp, grp_conf, cupW, cup_diff, cup_pts, prevw, rnd,
                    cupwin, cupgrp, cupstage)
        # ---- standings
        wins = np.zeros(NT)
        for t in range(NT):
            for j in range(NT):
                wins[t] += W[t, j]
        order = np.zeros((2, 15), np.int64)
        divwin = np.zeros(NT, np.bool_)
        for c in range(2):
            oc = np.zeros(15, np.int64)
            conference_order(c, W, G, div, conf, pdiff, rnd, oc, divwin)
            order[c] = oc
        crank = np.zeros(NT, np.int64)
        for c in range(2):
            for k in range(15):
                crank[order[c, k]] = k + 1
        # ---- play-in
        po_adj = np.zeros(NT)
        inj = np.zeros(NT)
        for t in range(NT):
            po_adj[t] = par[12] * po_delta[t]
            for k in range(min(8, n_top)):
                if np.random.random() < par[13]:
                    inj[t] += pw_po[t, k]
        champ_conf = np.zeros(2, np.int64)
        loser78 = np.zeros(2, np.int64)
        playoff_seed = np.zeros((2, 8), np.int64)
        for c in range(2):
            s7 = order[c, 6]
            s8 = order[c, 7]
            s9 = order[c, 8]
            s10 = order[c, 9]
            w78 = play_in_game(s7, s8, rt, par)
            l78 = s8 if w78 == s7 else s7
            w910 = play_in_game(s9, s10, rt, par)
            w8 = play_in_game(l78, w910, rt, par)
            loser78[c] = l78
            for k in range(6):
                playoff_seed[c, k] = order[c, k]
            playoff_seed[c, 6] = w78
            playoff_seed[c, 7] = w8
        # ---- playoffs
        for c in range(2):
            ps = playoff_seed[c]
            r1 = np.zeros(4, np.int64)
            r1[0] = series(ps[0], ps[7], rt, po_adj, inj, par)
            r1[1] = series(ps[3], ps[4], rt, po_adj, inj, par)
            r1[2] = series(ps[2], ps[5], rt, po_adj, inj, par)
            r1[3] = series(ps[1], ps[6], rt, po_adj, inj, par)
            # home court within conference by seed position
            def_pos = np.zeros(NT, np.int64)
            for k in range(8):
                def_pos[ps[k]] = k
            a = r1[0]
            b = r1[1]
            s1 = series(a, b, rt, po_adj, inj, par) if def_pos[a] < def_pos[b] else series(b, a, rt, po_adj, inj, par)
            a = r1[3]
            b = r1[2]
            s2 = series(a, b, rt, po_adj, inj, par) if def_pos[a] < def_pos[b] else series(b, a, rt, po_adj, inj, par)
            champ_conf[c] = series(s1, s2, rt, po_adj, inj, par) if def_pos[s1] < def_pos[s2] else series(s2, s1, rt, po_adj, inj, par)
        e = champ_conf[0]
        w_ = champ_conf[1]
        if wins[e] > wins[w_] or (wins[e] == wins[w_] and rnd[e] > rnd[w_]):
            title = series(e, w_, rt, po_adj, inj, par)
        else:
            title = series(w_, e, rt, po_adj, inj, par)
        # ---- lottery
        lot_team = np.zeros(16, np.int64)
        pos = 0
        # positions 1..10: conference rank >= 11 both conferences, worst first
        tmpk = np.zeros(10)
        tmpt = np.zeros(10, np.int64)
        kk = 0
        for c in range(2):
            for k in range(10, 15):
                t = order[c, k]
                tmpt[kk] = t
                tmpk[kk] = wins[t] + 1e-3 * rnd[t]
                kk += 1
        ix = np.argsort(tmpk)
        for k in range(10):
            lot_team[k] = tmpt[ix[k]]
        t4 = np.zeros(4, np.int64)
        k4 = np.zeros(4)
        kk = 0
        for c in range(2):
            for k in (8, 9):
                t = order[c, k]
                t4[kk] = t
                k4[kk] = wins[t] + 1e-3 * rnd[t]
                kk += 1
        ix = np.argsort(k4)
        for k in range(4):
            lot_team[10 + k] = t4[ix[k]]
        l2 = np.array([loser78[0], loser78[1]])
        k2 = np.array([wins[l2[0]] + 1e-3 * rnd[l2[0]], wins[l2[1]] + 1e-3 * rnd[l2[1]]])
        ix = np.argsort(k2)
        lot_team[14] = l2[ix[0]]
        lot_team[15] = l2[ix[1]]
        nfp = np.zeros(16, np.bool_)
        ntp = np.zeros(16, np.bool_)
        for k in range(16):
            if nf_team >= 0 and lot_team[k] == nf_team:
                nfp[k] = True
            if nt5_team >= 0 and lot_team[k] == nt5_team:
                ntp[k] = True
        u = np.random.random(16)
        outp = np.zeros(16, np.int64)
        lottery_draw(BALLS, nfp, ntp, int(par[19]), int(par[20]), u, outp)
        in_lot = np.zeros(NT, np.bool_)
        for k in range(16):
            t = lot_team[k]
            in_lot[t] = True
            o_pick[sim, t] = outp[k]
            o_lotpos[sim, t] = k + 1
        rest = np.zeros(14, np.int64)
        rk = np.zeros(14)
        kk = 0
        for t in range(NT):
            if not in_lot[t]:
                rest[kk] = t
                rk[kk] = wins[t] + 1e-3 * rnd[t]
                kk += 1
        ix = np.argsort(rk)
        for k in range(14):
            o_pick[sim, rest[ix[k]]] = 17 + k
        inb = np.zeros(NT, np.bool_)
        for c in range(2):
            for k in range(8):
                inb[playoff_seed[c, k]] = True
        # ---- outputs
        for t in range(NT):
            o_wins[sim, t] = wins[t]
            gtot = 0.0
            for j in range(NT):
                gtot += G[t, j]
            o_games[sim, t] = gtot
            o_conf_rank[sim, t] = crank[t]
            o_srs[sim, t] = rt[t]
            f = 0
            if crank[t] <= 10:
                f |= 1
            if crank[t] <= 6:
                f |= 2
            if divwin[t]:
                f |= 4
            if champ_conf[conf[t]] == t:
                f |= 8
            if title == t:
                f |= 16
            if inb[t]:
                f |= 128
            if cupgrp[t] == 1:
                f |= 32
            if cupwin[t] == 1:
                f |= 64
            o_flags[sim, t] = f
            o_cupstage[sim, t] = cupstage[t]
            for k in range(n_top):
                o_gp[sim, t, k] = gp_pl[t, k]
