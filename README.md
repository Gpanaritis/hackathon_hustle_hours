# Contract Intelligence

Turns PDF contracts into structured relational records. Supports AI chat, guided queries, and vector similarity search.

## Stack

| Layer | Tech |
|-------|------|
| Frontend | Next.js 15, TypeScript, Tailwind CSS |
| Backend | Python 3.11+, FastAPI |
| Database | PostgreSQL + pgvector |
| LLM | Claude (Anthropic) |
| Embeddings | sentence-transformers (local) |
| Storage | Local filesystem |

---

## Setup

### 1. PostgreSQL

Install PostgreSQL and create the database:

```bash
psql -U postgres -c "CREATE DATABASE contracts_db;"
psql -U postgres -d contracts_db -f schema.sql
```

### 2. Backend

```bash
cd backend

# Copy and fill in your env file
cp .env.example .env
# Edit .env: set DATABASE_URL and ANTHROPIC_API_KEY

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the API server
uvicorn app.main:app --reload --port 8000
```

API will be available at: http://localhost:8000
Interactive docs: http://localhost:8000/docs

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend will be available at: http://localhost:3000

---

## Environment Variables

### `backend/.env`

```
DATABASE_URL=postgresql://postgres:password@localhost:5432/contracts_db
ANTHROPIC_API_KEY=your_key_here
STORAGE_PATH=./storage/contracts
```

---

## Features

- **Upload** — PDF upload with duplicate detection (SHA-256). Automatically detects text vs scanned PDFs.
- **Contracts list** — Filter by country, party name, expiring this year, missing signature/stamp.
- **Contract detail** — Tabbed view: Metadata, Parties, Musical Works, Terms, AI summary.
- **Chat** — Natural language queries powered by Claude SQL generation.
- **Similarity search** — Find contracts similar to the current one using pgvector cosine similarity.

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py                      # FastAPI app
│   │   ├── config.py                    # Settings from .env
│   │   ├── database.py                  # SQLAlchemy engine
│   │   ├── models/contracts.py          # ORM models
│   │   ├── schemas/contracts.py         # Pydantic schemas
│   │   └── modules/
│   │       ├── contracts/
│   │       │   ├── router.py            # Upload, list, detail, download, similar
│   │       │   ├── processor.py         # PDF pipeline
│   │       │   ├── extractor.py         # Claude extraction
│   │       │   └── embedder.py          # sentence-transformers
│   │       └── chat/
│   │           └── router.py            # Chat endpoint
│   └── storage/contracts/               # PDF files stored here
├── frontend/
│   ├── app/
│   │   ├── contracts/page.tsx           # Contract list
│   │   ├── contracts/[id]/page.tsx      # Contract detail
│   │   ├── upload/page.tsx              # Upload
│   │   └── chat/page.tsx               # Chat
│   └── lib/api.ts                       # API client
├── schema.sql                           # Database schema
└── docs/PRD.md                          # Product requirements
```
