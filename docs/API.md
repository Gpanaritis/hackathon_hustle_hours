# Contract Intelligence — API Guide

Base URL: `http://<server-ip>:8000/api/v1`

Interactive docs (Swagger UI): `http://<server-ip>:8000/docs`

---

## Endpoints

### Health Check

```
GET /health
```

Verify the server is running.

**Response**
```json
{ "status": "ok" }
```

---

## Contracts

### Upload a Contract

```
POST /contracts/upload
```

Upload a PDF contract. The server will automatically:
- Detect if the PDF is text-based or scanned (OCR path)
- Extract all structured fields using Claude
- Generate an embedding for similarity search
- Store everything in the database

**Request** — `multipart/form-data`

| Field | Type | Required |
|-------|------|----------|
| `file` | PDF file | Yes |

**Example (curl)**
```bash
curl -X POST http://<server-ip>:8000/api/v1/contracts/upload \
  -F "file=@contract.pdf"
```

**Example (Python)**
```python
import requests

with open("contract.pdf", "rb") as f:
    res = requests.post(
        "http://<server-ip>:8000/api/v1/contracts/upload",
        files={"file": ("contract.pdf", f, "application/pdf")}
    )
print(res.json())
```

**Response** `201 Created`
```json
{
  "contract_id": 1,
  "internal_ref_no": "US004",
  "file_name": "contract.pdf",
  "country_code": "US",
  "jurisdiction_state_city": "New York, NY",
  "language": "English",
  "execution_date": "2022-03-15",
  "term_years": 10,
  "expiry_date": "2032-03-15",
  "is_exclusive": true,
  "status": "processed",
  "upload_date": "2025-02-28T14:00:00",
  "parties": [
    {
      "party_id": 1,
      "role": "Producer",
      "legal_name": "Acme Music LLC",
      "representative_name": "John Smith",
      "id_type": "VAT",
      "id_value": "US123456789",
      "address": "123 Main St, New York, NY",
      "signing_status": "signature_and_stamp"
    }
  ],
  "works": [...],
  "terms": {...},
  "intelligence": {...}
}
```

**Error responses**

| Status | Meaning |
|--------|---------|
| `400` | File is not a PDF or is empty |
| `409` | Duplicate — this file was already uploaded |
| `422` | Extraction failed (stored with status `needs_review`) |

---

### List Contracts

```
GET /contracts
```

Returns a paginated list of contracts. All query parameters are optional and can be combined.

**Query parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `country_code` | string | 2-letter ISO code (e.g. `US`, `BG`, `DK`) |
| `party_name` | string | Partial match on party legal name |
| `expiring_this_year` | boolean | Only contracts expiring in the current year |
| `missing_signature` | boolean | Only contracts where no party has a signature |
| `missing_stamp` | boolean | Only contracts where no party has a stamp |
| `page` | integer | Page number, default `1` |
| `page_size` | integer | Results per page, default `50`, max `200` |

**Example (curl)**
```bash
# All contracts from the US
curl "http://<server-ip>:8000/api/v1/contracts?country_code=US"

# Contracts expiring this year with missing signatures
curl "http://<server-ip>:8000/api/v1/contracts?expiring_this_year=true&missing_signature=true"

# Search by party name
curl "http://<server-ip>:8000/api/v1/contracts?party_name=Sony"

# Page 2
curl "http://<server-ip>:8000/api/v1/contracts?page=2&page_size=20"
```

**Response** `200 OK`
```json
[
  {
    "contract_id": 1,
    "internal_ref_no": "US004",
    "file_name": "contract.pdf",
    "country_code": "US",
    "language": "English",
    "execution_date": "2022-03-15",
    "expiry_date": "2032-03-15",
    "status": "processed",
    "upload_date": "2025-02-28T14:00:00"
  }
]
```

---

### Get Contract Details

```
GET /contracts/{contract_id}
```

Returns full details for a single contract including all parties, musical works, financial terms, and AI metadata.

**Example (curl)**
```bash
curl http://<server-ip>:8000/api/v1/contracts/1
```

**Response** `200 OK`
```json
{
  "contract_id": 1,
  "internal_ref_no": "US004",
  "file_name": "contract.pdf",
  "country_code": "US",
  "jurisdiction_state_city": "New York, NY",
  "language": "English",
  "execution_date": "2022-03-15",
  "term_years": 10,
  "expiry_date": "2032-03-15",
  "is_exclusive": true,
  "status": "processed",
  "upload_date": "2025-02-28T14:00:00",
  "parties": [
    {
      "party_id": 1,
      "role": "Producer",
      "legal_name": "Acme Music LLC",
      "representative_name": "John Smith",
      "id_type": "VAT",
      "id_value": "US123456789",
      "address": "123 Main St, New York, NY",
      "signing_status": "signature_and_stamp"
    }
  ],
  "works": [
    {
      "work_id": 1,
      "title": "Sunset Drive",
      "artist_performer": "SOFIE",
      "lyricist": "Jane Doe",
      "isrc_code": "USRC12345678",
      "collection_society": "BMI"
    }
  ],
  "terms": {
    "term_id": 1,
    "remuneration_amount": 5000.00,
    "currency": "USD",
    "min_penalty_liquidated_damages": 13000.00,
    "delivery_deadline_days": 30,
    "registration_deadline_days": 45,
    "streaming_requirement_days": null
  },
  "intelligence": {
    "intel_id": 1,
    "summary_short": "Exclusive music production agreement between Acme Music LLC and composer Jane Doe covering 3 works for a 10-year term.",
    "translated_text_en": null
  }
}
```

**Error responses**

| Status | Meaning |
|--------|---------|
| `404` | Contract not found |

---

### Download Original PDF

```
GET /contracts/{contract_id}/download
```

Returns the original uploaded PDF file.

**Example (curl)**
```bash
curl http://<server-ip>:8000/api/v1/contracts/1/download --output contract.pdf
```

**Example (browser)**

Just open the URL directly: `http://<server-ip>:8000/api/v1/contracts/1/download`

**Error responses**

| Status | Meaning |
|--------|---------|
| `404` | Contract not found, or file missing from disk |

---

### Find Similar Contracts

```
GET /contracts/{contract_id}/similar
```

Returns the 5 most similar contracts using vector cosine similarity.

**Example (curl)**
```bash
curl http://<server-ip>:8000/api/v1/contracts/1/similar
```

**Response** `200 OK`
```json
[
  {
    "contract_id": 7,
    "internal_ref_no": "BG001",
    "file_name": "contract_bg.pdf",
    "similarity": 91.4
  }
]
```

`similarity` is a percentage (0–100). Higher = more similar.

**Error responses**

| Status | Meaning |
|--------|---------|
| `404` | Contract not found |
| `422` | Contract has no embedding (processing may have failed) |

---

## Court Decisions

### Submit Decision as Text

```
POST /decisions/from-text
```

Send the text of a court decision directly in the request body — no file needed. Useful when you have already extracted or copied the text.

**Request body** — `application/json`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | string | Yes | Full text of the court decision |
| `label` | string | No | Optional name stored as the source filename (e.g. a case reference) |

**Example (curl)**
```bash
curl -X POST http://<server-ip>:8000/api/v1/decisions/from-text \
  -H "Content-Type: application/json" \
  -d '{
    "text": "IN THE HIGH COURT OF JUSTICE\nCase No. 2024/001\n...",
    "label": "2024-001-High-Court"
  }'
```

**Example (Python)**
```python
import requests

res = requests.post(
    "http://<server-ip>:8000/api/v1/decisions/from-text",
    json={
        "text": open("decision.txt").read(),
        "label": "2024-001"
    }
)
print(res.json())
```

**Response** `201 Created` — same shape as [Get Decision Details](#get-decision-details).

**Error responses**

| Status | Meaning |
|--------|---------|
| `400` | Text body is empty |
| `422` | Extraction failed |

---

### Upload a Decision File

```
POST /decisions/upload
```

Upload a court decision as a PDF or plain-text (`.txt`) file. The server will:
- For PDFs: detect if text-based or scanned, extract text accordingly
- For `.txt` files: read content directly
- Extract structured fields using Claude
- Generate chunked embeddings for similarity search

**Request** — `multipart/form-data`

| Field | Type | Required |
|-------|------|----------|
| `file` | PDF or TXT file | Yes |

**Example (curl)**
```bash
# PDF
curl -X POST http://<server-ip>:8000/api/v1/decisions/upload \
  -F "file=@decision.pdf"

# Text file
curl -X POST http://<server-ip>:8000/api/v1/decisions/upload \
  -F "file=@decision.txt"
```

**Response** `201 Created` — same shape as [Get Decision Details](#get-decision-details).

**Error responses**

| Status | Meaning |
|--------|---------|
| `400` | File is not a PDF/TXT or is empty |
| `422` | Extraction failed |

---

### List Decisions

```
GET /decisions
```

Returns a paginated list of court decisions. All query parameters are optional.

**Query parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `court` | string | Partial match on court name |
| `judge` | string | Partial match on judge name |
| `case_type` | string | Partial match on case type (e.g. `copyright`) |
| `outcome` | string | Partial match on outcome (e.g. `granted`, `dismissed`) |
| `plaintiff` | string | Partial match on plaintiff name |
| `defendant` | string | Partial match on defendant name |
| `page` | integer | Page number, default `1` |
| `page_size` | integer | Results per page, default `50`, max `200` |

**Example (curl)**
```bash
# Filter by court
curl "http://<server-ip>:8000/api/v1/decisions?court=High+Court"

# Filter by outcome and case type
curl "http://<server-ip>:8000/api/v1/decisions?outcome=granted&case_type=copyright"

# Search by party
curl "http://<server-ip>:8000/api/v1/decisions?plaintiff=Sony"
```

**Response** `200 OK`
```json
[
  {
    "id": "3f4a1b2c-...",
    "source_filename": "decision.pdf",
    "court": "High Court of Justice",
    "judge": "Hon. J. Smith",
    "case_number": "2024/001",
    "case_type": "copyright",
    "plaintiff": "Sony Music",
    "defendant": "John Doe",
    "outcome": "granted",
    "decision_date": "2024-06-15",
    "monetary_award": 50000.00,
    "processing_status": "extracted",
    "created_at": "2025-02-28T14:00:00"
  }
]
```

---

### Get Decision Details

```
GET /decisions/{decision_id}
```

Returns full details for a single decision including extracted arguments, legal references, summary, and full text.

**Example (curl)**
```bash
curl http://<server-ip>:8000/api/v1/decisions/3f4a1b2c-...
```

**Response** `200 OK`
```json
{
  "id": "3f4a1b2c-...",
  "source_filename": "decision.pdf",
  "court": "High Court of Justice",
  "judge": "Hon. J. Smith",
  "case_number": "2024/001",
  "case_type": "copyright",
  "plaintiff": "Sony Music",
  "defendant": "John Doe",
  "outcome": "granted",
  "decision_date": "2024-06-15",
  "monetary_award": 50000.00,
  "appeal_of": null,
  "summary": "The court ruled in favour of Sony Music, finding that John Doe had infringed copyright...",
  "full_text": "IN THE HIGH COURT OF JUSTICE...",
  "processing_status": "extracted",
  "is_ocr": false,
  "ocr_confidence": null,
  "extraction_error": null,
  "created_at": "2025-02-28T14:00:00",
  "arguments": [
    { "id": "...", "argument": "Plaintiff established ownership of the copyright.", "position": 0 },
    { "id": "...", "argument": "Defendant failed to obtain a licence.", "position": 1 }
  ],
  "legal_refs": [
    { "id": "...", "reference": "Copyright, Designs and Patents Act 1988, s.16" },
    { "id": "...", "reference": "Ladbroke v William Hill [1964] 1 WLR 273" }
  ]
}
```

**Error responses**

| Status | Meaning |
|--------|---------|
| `404` | Decision not found |

---

### Download Original File

```
GET /decisions/{decision_id}/download
```

Returns the original uploaded file (PDF or TXT).

**Example (curl)**
```bash
curl http://<server-ip>:8000/api/v1/decisions/3f4a1b2c-.../download --output decision.pdf
```

**Error responses**

| Status | Meaning |
|--------|---------|
| `404` | Decision not found, or file missing from disk |

---

### Find Similar Decisions

```
GET /decisions/{decision_id}/similar
```

Returns the 5 most similar decisions using vector cosine similarity on chunked embeddings.

**Example (curl)**
```bash
curl http://<server-ip>:8000/api/v1/decisions/3f4a1b2c-.../similar
```

**Response** `200 OK`
```json
[
  {
    "id": "7e9c3d1a-...",
    "source_filename": "decision2.pdf",
    "court": "Court of Appeal",
    "case_number": "2023/088",
    "similarity": 88.3
  }
]
```

`similarity` is a percentage (0–100). Higher = more similar.

**Error responses**

| Status | Meaning |
|--------|---------|
| `404` | Decision not found |
| `422` | Decision has no embeddings (processing may have failed) |

---

## Chat

### Ask a Question

```
POST /chat
```

Ask a natural language question about the contracts. Claude generates a SQL query, runs it, and returns the results with a plain English explanation.

Only `SELECT` queries are allowed — the database cannot be modified through this endpoint.

**Request body** — `application/json`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | string | Yes | Your question in natural language |
| `history` | array | No | Previous turns for follow-up questions |

**Example (curl)**
```bash
curl -X POST http://<server-ip>:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Show me all contracts expiring this year"}'
```

**Example (Python)**
```python
import requests

res = requests.post(
    "http://<server-ip>:8000/api/v1/chat",
    json={"message": "Show me all contracts expiring this year"}
)
data = res.json()
print(data["answer"])
print(data["results"])
```

**Response** `200 OK`
```json
{
  "answer": "These are the contracts whose expiry date falls within the current year.",
  "sql": "SELECT contract_id, internal_ref_no, file_name, expiry_date FROM contracts WHERE EXTRACT(YEAR FROM expiry_date) = 2025 LIMIT 200",
  "results": [
    {
      "contract_id": 2,
      "internal_ref_no": "DK001",
      "file_name": "contract_dk.pdf",
      "expiry_date": "2025-09-01"
    }
  ]
}
```

`sql` and `results` may be `null` if the question cannot be answered from the database schema.

**Follow-up questions (multi-turn)**

Pass previous turns in the `history` array to enable follow-up questions:

```bash
curl -X POST http://<server-ip>:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Which of those have missing signatures?",
    "history": [
      {"role": "user", "content": "Show me all contracts expiring this year"},
      {"role": "assistant", "content": "These are the contracts whose expiry date falls within the current year."}
    ]
  }'
```

**Example questions**

- `"Show me all contracts from Bulgaria"`
- `"Which contracts have a penalty above 10000?"`
- `"List all musical works across all contracts"`
- `"How many contracts are exclusive?"`
- `"Find contracts where the delivery deadline is less than 30 days"`
- `"Show me contracts signed by Sony"`

---

## Response field reference

### Contract status values

| Value | Meaning |
|-------|---------|
| `processing` | Upload received, extraction in progress |
| `processed` | Fully extracted and stored |
| `needs_review` | Extraction partially failed — some fields may be missing |

### Contract party `signing_status` values

| Value | Meaning |
|-------|---------|
| `none` | No signature or stamp detected |
| `signature_only` | Signature detected, no stamp |
| `stamp_only` | Stamp detected, no signature |
| `signature_and_stamp` | Both signature and stamp detected |

### Decision `processing_status` values

| Value | Meaning |
|-------|---------|
| `pending` | Received, extraction in progress |
| `extracted` | Fully extracted and stored |
| `failed` | Extraction failed — see `extraction_error` field |

### Common null fields

Fields extracted by Claude will be `null` if the information was not found in the document. This is expected for optional fields.

---

## Notes

- Processing time per document is typically **30–90 seconds** depending on PDF complexity and size.
- Duplicate contract uploads are rejected with `409`. Detection is based on file content (SHA-256 hash), not filename.
- The chat endpoint is **read-only** — it cannot modify, delete, or insert data.
- Similarity scores are percentages. Anything above ~80% is a strong match.
- Decisions use chunked embeddings (the document is split into 500-word overlapping chunks). Similarity is computed by averaging chunk vectors.
