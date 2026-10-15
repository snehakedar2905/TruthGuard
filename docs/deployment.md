# TruthGuard Deployment Guide

## 1. Local Development Quickstart

### Prerequisites
* Python 3.10+ (tested on Python 3.12)
* Node.js 18+ and npm

### Backend Setup
```powershell
# 1. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 2. Start FastAPI Server
uvicorn app.main:app --reload --port 8000
```
Backend Swagger API will be live at `http://localhost:8000/docs`.

### Frontend Setup
```powershell
cd frontend
npm install
npm run dev
```
Frontend UI will be live at `http://localhost:5173`.

---

## 2. Docker & Enterprise Production Deployment

TruthGuard includes production `Dockerfile`s and a multi-container `docker-compose.yml` with PostgreSQL and pgvector:

```bash
# Build and run all services
docker compose up --build -d

# Verify service health
docker compose ps
```

* **Frontend**: `http://localhost:5173`
* **Backend API**: `http://localhost:8000`
* **PostgreSQL / pgvector**: `localhost:5432`
