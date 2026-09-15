# AI API Documentation Agent ⚡

> **An AI-powered developer tool that monitors a backend repository, detects API changes from code commits, analyzes semantic diffs, automatically updates and validates OpenAPI specifications, and serves live Swagger documentation.**

---

## 1. Overview & Core Problem

Backend APIs evolve rapidly:
- New endpoints and routes are added
- Obsolete endpoints are deprecated and removed
- Path and query parameters change
- Request payload models and mandatory fields change
- Response structures and status codes evolve
- Authentication and security requirements change

**The Problem:** API documentation quickly drifts from actual backend code, breaking client integrations.

**The Solution:** An automated pipeline combining **Python AST static analysis**, **deterministic Git diffing**, **AI-driven semantic reasoning**, and **OpenAPI 3.0.3 validation & live publishing**.

---

## 2. Core Architectural Principle

```
CODE FOR DETERMINISTIC OPERATIONS.
AI FOR REASONING.
```

The system **never** sends the full repository to an LLM or allows an AI model to blindly overwrite `openapi.json`.

```
[Git Commit / Webhook]
          │
          ▼
   [Git Diff Engine] (Filters modified .py files)
          │
          ▼
[FastAPI AST Code Analyzer] (Extracts routes, parameters, schemas, auth)
          │
          ▼
[API Change Comparator] (Identifies structural additions, removals, modifications)
          │
          ▼
     [AI Agent] (Reasons on client impact, explanations, confidence)
          │
          ▼
[Deterministic OpenAPI Updater] (Applies surgical updates, preserves unrelated paths)
          │
          ▼
  [OpenAPI Validator] (Validates 3.0.3 spec compliance + deterministic auto-repair)
          │
          ▼
[Live Swagger UI & Developer Dashboard]
```

---

## 3. Technology Stack

- **Backend**: Python 3.11+, FastAPI, Uvicorn, SQLAlchemy 2.0, SQLite, GitPython, Pydantic v2, openapi-spec-validator, HTTPX, PyYAML.
- **Frontend**: React 18, Vite, Lucide Icons, Custom CSS Design System.
- **AI Layer**: Pluggable LLM Provider Abstraction (`MockProvider`, `GeminiProvider`, `OpenAIProvider`).

---

## 4. Setup & Installation

### Backend Setup

```powershell
# 1. Navigate to backend directory
cd "C:\Users\Rishita Sriya V\Documents\project\backend"

# 2. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 3. Configure environment variables (if customizing)
copy .env.example .env
```

### Running Automated Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

### Running Backend Server

```powershell
.\.venv\Scripts\uvicorn app.main:app --reload --port 8000
```

- Live API Health: [http://localhost:8000/health](http://localhost:8000/health)
- Backend Swagger: [http://localhost:8000/docs](http://localhost:8000/docs)

### Frontend Setup

```powershell
# 1. Navigate to frontend directory
cd "C:\Users\Rishita Sriya V\Documents\project\frontend"

# 2. Install dependencies
npm install

# 3. Start dashboard dev server
npm run dev
```

- Developer Dashboard: [http://localhost:3000](http://localhost:3000)

---

## 5. End-to-End Walkthrough Demonstration

### Step 1: Connect a Repository
1. Open the Dashboard at `http://localhost:3000`.
2. Click **Connect Repository**.
3. Enter `owner` (e.g. `store-org`) and `name` (e.g. `sample-backend`).
4. Or connect the provided sample backend at `C:\Users\Rishita Sriya V\Documents\project\sample-backend`.

### Step 2: Trigger Analysis
- Click **Analyze Now** on the repository card or send a POST request:
  ```powershell
  Invoke-RestMethod -Uri "http://localhost:8000/repositories/1/analyze?force=true" -Method Post
  ```

### Step 3: View Live Documentation
- Click **Swagger UI** on the repository card to open the synchronized Swagger documentation at:
  `http://localhost:8000/repositories/1/docs`

### Step 4: Inspect AI Reasoning & Code Traceability
- Click on any detected API change in the dashboard to see:
  - **Before vs After Structural JSON Diff**
  - **AI Agent Explanation**
  - **Impact Severity Classification (HIGH / MEDIUM / LOW)**
  - **Confidence Score & Auto-Publish Status**
  - **Source Code Traceability** (File and Line Number)

---

## 6. Environment Variables Reference

| Variable | Default | Description |
| :--- | :--- | :--- |
| `APP_ENV` | `development` | Runtime environment mode |
| `DATABASE_URL` | `sqlite:///./storage/api_agent.db` | SQLAlchemy database connection string |
| `STORAGE_PATH` | `./storage` | Directory for repositories, logs, and OpenAPI files |
| `GITHUB_TOKEN` | *(optional)* | Personal access token for authenticated GitHub REST API |
| `GITHUB_WEBHOOK_SECRET` | *(optional)* | Secret key for verifying HMAC-SHA256 webhook signatures |
| `LLM_PROVIDER` | `mock` | Active provider: `mock`, `gemini`, or `openai` |
| `LLM_API_KEY` | *(optional)* | API Key for Gemini / OpenAI |
| `CONFIDENCE_THRESHOLD` | `0.85` | Changes below this score are held for `REVIEW_REQUIRED` |
| `AUTO_PUBLISH` | `true` | Auto-publish high confidence validated specifications |

---

## 7. Key Differentiators

1. **Explainable API Changes:** Not just a raw diff, but clear reasoning explaining *why* documentation changed.
2. **API Impact Analysis:** Automatic classification of breaking vs non-breaking changes (`HIGH`, `MEDIUM`, `LOW`).
3. **Change History & Versioning:** Tracks every API evolution step across Git commits with version rollback protection.
4. **AI Safety & Determinism:** LLM reasoning is validated with Pydantic and applied programmatically, eliminating hallucinated file corruption.
5. **Code Traceability:** Every change links directly to the source file and line number where the change originated.
