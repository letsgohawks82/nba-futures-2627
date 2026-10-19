"""The latest live/ snapshot must agree with the released card (CARD rows == release/final_card.csv, stakes equal), cover every priced market and be hashed."""
import glob, hashlib, os
import pandas as pd
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def test_snapshot_matches_released_card():
    snaps = sorted(glob.glob(os.path.join(ROOT, "live", "opportunities_*.csv"))); assert snaps, "no live snapshot"
    S = pd.read_csv(snaps[0]); card = pd.read_csv(os.path.join(ROOT, "release", "final_card.csv"))
    C = S[S.status == "CARD"]; assert len(C) == len(card) == 4
    for r in card.itertuples():
        m = C[(C.market == r.market) & (C.selection == r.selection) & (C.side == r.side)]
        assert len(m) == 1 and abs(m.recommended_stake.iloc[0] - r.stake_frac) < 1e-9 and m.book_american.iloc[0] == r.american
    assert len(S) == len(pd.read_csv(os.path.join(ROOT, "data", "clean", "pricing_table.csv"))) + len(pd.read_csv(os.path.join(ROOT, "data", "clean", "player_pricing_table.csv")))
    assert set(S.status) <= {"CARD", "HELD", "EXCLUDED", "TIER2", "DISPLAY_ONLY", "IMPUTED", "NOT_BET"} and (S[S.status == "HELD"].shape[0] == 4)
    h = hashlib.sha256(S.drop(columns=["snapshot_utc"]).to_csv(index=False).encode()).hexdigest()
    assert open(snaps[0] + ".sha256").read().split()[0] == h
