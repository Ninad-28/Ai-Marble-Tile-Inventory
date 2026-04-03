# Marble AI — Visual Tile Search System

AI-powered marble and tile inventory search system.
Upload a photo of any tile → get exact match, shelf location, and stock level in under 3 seconds.

## Tech Stack
- **Backend**: Python, FastAPI, PostgreSQL, pgvector
- **AI**: OpenCLIP (ViT-B-32), OpenCV
- **Frontend**: Next.js, Tailwind CSS

## Project Structure
```
marble-ai/
├── backend/    → FastAPI + AI pipeline
└── frontend/   → Next.js dashboard
```

## Setup

### Backend
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # fill in your DB credentials
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Environment Variables
See `backend/.env.example`