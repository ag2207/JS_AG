import os, json, re, hashlib, requests
from datetime import datetime, timezone, timedelta
from jobs_store import load_store, save_store, fingerprint, now_iso

ROLE_TERMS=["supply chain","supply planning","s&op","sourcing","procurement","inventory","quick commerce","process excellence","operations excellence","demand planning","materials planning"]
EXCLUDE=["sales","investment banking","accountant","financial analyst","relationship manager","insurance sales","equity research"]
SKILLS=["sap mm","power bi","excel","mrp","bom","otif","vendor management","inventory optimisation","six sigma","quick commerce","forecasting","manufacturing"]
def norm(x): return re.sub(r"\\s+"," ",(x or "").strip())
def classify(t):
 t=t.lower()
 if any(x in t for x in ["sourcing","procurement","vendor"]): return "Sourcing / Procurement"
 if any(x in t for x in ["s&op","supply planning","demand planning","material planning"]): return "Planning / S&OP"
 if any(x in t for x in ["quick commerce","dark store","ecommerce","e-commerce"]): return "Quick Commerce"
 if any(x in t for x in ["inventory","warehouse","stock"]): return "Inventory"
 if any(x in t for x in ["process excellence","continuous improvement","lean","transformation"]): return "Process Excellence"
 if "supply chain" in t or "logistics" in t: return "Supply Chain"
 return "Other"
def score(j):
 t=" ".join([j.get("title",""),j.get("description",""),j.get("company","")]).lower()
 title=j.get("title","").lower(); ntitle=sum(x in title for x in ROLE_TERMS); nbody=sum(x in t for x in ROLE_TERMS); nskills=sum(x in t for x in SKILLS)
 val=35+min(30,ntitle*12)+min(20,nbody*3)+min(15,nskills*2)
 loc=j.get("location","").lower(); reasons=[]
 if any(x in loc for x in ["mumbai","thane","navi mumbai","pune","india"]): val+=10; reasons.append("Target geography")
 reasons += [x.title() for x in ROLE_TERMS if x in title]
 if "mba" in t: reasons.append("MBA qualification")
 return min(99,val),list(dict.fromkeys(reasons))
def relevant(j):
 t=(j.get("title","")+" "+j.get("description","")).lower()
 if any(x in t for x in EXCLUDE) and not any(x in t for x in ["supply chain","procurement","sourcing","planning"]): return False
 return any(x in t for x in ROLE_TERMS)
def adzuna():
 aid,key=os.getenv("ADZUNA_APP_ID"),os.getenv("ADZUNA_APP_KEY")
 if not aid or not key: return []
 out=[]
 for q in ["supply chain manager","procurement manager","supply planning","process excellence"]:
  try:
   data=requests.get("https://api.adzuna.com/v1/api/jobs/in/search/1",params={"app_id":aid,"app_key":key,"results_per_page":50,"what":q,"where":"Mumbai","sort_by":"date"},timeout=25).json()
   for x in data.get("results",[]): out.append({"title":x.get("title"),"company":(x.get("company") or {}).get("display_name"),"location":(x.get("location") or {}).get("display_name","Mumbai"),"description":x.get("description",""),"url":x.get("redirect_url"),"posted_date":(x.get("created") or "")[:10],"source":"Adzuna"})
  except Exception as e: print("Adzuna:",e)
 return out
def arbeitnow():
 try:
  data=requests.get("https://www.arbeitnow.com/api/job-board-api",timeout=25).json()
  return [{"title":x.get("title"),"company":x.get("company_name"),"location":x.get("location") or "Not specified","description":x.get("description",""),"url":x.get("url"),"posted_date":str(x.get("created_at",""))[:10],"source":"Arbeitnow"} for x in data.get("data",[])]
 except Exception as e: print("Arbeitnow:",e); return []
def remotive():
 try:
  data=requests.get("https://remotive.com/api/remote-jobs",params={"search":"supply chain"},timeout=25).json()
  return [{"title":x.get("title"),"company":x.get("company_name"),"location":x.get("candidate_required_location") or "Remote","description":x.get("description",""),"url":x.get("url"),"posted_date":str(x.get("publication_date",""))[:10],"source":"Remotive"} for x in data.get("jobs",[])]
 except Exception as e: print("Remotive:",e); return []
def apify():
 token,actor=os.getenv("APIFY_TOKEN"),os.getenv("APIFY_ACTOR_ID")
 if not token or not actor: return []
 try:
  inp=json.loads(os.getenv("APIFY_INPUT_JSON",'{"searches":[{"query":"supply chain manager","location":"Mumbai, India"}]}'))
  r=requests.post(f"https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items",params={"token":token,"format":"json","clean":"true"},json=inp,timeout=120); r.raise_for_status()
  out=[]
  for x in r.json():
   out.append({"title":x.get("title") or x.get("positionName"),"company":x.get("company") or x.get("companyName"),"location":x.get("location") or x.get("jobLocation","Not specified"),"description":x.get("description") or x.get("jobDescription",""),"url":x.get("url") or x.get("jobUrl") or x.get("applyUrl"),"posted_date":str(x.get("postedAt") or x.get("publishedAt") or "")[:10],"source":"Apify"})
  return out
 except Exception as e: print("Apify:",e); return []
def main():
 s=load_store(); raw=adzuna()+arbeitnow()+remotive()+apify()
 existing={fingerprint(j):j for j in s["jobs"]}; suppressed={x["fingerprint"] for x in s["suppressed"] if "fingerprint" in x}; added=0
 for j in raw:
  j={k:norm(v) if isinstance(v,str) else v for k,v in j.items()}
  if not j.get("title") or not j.get("url") or not relevant(j): continue
  j["role_family"]=classify(j["title"]+" "+j.get("description","")); j["match_score"],j["match_reasons"]=score(j)
  j["experience_text"]="Not specified"; j["experience_max"]=None
  fp=fingerprint(j)
  if fp in suppressed: continue
  if fp in existing:
   existing[fp].update({k:v for k,v in j.items() if k!="status"}); continue
  j["id"]=hashlib.sha1((fp+str(j.get("posted_date"))).encode()).hexdigest()[:14]; j["status"]="New"; j["added_at"]=now_iso()
  s["jobs"].append(j); existing[fp]=j; added+=1
 cutoff=datetime.now(timezone.utc)-timedelta(days=14); active=[]
 for j in s["jobs"]:
  try:
   dt=datetime.fromisoformat(j.get("added_at","").replace("Z","+00:00"))
   if dt<cutoff: j["archive_reason"]="Older than 14 days"; j["archived_at"]=now_iso(); s["archive"].append(j)
   else: active.append(j)
  except Exception: active.append(j)
 s["jobs"]=active; s["meta"].update({"last_refresh":now_iso(),"last_added":added,"sources_checked":["Adzuna","Arbeitnow","Remotive","Apify"]})
 save_store(s); print(f"Refresh complete: added {added}, active {len(active)}, archived {len(s['archive'])}")
if __name__=="__main__": main()
