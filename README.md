# HVAC Pricing Intelligence AI

A test-ready HVAC price comparison system with a FastAPI backend and a Next.js visual interface.

## Features

- Upload Excel, CSV, TSV, and PDF price sheets
- Rule-based parser for clean files
- Optional OpenAI or local Ollama assisted normalization for messy files
- Import preview with confidence, errors, valid rows, and skipped rows
- Automatic creation of price items and vendor quotes
- Dashboard with min, average, max, and quote counts
- SQLite by default, PostgreSQL ready through `DATABASE_URL`

## Quick Start

Backend:

```bash
cd backend
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open:

- App: http://localhost:3000
- API docs: http://localhost:8000/docs

## AI Import Options

The importer always starts with deterministic column and price detection. For messy Excel/PDF files, you can add an AI cleanup step.

### Option A: OpenAI

```bash
AI_PROVIDER=openai
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-4o-mini
```

### Option B: Local Ollama

Install Ollama, start it, and pull a model:

```bash
ollama pull qwen2.5:7b
```

Then set backend environment variables:

```bash
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_TIMEOUT=120
```

`AI_PROVIDER=auto` uses OpenAI when `OPENAI_API_KEY` is present, otherwise it uses Ollama when `OLLAMA_MODEL` is set. Without either, the importer still works using deterministic column detection.

## Test Workflow

1. Start backend and frontend.
2. Open `/import`.
3. Upload an `.xlsx`, `.csv`, `.tsv`, or `.pdf` vendor price sheet.
4. Review parsed rows and errors.
5. Turn on `Import valid rows` and upload again to write data into the system.
6. Return to dashboard to compare prices.
