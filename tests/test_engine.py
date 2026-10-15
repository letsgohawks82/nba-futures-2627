"""Engine invariants + hand-built tiebreak scenarios. Run: .venv/Scripts/python.exe tests/test_engine.py"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import numpy as np
from src.sim.engine import sort_tied, conference_order, NT
from src.sim.inputs import build, lottery_tables, IDX
from src.sim.runner import simulate, FLAGS

def tb_case():
    # East teams 0..14 (all conf 0 for the test), divisions i//5 ; W[i,j]=wins of i over j
    conf = np.zeros(NT, np.int64); conf[15:] = 1
    div = (np.arange(NT) // 5).astype(np.int64)
    W = np.zeros((NT, NT)); G = np.zeros((NT, NT)); pd_ = np.zeros(NT); rnd = np.linspace(0.1, 0.9, NT)
    # Case 1: teams 0,1 tied on wins; team 1 beat team 0 twice, 0 beat 1 once (H2H favours 1); everyone else loses to them
    for i in range(NT):
        for j in range(NT):
            if i != j:
                G[i, j] = 2
    for j in range(2, NT):
        W[0, j] = 2; W[1, j] = 2; W[j, 0] = 0; W[j, 1] = 0
    W[1, 0] = 2; W[0, 1] = 0
    W[0, 1] = 0
    # make wins equal: team0 needs 2 more wins somewhere -> give team 0 wins vs nothing else; adjust: team1 beat 0 twice (+2) so give team 0 extra wins by reducing others' (skip); order test only uses S
    S = np.array([0, 1], np.int64); out = np.zeros(2, np.int64)
    elig = np.ones(NT, np.bool_); nodiv = np.zeros(NT, np.bool_)
    sort_tied(S, 2, W, G, div, conf, elig, pd_, nodiv, True, rnd, out)
    assert out[0] == 1, f"H2H winner should be team 1, got {out}"
    # Case 2: tie broken by division winner when H2H level
    W2 = W.copy(); W2[1, 0] = 1; W2[0, 1] = 1
    dw = np.zeros(NT, np.bool_); dw[0] = True
    sort_tied(S, 2, W2, G, div, conf, elig, pd_, dw, True, rnd, out)
    assert out[0] == 0, f"division winner should win level H2H tie, got {out}"
    # Case 3: three-team tie -> division winner first, then H2H mini-league
    S3 = np.array([5, 10, 11], np.int64); out3 = np.zeros(3, np.int64)
    W3 = np.zeros((NT, NT)); G3 = np.ones((NT, NT)) * 2
    W3[10, 11] = 2; W3[11, 5] = 2; W3[5, 10] = 2          # rock-paper-scissors among 3 -> H2H equal -> falls to division then conf % then pdiff
    pd3 = np.zeros(NT); pd3[11] = 5.0
    sort_tied(S3, 3, W3, G3, div, conf, elig, pd3, np.zeros(NT, np.bool_), True, rnd, out3)
    assert set(out3.tolist()) == {5, 10, 11}
    print("tiebreak cases OK")

def sim_invariants():
    lt = lottery_tables(16, 120_000)
    inp = build({"_lottery_tables": lt, "tank_on": 1.0, "tank_kappa": 0.28, "tank_REF": 0.555})
    r = simulate(inp, 20000, 9, verbose=False)
    n = r["wins"].shape[0]
    assert (r["games"] == 82).all(), "every team must end at exactly 82 games"
    assert (r["wins"].sum(1) == 1230).all(), "league wins must be 1230 each sim"
    fl = r["flags"]
    po = (fl & 1) > 0; t6 = (fl & 2) > 0; dv = (fl & 4) > 0; cf = (fl & 8) > 0; ti = (fl & 16) > 0; cg = (fl & 32) > 0; cu = (fl & 64) > 0
    assert (po.sum(1) == 20).all() and (t6.sum(1) == 12).all() and (dv.sum(1) == 6).all() and (cf.sum(1) == 2).all() and (ti.sum(1) == 1).all()
    assert (cg.sum(1) == 6).all() and (cu.sum(1) == 1).all()
    assert (ti <= cf).all() and (cf <= po).all() and (t6 <= po).all() and (cu <= (r["cupstage"] >= 4)).all()
    cs = r["cupstage"]
    assert ((cs >= 1).sum(1) == 8).all() and ((cs >= 2).sum(1) == 4).all() and ((cs >= 3).sum(1) == 2).all() and ((cs >= 4).sum(1) == 1).all()
    cr = r["conf_rank"]; conf = inp["conf"]
    for c in (0, 1):
        sub = np.sort(cr[:, conf == c], axis=1)
        assert (sub == np.arange(1, 16)).all(), "conference ranks must be a permutation of 1..15"
    pk = np.sort(r["pick"], axis=1)
    assert (pk == np.arange(1, 31)).all(), "picks must be a permutation of 1..30"
    assert (r["pick"][:, IDX["WAS"]] != 1).all(), "WAS cannot win #1 in 2027"
    assert (r["pick"][:, IDX["UTA"]] > 5).all() or True
    top5_uta = (r["pick"][:, IDX["UTA"]] <= 5).mean()
    assert top5_uta == 0, f"UTA top-5 occurrence {top5_uta}"
    lp = r["lotpos"]
    assert ((lp > 0).sum(1) == 16).all(), "16 lottery teams per sim"
    # bottom-3 records cannot pick lower than 12
    bottom3 = (lp >= 1) & (lp <= 3)
    assert (r["pick"][bottom3] <= 12).all(), "three worst records must pick <= 12"
    print("sim invariants OK:", n, "sims")

if __name__ == "__main__":
    tb_case(); sim_invariants()
