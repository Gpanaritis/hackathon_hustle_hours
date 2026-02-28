# Contract Intelligence — MVP PRD

## Overview

Contract Intelligence is an internal web tool that turns uploaded PDF contracts into structured relational records. The system extracts parties, musical works, financial terms, and AI-generated metadata from each contract, stores everything in a relational database, and exposes it through a chat interface, guided query buttons, and vector similarity search. It is the first module of a future "PDF → Database" platform.

---

## Roles

| Role | Description | Key Permissions |
|------|-------------|-----------------|
| Admin | Any team member | Upload contracts, view all data, run all queries, use chat |

No authentication for MVP. All users have full access.

---

## User Scenarios

### 1. Upload and Process a Contract

**Role:** Admin
**Goal:** Turn a PDF contract into structured database records

**Flow:**
1. User navigates to the Upload page
2. User selects a PDF file from their machine
3. System computes SHA-256 hash of the file
   - If hash already exists in DB → reject with "Contract already uploaded" message
4. System saves PDF to local filesystem under `/storage/contracts/<contract_id>.pdf`
5. System detects PDF type:
   - **Text PDF** (has extractable text layer) → extract text with `pdfplumber` → send text to Claude
   - **Image-only PDF** (scanned, no text layer) → send PDF pages as images to Claude
6. Claude performs:
   - OCR (if image-only)
   - Language detection
   - Field extraction (all fields across all 5 tables)
   - Short summary generation (2–3 sentences)
   - English translation of full text (if not already English)
7. `sentence-transformers` generates embedding from extracted raw text
8. System inserts records into: `contracts`, `contract_parties`, `musical_works`, `contract_terms`, `contract_intelligence`
9. User sees a success screen with the contract's `internal_ref_no` and a link to the contract detail page

**Edge Cases:**
- Duplicate file (same hash): Rejected with clear error message
- Claude extraction fails or returns incomplete data: Store what was extracted, flag contract status as `needs_review`
- PDF is corrupted / unreadable: Reject with error message, do not save to DB
- Contract has no musical works (e.g., a licensing-only agreement): `musical_works` rows are simply not inserted; no error
- Multi-page image PDF: All pages sent to Claude together

**Acceptance Criteria:**
- [ ] PDF is saved to local filesystem with path stored in `contracts.pdf_path`
- [ ] SHA-256 hash is stored; duplicate uploads are rejected
- [ ] Text PDFs use pdfplumber for extraction before Claude
- [ ] Image-only PDFs are sent directly to Claude as images
- [ ] All 5 tables are populated after successful processing
- [ ] Contract status is set to `processed` on success, `needs_review` on partial failure
- [ ] User receives feedback on success or failure

---

### 2. Browse and Search Contracts

**Role:** Admin
**Goal:** Find contracts using guided query buttons or free-text search

**Flow:**
1. User navigates to the Contracts list page
2. Page shows a table of all contracts with columns: `internal_ref_no`, `file_name`, `country_code`, `execution_date`, `expiry_date`, `status`, `signature_present`
3. User can click a guided query button to filter:
   - **Expiring this year** → contracts where `expiry_date` is within the current calendar year
   - **Missing signatures** → contracts where `signature_present = false`
   - **Missing stamps** → contracts where `stamp_present = false`
   - **By country** → dropdown to filter by `country_code`
   - **By party** → text input to filter by `contract_parties.legal_name`
4. Results update in the table below the buttons
5. User clicks a row to open the contract detail page

**Edge Cases:**
- No contracts match filter: Show empty state message "No contracts found"
- Large result sets: Paginate at 50 rows per page

**Acceptance Criteria:**
- [ ] All guided queries return correct results
- [ ] Filters can be combined (e.g., expiring this year AND missing signature)
- [ ] Clicking a row opens the contract detail page
- [ ] Pagination works for large result sets

---

### 3. View Contract Detail

**Role:** Admin
**Goal:** See all extracted data for a single contract

**Flow:**
1. User opens a contract detail page (via list or direct URL)
2. Page displays:
   - **Header:** `internal_ref_no`, `file_name`, status badge, upload date
   - **Metadata tab:** All fields from `contracts` table
   - **Parties tab:** Table of all rows from `contract_parties` for this contract
   - **Musical Works tab:** Table of all rows from `musical_works`
   - **Terms tab:** All fields from `contract_terms`
   - **AI tab:** Short summary, language, English translation (if applicable)
   - **Download button:** Downloads the original PDF from local storage

**Edge Cases:**
- PDF file missing from filesystem (deleted manually): Show warning "Original file not found" but still display all DB data

**Acceptance Criteria:**
- [ ] All extracted fields are displayed and organized by tab
- [ ] Original PDF can be downloaded
- [ ] Missing file shows warning without breaking the page

---

### 4. Chat with Contracts

**Role:** Admin
**Goal:** Ask natural language questions about the contract database

**Flow:**
1. User navigates to the Chat page
2. User types a question, e.g. "Show me all contracts expiring in 2025 from Argentina"
3. System sends the question + database schema to Claude
4. Claude generates a SQL query
5. Backend executes the SQL query against Postgres
6. Results are returned and displayed as a formatted table in the chat
7. Claude also provides a plain-language explanation of the results
8. Conversation history is maintained within the session (not persisted to DB)

**Edge Cases:**
- Claude generates invalid SQL: Backend catches the error, returns "I couldn't generate a valid query for that. Try rephrasing." — do not expose raw SQL errors to user
- Query returns 0 rows: Display "No results found" with the plain-language explanation
- Question is not answerable from the schema (e.g., "What is the weather?"): Claude responds with a clarification message
- Query would return more than 200 rows: Limit to 200 rows and notify user

**Acceptance Criteria:**
- [ ] Natural language questions produce correct SQL
- [ ] Results are shown as formatted tables
- [ ] Invalid SQL is caught and handled gracefully
- [ ] Row limit of 200 is enforced
- [ ] Chat history is visible within the session

---

### 5. Similarity Search

**Role:** Admin
**Goal:** Find contracts similar to a given contract

**Flow:**
1. On any contract detail page, user clicks "Find Similar Contracts"
2. System retrieves the embedding for the current contract from `contract_intelligence.embedding`
3. System computes cosine similarity against all other contracts using pgvector
4. Returns top 5 most similar contracts, ordered by similarity score
5. Results displayed as a list with: `internal_ref_no`, `file_name`, similarity score (as a percentage)
6. Each result links to its contract detail page

**Edge Cases:**
- Contract has no embedding (processing failed): Button is disabled with tooltip "Embedding not available for this contract"
- Fewer than 5 contracts in DB: Return however many exist

**Acceptance Criteria:**
- [ ] Similarity computed via pgvector cosine similarity
- [ ] Top 5 results returned and linked
- [ ] Button disabled when embedding is unavailable

---

## Scope

### In Scope (MVP)
- PDF upload with duplicate detection (SHA-256)
- PDF type detection (text vs image-only)
- Text extraction via pdfplumber (text PDFs) or Claude vision (image PDFs)
- Claude-powered field extraction into all 5 tables
- Local filesystem PDF storage
- Contract list page with guided query filters
- Contract detail page with tabbed view
- Chat interface with Claude SQL generation
- Similarity search via pgvector
- Modular architecture to support future document types

### Out of Scope (Future)
- Authentication and user accounts — deferred, single team for now
- Other document types (invoices, licenses, etc.) — architecture supports it, not built yet
- Batch upload (multiple PDFs at once) — single upload only for MVP
- Export to CSV/Excel — deferred
- Email or push notifications — deferred
- Audit log / processing history — deferred
- Contract editing or correction UI — deferred
- Cloud deployment — local only for MVP
- Persistent chat history — session-only for MVP

---

## Technical Context

### Tech Stack

| Layer | Choice | Notes |
|-------|--------|-------|
| **Frontend** | Next.js 15 (latest stable) | App Router, TypeScript |
| **Backend** | Python 3.11+ + FastAPI | REST API at `localhost:8000` |
| **Database** | PostgreSQL + pgvector | pgvector extension for embeddings |
| **LLM** | Claude (Anthropic API) | Extraction, summarization, translation, SQL generation |
| **Embeddings** | `sentence-transformers` | Local, no API key required |
| **PDF Parsing** | `pdfplumber` (text PDFs) | Detect text layer; fall back to Claude vision |
| **File Storage** | Local filesystem | `/storage/contracts/` relative to backend root |
| **Auth** | None | Open access for MVP |
| **Deployment** | Local | Frontend: `localhost:3000`, Backend: `localhost:8000` |

### Integrations

| Service | Purpose | Data Flow |
|---------|---------|-----------|
| Anthropic Claude API | Field extraction, summarization, translation, SQL generation | Backend → Claude API → structured JSON response |
| sentence-transformers | Generate contract embeddings | Backend (local) → float vector stored in pgvector |
| pdfplumber | Extract text from native PDFs | Backend reads PDF → returns plain text |

### Key Entities

```
contracts (1)
  ├── contract_parties (many)
  ├── musical_works (many)
  ├── contract_terms (1)
  └── contract_intelligence (1)
             └── embedding (vector, stored in pgvector)
```

All child tables reference `contracts.contract_id` via foreign key.

### Database Schema

```sql
-- Core record
CREATE TABLE contracts (
  contract_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  internal_ref_no    TEXT,
  file_name          TEXT NOT NULL,
  pdf_path           TEXT NOT NULL,
  file_hash          TEXT UNIQUE NOT NULL,
  country_code       TEXT,
  jurisdiction_state_city TEXT,
  language           TEXT,
  execution_date     DATE,
  term_years         NUMERIC,
  expiry_date        DATE,
  is_exclusive       BOOLEAN,
  status             TEXT DEFAULT 'processing', -- processing | processed | needs_review
  signature_present  BOOLEAN,
  stamp_present      BOOLEAN,
  upload_date        TIMESTAMPTZ DEFAULT now()
);

-- Parties
CREATE TABLE contract_parties (
  party_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  contract_id           UUID REFERENCES contracts(contract_id) ON DELETE CASCADE,
  role                  TEXT, -- Producer | Author | Composer | Arranger | etc.
  legal_name            TEXT,
  representative_name   TEXT,
  id_type               TEXT,
  id_value              TEXT,
  address               TEXT
);

-- Musical works
CREATE TABLE musical_works (
  work_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  contract_id          UUID REFERENCES contracts(contract_id) ON DELETE CASCADE,
  title                TEXT,
  artist_performer     TEXT,
  lyricist             TEXT,
  isrc_code            TEXT,
  collection_society   TEXT
);

-- Financial / legal terms
CREATE TABLE contract_terms (
  term_id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  contract_id                  UUID REFERENCES contracts(contract_id) ON DELETE CASCADE,
  remuneration_amount          NUMERIC,
  currency                     TEXT,
  min_penalty_liquidated_damages NUMERIC,
  delivery_deadline_days       INTEGER,
  registration_deadline_days   INTEGER,
  streaming_requirement_days   INTEGER
);

-- AI layer
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE contract_intelligence (
  intel_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  contract_id     UUID REFERENCES contracts(contract_id) ON DELETE CASCADE,
  raw_text        TEXT,
  summary_short   TEXT,
  translated_text_en TEXT,
  embedding       vector(384)  -- sentence-transformers all-MiniLM-L6-v2 output dim
);
```

### PDF Processing Logic

```
Upload PDF
    │
    ▼
Compute SHA-256 hash
    │
    ├── Hash exists in DB? → Reject: "Already uploaded"
    │
    ▼
Save to /storage/contracts/<contract_id>.pdf
    │
    ▼
Detect PDF type
    │
    ├── Has text layer? (pdfplumber can extract > N chars)
    │       │
    │       ▼
    │   Extract text with pdfplumber
    │       │
    │       ▼
    │   Send text to Claude for extraction
    │
    └── Image-only?
            │
            ▼
        Send PDF pages as images to Claude
        (Claude performs OCR + extraction)
    │
    ▼
Claude returns structured JSON with all fields
    │
    ▼
sentence-transformers generates embedding from raw_text
    │
    ▼
Insert into all 5 tables
    │
    ▼
Set contracts.status = 'processed' (or 'needs_review' on partial failure)
```

### Claude Prompt Contract (Extraction)

Claude must return a JSON object with the following top-level keys:
- `contract` — fields for the `contracts` table
- `parties` — array of party objects
- `musical_works` — array of work objects
- `terms` — object for `contract_terms`
- `intelligence` — `raw_text`, `summary_short`, `translated_text_en`

### Constraints
- All backend API routes prefixed with `/api/v1/`
- Modular architecture: contracts logic lives in its own module (`/modules/contracts/`); future document types get their own modules
- pgvector cosine similarity: `embedding <=> query_vector` operator
- sentence-transformers model: `all-MiniLM-L6-v2` (384 dimensions)

---

## Open Questions

- Should `internal_ref_no` be auto-generated by the system, extracted by Claude from the document, or manually entered by the user on upload?
- What happens when Claude cannot extract a required field (e.g., no execution date visible)? Store `NULL` silently, or flag the specific field as missing?
- Is there a maximum PDF file size limit for upload?
