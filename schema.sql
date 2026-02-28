-- =====================================================
-- CONTRACT INTELLIGENCE — DATABASE SCHEMA
-- PostgreSQL + pgvector
-- =====================================================

CREATE EXTENSION IF NOT EXISTS vector;

-- 1. CONTRACTS (core record)
CREATE TABLE contracts (
    contract_id             SERIAL PRIMARY KEY,
    internal_ref_no         VARCHAR(50) UNIQUE,
    file_name               VARCHAR(255) NOT NULL,
    pdf_path                TEXT NOT NULL,
    file_hash               VARCHAR(64) UNIQUE NOT NULL,
    country_code            CHAR(2),
    jurisdiction_state_city VARCHAR(100),
    language                VARCHAR(20),
    execution_date          DATE,
    term_years              INTEGER,
    expiry_date             DATE,
    is_exclusive            BOOLEAN DEFAULT TRUE,
    status                  VARCHAR(20) DEFAULT 'processing', -- processing | processed | needs_review
    signature_present       BOOLEAN,
    stamp_present           BOOLEAN,
    upload_date             TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. CONTRACT PARTIES
CREATE TABLE contract_parties (
    party_id            SERIAL PRIMARY KEY,
    contract_id         INTEGER REFERENCES contracts(contract_id) ON DELETE CASCADE,
    role                VARCHAR(50),
    legal_name          VARCHAR(255),
    representative_name VARCHAR(255),
    id_type             VARCHAR(50),
    id_value            VARCHAR(100),
    address             TEXT
);

-- 3. MUSICAL WORKS
CREATE TABLE musical_works (
    work_id            SERIAL PRIMARY KEY,
    contract_id        INTEGER REFERENCES contracts(contract_id) ON DELETE CASCADE,
    title              VARCHAR(255),
    artist_performer   VARCHAR(255),
    lyricist           VARCHAR(255),
    isrc_code          VARCHAR(20),
    collection_society VARCHAR(50)
);

-- 4. FINANCIAL TERMS
CREATE TABLE contract_terms (
    term_id                         SERIAL PRIMARY KEY,
    contract_id                     INTEGER REFERENCES contracts(contract_id) ON DELETE CASCADE,
    remuneration_amount             DECIMAL(15, 2),
    currency                        VARCHAR(3),
    min_penalty_liquidated_damages  DECIMAL(15, 2),
    delivery_deadline_days          INTEGER,
    registration_deadline_days      INTEGER,
    streaming_requirement_days      INTEGER
);

-- 5. AI / INTELLIGENCE LAYER
-- embedding: 384 dimensions (sentence-transformers all-MiniLM-L6-v2)
CREATE TABLE contract_intelligence (
    intel_id            SERIAL PRIMARY KEY,
    contract_id         INTEGER REFERENCES contracts(contract_id) ON DELETE CASCADE,
    raw_text            TEXT,
    summary_short       TEXT,
    translated_text_en  TEXT,
    embedding           VECTOR(384)
);

-- =====================================================
-- INDEXES
-- =====================================================

CREATE INDEX idx_contracts_ref_no  ON contracts(internal_ref_no);
CREATE INDEX idx_contracts_country ON contracts(country_code);
CREATE INDEX idx_contracts_status  ON contracts(status);
CREATE INDEX idx_contracts_expiry  ON contracts(expiry_date);
CREATE INDEX idx_contracts_hash    ON contracts(file_hash);

CREATE INDEX idx_parties_contract  ON contract_parties(contract_id);
CREATE INDEX idx_parties_name      ON contract_parties(legal_name);

CREATE INDEX idx_works_contract    ON musical_works(contract_id);
CREATE INDEX idx_works_isrc        ON musical_works(isrc_code);

CREATE INDEX idx_terms_contract    ON contract_terms(contract_id);
CREATE INDEX idx_intel_contract    ON contract_intelligence(contract_id);

-- Vector similarity index (cosine) — enable after loading data for best performance
-- CREATE INDEX idx_embedding_cosine ON contract_intelligence
--     USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- =====================================================
-- USEFUL VIEWS
-- =====================================================

CREATE VIEW vw_contract_overview AS
SELECT
    c.contract_id,
    c.internal_ref_no,
    c.file_name,
    c.country_code,
    c.execution_date,
    c.expiry_date,
    c.status,
    c.signature_present,
    c.stamp_present,
    COUNT(DISTINCT mw.work_id)  AS total_works,
    COUNT(DISTINCT cp.party_id) AS total_parties,
    ct.remuneration_amount,
    ct.currency
FROM contracts c
LEFT JOIN musical_works    mw ON c.contract_id = mw.contract_id
LEFT JOIN contract_parties cp ON c.contract_id = cp.contract_id
LEFT JOIN contract_terms   ct ON c.contract_id = ct.contract_id
GROUP BY c.contract_id, ct.term_id;

CREATE VIEW vw_expiring_soon AS
SELECT
    contract_id,
    internal_ref_no,
    file_name,
    country_code,
    expiry_date,
    expiry_date - CURRENT_DATE AS days_until_expiry
FROM contracts
WHERE expiry_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '90 days'
  AND status = 'processed'
ORDER BY expiry_date;
