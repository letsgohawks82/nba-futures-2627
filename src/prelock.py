"""python run.py prelock : pre-lock refresh.
 1. snapshot the current Tier 1 state, rosters and injuries
 2. re-pull ESPN rosters + injuries + transactions (since PULL_SINCE) and diff them against the roster / pick tables
 3. re-run ratings + sims ONLY if anything material changed (roster membership, rotation injuries, a trade or pick transaction)
 4. re-price (team, player, joint Kelly), rebuild the workbook (Tier1_Card)
 5. write reports/prelock_YYYYMMDD.md listing every Tier 1 bet whose edge or minimum price moved, plus any Tier 1 bet gained or lost."""
import datetime, json, os, re, shutil, subprocess, sys
import numpy as np, pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
C = lambda f: os.path.join(ROOT, "data", "clean", f)
PY = sys.executable
PULL_SINCE = "2026-10-15"
B = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
MOVE_EV = 0.01; MOVE_P = 0.01; MOVE_PRICE = 5.0
ESPN_FIX = {"GS": "GSW", "NO": "NOP", "NY": "NYK", "SA": "SAS", "UTAH": "UTA", "WSH": "WAS", "PHO": "PHX", "BRK": "BKN", "CHO": "CHA"}
TEAMS30 = {"ATL", "BOS", "BKN", "CHA", "CHI", "CLE", "DAL", "DEN", "DET", "GSW", "HOU", "IND", "LAC", "LAL", "MEM", "MIA", "MIL", "MIN", "NOP", "NYK", "OKC", "ORL", "PHI", "PHX", "POR", "SAC", "SAS", "TOR", "UTA", "WAS"}
GUARDED = ["rosters_espn.csv", "injuries_espn.csv", "schedule_espn.csv"]
TRADE_WORDS = re.compile(r"\b(trad|acquir|sign|waiv|releas|pick|draft|exercis|extend|suspend)", re.I)


def sh(*mod):
    return subprocess.call([PY, "-W", "ignore", "-m", *mod], cwd=ROOT)


def tier1_state():
    out = {}
    T = pd.read_csv(C("pricing_table.csv")); T = T[T.tier1]
    for _, r in T.iterrows(): out[f"{r.market} {r.selection} {r.side}"] = dict(model=float(r.model_prob), fair=float(r.fair), ev75=float((0.25 * r.model_prob + 0.75 * r.fair) * r.dec - 1), min_price=float(r.min_price), stake=float(r.tier1_kelly), american=float(r.american))
    P = pd.read_csv(C("player_pricing_table.csv")); P = P[P.tier1]
    for _, r in P.iterrows(): out[f"{r.market} {r.selection} YES"] = dict(model=float(r.p), fair=float(r.fair), ev75=float((0.25 * r.p + 0.75 * r.fair) * r.dec - 1), min_price=float(r.min_price) if "min_price" in P else float("nan"), stake=float(r.stake_t1), american=float(r.american))
    return out


def parse_injuries(j):
    rows = []
    for t in j.get("injuries", []):
        for i in t.get("injuries", []):
            a = i.get("athlete", {}); d = i.get("details", {}) or {}
            rows.append(dict(team=t.get("displayName"), name=a.get("displayName"), espn_id=a.get("id"), status=i.get("status"), date=i.get("date"), type=d.get("type"), detail=d.get("detail"), side=d.get("side"), ret=d.get("returnDate"),
                             short=i.get("shortComment"), long=i.get("longComment")))
    return pd.DataFrame(rows)


def transactions(since):
    from .data.common import polite_get
    out = []; page = 1
    while page <= 40:
        r = polite_get(B + "/transactions", "espn", 0.5, params={"page": page}); j = r.json(); tr = j.get("transactions", [])
        if not tr: break
        for t in tr:
            if t["date"][:10] >= since: out.append(dict(date=t["date"], team=t["team"]["abbreviation"], description=t["description"]))
        if min(t["date"][:10] for t in tr) < since: break
        page += 1
    return pd.DataFrame(out)


def main(dry=False):
    bk = os.path.join(ROOT, "data", "clean", "prelock_backup"); os.makedirs(bk, exist_ok=True)
    for f in GUARDED: shutil.copy2(C(f), os.path.join(bk, f))
    stamp = datetime.date.today().strftime("%Y%m%d"); old = tier1_state()
    R0 = pd.read_csv(C("rosters_espn.csv")); I0 = pd.read_csv(C("injuries_espn.csv")); proj = pd.read_csv(C("player_projection_2027.csv"))
    print("[prelock] re-pulling ESPN rosters / injuries / transactions ...")
    from .data import pull_espn
    from .data.common import polite_get, save_raw
    pull_espn.run()
    R1 = pd.read_csv(C("rosters_espn.csv")); R1["team"] = R1.team.replace(ESPN_FIX); R1.to_csv(C("rosters_espn.csv"), index=False)
    if set(R1.team) != TEAMS30:      # guard: a malformed pull must never reach the model inputs
        for f in GUARDED: shutil.copy2(os.path.join(bk, f), C(f))
        raise SystemExit(f"[prelock] ESPN pull has unexpected team codes {sorted(set(R1.team) ^ TEAMS30)}; inputs restored")
    r = polite_get(B + "/injuries", "espn", 0.5); I1 = parse_injuries(r.json()); I1.to_csv(C("injuries_espn.csv"), index=False)
    tx = transactions(PULL_SINCE); tx_flag = tx[tx.description.str.contains(TRADE_WORDS)] if len(tx) else tx
    k0 = set(zip(R0.team, R0.espn_id.astype(str))); k1 = set(zip(R1.team, R1.espn_id.astype(str)))
    added = sorted(k1 - k0); dropped = sorted(k0 - k1); nm = dict(zip(R1.espn_id.astype(str), R1.name)); nm.update(dict(zip(R0.espn_id.astype(str), R0.name)))
    rot = set(proj[proj.proj_min >= 600].name)
    key = lambda d: {(x.name, x.status, str(x.ret)) for x in d.itertuples()} if len(d) else set()
    ichg = key(I1) ^ key(I0); ichg_rot = sorted({n for (n, s, rt) in ichg if n in rot})
    trades = tx_flag[tx_flag.description.str.contains(r"\b(trad|acquir)", case=False)] if len(tx_flag) else tx_flag
    picks = tx_flag[tx_flag.description.str.contains(r"\b(pick|draft)", case=False)] if len(tx_flag) else tx_flag
    material = bool(added or dropped or ichg_rot or len(trades) or len(picks))
    print(f"[prelock] roster adds {len(added)} drops {len(dropped)}, rotation injury changes {len(ichg_rot)}, trade/pick transactions {len(trades) + len(picks)} -> material={material}")
    rc = 0
    if dry:
        for f in GUARDED: shutil.copy2(os.path.join(bk, f), C(f))
        material_run = False
    if not dry and material:
        rc = sh("src.ratings.project_2027") or sh("src.sim.run_sim") or sh("src.sim.robust") or sh("src.pricing.param_draws") or sh("src.players.run_g4")
    if not dry: rc = rc or sh("src.pricing.run_pricing") or sh("src.pricing.tier1") or sh("src.pricing.price_players") or sh("src.pricing.joint") or sh("src.workbook.build")
    new = tier1_state(); lines = []
    for k in sorted(set(old) | set(new)):
        if k not in new: lines.append(f"- **LOST Tier 1:** {k}"); continue
        if k not in old: lines.append(f"- **NEW Tier 1:** {k} (model {new[k]['model']:.1%}, EV at shrink 0.75 {new[k]['ev75']:+.1%}, min price {new[k]['min_price']:+.0f})"); continue
        a, b = old[k], new[k]; mv = []
        if abs(b["model"] - a["model"]) >= MOVE_P: mv.append(f"model {a['model']:.1%} -> {b['model']:.1%}")
        if abs(b["ev75"] - a["ev75"]) >= MOVE_EV: mv.append(f"EV@0.75 {a['ev75']:+.1%} -> {b['ev75']:+.1%}")
        if abs(b["min_price"] - a["min_price"]) >= MOVE_PRICE: mv.append(f"min price {a['min_price']:+.0f} -> {b['min_price']:+.0f}")
        if abs(b["stake"] - a["stake"]) >= 0.0005: mv.append(f"stake {a['stake']:.2%} -> {b['stake']:.2%}")
        if mv: lines.append(f"- {k}: " + "; ".join(mv))
    rep = [f"# Pre-lock refresh {stamp}", "", f"Pulled {datetime.datetime.now():%Y-%m-%d %H:%M} (ESPN rosters, injuries, transactions since {PULL_SINCE}). {'**DRY RUN: nothing was applied; inputs restored.** ' if dry else ''}Re-ran sims: **{'YES' if (material and not dry) else 'no' if not dry else 'no (dry run); would have been ' + ('YES' if material else 'no')}**. Pipeline exit code {rc}.", "",
           "## Changes since the last pull", f"- Roster additions: {[(t, nm.get(i, i)) for t, i in added] or 'none'}", f"- Roster removals: {[(t, nm.get(i, i)) for t, i in dropped] or 'none'}",
           f"- Rotation-player injury status/return changes: {ichg_rot or 'none'}", f"- Trade / pick transactions since {PULL_SINCE}: {len(trades) + len(picks)}"]
    for d in (trades, picks):
        for x in (d.itertuples() if len(d) else []): rep.append(f"  - {x.date[:10]} {x.team}: {x.description}")
    rep += ["", "## Other transactions flagged (signings, waivers, extensions, suspensions)"] + [f"- {x.date[:10]} {x.team}: {x.description}" for x in (tx_flag.itertuples() if len(tx_flag) else [])][:60]
    rep += ["", "## Tier 1 bets whose edge, price, or stake moved", *(lines or ["- none moved beyond the tolerance (model 1pp, EV 1pp, min price 5 points, stake 0.05pp)"])]
    rep += ["", "## Current Tier 1 (after refresh)"] + [f"- {k}: book {v['american']:+.0f}, min {v['min_price']:+.0f}, model {v['model']:.1%}, fair {v['fair']:.1%}, EV@0.75 {v['ev75']:+.1%}, stake {v['stake']:.2%}" for k, v in new.items()]
    rep += ["", "## Not automated", "- Pick ownership tables (Hoops Rumors / RealGM / Tankathon) are manual sources: only trade/pick *transactions* from ESPN are scanned here. Recheck them by hand if any pick transaction is listed above.", "- Book odds: re-enter the live board in Odds_Input and the live price on Tier1_Card before the lock."]
    path = os.path.join(ROOT, "reports", f"prelock_{stamp}.md"); open(path, "w", encoding="utf-8").write("\n".join(rep)); print("[prelock] wrote", path); return rc


if __name__ == "__main__":
    sys.exit(main(dry="--dry-run" in sys.argv))
