# PlaceWise 🎓

**A smart placement tracker for students** — track every job application, prep for interviews with AI, and never miss an opportunity.

🌐 **Live Demo:** [placewise-azure.vercel.app](https://placewise-azure.vercel.app)

> Built as a group project by three contributors — see [Team](#-team) below.

---

## ✨ Features

### 📋 Dashboard
- Add, search, and filter job applications by company, role, and status
- Inline status updates (Applied → OA Received → Interview → Selected/Rejected)
- Per-application notes
- Direct links to job postings and Gmail threads
- Stats overview: Total, Active, Selected, Rejected

### 🗂️ Kanban Board
- Drag-and-drop cards across status columns
- Real-time sync with the backend on every drop
- Visual pipeline view of your entire job hunt

### 🤖 AI Interview Prep
- **HR Questions** — Generate company/role-specific behavioural questions; evaluate answers using the STAR method with a score, breakdown, and improvement tips
- **Coding Problems** — Practice DSA problems with an AI hint chat and code evaluation (correctness, time/space complexity)
- **Resume Analyzer** — Paste your resume and a job description; get keyword match scores, missing keywords, and tailored suggestions

### 📊 Analytics
- Status distribution pie chart
- Applications over time (line chart)
- Top companies applied to (bar chart)
- KPIs: Total applications, active pipeline, success rate

### 📧 Gmail Auto-Sync
- Connect Gmail via OAuth 2.0
- Auto-detect job application emails and add them to your tracker
- Never manually enter a company you already emailed

### 🧩 Chrome Extension
- One-click job saving while browsing Naukri, LinkedIn, Internshala, Indeed, or Wellfound
- Extension login syncs with your PlaceWise account (JWT-based)
- Download directly from the dashboard

---

## 👥 Team

| Contributor | GitHub | Responsibilities |
|-------------|--------|-----------------|
| Pranavi Devulapalli | [@pranavidevulapalli938-rgb](https://github.com/pranavidevulapalli938-rgb) | Frontend (React), Gmail parser & OAuth integration |
| Isha | [@Isha0816](https://github.com/Isha0816) | FastAPI backend, Chrome extension |
| Nayana Reddy K | [@NayanaReddyK](https://github.com/NayanaReddyK) | AI placement server, Gemini API integration |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, Vite 7, Tailwind CSS 4 |
| Routing | React Router v7 |
| Charts | Recharts |
| Drag & Drop | @hello-pangea/dnd |
| HTTP Client | Axios |
| Icons | Lucide React |
| Backend | Python, FastAPI |
| Auth | JWT (HS256), Google OAuth 2.0 |
| Database | PostgreSQL (Neon) |
| Email | SMTP (Gmail App Password) |
| AI Server | Node.js + Gemini API |
| Extension | Chrome Manifest v3 |
| Deployment | Vercel (frontend), Render (backend) |

---

## 🏗️ Project Structure

```
placewise/
├── frontend/               # React + Vite app (pranavidevulapalli938-rgb)
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Kanban.jsx
│   │   │   ├── InterviewPrep.jsx
│   │   │   ├── Analytics.jsx
│   │   │   ├── Login.jsx
│   │   │   ├── Register.jsx
│   │   │   └── ResetPassword.jsx
│   │   ├── components/
│   │   │   └── Layout.jsx
│   │   ├── context/
│   │   │   └── AuthContext.jsx
│   │   ├── App.jsx
│   │   └── main.jsx
│   └── package.json
│
├── backend/                # FastAPI Python app (Isha0816)
│   ├── main.py
│   ├── auth.py
│   ├── models.py
│   ├── schemas.py
│   ├── database.py
│   ├── gmail_parser.py     # (pranavidevulapalli938-rgb)
│   ├── requirements.txt
│   └── .env
│
├── extension/              # Chrome extension (Isha0816)
│   ├── manifest.json
│   ├── background.js
│   ├── popup.js
│   └── popup.html
│
└── ai_placement/           # Node.js AI server (NayanaReddyK)
    └── server/
        └── server.js
```

---

## 🚀 Local Development

### Prerequisites
- Node.js 18+
- Python 3.10+
- PostgreSQL (local or [Neon](https://neon.tech))

### 1. Clone the repository

```bash
git clone https://github.com/pranavidevulapalli938-rgb/placewise.git
cd placewise
```

### 2. Backend setup

```bash
cd backend
python -m venv venv

# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

Create a `.env` file in `backend/`:

```env
SECRET_KEY=your-64-char-random-secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

DATABASE_URL=postgresql://user:password@localhost:5432/placewise

FRONTEND_URL=http://localhost:5173

GEMINI_API_KEY=your-gemini-api-key

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-16-char-app-password
SMTP_FROM=PlaceWise <your-email@gmail.com>

GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/gmail/callback
```

Run the backend:
```bash
uvicorn main:app --reload --port 8000
```

### 3. AI server setup

```bash
cd ai_placement/server
npm install
node server.js
# Runs on port 3001
```

### 4. Frontend setup

```bash
cd frontend
npm install
```

Create a `.env.development` file:

```env
VITE_API_URL=http://localhost:8000
VITE_AI_URL=http://localhost:3001
```

Run the frontend:
```bash
npm run dev
# Runs on http://localhost:5173
```

### 5. Quick start (Windows)

A batch script is included to launch all three servers at once:

```bat
start_placewise.bat
```

---

## 🔌 Chrome Extension

1. From the Dashboard, click **Download Extension**
2. Unzip the downloaded file
3. Open Chrome → `chrome://extensions`
4. Enable **Developer mode** (top-right toggle)
5. Click **Load unpacked** → select the unzipped folder
6. The PlaceWise icon appears in your toolbar
7. Browse a job board and click the icon to save jobs instantly

> **Supported job boards:** Naukri, LinkedIn, Internshala, Indeed, Wellfound

---

## ☁️ Deployment

See [Deployment.md](./Deployment.md) for the full step-by-step guide. Summary:

| Service | Purpose | Free Tier |
|---------|---------|-----------|
| [Vercel](https://vercel.com) | Frontend hosting | Unlimited deploys |
| [Render](https://render.com) | Backend hosting | 750 hrs/month |
| [Neon](https://neon.tech) | PostgreSQL | 0.5 GB |

**Key environment variables for production:**

```env
# Vercel (Frontend)
VITE_API_URL=https://your-backend.onrender.com
VITE_AI_URL=https://your-ai-server.onrender.com

# Render (Backend) — set all .env variables using production URLs
FRONTEND_URL=https://your-app.vercel.app
GOOGLE_REDIRECT_URI=https://your-backend.onrender.com/gmail/callback
```

---

## 🔐 Authentication

- **Register** → email + password stored with bcrypt hash
- **Login** → returns JWT → stored in `localStorage` (remember me) or `sessionStorage`
- **Forgot Password** → email link with 30-minute expiry token
- **Google OAuth 2.0** → Gmail connect for email auto-sync

---

## 📄 License

This project is licensed under the MIT License — see [LICENSE](./LICENSE) for details.
