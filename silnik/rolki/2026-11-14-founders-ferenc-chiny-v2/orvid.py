"""Generowanie ujęć przez OpenRouter Video API. Użycie: python3 orvid.py jobs.json"""
import json, sys, time, os, urllib.request
KEY = open(os.path.expanduser("~/.or_key")).read().strip()
H = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
def call(method, url, body=None, raw=False):
    req = urllib.request.Request("https://openrouter.ai" + url, data=json.dumps(body).encode() if body else None, headers=H, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as r: return r.read() if raw else json.load(r)
    except urllib.error.HTTPError as e: return {"error": e.read().decode()[:500]}
jobs = json.load(open(sys.argv[1])); pend = {}
for j in jobs:
    out = f"broll/{j['name']}.mp4"
    if os.path.exists(out): continue
    r = call("POST", "/api/v1/videos", j["req"]); print(j["name"], "submit", r.get("id"), r.get("error", ""), flush=True)
    if "id" in r: pend[r["id"]] = j
cost = 0
while pend:
    time.sleep(10)
    for jid, j in list(pend.items()):
        r = call("GET", f"/api/v1/videos/{jid}")
        st = r.get("status")
        if st == "completed":
            data = call("GET", f"/api/v1/videos/{jid}/content", raw=True)
            open(f"broll/{j['name']}.mp4", "wb").write(data); c = (r.get("usage") or {}).get("cost", 0); cost += c or 0
            print(j["name"], "done", len(data), "B", "$", c, flush=True); del pend[jid]
        elif st in ("failed", "cancelled", "expired") or "error" in r:
            print(j["name"], st, r.get("error"), flush=True); del pend[jid]
print("total $", round(cost, 3))
