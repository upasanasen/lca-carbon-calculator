# Deploying the LCA Carbon Calculator

Goal: a live, shareable URL on **Streamlit Community Cloud** (free), deployed
from a **public GitHub repo**. Two stages: (1) push to GitHub, (2) deploy.

Steps and button labels below were checked against Streamlit's docs in June 2026.
The UI changes occasionally — if a label differs, follow the on-screen prompts.

---

## Stage 1 — Put the code on GitHub

You only need to do this once. Run it on **your Mac**, in Terminal:

```bash
cd "/Users/abc/Documents/Claude/Projects/project planner/lca-carbon-calculator"
bash setup-git.sh
```

That initialises git and makes the first commit locally. Then create the GitHub
repo and push. **Easiest if you have the GitHub CLI** (`gh`):

```bash
gh repo create lca-carbon-calculator --public --source=. --remote=origin --push
```

**Or** without the CLI:
1. On github.com, create a new **empty** repo named `lca-carbon-calculator`
   (no README, no .gitignore, no license).
2. Copy its URL and run:
   ```bash
   git remote add origin https://github.com/<your-username>/lca-carbon-calculator.git
   git push -u origin main
   ```

> Public is recommended: recruiters can see the code, and the free Streamlit tier
> deploys public repos with no extra steps. (Private also works, but you must
> authorise Streamlit to access private repos when connecting GitHub.)

---

## Stage 2 — Deploy on Streamlit Community Cloud

1. Go to **https://share.streamlit.io** and sign in with your **GitHub** account.
2. When prompted, **authorise / connect GitHub** so Streamlit can read your repos
   and auto-update the app when you push.
3. Click **"Create app"** (upper-right).
4. Choose **"deploy a public app from GitHub"** and fill in:
   - **Repository:** `<your-username>/lca-carbon-calculator`
   - **Branch:** `main`
   - **Main file path:** `app.py`
5. (Optional) Set a memorable **App URL** subdomain, e.g.
   `lca-carbon-calculator.streamlit.app`.
6. Click **Deploy**. First build takes ~2–3 minutes while it installs
   `requirements.txt`.

That's it — you'll get a public `…streamlit.app` link to share.

---

## What to expect once live

- **ÖKOBAUDAT search works** — the app makes outbound HTTPS calls to the public
  soda4LCA API; no key needed.
- **The openLCA tab will show "not found"** — that's expected. openLCA is a
  local-only desktop integration; it does not run on a server. The hosted data
  source is ÖKOBAUDAT (Inventory tab).
- **No secrets required** — EC3/openEPD is not enabled, so there is nothing to
  configure under app settings → Secrets. (If you add EC3 later, put the API key
  in the app's **Secrets**, not in the repo.)
- **Generic seed factors are indicative only** — fine for a demo; the UI labels
  them, and the README explains it.

## Updating the live app

Every push to `main` redeploys automatically:

```bash
git add -A
git commit -m "..."
git push
```

## Quick troubleshooting

- **App won't start / ModuleNotFoundError** → confirm `requirements.txt` is at the
  repo root (it is) and `Main file path` is exactly `app.py`.
- **ÖKOBAUDAT errors in the live app** → usually a transient API/network issue;
  the app falls back to generic/manual factors and shows a message. Retry.
- **Want it private** → keep the repo private and, when connecting GitHub to
  Streamlit, grant access to private repositories.

## Sources
- Deploy your app on Community Cloud — https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
- Connect your GitHub account — https://docs.streamlit.io/deploy/streamlit-community-cloud/get-started/connect-your-github-account
