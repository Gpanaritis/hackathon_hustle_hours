"""
PDF processing pipeline.

Strategy:
  1. Compute SHA-256 hash for duplicate detection.
  2. Detect PDF type: if pymupdf extracts meaningful text → text-based PDF.
     Otherwise → image-only (scanned).
  3. Text PDF: extract all text with pymupdf, send to Claude.
     Image PDF: render each page to image, send pages to Claude vision.
  4. Claude returns structured JSON with all contract fields.
  5. sentence-transformers generates embedding from raw_text.
  6. Insert into all 5 DB tables.
"""

import base64
import hashlib
import io
import json
import os
from pathlib import Path
from typing import Optional

import fitz  # pymupdf
from PIL import Image
from sqlalchemy.orm import Session

from app.config import settings
from app.models.contracts import (
    Contract,
    ContractIntelligence,
    ContractParty,
    ContractTerms,
    MusicalWork,
)
from app.modules.contracts.extractor import extract_contract_data
from app.modules.contracts.embedder import generate_embedding

MIN_TEXT_CHARS = 50
IMAGE_DPI = 200


def compute_hash(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def is_image_only_pdf(pdf_bytes: bytes) -> bool:
    """Return True if the PDF has no meaningful extractable text (scanned)."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    total_text = ""
    for page in doc:
        total_text += page.get_text("text").strip()
        if len(total_text) >= MIN_TEXT_CHARS:
            doc.close()
            return False
    doc.close()
    return len(total_text) < MIN_TEXT_CHARS


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract all text from a text-based PDF using pymupdf."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages_text = []
    for page in doc:
        pages_text.append(page.get_text("text").strip())
    doc.close()
    return "\n\n".join(pages_text)


def render_pages_to_base64(pdf_bytes: bytes) -> list[str]:
    """Render each page of a scanned PDF to a base64-encoded PNG."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []
    mat = fitz.Matrix(IMAGE_DPI / 72, IMAGE_DPI / 72)
    for page in doc:
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        images.append(base64.standard_b64encode(buf.getvalue()).decode())
    doc.close()
    return images


def save_pdf(file_bytes: bytes, contract_id: int) -> str:
    """Save PDF to local storage and return the file path."""
    storage_dir = Path(settings.storage_path)
    storage_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = storage_dir / f"{contract_id}.pdf"
    pdf_path.write_bytes(file_bytes)
    return str(pdf_path)


def process_contract(
    file_bytes: bytes,
    file_name: str,
    db: Session,
) -> Contract:
    """
    Full pipeline: hash check → save → extract → embed → persist.
    Returns the created Contract record.
    Raises ValueError if the file is a duplicate.
    """
    file_hash = compute_hash(file_bytes)

    # Duplicate check
    existing = db.query(Contract).filter(Contract.file_hash == file_hash).first()
    if existing:
        raise ValueError(f"Contract already uploaded (id={existing.contract_id})")

    # Create contract record with status=processing (no pdf_path yet)
    contract = Contract(
        file_name=file_name,
        file_hash=file_hash,
        pdf_path="",  # will be updated after we have the contract_id
        status="processing",
    )
    db.add(contract)
    db.flush()  # get contract_id without committing

    # Save PDF to disk
    pdf_path = save_pdf(file_bytes, contract.contract_id)
    contract.pdf_path = pdf_path
    db.flush()

    try:
        # Determine PDF type and extract text or images
        image_only = is_image_only_pdf(file_bytes)

        if image_only:
            page_images = render_pages_to_base64(file_bytes)
            extraction = extract_contract_data(text=None, page_images=page_images)
        else:
            raw_text = extract_text_from_pdf(file_bytes)
            extraction = extract_contract_data(text=raw_text, page_images=None)

        # Apply extracted fields to contract
        c = extraction.get("contract", {})
        contract.internal_ref_no = c.get("internal_ref_no")
        contract.country_code = c.get("country_code")
        contract.jurisdiction_state_city = c.get("jurisdiction_state_city")
        contract.language = c.get("language")
        contract.term_years = c.get("term_years")
        contract.is_exclusive = c.get("is_exclusive", True)
        contract.signature_present = c.get("signature_present")
        contract.stamp_present = c.get("stamp_present")

        if c.get("execution_date"):
            from datetime import date
            try:
                contract.execution_date = date.fromisoformat(c["execution_date"])
            except (ValueError, TypeError):
                pass

        if c.get("expiry_date"):
            from datetime import date
            try:
                contract.expiry_date = date.fromisoformat(c["expiry_date"])
            except (ValueError, TypeError):
                pass

        # Parties
        for p in extraction.get("parties", []):
            party = ContractParty(
                contract_id=contract.contract_id,
                role=p.get("role"),
                legal_name=p.get("legal_name"),
                representative_name=p.get("representative_name"),
                id_type=p.get("id_type"),
                id_value=p.get("id_value"),
                address=p.get("address"),
            )
            db.add(party)

        # Musical works
        for w in extraction.get("musical_works", []):
            work = MusicalWork(
                contract_id=contract.contract_id,
                title=w.get("title"),
                artist_performer=w.get("artist_performer"),
                lyricist=w.get("lyricist"),
                isrc_code=w.get("isrc_code"),
                collection_society=w.get("collection_society"),
            )
            db.add(work)

        # Terms
        t = extraction.get("terms", {})
        if t:
            terms = ContractTerms(
                contract_id=contract.contract_id,
                remuneration_amount=t.get("remuneration_amount"),
                currency=t.get("currency"),
                min_penalty_liquidated_damages=t.get("min_penalty_liquidated_damages"),
                delivery_deadline_days=t.get("delivery_deadline_days"),
                registration_deadline_days=t.get("registration_deadline_days"),
                streaming_requirement_days=t.get("streaming_requirement_days"),
            )
            db.add(terms)

        # Intelligence
        intel_data = extraction.get("intelligence", {})
        raw_text_for_embed = intel_data.get("raw_text", "")
        embedding = generate_embedding(raw_text_for_embed) if raw_text_for_embed else None

        intelligence = ContractIntelligence(
            contract_id=contract.contract_id,
            raw_text=intel_data.get("raw_text"),
            summary_short=intel_data.get("summary_short"),
            translated_text_en=intel_data.get("translated_text_en"),
            embedding=embedding,
        )
        db.add(intelligence)

        contract.status = "processed"

    except Exception as e:
        contract.status = "needs_review"
        db.commit()
        raise RuntimeError(f"Extraction failed: {e}") from e

    db.commit()
    db.refresh(contract)
    return contract
