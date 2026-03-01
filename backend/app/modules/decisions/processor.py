"""
PDF processing pipeline for court decisions.
Reuses the same PDF detection logic as the contracts module.
"""

import base64
import io
import uuid
from datetime import date
from pathlib import Path

import fitz
from PIL import Image
from sqlalchemy.orm import Session

from app.config import settings
from app.models.decisions import CourtDecision, DecisionArgument, DecisionCategory, DecisionEmbedding, DecisionLegalRef
from app.modules.contracts.embedder import generate_embedding
from app.modules.decisions.extractor import classify_decision, extract_decision_data

MIN_TEXT_CHARS = 50
IMAGE_DPI = 200


def _is_image_only(pdf_bytes: bytes) -> bool:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    total = ""
    for page in doc:
        total += page.get_text("text").strip()
        if len(total) >= MIN_TEXT_CHARS:
            doc.close()
            return False
    doc.close()
    return True


def _extract_text(pdf_bytes: bytes) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = [page.get_text("text").strip() for page in doc]
    doc.close()
    return "\n\n".join(pages)


def _render_pages(pdf_bytes: bytes) -> list[str]:
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


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping word-based chunks for embedding."""
    words = text.split()
    chunks = []
    step = chunk_size - overlap
    for i in range(0, len(words), step):
        chunk = " ".join(words[i : i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
    return chunks


def _save_file(file_bytes: bytes, decision_id: str, file_name: str) -> str:
    storage_dir = Path(settings.storage_path).parent / "decisions"
    storage_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(file_name).suffix.lower() or ".bin"
    file_path = storage_dir / f"{decision_id}{ext}"
    file_path.write_bytes(file_bytes)
    return str(file_path)


def _build_classification_context(decision: "CourtDecision", extraction: dict) -> str:
    """Build a rich text context for classification from all extracted fields."""
    parts = []

    if decision.case_type:
        parts.append(f"Case type: {decision.case_type}")
    if decision.outcome:
        parts.append(f"Outcome: {decision.outcome}")
    if decision.summary:
        parts.append(f"Summary: {decision.summary}")

    plaintiff_args = extraction.get("plaintiff_arguments", [])
    if plaintiff_args:
        parts.append("Plaintiff arguments:\n" + "\n".join(f"- {a}" for a in plaintiff_args))

    defendant_args = extraction.get("defendant_arguments", [])
    if defendant_args:
        parts.append("Defendant arguments:\n" + "\n".join(f"- {a}" for a in defendant_args))

    legal_refs = extraction.get("legal_refs", [])
    if legal_refs:
        parts.append("Legal references:\n" + "\n".join(f"- {r}" for r in legal_refs))

    return "\n\n".join(parts)


def process_decision_from_text(
    text: str,
    label: str,
    db: Session,
) -> CourtDecision:
    """Process a court decision supplied as raw text (no file upload)."""
    decision_id = str(uuid.uuid4())

    decision = CourtDecision(
        id=decision_id,
        source_filename=label or None,
        processing_status="pending",
        is_ocr=False,
    )
    db.add(decision)
    db.flush()

    try:
        extraction = extract_decision_data(text=text, page_images=None)
        if not extraction.get("full_text"):
            extraction["full_text"] = text

        decision.court = extraction.get("court")
        decision.judge = extraction.get("judge")
        decision.case_number = extraction.get("case_number")
        decision.case_type = extraction.get("case_type")
        decision.plaintiff = extraction.get("plaintiff")
        decision.defendant = extraction.get("defendant")
        decision.outcome = extraction.get("outcome")
        decision.summary = extraction.get("summary")
        decision.monetary_award = extraction.get("monetary_award")
        decision.appeal_of = extraction.get("appeal_of")
        decision.full_text = extraction.get("full_text")

        if extraction.get("decision_date"):
            from datetime import date
            try:
                decision.decision_date = date.fromisoformat(extraction["decision_date"])
            except (ValueError, TypeError):
                pass

        classification_context = _build_classification_context(decision, extraction)
        if classification_context:
            categories = classify_decision(classification_context)
            for cat in categories:
                db.add(DecisionCategory(
                    id=str(uuid.uuid4()),
                    decision_id=decision_id,
                    category=cat.get("category", ""),
                    subcategory=cat.get("subcategory", ""),
                ))

        for i, arg in enumerate(extraction.get("plaintiff_arguments", [])):
            db.add(DecisionArgument(
                id=str(uuid.uuid4()),
                decision_id=decision_id,
                side="plaintiff",
                argument=arg,
                position=i,
            ))
        for i, arg in enumerate(extraction.get("defendant_arguments", [])):
            db.add(DecisionArgument(
                id=str(uuid.uuid4()),
                decision_id=decision_id,
                side="defendant",
                argument=arg,
                position=i,
            ))

        for ref in extraction.get("legal_refs", []):
            db.add(DecisionLegalRef(
                id=str(uuid.uuid4()),
                decision_id=decision_id,
                reference=ref,
            ))

        text_to_embed = decision.summary or ""
        if text_to_embed.strip():
            embedding = generate_embedding(text_to_embed)
            db.add(DecisionEmbedding(
                id=str(uuid.uuid4()),
                decision_id=decision_id,
                chunk_index=0,
                chunk_text=text_to_embed,
                embedding=embedding,
            ))

        decision.processing_status = "extracted"

    except Exception as e:
        decision.processing_status = "failed"
        decision.extraction_error = str(e)
        db.commit()
        raise RuntimeError(f"Decision extraction failed: {e}") from e

    db.commit()
    db.refresh(decision)
    return decision


def process_decision(
    file_bytes: bytes,
    file_name: str,
    db: Session,
) -> CourtDecision:
    """
    Full pipeline for court decisions:
    detect file type → extract → embed (chunked) → persist.
    Supports PDF and plain-text (.txt) files.
    """
    decision_id = str(uuid.uuid4())

    decision = CourtDecision(
        id=decision_id,
        source_filename=file_name,
        processing_status="pending",
        is_ocr=False,
    )
    db.add(decision)
    db.flush()

    try:
        is_txt = file_name.lower().endswith(".txt")

        if is_txt:
            raw_text = file_bytes.decode("utf-8", errors="replace")
            extraction = extract_decision_data(text=raw_text, page_images=None)
            if not extraction.get("full_text"):
                extraction["full_text"] = raw_text
        else:
            image_only = _is_image_only(file_bytes)
            decision.is_ocr = image_only

            if image_only:
                page_images = _render_pages(file_bytes)
                raw_text = None
                extraction = extract_decision_data(text=None, page_images=page_images)
            else:
                raw_text = _extract_text(file_bytes)
                extraction = extract_decision_data(text=raw_text, page_images=None)
                if not extraction.get("full_text"):
                    extraction["full_text"] = raw_text

        # Map extracted fields
        decision.court = extraction.get("court")
        decision.judge = extraction.get("judge")
        decision.case_number = extraction.get("case_number")
        decision.case_type = extraction.get("case_type")
        decision.plaintiff = extraction.get("plaintiff")
        decision.defendant = extraction.get("defendant")
        decision.outcome = extraction.get("outcome")
        decision.summary = extraction.get("summary")
        decision.monetary_award = extraction.get("monetary_award")
        decision.appeal_of = extraction.get("appeal_of")
        decision.full_text = extraction.get("full_text") or raw_text

        if extraction.get("decision_date"):
            try:
                decision.decision_date = date.fromisoformat(extraction["decision_date"])
            except (ValueError, TypeError):
                pass

        # Arguments
        classification_context = _build_classification_context(decision, extraction)
        if classification_context:
            categories = classify_decision(classification_context)
            for cat in categories:
                db.add(DecisionCategory(
                    id=str(uuid.uuid4()),
                    decision_id=decision_id,
                    category=cat.get("category", ""),
                    subcategory=cat.get("subcategory", ""),
                ))

        for i, arg in enumerate(extraction.get("plaintiff_arguments", [])):
            db.add(DecisionArgument(
                id=str(uuid.uuid4()),
                decision_id=decision_id,
                side="plaintiff",
                argument=arg,
                position=i,
            ))
        for i, arg in enumerate(extraction.get("defendant_arguments", [])):
            db.add(DecisionArgument(
                id=str(uuid.uuid4()),
                decision_id=decision_id,
                side="defendant",
                argument=arg,
                position=i,
            ))

        # Legal references
        for ref in extraction.get("legal_refs", []):
            db.add(DecisionLegalRef(
                id=str(uuid.uuid4()),
                decision_id=decision_id,
                reference=ref,
            ))

        # Embed the summary — it's concise and discriminative, no chunking needed
        text_to_embed = decision.summary or ""
        if text_to_embed.strip():
            embedding = generate_embedding(text_to_embed)
            db.add(DecisionEmbedding(
                id=str(uuid.uuid4()),
                decision_id=decision_id,
                chunk_index=0,
                chunk_text=text_to_embed,
                embedding=embedding,
            ))

        # Save file to disk
        _save_file(file_bytes, decision_id, file_name)

        decision.processing_status = "extracted"

    except Exception as e:
        decision.processing_status = "failed"
        decision.extraction_error = str(e)
        db.commit()
        raise RuntimeError(f"Decision extraction failed: {e}") from e

    db.commit()
    db.refresh(decision)
    return decision
