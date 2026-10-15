import pandas as pd, os, json
from .teams import *
from .common import ROOT
b = pd.read_csv(os.path.join(ROOT,'data/clean/schedule_raw_bbref.csv'))
b['date'] = pd.to_datetime(b['Date'], format='%a, %b %d, %Y')
b['away'] = b['Visitor/Neutral'].map(NAME2ABBR); b['home'] = b['Home/Neutral'].map(NAME2ABBR)
assert b.away.notna().all() and b.home.notna().all()
b['cup_group'] = b['Notes'].fillna('').str.contains('NBA Cup')
b['start_et'] = b['Start (ET)']; b['arena'] = b['Arena']
g = b[['date','start_et','away','home','cup_group','arena']].sort_values(['date','start_et','home']).reset_index(drop=True)
g['game_no'] = range(1, len(g)+1)
# long format for rest/B2B (calendar-day basis, ET date as listed by bbref)
L = pd.concat([g.assign(team=g.home, opp=g.away, is_home=1), g.assign(team=g.away, opp=g.home, is_home=0)]).sort_values(['team','date','start_et'])
L['prev'] = L.groupby('team')['date'].shift(1); L['rest_days'] = (L['date']-L['prev']).dt.days-1
L['b2b'] = (L['rest_days']==0).astype(int)
L['b2b_second_of_pair'] = L['b2b']
g.to_csv(os.path.join(ROOT,'data/clean/schedule_games.csv'), index=False)
L.drop(columns=['prev']).to_csv(os.path.join(ROOT,'data/clean/schedule_team_games.csv'), index=False)
# validation vs ESPN
e = pd.read_csv(os.path.join(ROOT,'data/clean/schedule_espn.csv')); e['home']=e.home.replace(ESPN_FIX); e['away']=e.away.replace(ESPN_FIX)
e['d'] = pd.to_datetime(e['date'], utc=True).dt.tz_convert('US/Eastern').dt.date
gg = g.assign(d=g.date.dt.date)
m = gg.merge(e, on=['d','home','away'], how='outer', indicator=True)
res = {'bbref_games': len(g), 'espn_games': len(e), 'matched_on_date_home_away': int((m._merge=='both').sum()),
       'bbref_only': int((m._merge=='left_only').sum()), 'espn_only': int((m._merge=='right_only').sum()),
       'cup_group_games': int(g.cup_group.sum()),
       'games_per_team_min_max': [int(L.groupby('team').size().min()), int(L.groupby('team').size().max())],
       'cup_games_per_team_min_max': [int(L[L.cup_group].groupby('team').size().min()), int(L[L.cup_group].groupby('team').size().max())],
       'b2b_per_team_min_max_mean': [int(L.groupby('team').b2b.sum().min()), int(L.groupby('team').b2b.sum().max()), float(L.groupby('team').b2b.sum().mean())],
       'first': str(g.date.min().date()), 'last': str(g.date.max().date())}
print(json.dumps(res, indent=1)); json.dump(res, open(os.path.join(ROOT,'data/clean/schedule_validation.json'),'w'), indent=1)
if (m._merge!='both').any(): print(m[m._merge!='both'][['d','home','away','_merge']].head(10))
