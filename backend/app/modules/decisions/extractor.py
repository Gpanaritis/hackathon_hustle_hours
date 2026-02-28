"""
Claude-powered structured extraction for court decisions.
"""

import json
from typing import Optional

import anthropic

from app.config import settings

MODEL = "claude-opus-4-6"

SYSTEM_PROMPT = """You are an expert legal analyst. Extract structured data from the provided court decision document.

Return ONLY a valid JSON object with this exact structure (use null for missing fields):

{
  "court": "name of the court or null",
  "judge": "name of the judge or null",
  "case_number": "case number or null",
  "case_type": "e.g. Civil, Criminal, Administrative, Appeal or null",
  "plaintiff": "plaintiff name(s) or null",
  "defendant": "defendant name(s) or null",
  "outcome": "e.g. Upheld, Dismissed, Settled, Appealed or null",
  "decision_date": "YYYY-MM-DD or null",
  "summary": "2-3 sentence summary of the decision",
  "monetary_award": number or null,
  "appeal_of": "reference to the original case being appealed, or null",
  "arguments": [
    "main argument 1",
    "main argument 2"
  ],
  "legal_refs": [
    "statute or case reference 1",
    "statute or case reference 2"
  ]
}

Return only the JSON object. No markdown fences, no explanation."""


def extract_decision_data(
    text: Optional[str],
    page_images: Optional[list[str]],
) -> dict:
    """
    Call Claude to extract structured data from a court decision.

    Args:
        text: Extracted text for text-based PDFs.
        page_images: List of base64-encoded PNG strings for image-only PDFs.

    Returns:
        Parsed dict with extracted decision fields.
    """
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    if text is not None:
        user_content = [
            {
                "type": "text",
                "text": f"Extract all structured data from this court decision:\n\n{text}",
            }
        ]
    else:
        user_content = []
        for i, img_b64 in enumerate(page_images):
            user_content.append({"type": "text", "text": f"Page {i + 1}:"})
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
            "text": "Extract all structured data from this court decision (all pages shown above).",
        })

    message = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )

    raw = message.content[0].text.strip()

    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

    return json.loads(raw)
