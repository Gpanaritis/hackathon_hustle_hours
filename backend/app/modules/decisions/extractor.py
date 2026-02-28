"""
Claude-powered structured extraction for court decisions.
"""

import json
from typing import Optional

import anthropic

from app.config import settings

MODEL = "claude-opus-4-6"

TAXONOMY = {
    "Αστικό Δίκαιο": [
        "Ενοικιαστικές_σχέσεις", "Αγωγή_αναγνωριστική", "Αγωγή_διεκδικητική",
        "Αγωγή_αρνητική", "Καταβολή_χρεών", "Ακύρωση_συμβάσεων",
        "Ευθύνη_αδικοπραξίας", "Αποζημίωση", "Κληρονομικό_δίκαιο",
        "Συμβολαιογραφικές_πράξεις",
    ],
    "Εργατικό Δίκαιο": [
        "Απόλυση", "Ακυρότητα_απόλυσης", "Μισθός", "Καθυστέρηση_αποδοχών",
        "Υπερωριακή_εργασία", "Εργατικό_ατύχημα",
        "Συμβάσεις_εργασίας_ορισμένου_χρόνου", "Συνδικαλιστικά_δικαιώματα",
    ],
    "Ποινικό Δίκαιο": [
        "Ανθρωποκτονία_από_πρόθεση", "Ανθρωποκτονία_από_αμέλεια", "Ασέλγεια",
        "Βιασμός", "Κλοπή", "Ληστεία", "Απάτη", "Ναρκωτικά",
        "Σωματική_βλάβη_απλή", "Σωματική_βλάβη_βαριά", "Συμμορία",
    ],
    "Διοικητικό Δίκαιο": [
        "Ακύρωση_διοικητικής_πράξης", "Έλεγχος_νομιμότητας",
        "Αναστολή_διοικητικής_απόφασης", "Δημόσιο_συμβόλαιο",
        "Αναγκαστική_απαλλοτρίωση",
    ],
    "Δίκαιο Περιβάλλοντος και Ακίνητης Περιουσίας": [
        "Ανεξέλεγκτες_κατασκευές", "Απαλλοτρίωση", "Περιβαλλοντική_ζημία",
        "Ακίνητη_ιδιοκτησία", "Πλημμυρικά_ατυχήματα",
    ],
    "Δίκαιο Συμβάσεων & Εμπορικό Δίκαιο": [
        "Σύμβαση_αγοραπωλησίας", "Σύμβαση_παροχής_υπηρεσιών", "Σύμβαση_έργου",
        "Εμπορικές_διαφορές", "Πληρεξουσιότητα", "Αφερεγγυότητα",
    ],
    "Ειδικές Κατηγορίες": [
        "Αιτήματα_αναστολής", "Αιτήματα_αναίρεσης", "Αναιρέσεις_λόγοι",
        "Προκαταβολή_ζημίας", "Προσφυγή_σε_Διοικητικό", "Τεκμήριο_αθωότητας",
    ],
}

_TAXONOMY_TEXT = "\n".join(
    f"  {cat}:\n" + "\n".join(f"    - {sub}" for sub in subs)
    for cat, subs in TAXONOMY.items()
)

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

CLASSIFICATION_SYSTEM_PROMPT = f"""You are a legal classification expert. Given a summary of a court decision, classify it using ONLY the categories and subcategories listed below.

Assign every subcategory that applies with a confidence score between 0.0 and 1.0. Only include matches with confidence >= 0.3.

TAXONOMY:
{_TAXONOMY_TEXT}

Return ONLY a valid JSON array of objects. No markdown fences, no explanation.

Example:
[
  {{"category": "Ποινικό Δίκαιο", "subcategory": "Κλοπή", "confidence": 0.95}},
  {{"category": "Ειδικές Κατηγορίες", "subcategory": "Αιτήματα_αναίρεσης", "confidence": 0.80}}
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


def classify_decision(context: str) -> list[dict]:
    """
    Second-pass classification: given a context string built from the
    extracted fields, assign taxonomy categories with confidence scores.

    Returns a list of {category, subcategory, confidence} dicts.
    """
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    message = client.messages.create(
        model=MODEL,
        max_tokens=1024,
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
    return result if isinstance(result, list) else []
