# 🚀 FastAPI + PostgreSQL Backend

High-performance, async backend for **AI Personal Finance Tracker** built with **FastAPI**, **PostgreSQL**, **SQLAlchemy 2.0 (async)**, and **Pydantic v2**.

---

## 🏗️ Architecture & Highlights

- **FastAPI Framework**: Async-native REST API with automatic OpenAPI/Swagger documentation at `/docs`.
- **PostgreSQL Database**: Relational schema with strict foreign keys and database-level cascading deletion (`ON DELETE CASCADE`).
- **SQLAlchemy 2.0 (asyncio + asyncpg)**: Type-safe, explicit database operations using modern `select()` queries and async sessions.
- **Dual-Token Authentication**:
  - Short-lived Access Token (15 minutes).
  - Long-lived Refresh Token (7 days) stored in an `httpOnly`, `SameSite=Lax` cookie.
  - Complete with silent refresh (`POST /api/auth/refresh`) and cascading account purge (`DELETE /api/auth/account`).
- **Zero Frontend Breaking Changes**: Perfectly preserves existing endpoint URLs (`/api/...`), camelCase keys, status codes, and payload formats expected by the React client.
- **AI & Heuristic Analytics**:
  - Integrated with OpenAI (async) with automatic fallback to a deterministic financial heuristic engine.
  - In-memory cache with 15-minute TTL and transaction-based cache invalidation.
- **ReportLab PDF Generator**: Native server-side PDF generation for monthly financial summaries.

---

## 📁 Directory Structure

```text
server/
├── app/
│   ├── core/
│   │   ├── config.py         # App settings & environment variables
│   │   ├── database.py       # Async SQLAlchemy engine & session dependency
│   │   └── security.py       # Password hashing (bcrypt) & JWT helpers
│   ├── models/
│   │   ├── user.py           # User table (cascading relation)
│   │   ├── transaction.py    # Transaction table
│   │   └── budget.py         # Budget table (with PostgreSQL JSONB category limits)
│   ├── schemas/              # Pydantic v2 request & response schemas
│   ├── api/
│   │   ├── deps.py           # Dependency injection (get_current_user)
│   │   ├── auth.py           # Auth routes & cookie management
│   │   ├── transactions.py   # Transaction CRUD, search & pagination
│   │   ├── budgets.py        # Budget configuration
│   │   ├── dashboard.py      # Real-time PostgreSQL aggregations
│   │   ├── ai.py             # AI insights & predictions
│   │   └── reports.py        # Monthly reporting & PDF stream
│   ├── services/
│   │   ├── finance_analyzer.py # Python financial calculation & heuristic engine
│   │   ├── ai_service.py       # OpenAI integration & TTL cache
│   │   └── pdf_service.py      # ReportLab PDF report builder
│   └── main.py               # FastAPI app, CORS, and lifespan table creation
├── test_api.py               # End-to-end integration test suite
├── run.py                    # Server entrypoint
├── requirements.txt
└── .env
```

---

## 🏃 Running the Server

### 1. Ensure PostgreSQL is Running
Make sure PostgreSQL is running locally with database `finance_tracker`:
```bash
createdb finance_tracker
```

### 2. Activate Virtual Environment & Install Dependencies
```bash
cd server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Run the Server
```bash
python run.py
```
Server starts on `http://localhost:5055` (matching the Vite frontend proxy).

### 4. Interactive API Docs
Open `http://localhost:5055/docs` in your browser to view the interactive Swagger UI and test any endpoint directly.

### 5. Run Verification Tests
```bash
python test_api.py
```
