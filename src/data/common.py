"""Shared pull helpers: cached raw saves + data/manifest.csv (file, source URL, pull timestamp, rows, sha256)."""
import csv, hashlib, json, os, time, datetime as dt
import requests

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW = os.path.join(ROOT, "data", "raw")
MANIFEST = os.path.join(ROOT, "data", "manifest.csv")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/126.0 Safari/537.36")
NBA_HEADERS = {"User-Agent": UA, "Referer": "https://www.nba.com/", "Origin": "https://www.nba.com",
               "Accept": "application/json", "x-nba-stats-origin": "stats", "x-nba-stats-token": "true"}
_last = {}

def now_iso():
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def log_manifest(path, url, rows, note=""):
    new = not os.path.exists(MANIFEST)
    rel = os.path.relpath(path, ROOT).replace("\\", "/")
    with open(MANIFEST, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["file", "source_url", "pull_timestamp", "row_count", "sha256", "note"])
        w.writerow([rel, url, now_iso(), rows, sha256(path), note])

def polite_get(url, host_key, min_gap, params=None, headers=None, retries=4, timeout=60):
    """GET with per-host min gap + exponential backoff."""
    for i in range(retries):
        wait = min_gap - (time.time() - _last.get(host_key, 0))
        if wait > 0:
            time.sleep(wait)
        _last[host_key] = time.time()
        try:
            r = requests.get(url, params=params, headers=headers or {"User-Agent": UA}, timeout=timeout)
            if r.status_code == 200:
                r.encoding = "utf-8"
                return r
            if r.status_code in (403, 404):
                return r
        except requests.RequestException as e:
            r = None
        time.sleep(2 ** (i + 1))
    return r

def save_raw(subdir, name, content, url, rows, note=""):
    d = os.path.join(RAW, subdir); os.makedirs(d, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d")
    p = os.path.join(d, f"{name}_{stamp}")
    mode = "wb" if isinstance(content, bytes) else "w"
    with open(p, mode, **({} if mode == "wb" else {"encoding": "utf-8"})) as f:
        f.write(content)
    log_manifest(p, url, rows, note)
    return p
