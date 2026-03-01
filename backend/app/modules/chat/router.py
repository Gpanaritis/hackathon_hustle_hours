"""
Chat router: natural language → Claude generates SQL → execute → return results.
"""

import json
from typing import List

import anthropic
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.decisions import CourtDecision, DecisionCategory, DecisionEmbedding
from app.modules.contracts.embedder import generate_embedding
from app.modules.decisions.extractor import classify_decision, summarize_for_search
from app.schemas.contracts import CaseSummaryRequest, ChatMessage, ChatResponse, SummaryMatchResult

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


@router.post("/find-by-categories", response_model=List[SummaryMatchResult])
def find_by_categories(body: CaseSummaryRequest, db: Session = Depends(get_db)):
    """Classify the summary using the legal taxonomy, then return decisions with overlapping categories."""
    if not body.summary.strip():
        raise HTTPException(status_code=400, detail="Summary is empty.")

    categories = classify_decision(body.summary)
    valid_subcategories = [c["subcategory"] for c in categories if c.get("subcategory") != "UNKNOWN"]

    if not valid_subcategories:
        return []

    matches = (
        db.query(CourtDecision)
        .join(DecisionCategory, DecisionCategory.decision_id == CourtDecision.id)
        .filter(DecisionCategory.subcategory.in_(valid_subcategories))
        .distinct()
        .limit(20)
        .all()
    )

    results = []
    for d in matches:
        matched = [c.subcategory for c in d.categories if c.subcategory in valid_subcategories]
        results.append(SummaryMatchResult(
            id=d.id,
            source_filename=d.source_filename,
            court=d.court,
            case_number=d.case_number,
            case_type=d.case_type,
            plaintiff=d.plaintiff,
            defendant=d.defendant,
            outcome=d.outcome,
            matched_categories=matched,
        ))
    return results


@router.get("/debug-embeddings")
def debug_embeddings(db: Session = Depends(get_db)):
    """Diagnostic: report the state of the decision_embeddings table."""
    total = db.query(DecisionEmbedding).count()
    with_vector = db.query(DecisionEmbedding).filter(DecisionEmbedding.embedding.isnot(None)).count()
    return {"total_rows": total, "rows_with_embedding": with_vector, "rows_without_embedding": total - with_vector}


@router.post("/find-by-similarity", response_model=List[SummaryMatchResult])
def find_by_similarity(body: CaseSummaryRequest, db: Session = Depends(get_db)):
    """Embed the summary and return the most semantically similar decisions via vector search."""
    if not body.summary.strip():
        raise HTTPException(status_code=400, detail="Summary is empty.")

    # Verify embeddings exist before doing the search
    embedding_count = (
        db.query(DecisionEmbedding)
        .filter(DecisionEmbedding.embedding.isnot(None))
        .count()
    )
    if embedding_count == 0:
        raise HTTPException(
            status_code=422,
            detail="No embeddings found in the database. Make sure decisions have been processed successfully.",
        )

    # Normalize the input into the same summary style as stored embeddings
    normalized = summarize_for_search(body.summary)
    embedding = generate_embedding(normalized)
    if not embedding:
        raise HTTPException(status_code=422, detail="Could not generate embedding for the provided summary.")

    vec_str = "[" + ",".join(str(x) for x in embedding) + "]"
    try:
        rows = db.execute(
            text("""
                SELECT decision_id,
                       embedding <=> CAST(:query_vec AS vector(384)) AS distance
                FROM decisions.decision_embeddings
                WHERE embedding IS NOT NULL
                ORDER BY distance
                LIMIT 10
            """),
            {"query_vec": vec_str},
        ).fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vector search failed: {e}")

    results = []
    for row in rows:
        if row.distance is None:
            continue
        d = db.query(CourtDecision).filter(CourtDecision.id == row.decision_id).first()
        if d:
            results.append(SummaryMatchResult(
                id=d.id,
                source_filename=d.source_filename,
                court=d.court,
                case_number=d.case_number,
                case_type=d.case_type,
                plaintiff=d.plaintiff,
                defendant=d.defendant,
                outcome=d.outcome,
                similarity=round((1 - row.distance) * 100, 1),
            ))
    return results
