"""
Claude-powered structured extraction from contract text or images.
Returns a dict matching the 5-table schema.
"""

import json
import os
from typing import Optional

import anthropic

from app.config import settings

MODEL = "claude-opus-4-6"

SYSTEM_PROMPT = """You are an expert contract analyst. Extract structured data from the provided contract.

Return ONLY a valid JSON object with this exact structure (use null for missing fields):

{
  "contract": {
    "internal_ref_no": "string or null",
    "country_code": "2-letter ISO code or null",
    "jurisdiction_state_city": "string or null",
    "language": "language name, e.g. English, Bulgarian, Danish or null",
    "execution_date": "YYYY-MM-DD or null",
    "term_years": integer or null,
    "expiry_date": "YYYY-MM-DD or null",
    "is_exclusive": true or false or null
  },
  "parties": [
    {
      "role": "Producer | Author | Composer | Arranger | Publisher | other",
      "legal_name": "string or null",
      "representative_name": "string or null",
      "id_type": "SSN | EGN | CPR | VAT | Passport | other or null",
      "id_value": "string or null",
      "address": "string or null",
      "signing_status": "none | signature_only | stamp_only | signature_and_stamp"
    }
  ],
  "musical_works": [
    {
      "title": "string or null",
      "artist_performer": "string or null",
      "lyricist": "string or null",
      "isrc_code": "string or null",
      "collection_society": "GEMA | KODA | BMI | ASCAP | Musicautor | other or null"
    }
  ],
  "terms": {
    "remuneration_amount": number or null,
    "currency": "3-letter ISO code, e.g. USD, EUR, BGN or null",
    "min_penalty_liquidated_damages": number or null,
    "delivery_deadline_days": integer or null,
    "registration_deadline_days": integer or null,
    "streaming_requirement_days": integer or null
  },
  "intelligence": {
    "raw_text": "full extracted text of the contract",
    "summary_short": "2-3 sentence summary of the contract",
    "translated_text_en": "full English translation if not already in English, otherwise null"
  }
}

Return only the JSON object. No markdown fences, no explanation."""


def extract_contract_data(
    text: Optional[str],
    page_images: Optional[list[str]],
) -> dict:
    """
    Call Claude to extract structured data from a contract.

    Args:
        text: Extracted text for text-based PDFs.
        page_images: List of base64-encoded PNG strings for image-only PDFs.

    Returns:
        Parsed dict with keys: contract, parties, musical_works, terms, intelligence.
    """
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    if text is not None:
        # Text-based PDF
        user_content = [
            {
                "type": "text",
                "text": f"Extract all structured data from this contract:\n\n{text}",
            }
        ]
    else:
        # Image-only PDF — send all pages
        user_content = []
        for i, img_b64 in enumerate(page_images):
            user_content.append({
                "type": "text",
                "text": f"Page {i + 1}:",
            })
            user_content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": img_b64,
                },
            })
        user_content.append({
            "type": "text",
            "text": "Extract all structured data from this contract (all pages shown above).",
        })

    message = client.messages.create(
        model=MODEL,
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )

    raw = message.content[0].text.strip()

    # Strip markdown fences if present despite instructions
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

    return json.loads(raw)
