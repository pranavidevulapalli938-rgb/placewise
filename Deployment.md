# PlaceWise — Deployment Guide

## Architecture
- **Frontend**: React + Vite → deploy on Vercel (free)
- **Backend**: FastAPI → deploy on Render (free)
- **Database**: PostgreSQL → Render managed DB or Neon (free)
- **Extension**: Chrome only, load manually

---

## Step 1 — Push to GitHub

Create two repos (or one monorepo):
```
placewise/
  backend/        ← Python FastAPI
  frontend/       ← React Vite
  extension/      ← Chrome extension
  interview-ai/   ← Node.js
```

Make sure these files are in `.gitignore`:
```
backend/.env
frontend/.env.local
node_modules/
__pycache__/
*.pyc
.venv/
venv/
```

---

## Step 2 — Deploy Database (Neon — free PostgreSQL)

1. Go to https://neon.tech → Sign up free
2. Create project: `placewise`
3. Copy the **connection string** — looks like:
   `postgresql://user:password@ep-xxxx.us-east-2.aws.neon.tech/neondb?sslmode=require`
4. Run your migration scripts once (see Step 4)

---

## Step 3 — Deploy Backend (Render)

1. Go to https://render.com → Connect GitHub
2. New → Web Service → select your `backend/` folder
3. Settings:
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add ALL these environment variables in Render dashboard:
   ```
   SECRET_KEY          = (generate a random 64-char string)
   ALGORITHM           = HS256
   ACCESS_TOKEN_EXPIRE_MINUTES = 60
   DATABASE_URL        = (paste Neon connection string)
   FRONTEND_URL        = https://your-app.vercel.app
   GEMINI_API_KEY      = (your key)
   SMTP_HOST           = smtp.gmail.com
   SMTP_PORT           = 587
   SMTP_USER           = your-email@gmail.com
   SMTP_PASS           = (16-char Gmail App Password)
   SMTP_FROM           = PlaceWise <your-email@gmail.com>
   GOOGLE_CLIENT_ID    = (from Google Cloud Console)
   GOOGLE_CLIENT_SECRET = (from Google Cloud Console)
   GOOGLE_REDIRECT_URI = https://your-backend.onrender.com/gmail/callback
   ```
5. Deploy. Note your URL: `https://placewise-backend.onrender.com`

---

## Step 4 — Run DB Migrations on Production

After backend is deployed, run once via Render Shell:
```bash
python fix_db.py
python migrate.py
```
Or connect to Neon directly with psql and run the SQL manually.

---

## Step 5 — Deploy Frontend (Vercel)

1. Go to https://vercel.com → Connect GitHub
2. New Project → select your `frontend/` folder
3. Framework: **Vite**
4. Add environment variable:
   ```
   VITE_API_URL = https://your-backend.onrender.com
   ```
5. Deploy. Note your URL: `https://placewise.vercel.app`

### IMPORTANT: Update your frontend code
Right now your frontend likely has `http://localhost:8000` hardcoded.
Replace ALL instances with `import.meta.env.VITE_API_URL` like:

```javascript
// Instead of:
const res = await fetch("http://localhost:8000/applications")

// Use:
const res = await fetch(`${import.meta.env.VITE_API_URL}/applications`)
```

---

## Step 6 — Update Google OAuth Redirect URI

1. Go to Google Cloud Console → APIs & Services → Credentials
2. Edit your OAuth 2.0 Client ID
3. Add to Authorized redirect URIs:
   ```
   https://your-backend.onrender.com/gmail/callback
   ```
4. Add to Authorized JavaScript origins:
   ```
   https://your-app.vercel.app
   ```

---

## Step 7 — Update Extension for Production

In `extension/background.js`, change the API URL:
```javascript
// Change from:
const API_BASE = "http://localhost:8000"

// To:
const API_BASE = "https://your-backend.onrender.com"
```

---

## Gmail OAuth — Public vs Testing Mode

### Testing Mode (current — max 100 users)
- Only manually added test users can connect Gmail
- No Google verification needed
- Fine for personal use or small beta

### Production Mode (for public launch)
- Anyone can connect their Gmail
- Requires Google verification:
  1. Add Privacy Policy page to your frontend
  2. Add Terms of Service page
  3. Submit app for Google review (1–4 weeks)
  4. Google audits your OAuth scopes

### Privacy Policy (required for verification)
Add a `/privacy` route to your frontend with text like:
> PlaceWise uses Gmail read-only access to detect job application emails.
> We never store email content — only company name, role, and application status.
> Your data is never shared with third parties.

---

## CORS — Already Configured?

Make sure `FRONTEND_URL` in backend `.env` / Render env vars matches
your exact Vercel URL. The FastAPI CORS middleware uses this to allow requests.

---

## Free Tier Limitations

| Service | Free Limit | Notes |
|---------|-----------|-------|
| Render  | 750 hrs/month, spins down after 15min inactivity | First request after sleep = slow |
| Neon    | 0.5 GB storage, 1 project | Enough for ~10k applications |
| Vercel  | Unlimited deploys, 100GB bandwidth | No limits for this app |

### Fix Render Cold Start (optional)
Add this to frontend to ping backend on app load:
```javascript
// In App.jsx useEffect
fetch(`${import.meta.env.VITE_API_URL}/health`).catch(() => {})
```

And add a health endpoint to FastAPI:
```python
@app.get("/health")
def health():
    return {"status": "ok"}
```

---

## Quick Checklist

- [ ] Push code to GitHub (without .env files)
- [ ] Set up Neon database, copy connection string
- [ ] Deploy backend on Render, set all env vars
- [ ] Run DB migrations
- [ ] Deploy frontend on Vercel, set VITE_API_URL
- [ ] Update Google OAuth redirect URIs
- [ ] Update extension background.js API URL
- [ ] Test login, Gmail sync, add application