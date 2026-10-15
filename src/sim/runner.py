import time, numpy as np
from .season import run_sims
from .inputs import K_TOP

def simulate(inp, n, seed=1, verbose=True):
    n_top = inp["pw"].shape[1]
    o_wins = np.zeros((n, 30), np.int16); o_conf_rank = np.zeros((n, 30), np.int8); o_flags = np.zeros((n, 30), np.int16)
    o_pick = np.zeros((n, 30), np.int8); o_gp = np.zeros((n, 30, n_top), np.int8); o_cupstage = np.zeros((n, 30), np.int8)
    o_lotpos = np.zeros((n, 30), np.int8); o_srs = np.zeros((n, 30), np.float32); o_games = np.zeros((n, 30), np.int16)
    t = time.time()
    run_sims(n, seed, inp["par"], inp["conf"], inp["div"], inp["grp"], inp["grp_conf"], inp["prevw"], inp["rating"], inp["pw"], inp["pa"], inp["pw_po"], inp["po_delta"],
             inp["gh"], inp["ga"], inp["gb2bh"], inp["gb2ba"], inp["gday"], inp["gcup"], inp["deadline_day"], inp["cup_ko_day"],
             inp["pickval"], inp["Pgen"], inp["Pnf"], inp["Pnt5"], inp["kprot"], inp["fover"], inp["nf_team"], inp["nt5_team"],
             o_wins, o_conf_rank, o_flags, o_pick, o_gp, o_cupstage, o_lotpos, o_srs, o_games)
    if verbose: print(f"{n} sims in {time.time()-t:.1f}s")
    return dict(wins=o_wins, conf_rank=o_conf_rank, flags=o_flags, pick=o_pick, gp=o_gp, cupstage=o_cupstage, lotpos=o_lotpos, srs=o_srs, games=o_games, teams=inp["teams"])

FLAGS = dict(playoffs=1, top6=2, division=4, conference=8, title=16, cup_group=32, cup=64, bracket=128)
def prob(res, name):
    return ((res["flags"] & FLAGS[name]) > 0).mean(0)
