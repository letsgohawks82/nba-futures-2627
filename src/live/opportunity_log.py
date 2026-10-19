"""Append-only log of EVERY evaluated market (team + player), stamped with commit / release / seed / N, so selection bias can be measured later.
    python -m src.live.opportunity_log snapshot            -> live/opportunities_<UTC date>_<HHMM>.csv  (never overwrites; refuses if the file exists)
    python -m src.live.opportunity_log close CLOSES.csv    -> appends live/clv_ledger.csv from a closing-price file you supply
CLOSES.csv columns: market,selection,side,line,closing_american[,closed_at_utc,result]  (side/line blank where not applicable; result W/L/P optional).
Closing prices are entered by hand from the book (nothing is scraped). CLV is in implied-probability points of the SAME side: implied(close) - implied(price at snapshot);
positive = the market moved toward the pick. Status: CARD / HELD / EXCLUDED / TIER2 / DISPLAY_ONLY / IMPUTED / NOT_BET."""
import csv, datetime as dt, hashlib, json, os, subprocess, sys
import pandas as pd
from ..release.meta import META
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LIVE = os.path.join(ROOT, "live"); C = lambda f: os.path.join(ROOT, "data", "clean", f)
KEY = ["market", "selection", "side", "line"]


def impl(a):
    a = float(a); return 100 / (a + 100) if a > 0 else -a / (-a + 100)


def git(*a):
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def status(r, card, hold, is_player):
    k = (r.market, r.selection, r.side, None if pd.isna(r.line) else float(r.line))
    if k in card: return "CARD"
    if bool(getattr(r, "t1_excluded", False)):
        if (r.market, r.selection) in hold or (r.market, getattr(r, "team", "")) in hold: return "HELD" if (is_player or (getattr(r, "ev75", -1) or -1) > 0) else "NOT_BET"
        return "EXCLUDED"
    if False: return "HELD" if (r.market, r.selection) in hold or (r.market, getattr(r, "team", "")) in hold else "EXCLUDED"
    if bool(getattr(r, "imputed", False)): return "IMPUTED"
    if bool(getattr(r, "display_only", False)): return "DISPLAY_ONLY"
    if bool(getattr(r, "qualifies", False)) or bool(getattr(r, "tier2", False)): return "TIER2"
    return "NOT_BET"


def snapshot():
    os.makedirs(LIVE, exist_ok=True)
    card_df = pd.read_csv(os.path.join(ROOT, "release", "final_card.csv")); card = {(r.market, r.selection, r.side, None if pd.isna(r.line) else float(r.line)): r for r in card_df.itertuples()}
    ov = json.load(open(os.path.join(ROOT, "params", "tier1_overrides.json"))); hold = {(h["market"], h.get("selection", h.get("team"))) for h in ov["hold"]} | {(h["market"], h["team"]) for h in ov["hold"] if "team" in h}
    now = dt.datetime.now(dt.timezone.utc); rows = []
    sim_meta = json.load(open(os.path.join(ROOT, "sims", "run_meta.json"))) if os.path.exists(os.path.join(ROOT, "sims", "run_meta.json")) else {}
    common = dict(snapshot_utc=now.strftime("%Y-%m-%dT%H:%M:%SZ"), git_commit=git("rev-parse", "HEAD"), git_dirty=int(bool(git("status", "--porcelain", "--untracked-files=no"))), release=META["version"], odds_as_of=META["odds_as_of"],
                  sim_n=sim_meta.get("n_sims", sim_meta.get("N", "")), sim_seed=sim_meta.get("seed", ""))
    for src, is_p in (("pricing_table.csv", False), ("player_pricing_table.csv", True)):
        T = pd.read_csv(C(src))
        for r in T.itertuples():
            k = (r.market, r.selection, r.side, None if pd.isna(r.line) else float(r.line)); c = card.get(k)
            st = status(r, card, hold, is_p)
            mp = r.model_prob; ev = r.ev
            rows.append(dict(common, kind="player" if is_p else "team", market=r.market, selection=r.selection, side=r.side, line=r.line, book_american=r.american, book_implied=round(impl(r.american), 6),
                             fair_prob=r.fair, model_prob=mp, ev=ev, ev_lo=getattr(r, "ev_lo", ""), status=st, recommended_stake=(c.stake_frac if c is not None else 0.0), min_price=(c.min_price if c is not None else ""),
                             closing_american="", result=""))
    df = pd.DataFrame(rows); h = hashlib.sha256(df.drop(columns=["snapshot_utc"]).to_csv(index=False).encode()).hexdigest()
    path = os.path.join(LIVE, f"opportunities_{now.strftime('%Y%m%d_%H%M')}.csv")
    if os.path.exists(path): sys.exit(f"refusing to overwrite {path}")
    df.to_csv(path, index=False, lineterminator="\n"); open(path + ".sha256", "w").write(f"{h}  content-without-snapshot_utc\n")
    print(f"wrote {path}: {len(df)} rows; " + ", ".join(f"{k} {v}" for k, v in df.status.value_counts().items()))
    return path


def close(closes):
    snaps = sorted(f for f in os.listdir(LIVE) if f.startswith("opportunities_") and f.endswith(".csv"))
    if not snaps: sys.exit("no snapshot in live/")
    S = pd.read_csv(os.path.join(LIVE, snaps[0])); S["line"] = S["line"].astype(float)       # the FIRST snapshot is the price decision is judged against
    Cl = pd.read_csv(closes); Cl["line"] = Cl["line"].astype(float); led_path = os.path.join(LIVE, "clv_ledger.csv")
    led = pd.read_csv(led_path) if os.path.exists(led_path) else pd.DataFrame()
    new = []
    for r in Cl.itertuples():
        m = S[(S.market == r.market) & (S.selection == r.selection) & (S.side.fillna("") == (r.side if isinstance(r.side, str) else "")) & (S.line.fillna(-999) == (-999 if pd.isna(r.line) else r.line))]
        if len(m) != 1: sys.exit(f"closing row does not match exactly one snapshot row: {r}")
        s = m.iloc[0]; clv = impl(r.closing_american) - impl(s.book_american)
        new.append(dict(snapshot=snaps[0], market=s.market, selection=s.selection, side=s.side, line=s.line, status=s.status, book_american=s.book_american, closing_american=r.closing_american, model_prob=s.model_prob, fair_prob=s.fair_prob,
                        clv_implied_pp=round(100 * clv, 3), closed_at_utc=getattr(r, "closed_at_utc", ""), result=getattr(r, "result", "")))
    new = pd.DataFrame(new)
    allr = pd.concat([led, new], ignore_index=True); allr.to_csv(led_path, index=False, lineterminator="\n")
    g = allr.groupby("status").clv_implied_pp.agg(["count", "mean", "median", lambda x: (x > 0).mean()]); g.columns = ["n", "mean_clv_pp", "median_clv_pp", "share_positive"]; print(g.to_string())


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "snapshot": snapshot()
    elif len(sys.argv) == 3 and sys.argv[1] == "close": close(sys.argv[2])
    else: print(__doc__)
