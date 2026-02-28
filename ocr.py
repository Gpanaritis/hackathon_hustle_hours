"""
OCR pipeline for contract PDFs using Claude vision.

Strategy per page:
  1. Try pymupdf to extract text (fast, works for text-based PDFs).
  2. If the page has no meaningful text (scanned), convert it to an image
     and send it to Claude's vision API for OCR.

Output: JSON (fields to be specified via the SYSTEM_PROMPT).
"""

import base64
import io
import json
import os
from pathlib import Path

import anthropic
import fitz  # pymupdf
from PIL import Image

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PDF_DIR = Path(__file__).parent / "1. Contracts Challenge"
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Minimum number of characters extracted by pymupdf to consider a page
# "text-based" (otherwise fall back to vision OCR).
MIN_TEXT_CHARS = 50

# Resolution for rendering scanned pages to images (higher = better OCR).
IMAGE_DPI = 200

# Claude model to use for vision OCR.
MODEL = "claude-opus-4-5"

# System prompt — update this with the specific JSON fields you need.
SYSTEM_PROMPT = """You are an expert contract analyst and OCR assistant.
Extract all text from the provided contract page image accurately.
Return a JSON object. The schema will be specified later — for now use:
{
  "page_text": "<full extracted text from the page>"
}
Only return valid JSON. No explanation, no markdown fences."""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def page_to_base64_png(page: fitz.Page, dpi: int = IMAGE_DPI) -> str:
    """Render a pymupdf page to a base64-encoded PNG string."""
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.standard_b64encode(buf.getvalue()).decode()


def ocr_page_with_claude(client: anthropic.Anthropic, page: fitz.Page) -> dict:
    """Send a page image to Claude and return parsed JSON."""
    img_b64 = page_to_base64_png(page)
    message = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": img_b64,
                        },
                    },
                    {"type": "text", "text": "Extract all text from this contract page."},
                ],
            }
        ],
    )
    raw = message.content[0].text.strip()
    # Strip markdown fences if the model adds them despite instructions.
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw)


def extract_text_pymupdf(page: fitz.Page) -> str:
    """Extract plain text from a page using pymupdf."""
    return page.get_text("text").strip()


def process_pdf(pdf_path: Path, client: anthropic.Anthropic) -> list[dict]:
    """Process a single PDF and return a list of per-page results."""
    doc = fitz.open(str(pdf_path))
    results = []

    for page_num, page in enumerate(doc, start=1):
        text = extract_text_pymupdf(page)

        if len(text) >= MIN_TEXT_CHARS:
            # Text-based page — no vision needed.
            page_result = {
                "page": page_num,
                "method": "pymupdf",
                "page_text": text,
            }
        else:
            # Scanned page — use Claude vision OCR.
            print(f"  Page {page_num}: scanned, using Claude vision OCR...")
            claude_data = ocr_page_with_claude(client, page)
            page_result = {"page": page_num, "method": "claude_vision", **claude_data}

        results.append(page_result)
        print(f"  Page {page_num}: done ({page_result['method']})")

    doc.close()
    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY environment variable is not set.")

    client = anthropic.Anthropic(api_key=api_key)

    pdf_files = sorted(PDF_DIR.glob("*.pdf"))
    print(f"Found {len(pdf_files)} PDFs in '{PDF_DIR}'.\n")

    for pdf_path in pdf_files:
        out_path = OUTPUT_DIR / (pdf_path.stem + ".json")
        if out_path.exists():
            print(f"[SKIP] {pdf_path.name} (output already exists)")
            continue

        print(f"[PROCESSING] {pdf_path.name}")
        try:
            pages = process_pdf(pdf_path, client)
            result = {
                "file": pdf_path.name,
                "pages": pages,
            }
            out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False))
            print(f"  -> Saved to {out_path.name}\n")
        except Exception as exc:
            print(f"  [ERROR] {exc}\n")


if __name__ == "__main__":
    main()
