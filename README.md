# FinTrack — Modern AI Personal Finance Tracker

A high-performance personal finance management platform built with **React (Vite) + Redux Toolkit** on the frontend, a high-throughput **FastAPI + PostgreSQL (Neon Cloud)** backend, and **Google Gemini 2.5 AI** with automated model cascading and offline deterministic heuristic fallback.

---

## Architecture Overview

```
Finance-Tracker/
├── client/                     # Modern React 18 SPA (Vite + Tailwind CSS + Recharts)
│   ├── src/
│   │   ├── pages/              # Dashboard, Transactions, Budget, Insights, Reports, Profile
│   │   ├── components/         # Reusable UI components & Layouts
│   │   ├── redux/              # Redux Toolkit slices (auth, transactions, budget, etc.)
│   │   └── services/           # Axios instance with JWT interceptor & auto-refresh
│   ├── vercel.json             # Vercel SPA routing configuration
│   └── package.json
│
├── server/             # Production FastAPI + PostgreSQL Async Backend
│   ├── app/
│   │   ├── api/                # API routes (auth, transactions, budgets, dashboard, ai, reports)
│   │   ├── core/               # App configuration, security, TTL caching, database engine
│   │   ├── models/             # SQLAlchemy async models (User, Transaction, Budget)
│   │   ├── schemas/            # Pydantic validation schemas
│   │   └── services/           # Gemini AI service, financial analyzer, PDF export service
│   ├── Dockerfile              # Production container build
│   ├── Procfile                # Web process definition for Render / Heroku
│   ├── requirements.txt        # Python production dependencies
│   └── run.py                  # Server runner
│
├── render.yaml                 # Render Blueprint configuration for 1-click deployment
├── vercel.json                 # Root Vercel deployment & rewrite configuration
└── .env.example                # Full environment variable template
```

---

## Tech Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React 18, Vite, Redux Toolkit, React Router v6, Tailwind CSS, Recharts |
| **Backend** | Python 3.11+, FastAPI, SQLAlchemy 2.0 (Async), asyncpg, Pydantic v2, Uvicorn |
| **Database** | PostgreSQL on **Neon Cloud** (Hosted in AWS Singapore for low latency) |
| **AI Engine** | Google Gemini 2.5 Flash-Lite (with model cascading to Gemini 3.5 & deterministic fallback) |
| **Auth** | Dual-Token System: In-memory/header JWT access token + secure HttpOnly refresh cookie |
| **Deployment** | **Vercel** (Frontend) & **Render** (Backend) |

---

## Key Features

1. **Executive Dashboard**:
   - Live KPI cards: Total Balance, Monthly Income, Monthly Expenses, Net Savings.
   - Interactive Recharts: Monthly cash flow trend analysis and category distribution donut charts.
   - Sub-5ms response times powered by in-memory TTL query caching.

2. **Transaction Management**:
   - Instant search, multi-field filtering (type, category, date), and pagination.
   - Calendar-day timezone normalization (preventing UTC boundary date-shift bugs).
   - Strict currency formatting in Indian Rupees (`₹`).

3. **Smart Budgeting & Alerts**:
   - Monthly spending limits and granular per-category budget allocations.
   - Real-time progress bars with dynamic status indicators (*Healthy*, *Warning*, *Exceeded*).

4. **AI-Powered Insights**:
   - Automated financial health analysis powered by Google Gemini 2.5 Flash-Lite.
   - Spending run-rate forecast with a live confidence percentage meter.
   - Resilient 3-tier architecture: Primary Gemini → Model Cascade → Deterministic Local Heuristic Fallback.

5. **Financial Report Export**:
   - Export full monthly financial statements as structured, executive-ready PDF documents via ReportLab.

---

## Local Development Setup

### 1. Prerequisites
- **Node.js**: v18+ and `npm`
- **Python**: v3.11+
- **PostgreSQL**: Local PostgreSQL or a free instance on [Neon](https://neon.tech)

### 2. Backend Setup (`server`)

```bash
# Navigate to the backend directory
cd server

# Create and activate Python virtual environment
python3 -m venv venv
source venv/bin/activate       # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
```

Edit `server/.env` with your values:
```env
PORT=5055
ENVIRONMENT=development
DATABASE_URL=postgresql+asyncpg://<username>:<password>@<host>/<database>?ssl=require
JWT_SECRET=your_secret_key_min_32_characters
FRONTEND_URL=http://localhost:5173
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash-lite
```

Start the FastAPI server:
```bash
python run.py
```
*API will run at `http://localhost:5055` with interactive Swagger docs at `http://localhost:5055/docs`.*

### 3. Frontend Setup (`client`)

In a new terminal window:
```bash
# Navigate to the frontend directory
cd client

# Install dependencies
npm install

# Copy environment template
cp .env.example .env
```

Start the Vite development server:
```bash
npm run dev
```
*App will run at `http://localhost:5173`.*

---

## Deployment Guide

### A. Deploy Backend to Render

You can deploy the FastAPI backend to Render using either the **1-Click Blueprint** or as a **Web Service**:

#### Option 1: Render Web Service (Recommended)
1. Go to [Render Dashboard](https://dashboard.render.com/) and click **New +** → **Web Service**.
2. Connect your GitHub repository.
3. Configure the settings:
   - **Name**: `finance-tracker-api`
   - **Root Directory**: `server`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: `Free`
4. Add the following **Environment Variables** in Render:
   | Key | Example Value | Description |
   | :--- | :--- | :--- |
   | `ENVIRONMENT` | `production` | Enables secure cross-site cookies (`SameSite=None`) |
   | `DATABASE_URL` | `postgresql+asyncpg://...` | Neon PostgreSQL connection string |
   | `JWT_SECRET` | `long_random_secret_key` | Secret key for JWT signing |
   | `FRONTEND_URL` | `https://your-app.vercel.app` | Your Vercel frontend URL for CORS |
   | `GEMINI_API_KEY` | `AIzaSy...` | Your Google Gemini API Key |
   | `GEMINI_MODEL` | `gemini-2.5-flash-lite` | Primary Gemini model |
   | `PYTHON_VERSION` | `3.11.9` | Target Python version |
5. Click **Deploy Web Service**.
6. Once deployed, copy your Render URL (e.g., `https://finance-tracker-api.onrender.com`).

---

### B. Deploy Frontend to Vercel

1. Go to [Vercel Dashboard](https://vercel.com/) and click **Add New...** → **Project**.
2. Import your GitHub repository.
3. In the project configuration:
   - **Framework Preset**: `Vite`
   - **Root Directory**: Click *Edit* and select `client` (or leave as `./` with the provided root config)
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Add the **Environment Variable**:
   | Key | Value |
   | :--- | :--- |
   | `VITE_API_URL` | `https://your-render-service.onrender.com/api` |
5. Click **Deploy**.
6. After deployment completes, copy your live Vercel URL and update `FRONTEND_URL` on Render to match!

---

## Security & Best Practices Implemented

- **Cross-Origin Cookie Security**: In production, authentication cookies are automatically flagged with `SameSite=None; Secure`, ensuring reliable session persistence between Vercel and Render.
- **Connection URL Normalization**: The database engine automatically normalizes both standard `postgres://` and `postgresql://` strings to asyncpg driver syntax (`postgresql+asyncpg://`).
- **Resilient AI Fallback**: If Gemini encounters quota rate limits (HTTP 429), it cascades to alternative models and safely falls back to a deterministic local financial analyzer without disrupting the UI.
- **Strict Input Validation**: All user transactions and budget data are sanitized and validated with Pydantic v2.

---

## License
MIT License.
