# Akash's Career Radar — Streamlit

## Features
- Mumbai-first job discovery for supply chain, sourcing/procurement, planning/S&OP, inventory, quick commerce and process excellence.
- Finance/sales roles excluded unless clearly relevant to supply chain.
- Match score based on role keywords, skills and geography.
- Statuses: New, Interested, Applied, Shortlisted, Rejected.
- **NA – Expired:** confirm deletion to remove a job from active listings and add a suppression fingerprint so the same listing will not return.
- Listings older than 14 days are moved to Archive.
- Duplicate prevention based on title, company, location and URL.
- Daily GitHub Actions refresh at 08:00 IST; manual workflow dispatch also available.

## Sources
- Adzuna India API: recommended for India/Mumbai jobs. Requires `ADZUNA_APP_ID` and `ADZUNA_APP_KEY`.
- Apify: optional; requires `APIFY_TOKEN`, `APIFY_ACTOR_ID`, and optionally `APIFY_INPUT_JSON`. Adapt the output mapper to the actor you select.
- Arbeitnow and Remotive are supplementary public sources; their geography is not reliably Mumbai-specific.

Free/public sources may have limited India coverage. No results does not mean no jobs exist.

## Local setup
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python refresh_jobs.py
streamlit run app.py
```
Set source credentials as environment variables before refresh.

## Deployment
1. Create a **private GitHub repository** and upload this folder.
2. Add API credentials under GitHub → Settings → Secrets and variables → Actions.
3. Enable Actions and run **Daily job refresh** manually once.
4. Deploy `app.py` to Streamlit Community Cloud using this repository.
5. Keep the repository private because it stores application statuses.

## Important limitations / setup notes
- Scheduled collection runs in GitHub Actions, not in the Streamlit browser session.
- The dashboard's Refresh Jobs button triggers GitHub Actions using the GitHub API. Add `GITHUB_TOKEN` and `GITHUB_REPOSITORY` to Streamlit app secrets. The token needs Actions: write permission; set the repository as `owner/repo`. Never expose tokens in app code.
- JSON storage is suitable for a personal starter project. For multi-user or concurrent editing, migrate to a database such as Supabase.
- The 14-day archive rule currently uses the date a listing entered this tracker (`added_at`), not the employer's original posted date.
- Match scoring is a transparent keyword heuristic, not an AI verdict. AI JD analysis can be added once an API key and desired analysis format are configured.


### Streamlit app secrets for the manual refresh button

In Streamlit Community Cloud → App → Settings → Secrets, add:

```toml
GITHUB_TOKEN = "your-fine-grained-token"
GITHUB_REPOSITORY = "your-github-username/your-private-repo"
```

Grant the token Actions: write permission for this repository. The workflow dispatch currently targets the `main` branch; change `ref` in `app.py` if your default branch differs.
