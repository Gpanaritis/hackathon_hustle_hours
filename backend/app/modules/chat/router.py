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
-- =====================================================
-- COURT DECISIONS — DATABASE SCHEMA
-- PostgreSQL + pgvector
-- Schema: decisions
-- =====================================================

CREATE EXTENSION IF NOT EXISTS vector;

CREATE SCHEMA IF NOT EXISTS decisions;

-- ENUM
CREATE TYPE decisions.decisionstatus AS ENUM ('pending', 'extracted', 'failed');

-- 1. COURT DECISIONS (core record)
CREATE TABLE decisions.court_decisions (
    id                  VARCHAR(36)                     PRIMARY KEY,
    source_filename     TEXT,

    court               TEXT,
    judge               TEXT,
    case_number         TEXT,
    case_type           TEXT,
    plaintiff           TEXT,
    defendant           TEXT,
    outcome             TEXT,
    decision_date       DATE,

    full_text           TEXT,
    summary             TEXT,
    monetary_award      NUMERIC(15, 2),
    appeal_of           TEXT,

    processing_status   decisions.decisionstatus        NOT NULL DEFAULT 'pending',
    is_ocr              BOOLEAN                         NOT NULL DEFAULT FALSE,
    ocr_confidence      FLOAT,
    extraction_error    TEXT,

    created_at          TIMESTAMPTZ                     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ                     NOT NULL DEFAULT NOW()
);

-- 2. EMBEDDINGS
CREATE TABLE decisions.decision_embeddings (
    id              VARCHAR(36) PRIMARY KEY,
    decision_id     VARCHAR(36) NOT NULL REFERENCES decisions.court_decisions(id) ON DELETE CASCADE,
    chunk_index     INT         NOT NULL,
    chunk_text      TEXT        NOT NULL,
    embedding       VECTOR(384),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (decision_id, chunk_index)
);

-- 3. ARGUMENTS
CREATE TABLE decisions.decision_arguments (
    id              VARCHAR(36) PRIMARY KEY,
    decision_id     VARCHAR(36) NOT NULL REFERENCES decisions.court_decisions(id) ON DELETE CASCADE,
    side            VARCHAR(20) NOT NULL,
    argument        TEXT        NOT NULL,
    position        INT         NOT NULL
);

-- 4. CATEGORIES
CREATE TABLE decisions.decision_categories (
    id          VARCHAR(36) PRIMARY KEY,
    decision_id VARCHAR(36) NOT NULL REFERENCES decisions.court_decisions(id) ON DELETE CASCADE,
    category    TEXT        NOT NULL,
    subcategory TEXT        NOT NULL
);

-- 5. LEGAL REFERENCES
CREATE TABLE decisions.decision_legal_refs (
    id              VARCHAR(36) PRIMARY KEY,
    decision_id     VARCHAR(36) NOT NULL REFERENCES decisions.court_decisions(id) ON DELETE CASCADE,
    reference       TEXT        NOT NULL
);
"""

SYSTEM_PROMPT = f"""You are a SQL expert assistant for a court decisions management system. You help users query a database of court decisions, including case details, parties (plaintiff/defendant), arguments, legal references, and categories.

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
