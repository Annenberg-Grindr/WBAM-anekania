#!/usr/bin/env python3
"""Extract text from all BigLaw Bench PDFs for evaluation."""

import json
import os
from pathlib import Path
from PyPDF2 import PdfReader

BIGLAW_BENCH_DIR = Path("/tmp/biglaw-bench")
OUTPUT_DIR = Path("/home/user/WBAM-anekania/biglaw-bench-eval/extracted_text")


def extract_pdf_text(pdf_path: str) -> str:
    """Extract text from a PDF file."""
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            text += f"\n--- Page {i+1} ---\n{page_text}"
        return text.strip()
    except Exception as e:
        return f"[Error reading PDF: {e}]"


def extract_all():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    results = {}

    # Extract core documents
    core_docs = BIGLAW_BENCH_DIR / "blb-core" / "documents"
    if core_docs.exists():
        for pdf in sorted(core_docs.iterdir()):
            if pdf.suffix.lower() == '.pdf':
                print(f"Extracting: {pdf.name}")
                text = extract_pdf_text(str(pdf))
                results[f"core/{pdf.name}"] = {
                    "path": str(pdf),
                    "text_length": len(text),
                    "text": text[:50000],  # Limit for manageability
                }

    # Extract workflow SPA documents
    spa_docs = BIGLAW_BENCH_DIR / "blb-workflows" / "spa" / "documents"
    if spa_docs.exists():
        for pdf in sorted(spa_docs.iterdir()):
            if pdf.suffix.lower() == '.pdf':
                print(f"Extracting: {pdf.name}")
                text = extract_pdf_text(str(pdf))
                results[f"workflows-spa/{pdf.name}"] = {
                    "path": str(pdf),
                    "text_length": len(text),
                    "text": text[:50000],
                }

    # Extract retrieval documents
    for subdir in ["discovery_emails", "spa", "merger_agreements"]:
        ret_docs = BIGLAW_BENCH_DIR / "blb-retrieval" / subdir
        if ret_docs.exists():
            for pdf in sorted(ret_docs.iterdir()):
                if pdf.suffix.lower() in ['.pdf']:
                    print(f"Extracting: {subdir}/{pdf.name}")
                    text = extract_pdf_text(str(pdf))
                    results[f"retrieval-{subdir}/{pdf.name}"] = {
                        "path": str(pdf),
                        "text_length": len(text),
                        "text": text[:50000],
                    }

    # Save extraction summary
    summary = {k: {"path": v["path"], "text_length": v["text_length"]} for k, v in results.items()}
    with open(OUTPUT_DIR / "extraction_summary.json", 'w') as f:
        json.dump(summary, f, indent=2)

    # Save individual texts
    for key, data in results.items():
        safe_name = key.replace("/", "__").replace(" ", "_")
        with open(OUTPUT_DIR / f"{safe_name}.txt", 'w', encoding='utf-8') as f:
            f.write(data["text"])

    print(f"\nExtracted {len(results)} documents")
    print(f"Summary saved to {OUTPUT_DIR / 'extraction_summary.json'}")


if __name__ == "__main__":
    extract_all()
