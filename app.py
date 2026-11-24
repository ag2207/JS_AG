import streamlit as st
import requests
import re
from html import unescape
from jobs_store import load_store, save_store, delete_job, update_status, active_jobs, refresh_metadata

st.set_page_config(page_title="Akash | Career Radar", page_icon="🎯", layout="wide")

def clean_description(value):
    """Convert source HTML snippets into readable plain text for job cards."""
    value = unescape(str(value or ""))
    value = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", value)
    value = re.sub(r"(?i)<br\s*/?>|</p>|</li>|</h[1-6]>", " ", value)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()
st.title("🎯 Akash's Career Radar")
st.caption("Daily job discovery • CV-based matching • application tracking")
store = load_store()
jobs = active_jobs(store)
meta = refresh_metadata(store)

with st.sidebar:
    st.header("Search & filters")
    search = st.text_input("Keyword")
    loc_filter = st.text_input(
        "Location",
        value="Mumbai",
        placeholder="e.g. Mumbai, Pune, Bengaluru",
        help="Defaults to Mumbai. Clear this field to see jobs across all collected Indian locations."
    ).strip()
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
        branch = st.secrets.get("GITHUB_BRANCH", "main")
        if not token or not repo:
            st.warning("To enable this button, add GITHUB_TOKEN and GITHUB_REPOSITORY to Streamlit app secrets. See README.")
        else:
            response = requests.post(
                f"https://api.github.com/repos/{repo}/actions/workflows/daily_refresh.yml/dispatches",
                headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
                json={"ref": branch}, timeout=20
            )
            if response.status_code == 204:
                st.success("Refresh workflow started. New listings will appear after GitHub Actions finishes and commits the updated tracker.")
            else:
                detail = (response.text or "").strip().replace("\\n", " ")[:400]
                st.error(
                    f"Could not start refresh (HTTP {response.status_code}). "
                    f"Check GITHUB_REPOSITORY, GITHUB_BRANCH, workflow path and token permissions. "
                    f"GitHub response: {detail or 'No additional details.'}"
                )
with y:
    st.link_button("Streamlit deployment guide", "https://docs.streamlit.io/deploy/streamlit-community-cloud")

st.info("Automatic collection is scheduled daily at 08:00 IST through GitHub Actions. The Refresh Jobs button triggers the same workflow when GitHub credentials are configured.")
st.divider()
filtered=[]
for j in jobs:
    text = " ".join([j.get("title",""),j.get("company",""),j.get("description",""),j.get("location","")]).lower()
    if search and search.lower() not in text: continue
    if loc_filter and loc_filter.lower() not in str(j.get("location", "")).lower(): continue
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
            desc=clean_description(j.get("description", ""))
            st.write(desc[:450]+("…" if len(desc)>450 else ""))
            if j.get("match_reasons"): st.caption("Match signals: "+" · ".join(j["match_reasons"][:4]))
            url = str(j.get("url") or "").strip()
            if url.startswith(("https://", "http://")):
                st.link_button("View / Apply ↗", url)
            else:
                st.caption("Application link unavailable")
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
