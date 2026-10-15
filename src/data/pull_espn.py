import json, pandas as pd, os
from .common import polite_get, save_raw, ROOT
B = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
def teams():
    r = polite_get(B + "/teams", "espn", 0.5)
    return [t["team"] for t in r.json()["sports"][0]["leagues"][0]["teams"]]
def run():
    T = teams(); sched = []; ros = []
    for t in T:
        tid = t["id"]
        r = polite_get(f"{B}/teams/{tid}/schedule", "espn", 0.5, params={"season": 2027, "seasontype": 2})
        j = r.json(); save_raw("espn", f"schedule_{t['abbreviation']}.json", r.text, r.url, len(j.get("events", [])))
        for e in j.get("events", []):
            c = e["competitions"][0]; cs = {x["homeAway"]: x["team"]["abbreviation"] for x in c["competitors"]}
            sched.append(dict(id=e["id"], date=e["date"], home=cs.get("home"), away=cs.get("away"), note=json.dumps(c.get("notes", [])), neutral=c.get("neutralSite")))
        r = polite_get(f"{B}/teams/{tid}/roster", "espn", 0.5)
        j = r.json(); save_raw("espn", f"roster_{t['abbreviation']}.json", r.text, r.url, len(j.get("athletes", [])))
        for a in j.get("athletes", []):
            ros.append(dict(team=t["abbreviation"], espn_id=a["id"], name=a["fullName"], pos=a.get("position", {}).get("abbreviation"),
                            age=a.get("age"), height=a.get("displayHeight"), weight=a.get("displayWeight"), exp=a.get("experience", {}).get("years"),
                            college=(a.get("college") or {}).get("name"), jersey=a.get("jersey"),
                            status=(a.get("status") or {}).get("name"), injuries=json.dumps(a.get("injuries", [])), dob=a.get("dateOfBirth")))
    s = pd.DataFrame(sched).drop_duplicates("id"); s.to_csv(os.path.join(ROOT, "data/clean/schedule_espn.csv"), index=False)
    p = pd.DataFrame(ros); p.to_csv(os.path.join(ROOT, "data/clean/rosters_espn.csv"), index=False)
    r = polite_get(B.replace("/apis/site/v2", "/apis/site/v2") + "/injuries", "espn", 0.5)
    save_raw("espn", "injuries.json", r.text, r.url, len(r.json().get("injuries", [])))
    return s, p
if __name__ == "__main__":
    s, p = run(); print(s.shape, p.shape); print(p.groupby("team").size().describe())
