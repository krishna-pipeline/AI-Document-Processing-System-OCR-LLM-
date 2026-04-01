# 🏥 Medical Intelligent Document Processing Pipeline

> An end-to-end AI pipeline that extracts structured data from medical insurance documents using OCR + Local LLM (Ollama), generating a clean adjudicator-ready PDF report.

---

## 📋 Overview

This system automates the extraction of key fields from three types of health insurance documents:

| Document Type | Description |
|---|---|
| **Policy Copy** | Insurance policy details, coverage, PED, waiting periods |
| **Discharge Summary** | Hospital stay, diagnosis, procedures, billing |
| **Rejection Letter** | Claim rejection reasons, clause references, TPA details |

The pipeline runs in two phases:
1. **Phase 1 — OCR Extraction**: Detects digital vs scanned PDFs and extracts raw text
2. **Phase 2 — LLM Extraction**: Uses a local Ollama model to parse structured fields from OCR text, then generates a combined PDF report

---

## 🗂️ Project Structure

```
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
```

---

## ⚙️ Prerequisites

### System Dependencies

```bash
# Tesseract OCR (required for scanned PDFs)
sudo apt-get install tesseract-ocr

# Poppler (required for pdf2image)
sudo apt-get install poppler-utils
```

### Python Dependencies

```bash
pip install -r requirements.txt
```

**requirements.txt:**
```
pdfplumber
pdf2image
pytesseract
opencv-python
numpy
Pillow
fpdf
python-dateutil
requests
```

### Ollama Setup

This pipeline uses a **local LLM via Ollama** — no API keys needed.

```bash
# 1. Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# 2. Pull the model (default: gemma3:12b)
ollama pull gemma3:12b

# 3. Start Ollama server
ollama serve
```

> 💡 You can swap the model by changing `LOCAL_LLM_CONFIG['model']` in `llm_extraction.py`. Tested with `gemma3:12b` and `llama3.1:8b`.

---

## 🚀 Quick Start

```bash
# Clone the repo
git clone <your-repo-url>
cd <project-folder>

# Install Python dependencies
pip install -r requirements.txt

# Start Ollama in a separate terminal
ollama serve

# Add your PDFs to the input folders
cp your_policy.pdf input_pdfs/policy_copy/
cp your_discharge.pdf input_pdfs/discharge_summary/
cp your_rejection.pdf input_pdfs/rejection_letter/

# Run the pipeline
python main.py
```

The final report will be saved as **`combined_summary.pdf`** in the project root.

---

## 📤 Output

### combined_summary.pdf

A structured 4-bucket PDF report for adjudicator review:

| Bucket | Contents |
|---|---|
| **Bucket 1** | Insurance Policy Details (holder info, coverage, PED, waiting periods) |
| **Bucket 2** | Hospital Discharge Summary (diagnosis, procedures, billing, LOS) |
| **Bucket 3** | Declared vs Found (PED cross-check between policy and discharge) |
| **Bucket 4** | Claim Rejection Details (reasons, clauses, TPA info) |

### Individual JSON Files

Each document type also produces a standalone JSON in `extracted_text/<type>/`:

```json
{
  "Policy_Number": "P/123456/01/2024",
  "Policy_Holder_Name": "Ramesh Kumar",
  "Coverage_Amount": "10,00,000",
  "Policy_Inception_Date": "15/03/2019",
  "Member_wise_PED": [
    {
      "Member_Name": "Ramesh Kumar",
      "Relation": "Self",
      "Pre_Existing_Diseases": "Hypertension",
      "Waiting_Period": "2 Years",
      "Waiting_Period_Expiry": "15/03/2021"
    }
  ]
}
```

---

## 🧠 How It Works

### Phase 1 — OCR Extraction (`OCR_EXTRACTION.py`)

- **Digital PDFs** → extracted directly via `pdfplumber` (fast, accurate)
- **Scanned PDFs** → converted to images at 300 DPI → preprocessed with OpenCV (grayscale + Otsu thresholding) → OCR via Tesseract (`--oem 3 --psm 3`)
- Text is cleaned: excess whitespace, non-ASCII chars, and camelCase OCR artifacts are normalized

### Phase 2 — LLM Extraction (`llm_extraction.py`)

- Sends cleaned OCR text to a local Ollama model with a strict field-extraction prompt
- Returns a structured JSON object with all defined fields
- **Post-processing** computes derived fields:
  - `Age` calculated from `Date_of_Birth`
  - `Length_of_Stay` calculated from admission/discharge dates
  - `Waiting_Period_Expiry` calculated per member from inception date + waiting period

---

## ⚠️ Important Notes

- **AI extraction only** — the generated report is a decision-support tool. The human adjudicator has final authority.
- **Indian number format** is preserved (e.g., `10,00,000` is not converted or truncated).
- If a field is not found in the document, it is explicitly marked as `"Not Found"` — the model is instructed never to invent data.
- Only **one PDF per document type** is processed per run (the first file found in each input folder).

---

## 🔧 Configuration

Edit constants at the top of `llm_extraction.py`:

```python
LOCAL_LLM_CONFIG = {
    'url': 'http://localhost:11434/api/generate',
    'model': 'gemma3:12b',   # Change model here
    'timeout': 600
}
```

---

## 📄 License

MIT License — see `LICENSE` for details.
