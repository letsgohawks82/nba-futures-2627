"""Market-reference layer (display + gating only; never a model input). Exchange prices (Kalshi, Polymarket) are normalised to sum to 1 over the listed names, per market and source.
Exchange average = mean of the available exchange probabilities for a selection. Prices below 10% carry a longshot bias (noted, not adjusted). The NBA GM survey is displayed only.
Gate for player / award bets: EV > 0 at the blended probability (book fair + exchange average) / 2 as well as at the model probability; model vs exchange average more than 2x apart is flagged."""
import os
import numpy as np, pandas as pd
from ..data.namemap import norm
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EXCHANGES = ("Kalshi", "Polymarket")
ALIAS = {"darius acuff": "darius acuff", "mikel brown": "mikel brown"}


def load():
    d = pd.read_csv(os.path.join(ROOT, "data/consensus/raw_marketref_20261016.csv"))
    d["key"] = d.selection.map(norm); d["pct"] = d.price_or_pct.astype(float)
    d["is_exchange"] = d.source.map(lambda s: any(str(s).startswith(e) for e in EXCHANGES))
    d["norm_prob"] = d.pct / d.groupby(["market", "source"]).pct.transform("sum")
    d["listed_sum"] = d.groupby(["market", "source"]).pct.transform("sum")
    d["longshot_bias_note"] = np.where(d.pct < 10, "price < 10%: longshot bias (not adjusted)", "")
    return d


def exchange_avg(d=None):
    d = load() if d is None else d
    e = d[d.is_exchange]
    return e.groupby(["market", "key"]).norm_prob.mean()
