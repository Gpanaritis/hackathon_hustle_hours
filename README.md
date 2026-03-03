Go here to view the app:
http://192.168.20.146:5173/

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

## Docker

Default Docker stack:

- `db` for PostgreSQL + pgvector
- `backend` for the FastAPI API

Optional Docker service:

- `frontend` is a temporary dev UI and is disabled by default behind the `dev-ui` profile

### 1. Prepare backend env

```bash
cp backend/.env.example backend/.env
```

Fill in `backend/.env` with your secrets. When running through Docker Compose:

- `ANTHROPIC_API_KEY` is read from `backend/.env`
- `DATABASE_URL` from `backend/.env` is overridden automatically to point at the `db` container
- uploaded files are stored in a persistent Docker volume mounted at `/app/storage`

### 2. Start the default stack

```bash
docker compose up --build
```

Services:

- API: `http://localhost:8001`
- Health: `http://localhost:8001/api/v1/health`
- PostgreSQL: `localhost:5432`

### 3. Start with the optional frontend

```bash
docker compose --profile dev-ui up --build
```

Optional frontend:

- Dev UI: `http://localhost:3001`

### 4. Restore an existing PostgreSQL backup

Put your backup file in `./backups`, then run the restore profile with `RESTORE_FILE` set to the filename.

Examples:

```bash
RESTORE_FILE=old_db.dump docker compose --profile restore up db_restore
```

```bash
RESTORE_FILE=old_db.sql docker compose --profile restore up db_restore
```

Notes:

- Supported formats: `.dump`, `.backup`, `.tar`, `.sql`
- The restore service waits for the Docker database to be healthy, then imports into the running `db` service
- For custom-format dumps, restore runs with `--clean --if-exists --no-owner --no-privileges`
- Using PostgreSQL 18 for both `db` and `db_restore` avoids the `transaction_timeout` mismatch you hit when restoring a newer dump into an older server

### Notes

- Database schema is initialized on first boot from `schema.sql` and `schema_decisions.sql`
- PostgreSQL data, uploaded files, and model cache are persisted in Docker volumes
- You can override ports and credentials with Compose environment variables such as `BACKEND_PORT`, `FRONTEND_PORT`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB`

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
