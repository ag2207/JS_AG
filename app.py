import streamlit as st
import requests
from jobs_store import load_store, save_store, delete_job, update_status, active_jobs, refresh_metadata

st.set_page_config(page_title="Akash | Career Radar", page_icon="🎯", layout="wide")
st.title("🎯 Akash's Career Radar")
st.caption("Daily job discovery • CV-based matching • application tracking")
store = load_store()
jobs = active_jobs(store)
meta = refresh_metadata(store)

with st.sidebar:
    st.header("Search & filters")
    search = st.text_input("Keyword")
    locations = sorted({j.get("location", "Not specified") for j in jobs})
    loc_filter = st.multiselect("Location", locations, default=[x for x in locations if "mumbai" in x.lower()])
    families = ["Supply Chain","Sourcing / Procurement","Planning / S&OP","Inventory","Quick Commerce","Process Excellence","Other"]
    family_filter = st.multiselect("Role family", families, default=families[:-1])
    min_match = st.slider("Minimum match", 0, 100, 55, 5)
    status_filter = st.multiselect("Status", ["New","Interested","Applied","Shortlisted","Rejected"], default=["New","Interested","Applied","Shortlisted","Rejected"])

a,b,c,d = st.columns(4)
a.metric("Active jobs", len(jobs))
b.metric("New", sum(j.get("status","New")=="New" for j in jobs))
c.metric("Interested / Applied", sum(j.get("status") in ["Interested","Applied"] for j in jobs))
d.metric("Last refresh", (meta.get("last_refresh") or "Not yet")[:16].replace("T"," "))

x,y = st.columns([1,1])
with x:
    if st.button("🔄 Refresh jobs now", type="primary", use_container_width=True):
        token = st.secrets.get("GITHUB_TOKEN", "")
        repo = st.secrets.get("GITHUB_REPOSITORY", "")
        if not token or not repo:
            st.warning("To enable this button, add GITHUB_TOKEN and GITHUB_REPOSITORY to Streamlit app secrets. See README.")
        else:
            response = requests.post(
                f"https://api.github.com/repos/{repo}/actions/workflows/daily_refresh.yml/dispatches",
                headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
                json={"ref": "app.py"}, timeout=20
            )
            if response.status_code == 204:
                st.success("Refresh workflow started. New listings will appear after GitHub Actions finishes and commits the updated tracker.")
            else:
                st.error(f"Could not start refresh (HTTP {response.status_code}). Check token permissions, repository name and default branch.")
with y:
    st.link_button("Streamlit deployment guide", "https://docs.streamlit.io/deploy/streamlit-community-cloud")

st.info("Automatic collection is scheduled daily at 08:00 IST through GitHub Actions. The Refresh Jobs button triggers the same workflow when GitHub credentials are configured.")
st.divider()
filtered=[]
for j in jobs:
    text = " ".join([j.get("title",""),j.get("company",""),j.get("description",""),j.get("location","")]).lower()
    if search and search.lower() not in text: continue
    if loc_filter and j.get("location") not in loc_filter: continue
    if j.get("role_family","Other") not in family_filter: continue
    if int(j.get("match_score",0)) < min_match: continue
    if j.get("status","New") not in status_filter: continue
    filtered.append(j)

st.subheader(f"Job listings ({len(filtered)})")
if not filtered:
    st.info("No matching jobs yet. Configure at least one source and run a refresh.")
for j in sorted(filtered,key=lambda z:(int(z.get("match_score",0)),z.get("posted_date","")),reverse=True):
    with st.container(border=True):
        l,r=st.columns([5,1])
        with l:
            st.markdown(f"**{j.get('title','Untitled')}**")
            st.write(f"{j.get('company','Unknown company')} · {j.get('location','Location not listed')}")
            st.caption(f"{j.get('role_family','Other')} · {j.get('experience_text','Experience not specified')} · Posted {j.get('posted_date','Unknown')}")
            desc=j.get("description","")
            st.write(desc[:450]+("…" if len(desc)>450 else ""))
            if j.get("match_reasons"): st.caption("Match signals: "+" · ".join(j["match_reasons"][:4]))
            if j.get("url"): st.markdown(f"[View / Apply ↗]({j['url']})")
        with r:
            st.metric("Match",f"{j.get('match_score',0)}%")
            choices=["New","Interested","Applied","Shortlisted","Rejected","NA – Expired"]
            current=j.get("status","New")
            choice=st.selectbox("Status",choices,index=choices.index(current) if current in choices else 0,key=f"s_{j['id']}")
            if choice=="NA – Expired":
                st.warning("This permanently removes the job from the active tracker.")
                if st.button("Confirm delete",key=f"d_{j['id']}",type="primary"):
                    delete_job(store,j["id"]); save_store(store); st.rerun()
            elif choice!=current:
                update_status(store,j["id"],choice); save_store(store); st.rerun()

with st.expander("NA deletion and expiry rules"):
    st.write("Confirming NA – Expired removes the job from active listings and saves a suppression fingerprint so the same listing is not re-imported. Jobs older than 14 days are moved to Archive by the scheduled refresh.")
