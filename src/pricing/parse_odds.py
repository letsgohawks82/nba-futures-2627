"""run.py parse-odds <file.pdf|file.txt> : convert a raw book PDF/text dump into the odds CSV schema (market,selection,side,line,american,flag).
Handles this book's format: futures lines '<rotation> <selection> <price>', 'Team O 59½ -135' / 'Regular Season Wins U 59½ +115' wins pairs, and
'<Team> To Make The Playoffs - Yes|No <price>'. Reconciles rotation numbers (sequential within a market) and repairs the concatenation bug where a price runs
into the next line's rotation, e.g. '+3752' / '0764' = '+375' then rotation 20764."""
import re, sys, os
import pandas as pd
from ..data.teams import NAME2ABBR

HEADERS = [(r"Championship", "TITLE"), (r"Eastern Conference Play-In", "PLAYIN_EAST"), (r"Western Conference Play-In", "PLAYIN_WEST"),
           (r"Atlantic Division", "DIV_ATLANTIC"), (r"Central Division", "DIV_CENTRAL"), (r"Southeast Division", "DIV_SOUTHEAST"), (r"Northwest Division", "DIV_NORTHWEST"),
           (r"Pacific Division", "DIV_PACIFIC"), (r"Southwest Division", "DIV_SOUTHWEST"), (r"Eastern Conference 20", "CONF_EAST"), (r"Western Conference 20", "CONF_WEST"),
           (r"NBA Cup 20", "CUP"), (r"East Group A", "CUP_EAST_A"), (r"East Group B", "CUP_EAST_B"), (r"East Group C", "CUP_EAST_C"), (r"West Group A", "CUP_WEST_A"),
           (r"West Group B", "CUP_WEST_B"), (r"West Group C", "CUP_WEST_C"), (r"Clutch Player", "CLUTCH"), (r"Coach of the Year", "COY"), (r"Defensive Player", "DPOY"),
           (r"Most Improved", "MIP"), (r"Rookie of the Year", "ROY"), (r"Cup MVP", "CUP_MVP"), (r"6th Man|Sixth Man", "SMOY"), (r"APG", "LDR_APG"), (r"BPG", "LDR_BPG"),
           (r"PPG", "LDR_PPG"), (r"RPG", "LDR_RPG"), (r"SPG", "LDR_SPG"), (r"TPG", "LDR_TPG"), (r"Reg Season MVP|Season MVP", "MVP"),
           (r"Regular Season Wins", "WINS"), (r"To Make The Playoffs", "PLAYOFFS")]
PRICE = r"([+-]\d{2,6})"
ROT = re.compile(r"^(\d{5})\s+(.+?)\s+" + PRICE + r"$")
NICK = {}
for full in NAME2ABBR:
    NICK[full.split()[-1].lower()] = full
SPELL = {"Golden St Warriors": "Golden State Warriors", "De Aaron Fox": "De'Aaron Fox"}
NICK.update({"76ers": "Philadelphia 76ers", "trail blazers": "Portland Trail Blazers"})


def repair(lines):
    """Fix 'price glued to next rotation' using sequential rotation numbers."""
    out, prev_rot = [], None
    i = 0
    while i < len(lines):
        l = lines[i].strip()
        m = re.match(r"^(\d{5})\s+(.+?)\s+([+-]\d{2,7})$", l)
        if m:
            rot, name, price = m.group(1), m.group(2), m.group(3)
            digits = price[1:]
            nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
            if len(digits) >= 5 and re.match(r"^\d{3,4}$", nxt):
                for k in (1, 2):                      # move k trailing digits of the price to the front of the next line
                    cand = int(digits[-k:] + nxt)
                    if len(str(cand)) == 5 and prev_rot is not None and cand == int(rot) + 1:
                        price = price[: len(price) - k]; lines[i + 1] = str(cand) + " "
                        break
            out.append((rot, name, price))
            prev_rot = int(rot)
        else:
            out.append((None, l, None))
        i += 1
    return out


def parse_text(text, wins_only=False):
    rows, market, pend = [], None, None
    L = [x for x in text.splitlines()]
    L = [re.sub(r"½", ".5", x) for x in L]
    for x in L:
        for pat, code in HEADERS:
            if re.search(pat, x) and not re.match(r"^\d{5}\s", x.strip()) and ("Odds" in x or "NBA" in x or "Wins" in x or "Make" in x):
                market = code
    prev_rot = None
    pending_team_line = None
    for raw in L:
        x = raw.strip()
        for pat, code in HEADERS:
            if re.search(pat, x) and not re.match(r"^\d{5}\s", x) and re.search(r"(Odds to|NBA .*Play-In|NBA To Make|NBA Regular Season)", x):
                market = code
        m = ROT.match(x)
        if m and market and market not in ("WINS", "PLAYOFFS"):
            rows.append(dict(market=market, selection=m.group(2), side="YES", line=None, american=int(m.group(3)), flag="", rotation=int(m.group(1))))
            continue
        m = re.match(r"^(.+?)\s+O\s+(\d{2}\.5)\s*([+-]\d{2,4})?$", x)
        if m and market == "WINS":
            pending_team_line = (m.group(1).strip(), float(m.group(2)))
            if m.group(3): rows.append(dict(market="WINS", selection=pending_team_line[0], side="OVER", line=pending_team_line[1], american=int(m.group(3)), flag="", rotation=None))
            else: rows.append(dict(market="WINS", selection=pending_team_line[0], side="OVER", line=pending_team_line[1], american=None, flag="", rotation=None))
            continue
        m = re.match(r"^Regular Season Wins U\s+(\d{2}\.5)\s*([+-]\d{2,4})?$", x)
        if m and rows and rows[-1]["market"] == "WINS":
            rows.append(dict(market="WINS", selection=rows[-1]["selection"], side="UNDER", line=float(m.group(1)), american=int(m.group(2)) if m.group(2) else None, flag="", rotation=None))
            continue
        m = re.match(r"^([A-Za-z0-9 .]+?) To Make The Playoffs - (Yes|No) ([+-]\d{2,6})$", x)
        if m:
            nick = m.group(1).strip().lower()
            rows.append(dict(market="PLAYOFFS", selection=NICK.get(nick, m.group(1)), side=m.group(2).upper(), line=None, american=int(m.group(3)), flag="", rotation=None))
    return pd.DataFrame(rows)


def main(path, out="odds_parsed.csv"):
    if path.lower().endswith(".pdf"):
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            text = "\n".join((p.extract_text() or "") for p in pdf.pages)
    else:
        text = open(path, encoding="utf-8").read()
    lines = text.splitlines()
    fixed = repair(lines)
    text2 = "\n".join(f"{r} {n} {p}" if r else n for r, n, p in fixed)
    df = parse_text(text2)
    df.to_csv(out, index=False)
    print(f"parsed {len(df)} rows -> {out}; rows missing a price: {int(df.american.isna().sum())} (fill from the cached alternate sheet / flag BACKFILL_*)")
    return df


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "odds_parsed.csv")
