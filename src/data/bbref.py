import io, re, pandas as pd
from .common import polite_get, save_raw, UA

BBREF_GAP = 4.2  # <=15 req/min

def get(url, subdir, name):
    r = polite_get(url, "bbref", BBREF_GAP)
    if r is None or r.status_code != 200:
        raise RuntimeError(f"bbref {url} -> {None if r is None else r.status_code}")
    html = r.text
    p = save_raw(subdir, name + ".html", html, url, html.count("<tr"))
    return html, p

def tables(html):
    # bbref hides some tables in HTML comments
    html = html.replace("<!--", "").replace("-->", "")
    return pd.read_html(io.StringIO(html))
