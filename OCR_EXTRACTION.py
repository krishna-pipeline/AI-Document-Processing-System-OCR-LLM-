import os
import re
import pdfplumber
import numpy as np
import cv2
from pdf2image import convert_from_path
from PIL import Image
import pytesseract

# =========================================================
# BASE DIRECTORY SETUP
# =========================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, 'input_pdfs')
OUTPUT_DIR = os.path.join(BASE_DIR, 'extracted_text')

DOCUMENT_TYPES = {
    'policy_copy': {
        'input': os.path.join(INPUT_DIR, 'policy_copy'),
        'output': os.path.join(OUTPUT_DIR, 'policy_copy')
    },
    'discharge_summary': {
        'input': os.path.join(INPUT_DIR, 'discharge_summary'),
        'output': os.path.join(OUTPUT_DIR, 'discharge_summary')
    },
    'rejection_letter': {
        'input': os.path.join(INPUT_DIR, 'rejection_letter'),
        'output': os.path.join(OUTPUT_DIR, 'rejection_letter')
    }
}


# =========================================================
# DIRECTORY CREATION
# =========================================================
def create_directories():
    """Create input and output directories if they don't exist"""
    for doc_type in DOCUMENT_TYPES.values():
        os.makedirs(doc_type['input'], exist_ok=True)
        os.makedirs(doc_type['output'], exist_ok=True)
    print("✓ Directories created/verified")


# =========================================================
# PDF TYPE DETECTION
# =========================================================
def is_digital_pdf(pdf_path):
    """
    Detect if PDF is digital (text-based) or scanned (image-based)
    Returns: 'digital' or 'scanned'
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text_len = 0
            pages = min(3, len(pdf.pages))  # Check first 3 pages

            for i in range(pages):
                t = pdf.pages[i].extract_text()
                if t:
                    text_len += len(t.strip())

            # If average text per page > 200 chars, consider it digital
            avg_text = text_len / max(pages, 1)
            return 'digital' if avg_text > 200 else 'scanned'

    except Exception as e:
        print(f"   ⚠ Error detecting PDF type: {e}")
        return 'scanned'  # Default to scanned if error


# =========================================================
# DIGITAL PDF EXTRACTION
# =========================================================
def extract_digital_pdf(pdf_path):
    """Extract text from digital (text-based) PDF"""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
    except Exception as e:
        print(f"   ❌ Digital PDF error: {e}")

    return text


# =========================================================
# SCANNED PDF EXTRACTION (PYTESSERACT)
# =========================================================
def extract_scanned_pdf(pdf_path):
    """Extract text from scanned (image-based) PDF using OCR"""
    text = ""
    try:
        # Convert PDF pages to images
        images = convert_from_path(pdf_path, dpi=300)

        for i, image in enumerate(images):
            # Convert PIL Image to OpenCV format
            gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)

            # Apply thresholding for better OCR accuracy
            clean_img = cv2.threshold(
                gray, 0, 255,
                cv2.THRESH_BINARY | cv2.THRESH_OTSU
            )[1]

            # PSM 3: Fully automatic page segmentation (best for medical documents)
            page_text = pytesseract.image_to_string(
                clean_img,
                config="--oem 3 --psm 3"
            )

            if page_text.strip():
                text += f"\n--- PAGE {i + 1} ---\n" + page_text

    except Exception as e:
        print(f"   ❌ OCR error: {e}")
        print(f"      Make sure tesseract is installed: sudo apt-get install tesseract-ocr")

    return text


# =========================================================
# TEXT CLEANING
# =========================================================
def clean_text(text):
    """Clean and normalize extracted text"""
    if not text:
        return ""

    # Remove multiple spaces
    text = re.sub(r'[ \t]+', ' ', text)

    # Remove excessive newlines (keep max 2)
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)

    # Remove non-ASCII characters
    text = re.sub(r'[^\x00-\x7F]+', '', text)

    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    text = re.sub(r'([A-Z]{2,})([A-Z][a-z])', r'\1 \2', text)

    return text.strip()


# =========================================================
# MAIN EXTRACTION FUNCTION
# =========================================================
def extract_text_from_pdf(pdf_path, document_type):
    """
    Main function to extract text from PDF
    Automatically detects PDF type and uses appropriate extraction method
    """
    print(f"\n📄 Processing: {os.path.basename(pdf_path)}")

    # Detect PDF type
    pdf_type = is_digital_pdf(pdf_path)
    print(f"   Type detected: {pdf_type.upper()}")

    # Extract text based on type
    raw_text = (
        extract_digital_pdf(pdf_path)
        if pdf_type == 'digital'
        else extract_scanned_pdf(pdf_path)
    )

    # Clean text
    cleaned_text = clean_text(raw_text)

    # Save to file
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_path = os.path.join(
        DOCUMENT_TYPES[document_type]['output'],
        f"{pdf_name}.txt"
    )

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(cleaned_text)

    print(f"   ✓ Text saved: {output_path}")
    print(f"   ✓ Characters: {len(cleaned_text)}")

    return output_path, cleaned_text


# =========================================================
# PROCESS ALL DOCUMENTS
# =========================================================
def process_all_documents():
    """
    Process all PDFs in input directories
    Returns: Dictionary with results for each document type
    """
    create_directories()
    results = {}

    for doc_type, paths in DOCUMENT_TYPES.items():
        print("\n" + "=" * 60)
        print(f"Processing {doc_type.upper().replace('_', ' ')}")
        print("=" * 60)

        # Find all PDFs in input directory
        pdfs = [f for f in os.listdir(paths['input']) if f.lower().endswith('.pdf')]

        if not pdfs:
            print("⚠ No PDFs found")
            results[doc_type] = []
            continue

        results[doc_type] = []

        # Process each PDF
        for pdf in pdfs:
            pdf_path = os.path.join(paths['input'], pdf)
            out_path, text = extract_text_from_pdf(pdf_path, doc_type)

            results[doc_type].append({
                'pdf_path': pdf_path,
                'text_path': out_path,
                'text': text,
                'filename': pdf
            })

    return results


# =========================================================
# STANDALONE TEST
# =========================================================
if __name__ == "__main__":
    print("🚀 Running OCR Extraction...")
    results = process_all_documents()

    print("\n" + "=" * 60)
    print("EXTRACTION COMPLETE")
    print("=" * 60)

    for doc_type, docs in results.items():
        print(f"\n{doc_type.replace('_', ' ').title()}: {len(docs)} document(s)")