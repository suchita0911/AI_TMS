# Deploying AI Powered TMS to Render

This app deploys as a 3-service Render Blueprint (`render.yaml`): a managed
PostgreSQL database, the FastAPI backend (Docker), and the nginx/React frontend
(Docker). The frontend proxies `/api` to the backend over Render's private
network, so the app runs **same-origin** — no CORS or frontend changes.

> **Nothing about the running app changed.** The React UI, `nginx.conf`, and all
> backend Python are untouched. The only code edit is the backend Dockerfile
> honoring the platform `$PORT` (falls back to 8000 locally, so `docker-compose`
> still works exactly as before).

## 1. Push to GitHub

```bash
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin main
```

## 2. Create the Blueprint on Render

1. Render Dashboard → **New** → **Blueprint**.
2. Connect the GitHub repo. Render reads `render.yaml` and shows 3 resources.
3. You'll be prompted for the `sync: false` secrets:
   - **FIRST_ADMIN_PASSWORD** — e.g. `Admin@12345` (or anything stronger).
   - **ANTHROPIC_API_KEY** — optional. Leave blank to run with AI fallbacks;
     paste a valid key for live Claude features.
   - **FRONTEND_BASE_URL** — you don't know the URL yet; enter a placeholder
     like `https://frontend.onrender.com` and fix it in step 4.
   - **BACKEND_CORS_ORIGINS** — same; placeholder now, real URL in step 4.
4. Click **Apply**. First build takes a few minutes (Docker images + `npm build`).

## 3. Get your live URL

Open the **frontend** service — its `https://<name>.onrender.com` URL is the app.
Log in with `admin` / the password you set. The backend auto-creates all tables
and seeds the admin on first boot.

## 4. Fix the two URL env vars (recommended)

After the frontend URL is known, set on the **backend** service → Environment:
- `FRONTEND_BASE_URL` = the frontend URL (used as a fallback for email links).
- `BACKEND_CORS_ORIGINS` = the frontend URL.

Save → backend redeploys. (Email links normally follow the request origin, so
this is a correctness safety net, not strictly required for the UI to work.)

## Optional features (config only — no code changes)

These stay **gracefully disabled** until you add their secrets on the backend
service, matching local behavior:

| Feature | Env vars to add |
|---|---|
| Invite/reset **emails** | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_TLS` |
| **Microsoft SSO** | `SSO_TENANT_ID`, `SSO_CLIENT_ID`, `SSO_CLIENT_SECRET`, `SSO_REDIRECT_URI`, `SSO_POST_LOGIN_URL` |
| Live **AI** | valid `ANTHROPIC_API_KEY` |

## Free-tier caveats

- **Postgres (free)** is deleted ~30 days after creation. For anything lasting,
  upgrade the DB to a paid plan (data is preserved on upgrade).
- **Web services (free)** sleep after ~15 min idle; the first request then cold-
  starts in ~50s. Upgrade to keep them always-on.
- **512 MB RAM (free):** idle backend fits fine. Actual **audio/video
  transcription** (faster-whisper) loads a model into RAM and may OOM on free —
  upgrade the backend to a larger plan if you demo that specific feature.
</content>
</invoke>
