# StadiumMind OS

Enterprise-grade Autonomous Multi-Agent Stadium Intelligence Platform for FIFA World Cup 2026.

## Architecture

- **Backend**: FastAPI + SQLAlchemy (async) + PostgreSQL + Firebase Auth
- **Frontend**: Next.js 15 + TypeScript + Tailwind CSS
- **Auth**: Firebase Authentication + JWT + Refresh Token Rotation
- **RBAC**: Role-Based Access Control with fine-grained permissions

## Getting Started

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env  # Fill in values
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local  # Fill in values
npm run dev
```

## Documentation

See [docs/IAM_ARCHITECTURE.md](docs/IAM_ARCHITECTURE.md) for complete architecture, API reference, threat model, and test plans.
