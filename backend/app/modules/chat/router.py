"""
Chat router: natural language → Claude generates SQL → execute → return results.
"""

import json

import anthropic
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.schemas.contracts import ChatMessage, ChatResponse

router = APIRouter()

MODEL = "claude-opus-4-6"

DB_SCHEMA = """
Database schema (PostgreSQL):

contracts (
  contract_id SERIAL PRIMARY KEY,
  internal_ref_no VARCHAR(50),
  file_name VARCHAR(255),
  pdf_path TEXT,
  file_hash VARCHAR(64),
  country_code CHAR(2),
  jurisdiction_state_city VARCHAR(100),
  language VARCHAR(20),
  execution_date DATE,
  term_years INTEGER,
  expiry_date DATE,
  is_exclusive BOOLEAN,
  status VARCHAR(20),
  signature_present BOOLEAN,
  stamp_present BOOLEAN,
  upload_date TIMESTAMP
)

contract_parties (
  party_id SERIAL PRIMARY KEY,
  contract_id INTEGER REFERENCES contracts(contract_id),
  role VARCHAR(50),
  legal_name VARCHAR(255),
  representative_name VARCHAR(255),
  id_type VARCHAR(50),
  id_value VARCHAR(100),
  address TEXT
)

musical_works (
  work_id SERIAL PRIMARY KEY,
  contract_id INTEGER REFERENCES contracts(contract_id),
  title VARCHAR(255),
  artist_performer VARCHAR(255),
  lyricist VARCHAR(255),
  isrc_code VARCHAR(20),
  collection_society VARCHAR(50)
)

contract_terms (
  term_id SERIAL PRIMARY KEY,
  contract_id INTEGER REFERENCES contracts(contract_id),
  remuneration_amount DECIMAL(15,2),
  currency VARCHAR(3),
  min_penalty_liquidated_damages DECIMAL(15,2),
  delivery_deadline_days INTEGER,
  registration_deadline_days INTEGER,
  streaming_requirement_days INTEGER
)

contract_intelligence (
  intel_id SERIAL PRIMARY KEY,
  contract_id INTEGER REFERENCES contracts(contract_id),
  raw_text TEXT,
  summary_short TEXT,
  translated_text_en TEXT
)
"""

SYSTEM_PROMPT = f"""You are a SQL expert assistant for a music contract management system.

{DB_SCHEMA}

When given a question, respond with a JSON object in this format:
{{
  "sql": "SELECT ... LIMIT 200",
  "explanation": "Plain English explanation of what this query returns"
}}

Rules:
- Always include LIMIT 200 or less.
- Use only SELECT statements. Never INSERT, UPDATE, DELETE, DROP, or any mutation.
- If the question cannot be answered with the available schema, set sql to null and explain why.
- Only return the JSON object, no markdown fences."""


@router.post("", response_model=ChatResponse)
def chat(body: ChatMessage, db: Session = Depends(get_db)):
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    # Build message history for Claude
    messages = []
    for h in body.history[-10:]:  # keep last 10 turns
        if h.get("role") in ("user", "assistant"):
            messages.append({"role": h["role"], "content": h["content"]})

    messages.append({"role": "user", "content": body.message})

    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=messages,
    )

    raw = response.content[0].text.strip()

    # Strip markdown fences if present
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return ChatResponse(
            answer="I couldn't generate a valid response. Please try rephrasing your question.",
        )

    sql = parsed.get("sql")
    explanation = parsed.get("explanation", "")

    if not sql:
        return ChatResponse(answer=explanation)

    # Safety check — only allow SELECT
    sql_stripped = sql.strip().upper()
    if not sql_stripped.startswith("SELECT"):
        return ChatResponse(
            answer="I can only run SELECT queries. Please ask a read-only question.",
        )

    try:
        result = db.execute(text(sql))
        columns = list(result.keys())
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
    except Exception as e:
        return ChatResponse(
            answer=f"I couldn't run that query. Try rephrasing your question.",
        )

    if not rows:
        return ChatResponse(
            answer=f"{explanation}\n\nNo results found.",
            sql=sql,
            results=[],
        )

    return ChatResponse(
        answer=explanation,
        sql=sql,
        results=rows,
    )
