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
-- embedding: 384 dimensions (sentence-transformers all-MiniLM-L6-v2)
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
    side            VARCHAR(20) NOT NULL,   -- 'plaintiff' or 'defendant'
    argument        TEXT        NOT NULL,
    position        INT         NOT NULL
);

-- 4. CATEGORIES
CREATE TABLE decisions.decision_categories (
    id          VARCHAR(36) PRIMARY KEY,
    decision_id VARCHAR(36) NOT NULL REFERENCES decisions.court_decisions(id) ON DELETE CASCADE,
    category    TEXT        NOT NULL,
    subcategory TEXT        NOT NULL,
    confidence  FLOAT       NOT NULL
);

-- 5. LEGAL REFERENCES
CREATE TABLE decisions.decision_legal_refs (
    id              VARCHAR(36) PRIMARY KEY,
    decision_id     VARCHAR(36) NOT NULL REFERENCES decisions.court_decisions(id) ON DELETE CASCADE,
    reference       TEXT        NOT NULL
);

-- =====================================================
-- INDEXES
-- =====================================================

CREATE INDEX ix_decisions_judge      ON decisions.court_decisions(judge);
CREATE INDEX ix_decisions_court      ON decisions.court_decisions(court);
CREATE INDEX ix_decisions_outcome    ON decisions.court_decisions(outcome);
CREATE INDEX ix_decisions_case_type  ON decisions.court_decisions(case_type);
CREATE INDEX ix_decisions_date       ON decisions.court_decisions(decision_date);
CREATE INDEX ix_decisions_status     ON decisions.court_decisions(processing_status);

CREATE INDEX ix_decisions_fulltext   ON decisions.court_decisions
    USING gin(to_tsvector('simple', coalesce(full_text, '')));

CREATE INDEX ix_embeddings_vector    ON decisions.decision_embeddings
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX ix_categories_decision  ON decisions.decision_categories(decision_id);
CREATE INDEX ix_arguments_decision   ON decisions.decision_arguments(decision_id);
CREATE INDEX ix_legalrefs_decision   ON decisions.decision_legal_refs(decision_id);
CREATE INDEX ix_legalrefs_reference  ON decisions.decision_legal_refs(reference);
