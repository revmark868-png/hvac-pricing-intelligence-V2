# HVAC Pricing Intelligence AI

A test-ready HVAC price comparison system with a FastAPI backend and a Next.js visual interface.

## Features

- Upload Excel, CSV, TSV, and PDF price sheets
- Rule-based parser for clean files
- Optional OpenAI assisted normalization for messy files
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

## Optional AI Import

Set an OpenAI key before starting the backend:

```bash
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-4o-mini
```

Without the key, the importer still works using deterministic column detection.

## Test Workflow

1. Start backend and frontend.
2. Open `/import`.
3. Upload an `.xlsx`, `.csv`, `.tsv`, or `.pdf` vendor price sheet.
4. Review parsed rows and errors.
5. Turn on `Import valid rows` and upload again to write data into the system.
6. Return to dashboard to compare prices.
