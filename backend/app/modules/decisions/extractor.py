"""
Claude-powered structured extraction for court decisions.
"""

import json
from typing import Optional

import anthropic

from app.config import settings

MODEL = "claude-opus-4-6"

TAXONOMY = {
    "legal_domain": {
        "description": "Το βασικό πεδίο δικαίου της υπόθεσης.",
        "values": {
            "Αστικό_Δίκαιο": "Διαφορές μεταξύ ιδιωτών.",
            "Εργατικό_Δίκαιο": "Διαφορές εργοδότη και εργαζομένου.",
            "Ποινικό_Δίκαιο": "Ποινικές υποθέσεις.",
            "Διοικητικό_Δίκαιο": "Διαφορές με δημόσια διοίκηση.",
            "Εμπορικό_Δίκαιο": "Επιχειρηματικές διαφορές.",
            "Ακίνητα_και_Περιβάλλον": "Υποθέσεις σχετικές με ακίνητα ή περιβάλλον.",
            "UNKNOWN": "",
        },
    },
    "legal_topic": {
        "description": "Το βασικό αντικείμενο της διαφοράς. Δεν πρέπει να επαναλαμβάνει το legal_domain.",
        "values": {
            "Σύμβαση": "Διαφορές από σύμβαση.",
            "Χρηματική_Οφειλή": "Διαφορές για πληρωμή χρημάτων.",
            "Αποζημίωση": "Αιτήματα αποζημίωσης.",
            "Αδικοπραξία": "Ζημία από παράνομη πράξη.",
            "Μίσθωση": "Διαφορές από μίσθωση.",
            "Κληρονομιά": "Κληρονομικές διαφορές.",
            "Ακίνητο": "Διαφορές κυριότητας ή χρήσης ακινήτου.",
            "Διοικητική_Πράξη": "Αμφισβήτηση διοικητικής πράξης.",
            "Δημόσια_Σύμβαση": "Συμβάσεις με δημόσιο.",
            "Εργασιακές_Αποδοχές": "Διαφορές για μισθούς ή αποδοχές.",
            "Λύση_Σύμβασης_Εργασίας": "Διαφορές από απόλυση ή λύση σύμβασης.",
            "UNKNOWN": "",
        },
    },
    "legal_action": {
        "description": "Το είδος της δικαστικής ενέργειας.",
        "values": {
            "Αγωγή": "Κατάθεση αγωγής.",
            "Προσφυγή": "Προσφυγή σε δικαστήριο.",
            "Αναίρεση": "Αίτηση αναίρεσης.",
            "Αναστολή": "Αίτηση αναστολής.",
            "Ακύρωση": "Αίτηση ακύρωσης.",
            "Ποινική_Δίωξη": "Ποινική διαδικασία.",
            "UNKNOWN": "",
        },
    },
    "crime_type": {
        "description": "Συμπληρώνεται μόνο αν legal_domain = Ποινικό_Δίκαιο",
        "values": {
            "Κλοπή": "",
            "Ληστεία": "",
            "Απάτη": "",
            "Ναρκωτικά": "",
            "Βιασμός": "",
            "Ασέλγεια": "",
            "Σωματική_Βλάβη": "",
            "Ανθρωποκτονία": "",
            "Συμμορία": "",
            "UNKNOWN": "",
        },
    },
}


def _build_taxonomy_text() -> str:
    lines = []
    for dim, meta in TAXONOMY.items():
        lines.append(f"{dim}: {meta['description']}")
        for val, desc in meta["values"].items():
            if desc:
                lines.append(f"  - {val}: {desc}")
            else:
                lines.append(f"  - {val}")
    return "\n".join(lines)


_TAXONOMY_TEXT = _build_taxonomy_text()

EXTRACTION_SYSTEM_PROMPT = """You are an expert legal analyst. Extract structured data from the provided court decision document.

IMPORTANT: All extracted text fields (court, judge, case_number, case_type, plaintiff, defendant, outcome, summary, appeal_of, arguments) must be returned in the same language as the source document. Do not translate anything.

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
  "plaintiff_arguments": [
    "plaintiff argument 1",
    "plaintiff argument 2"
  ],
  "defendant_arguments": [
    "defendant argument 1",
    "defendant argument 2"
  ],
  "legal_refs": [
    "statute or case reference 1",
    "statute or case reference 2"
  ]
}

Return only the JSON object. No markdown fences, no explanation."""

CLASSIFICATION_SYSTEM_PROMPT = f"""You are a legal classification expert. Given a court decision, assign exactly one value per taxonomy dimension below.

For each dimension pick the single best-matching value from its allowed list. Use "UNKNOWN" only when no value fits.
For "crime_type", if legal_domain is NOT "Ποινικό_Δίκαιο", set the value to "UNKNOWN".

TAXONOMY DIMENSIONS:
{_TAXONOMY_TEXT}

Return ONLY a valid JSON array — one object per dimension — with this exact shape. No markdown fences, no explanation.

[
  {{"category": "legal_domain", "subcategory": "<value>"}},
  {{"category": "legal_topic",  "subcategory": "<value>"}},
  {{"category": "legal_action", "subcategory": "<value>"}},
  {{"category": "crime_type",   "subcategory": "<value>"}}
]"""


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
        system=EXTRACTION_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

    return json.loads(raw)


_TAXONOMY_DIMENSIONS = list(TAXONOMY.keys())


def classify_decision(context: str) -> list[dict]:
    """
    Second-pass classification: given a context string built from the
    extracted fields, assign one value per taxonomy dimension.

    Returns a list of {category, subcategory} dicts — one
    entry per dimension (legal_domain, legal_topic, legal_action,
    crime_type).
    """
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    message = client.messages.create(
        model=MODEL,
        max_tokens=512,
        system=CLASSIFICATION_SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Classify this court decision:\n\n{context}",
        }],
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

    result = json.loads(raw)
    if not isinstance(result, list):
        result = []

    # Ensure every dimension is present; fill missing ones with UNKNOWN
    seen = {item["category"] for item in result if isinstance(item, dict)}
    for dim in _TAXONOMY_DIMENSIONS:
        if dim not in seen:
            result.append({"category": dim, "subcategory": "UNKNOWN"})

    # Validate each subcategory against the allowed values; fall back to UNKNOWN
    allowed = {dim: set(meta["values"].keys()) for dim, meta in TAXONOMY.items()}
    for item in result:
        dim = item.get("category", "")
        if dim in allowed and item.get("subcategory") not in allowed[dim]:
            item["subcategory"] = "UNKNOWN"

    return result
