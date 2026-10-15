"""College-translation rookie model. Torvik columns (headerless CSV, verified on AJ Dybantsa/Darryn Peterson 2026): 0 name, 1 team, 3 GP,
4 min%, 5 ORtg, 6 usg, 25 class, 26 height, 31 year, 32 pid, 45 NBA pick (draft-pick column), 50 BPM, 51 OBPM, 52 DBPM, 54 mpg."""
import glob, os
import numpy as np, pandas as pd
from ..data.namemap import norm
from .model import _wols

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CLASS = {"Fr": 0, "So": 1, "Jr": 2, "Sr": 3}


def height_in(h):
    try:
        f, i = str(h).split("-"); return int(f) * 12 + int(i)
    except Exception:
        return np.nan


def load_torvik():
    rows = []
    for f in sorted(glob.glob(os.path.join(ROOT, "data/raw/barttorvik/advstats_*.csv_*"))):
        d = pd.read_csv(f, header=None, low_memory=False)
        d = d[[0, 1, 3, 4, 6, 25, 26, 31, 45, 50, 51, 52]]
        d.columns = ["name", "team", "gp", "min_pct", "usg", "cls", "ht", "year", "pick_t", "bpm_c", "obpm_c", "dbpm_c"]
        rows.append(d)
    T = pd.concat(rows, ignore_index=True)
    for c in ["gp", "min_pct", "usg", "year", "pick_t", "bpm_c", "obpm_c", "dbpm_c"]:
        T[c] = pd.to_numeric(T[c], errors="coerce")
    T["k"] = T.name.map(norm); T["cls_n"] = T.cls.map(CLASS); T["ht_in"] = T.ht.map(height_in)
    T["load"] = T.gp * T.min_pct
    return T.sort_values("load", ascending=False).drop_duplicates(["k", "year"])


def college_table(D, T):
    """Per draftee (all drafts 2013-2026): pick, college BPM etc. (draft year == Torvik year)."""
    dr = D.dr.copy(); dr["k"] = dr.player.map(norm)
    m = dr.merge(T[["k", "year", "bpm_c", "obpm_c", "dbpm_c", "usg", "cls_n", "ht_in"]], left_on=["k", "draft_year"], right_on=["k", "year"], how="left")
    return m.drop(columns=["year"])


def fit_rookie(D, T, max_season, use_college=True):
    """Fit rookie-season BPM ~ ln(pick) [+ college bpm + age proxy + height]. Returns params dict."""
    ct = college_table(D, T)
    rk = D.draft_ids[D.draft_ids.draft_year + 1 <= max_season].merge(ct[["draft_year", "pick", "k", "bpm_c", "cls_n", "ht_in", "player"]].assign(),
                                                                      on=["draft_year", "pick"], how="left")
    ps = D.ps
    rs = ps.merge(rk, on="bbref_id"); rs = rs[(rs.season == rs.draft_year + 1) & (rs.mp >= 100)].copy()
    rs["lp"] = np.log(rs.pick)
    has = rs.bpm_c.notna()
    rs["bpm_c0"] = rs.bpm_c.fillna(rs.bpm_c.mean()); rs["miss"] = (~has).astype(float)
    rs["cls0"] = rs.cls_n.fillna(0); rs["ht0"] = (rs.ht_in.fillna(rs.ht_in.mean()) - 78) / 3
    cols = ["lp"] + (["bpm_c0", "miss", "cls0", "ht0"] if use_college else [])
    X = np.column_stack([np.ones(len(rs))] + [rs[c].values for c in cols])
    b = _wols(X, rs.bpm.values, rs.mp.values)
    res = rs.bpm.values - X @ b
    return dict(cols=cols, beta=b.tolist(), n=int(len(rs)), bpm_c_mean=float(rs.bpm_c.mean()), ht_mean=float(rs.ht_in.mean()),
                rmse=float(np.sqrt(np.average(res ** 2, weights=rs.mp.values))), match_rate=float(has.mean()))


def predict_rookie(P, pick, bpm_c=np.nan, cls_n=np.nan, ht_in=np.nan):
    c = P["cols"]; b = P["beta"]
    v = {"lp": np.log(pick), "bpm_c0": P["bpm_c_mean"] if pd.isna(bpm_c) else bpm_c, "miss": float(pd.isna(bpm_c)),
         "cls0": 0.0 if pd.isna(cls_n) else cls_n, "ht0": ((P["ht_mean"] if pd.isna(ht_in) else ht_in) - 78) / 3}
    return b[0] + sum(b[i + 1] * v[k] for i, k in enumerate(c))


def loo_draft_year(D, T, years=range(2018, 2026)):
    """Leave-future-out: fit on drafts < y, test on draftees of year y. Returns RMSE with/without college."""
    ps = D.ps; ct = college_table(D, T)
    out = []
    for y in years:
        for uc in (False, True):
            P = fit_rookie(D, T, y - 1 + 0, use_college=uc)  # rookies through season y-1 => drafts <= y-2
            rk = D.draft_ids[D.draft_ids.draft_year == y].merge(ct[["draft_year", "pick", "bpm_c", "cls_n", "ht_in"]], on=["draft_year", "pick"], how="left")
            rs = ps.merge(rk, on="bbref_id"); rs = rs[(rs.season == y + 1) & (rs.mp >= 100)]
            pred = np.array([predict_rookie(P, r.pick, r.bpm_c, r.cls_n, r.ht_in) for r in rs.itertuples()])
            out.append(dict(draft_year=y, college=uc, n=len(rs), sse=float(((rs.bpm.values - pred) ** 2 * rs.mp.values).sum()), w=float(rs.mp.sum())))
    o = pd.DataFrame(out)
    g = o.groupby("college").agg(sse=("sse", "sum"), w=("w", "sum"), n=("n", "sum"))
    return {bool(k): dict(rmse=float(np.sqrt(v.sse / v.w)), n=int(v.n)) for k, v in g.iterrows()}
