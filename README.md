# Rovr

RAG chatbot for Adobe Experience Cloud documentation — Adobe Analytics, Customer Journey Analytics, Experience Platform, Target, Journey Optimizer, and Data Collection.

**Live app:** [thelearningproject.in/tools/rovr](https://thelearningproject.in/tools/rovr)

## Stack

| Layer | Tech |
|-------|------|
| Frontend | React, Vite, TypeScript |
| Backend | FastAPI, Python 3.11+ |
| LLM | Anthropic Claude (Haiku / Sonnet routing) |
| Vector store | ChromaDB |
| Docs pipeline | Adobe GitHub → S3 → Chroma (GitHub Actions) |
| Hosting | Railway (API), Cloudflare Pages (UI) |

## Local development

```bash
git clone https://github.com/riteshvg/ExperienceLeagueChatBotAWS.git
cd ExperienceLeagueChatBotAWS

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.template .env   # fill in keys (see template)

uvicorn backend.main:app --reload --port 8000
```

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). The dev server proxies `/api` to port 8000.

## Tests

```bash
pytest tests/
```

## Repository layout

```
backend/     API, RAG pipeline, auth
frontend/    React chat UI
config/      Settings and prompts
scripts/     Doc sync and ingest utilities
tests/       Backend tests
```

## Environment

Copy `.env.template` to `.env`. Required for local chat: `ANTHROPIC_API_KEY` and `DATABASE_URL` (PostgreSQL). See the template for optional Google OAuth, AWS/S3, and admin settings.

Production deploys via Railway (backend, git push to `main`) and Cloudflare Pages (frontend, separate Hugo site repo).
