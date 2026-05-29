# HVAC Pricing Intelligence AI

A test-ready HVAC price comparison system with a FastAPI backend and a Next.js visual interface.

## Features

- Upload Excel, CSV, TSV, and PDF price sheets
- Three selectable price analysis channels: rules parser, OpenAI, and local Ollama
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
- Import page: http://localhost:3000/import
- API docs: http://localhost:8000/docs

## Price Analysis Channels

The import page lets you choose one of three channels for every upload:

- `Rules parser`: deterministic column and price detection. No AI service required.
- `Local Ollama`: sends the parsed rows to a local Ollama model for cleanup.
- `OpenAI`: sends the parsed rows to OpenAI for structured cleanup.

### OpenAI Setup

```bash
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-4o-mini
```

### Local Ollama Setup

Install Ollama, start it, and pull a model:

```bash
ollama pull qwen2.5:7b
```

Then set backend environment variables:

```bash
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_TIMEOUT=120
```

`AI_PROVIDER` can still be used as a backend default for API callers that do not send a channel, but the web UI now sends `rules`, `openai`, or `ollama` explicitly with each upload.

## Test Workflow

1. Start backend and frontend.
2. Open `/import`.
3. Select `Rules parser`, `Local Ollama`, or `OpenAI`.
4. Upload an `.xlsx`, `.csv`, `.tsv`, or `.pdf` vendor price sheet.
5. Review parsed rows and errors.
6. Turn on `Import valid rows` and upload again to write data into the system.
7. Return to dashboard to compare prices.
