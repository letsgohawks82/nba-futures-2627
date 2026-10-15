"""INDEPENDENT stripped-down check of title/conference/playoff/division odds. Imports NO model code (src.sim / src.ratings): only numpy/pandas + data files.
Inputs (raw-ish): team ratings csv, schedule csv, game-model fit json, sigma_team from provenance. No availability, no tank, no Cup extras (80-game schedule),
random tie-breaks, simplified play-in/playoffs. Writes data/clean/verify_title_independent.json"""
import json, os
import numpy as np, pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
C = lambda f: os.path.join(ROOT, "data", "clean", f)
EAST = {"ATL","BOS","BKN","CHA","CHI","CLE","DET","IND","MIA","MIL","NYK","ORL","PHI","TOR","WAS"}
DIV = {"Atlantic":["BOS","BKN","NYK","PHI","TOR"],"Central":["CHI","CLE","DET","IND","MIL"],"Southeast":["ATL","CHA","MIA","ORL","WAS"],
       "Northwest":["DEN","MIN","OKC","POR","UTA"],"Pacific":["GSW","LAC","LAL","PHX","SAC"],"Southwest":["DAL","HOU","MEM","NOP","SAS"]}

def main(N=200_000, batch=10_000, seed=77):
    rng = np.random.default_rng(seed)
    tp = pd.read_csv(C("team_projection_2027.csv")).set_index("abbr").sort_index()
    teams = list(tp.index); idx = {t: i for i, t in enumerate(teams)}
    gm = json.load(open(C("game_model_fit.json"))); sig_team = json.load(open(os.path.join(ROOT, "params/provenance.json")))["sigma_team_srs"]["value"]
    g = pd.read_csv(C("schedule_games.csv")); L = pd.read_csv(C("schedule_team_games.csv"))
    b2b = dict(zip(L.date + "|" + L.team + "|" + L.opp, L.b2b))
    h = g.home.map(idx).values; a = g.away.map(idx).values
    bh = np.array([b2b.get(f"{d}|{x}|{y}", 0) for d, x, y in zip(g.date, g.home, g.away)], float)
    ba = np.array([b2b.get(f"{d}|{y}|{x}", 0) for d, x, y in zip(g.date, g.home, g.away)], float)
    base = gm["hca"] + gm["b2b_home"] * bh + gm["b2b_away"] * ba
    r0 = tp.pred_srs.values; east = np.array([t in EAST for t in teams]); divs = {d: [idx[t] for t in ts] for d, ts in DIV.items()}
    cnt = {k: np.zeros(30) for k in ("title", "conf", "po", "top6", "div", "wins")}; n_done = 0
    pattern = np.array([1, 1, 0, 0, 1, 0, 1])
    def series(hi, lo, rt):       # hi has home court; arrays of team ids per sim
        wh = np.zeros(len(hi), int); wl = np.zeros(len(hi), int)
        for k in range(7):
            m = rt[np.arange(len(hi)), hi] - rt[np.arange(len(hi)), lo] + (gm["hca_post"] if pattern[k] else -gm["hca_post"])
            hw = (m + gm["sigma_game"] * rng.standard_normal(len(hi))) > 0
            live = (wh < 4) & (wl < 4)
            wh += (live & (hw == bool(pattern[k]))).astype(int) if False else (live & (hw == (pattern[k] == 1))).astype(int)
            wl += (live & (hw != (pattern[k] == 1))).astype(int)
        return np.where(wh == 4, hi, lo)
    while n_done < N:
        n = min(batch, N - n_done)
        rt = r0[None, :] + sig_team * rng.standard_normal((n, 30)); rt -= rt.mean(1, keepdims=True)
        m = base[None, :] + rt[:, h] - rt[:, a] + gm["sigma_game"] * rng.standard_normal((n, len(g)))
        hw = m > 0
        wins = np.zeros((n, 30))
        for t in range(30):
            wins[:, t] = hw[:, h == t].sum(1) + (~hw)[:, a == t].sum(1)
        key = wins + 1e-3 * rng.random((n, 30))
        rank_in_conf = np.zeros((n, 30), int); order = {}
        for c, msk in ((0, east), (1, ~east)):
            ids = np.where(msk)[0]; o = np.argsort(-key[:, ids], axis=1); order[c] = ids[o]
            for k in range(15):
                rank_in_conf[np.arange(n), order[c][:, k]] = k + 1
        cnt["po"] += (rank_in_conf <= 10).sum(0); cnt["top6"] += (rank_in_conf <= 6).sum(0); cnt["wins"] += wins.sum(0)
        for d, ids in divs.items():
            w = np.argmax(key[:, ids], axis=1); np.add.at(cnt["div"], np.array(ids)[w], 1)
        champs = []
        for c in (0, 1):
            o = order[c]; ar = np.arange(n)
            w78 = np.where((rt[ar, o[:, 6]] - rt[ar, o[:, 7]] + gm["hca_post"] + gm["sigma_game"] * rng.standard_normal(n)) > 0, o[:, 6], o[:, 7])
            l78 = np.where(w78 == o[:, 6], o[:, 7], o[:, 6])
            w910 = np.where((rt[ar, o[:, 8]] - rt[ar, o[:, 9]] + gm["hca_post"] + gm["sigma_game"] * rng.standard_normal(n)) > 0, o[:, 8], o[:, 9])
            w8 = np.where((rt[ar, l78] - rt[ar, w910] + gm["hca_post"] + gm["sigma_game"] * rng.standard_normal(n)) > 0, l78, w910)
            s = [o[:, k] for k in range(6)] + [w78, w8]
            r1 = [series(s[0], s[7], rt), series(s[3], s[4], rt), series(s[2], s[5], rt), series(s[1], s[6], rt)]
            pos = np.zeros((n, 30), int)
            for k in range(8): pos[ar, s[k]] = k
            def hc(x, y):
                xb = pos[ar, x] < pos[ar, y]; return series(np.where(xb, x, y), np.where(xb, y, x), rt)
            sf1 = hc(r1[0], r1[1]); sf2 = hc(r1[3], r1[2]); champs.append(hc(sf1, sf2))
            np.add.at(cnt["conf"], champs[-1], 1)
        e, w_ = champs; ar = np.arange(n)
        eb = (wins[ar, e] > wins[ar, w_]) | ((wins[ar, e] == wins[ar, w_]) & (rng.random(n) > 0.5))
        title = series(np.where(eb, e, w_), np.where(eb, w_, e), rt); np.add.at(cnt["title"], title, 1)
        n_done += n
    out = {k: (v / n_done).tolist() for k, v in cnt.items()}; out["teams"] = teams; out["N"] = n_done
    json.dump(out, open(C("verify_title_independent.json"), "w"), indent=1)
    return out

if __name__ == "__main__":
    o = main(); print("independent title odds (top5):", sorted(zip(o["title"], o["teams"]), reverse=True)[:5], "sum", sum(o["title"]))
