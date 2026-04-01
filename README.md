An end-to-end AI pipeline that extracts structured data from medical insurance documents using OCR + Local LLM (Ollama), generating a clean adjudicator-ready PDF report.
This system automates the extraction of key fields from three types of health insurance documents:
Policy_Copy : Insurance policy details, coverage, PED, waiting periods
Discharge_Summary : Hospital stay, diagnosis, procedures, billing
Rejection_Letter : Claim rejection reasons, clause references, TPA details
This pipeline runs in two phases:
Phase - 1: OCR Extraction: Detects digital vs scanned PDFs and extracts raw text
Phase -2 : LLM Extraction: Uses a local Ollama model to parse structured fields from OCR text, then generates a combined PDF report.
Project Structure:
project-root/
│
├── main.py                    # Pipeline orchestrator (run this)
├── OCR_EXTRACTION.py          # Phase 1: PDF → raw text
├── llm_extraction.py          # Phase 2: raw text → structured JSON + PDF
│
├── input_pdfs/
│   ├── policy_copy/           # Drop policy PDF files here
│   ├── discharge_summary/     # Drop discharge summary PDFs here
│   └── rejection_letter/      # Drop rejection letter PDFs here
│
├── extracted_text/
│   ├── policy_copy/
│   │   ├── *.txt              # Extracted raw text
│   │   └── policy_copy_extracted.json
│   ├── discharge_summary/
│   │   ├── *.txt
│   │   └── discharge_summary_extracted.json
│   └── rejection_letter/
│       ├── *.txt
│       └── rejection_letter_extracted.json
│
└── combined_summary.pdf       # Final adjudicator report (auto-generated)
