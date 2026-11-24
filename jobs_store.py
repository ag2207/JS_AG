import json, hashlib
from pathlib import Path
from datetime import datetime, timezone

PATH=Path("data/jobs.json")
def now_iso(): return datetime.now(timezone.utc).isoformat()
def empty(): return {"jobs":[],"archive":[],"suppressed":[],"meta":{"last_refresh":None}}
def load_store():
    PATH.parent.mkdir(exist_ok=True)
    if not PATH.exists(): return empty()
    try:
        d=json.loads(PATH.read_text(encoding="utf-8"))
        for k,v in empty().items(): d.setdefault(k,v)
        return d
    except Exception: return empty()
def save_store(d):
    PATH.parent.mkdir(exist_ok=True)
    tmp=PATH.with_suffix(".tmp"); tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding="utf-8"); tmp.replace(PATH)
def fingerprint(j):
    raw="|".join((j.get(k) or "").strip().lower() for k in ["title","company","location","url"])
    return hashlib.sha256(raw.encode()).hexdigest()
def active_jobs(s): return s.get("jobs",[])
def refresh_metadata(s): return s.get("meta",{})
def update_status(s,jid,status):
    for j in s["jobs"]:
        if j.get("id")==jid: j["status"]=status; j["updated_at"]=now_iso(); return
def delete_job(s,jid):
    kept=[]
    for j in s.get("jobs",[]):
        if j.get("id")==jid:
            s.setdefault("suppressed",[]).append({"fingerprint":fingerprint(j),"deleted_at":now_iso(),"reason":"NA – Expired"})
        else: kept.append(j)
    s["jobs"]=kept
