# 🤖 AI API Documentation Agent

> An AI-powered developer tool that automatically detects API changes in a GitHub repository, analyzes their impact, updates OpenAPI documentation, validates the specification, and keeps API documentation synchronized with backend code.

---

## 🚀 Overview

Backend APIs change constantly during software development.

Developers may:

- Add new endpoints
- Remove existing endpoints
- Change HTTP methods
- Add or remove request fields
- Modify response structures
- Change path or query parameters
- Modify authentication requirements

However, API documentation is often updated manually, which can result in outdated or incorrect documentation.

**AI API Documentation Agent** automates this process.

The system monitors a GitHub backend repository, detects API-related code changes, analyzes their meaning using AI, updates the OpenAPI specification, validates the result, and publishes synchronized API documentation.

### Core Flow

```text
Developer
    │
    │ git push
    ▼
GitHub Repository
    │
    │ Webhook
    ▼
AI API Documentation Agent
    │
    ├── Change Detection
    ├── API Route Analysis
    ├── API Change Comparison
    ├── AI Change Analysis
    ├── OpenAPI Update
    ├── Validation
    └── Documentation Publishing
    │
    ▼
Swagger / OpenAPI Documentation# AI API Documentation Agent ⚡

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

