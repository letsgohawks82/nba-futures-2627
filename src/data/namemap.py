"""Name map: odds-book spellings & DARKO names -> canonical ESPN roster player. Exact-normalized, explicit aliases, fuzzy >=0.9 only as REPORTED candidates (never auto-accepted)."""
import re, unicodedata, difflib, os, sys
import pandas as pd
from .common import ROOT
TEAM_MARKETS_NONPLAYER = {'WINS','PLAYOFFS','TITLE','CUP','COY','CONF_EAST','CONF_WEST','PLAYIN_EAST','PLAYIN_WEST'}
def norm(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii','ignore').decode().lower()
    s = re.sub(r"[.'`’]", '', s).replace('-', ' '); s = re.sub(r'\b(jr|sr|ii|iii|iv|v)\b', '', s)
    return re.sub(r'\s+', ' ', s).strip()
# explicit aliases (book spelling -> canonical roster spelling), each verified by hand against roster
ALIASES = {'kelel ware':"Kel'el Ware", 'deaaron fox':"De'Aaron Fox", 'alperen segun':'Alperen Sengun',
           'luguentz dort':'Luguentz Dort',
           'alexandre sarr':'Alex Sarr', 'carlton carrington':'Bub Carrington', 'nicolas claxton':'Nic Claxton', 'nahshon hyland':'Bones Hyland'}
def load():
    r = pd.read_csv(os.path.join(ROOT,'data/clean/rosters_espn.csv'))
    o = pd.read_csv(os.path.join(ROOT,'data/raw/odds/odds_2026-10-15.csv'))
    return r, o
def match(names, canon):
    cm = {}
    for n in canon: cm.setdefault(norm(n), []).append(n)
    rows = []
    for n in sorted(set(names)):
        k = norm(n); how = None; hit = None
        if k in ALIASES: hit, how = ALIASES[k], 'alias'
        elif k in cm and len(cm[k]) == 1: hit, how = cm[k][0], 'exact_norm'
        elif k in cm: how = 'AMBIGUOUS'
        cand = difflib.get_close_matches(k, list(cm), n=2, cutoff=0.9) if hit is None else []
        rows.append(dict(source_name=n, canonical=hit, method=how or 'UNMATCHED', fuzzy_candidates='; '.join(cm[c][0] for c in cand)))
    return pd.DataFrame(rows)
if __name__ == '__main__':
    r, o = load()
    pm = o[~o.market.isin(TEAM_MARKETS_NONPLAYER) & ~o.market.str.startswith(('DIV_','CUP_E','CUP_W'))]
    pm = pm[~pm.selection.isin(r.name)]
    names = o[~o.market.isin(TEAM_MARKETS_NONPLAYER) & ~o.market.str.startswith(('DIV_','CUP_E','CUP_W'))].selection
    odds_map = match(names, r.name.tolist()); odds_map['source'] = 'odds_book'
    d = pd.read_csv(os.path.join(ROOT,'data/raw/darko/darko_dpm_leaderboard_20261015.csv'))
    dn = d.iloc[:,0].str.replace(r'\s+[A-Z]{2,3}\|.*$','',regex=True)
    dk_map = match(dn, r.name.tolist()); dk_map['source'] = 'darko'
    allm = pd.concat([odds_map, dk_map]); allm.to_csv(os.path.join(ROOT,'data/clean/name_map.csv'), index=False)
    print(allm.groupby(['source','method']).size())
    print(odds_map[odds_map.method!='exact_norm'].to_string())
    print('darko unmatched (not on current ESPN rosters):', (dk_map.method=='UNMATCHED').sum())
