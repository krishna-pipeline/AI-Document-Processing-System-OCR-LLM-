import os
import sys
from OCR_EXTRACTION import process_all_documents
from llm_extraction import process_all_extractions, check_local_llm


def print_banner():
    """Print welcome banner"""
    print("\n" + "=" * 60)
    print("   MEDICAL INTELLIGENT DOCUMENT PROCESSING PIPELINE")
    print("=" * 60)
    print()


def print_summary(ocr_results, llm_results):
    """Print processing summary"""
    print("\n" + "=" * 60)
    print("PROCESSING SUMMARY")
    print("=" * 60)

    # OCR Summary
    print("\n OCR EXTRACTION:")
    total_docs = 0
    for doc_type, docs in ocr_results.items():
        count = len(docs)
        total_docs += count
        print(f"   • {doc_type.replace('_', ' ').title()}: {count} document(s)")
    print(f"   Total: {total_docs} documents processed")

    # LLM Summary
    print("\n LLM EXTRACTION:")
    if llm_results and 'combined_data' in llm_results:
        for doc_type, data in llm_results['combined_data'].items():
            field_count = len(data)
            print(f"   • {doc_type.replace('_', ' ').title()}: {field_count} fields extracted")
    else:
        print("   ⚠ No data extracted")

    # Output Files
    print("\n OUTPUT FILES:")
    if llm_results and 'pdf_path' in llm_results:
        print(f"   • Summary PDF: {llm_results['pdf_path']}")

    base_dir = os.path.dirname(os.path.abspath(__file__))
    text_dir = os.path.join(base_dir, 'extracted_text')
    print(f"   • Extracted Text: {text_dir}")
    print(f"   • Individual JSONs: {text_dir}/<document_type>/")

    print("\n" + "=" * 60)


def main():
    """Main pipeline orchestration"""
    print_banner()


    # PHASE 1: OCR EXTRACTION

    print("=" * 60)
    print("PHASE 1: OCR EXTRACTION")
    print("=" * 60)
    print()

    try:
        ocr_results = process_all_documents()

        total_processed = sum(len(docs) for docs in ocr_results.values())
        if total_processed == 0:
            print("\n⚠ WARNING: No PDF files found in input directories")
            print("Please add PDF files to the following folders:")
            base_dir = os.path.dirname(os.path.abspath(__file__))
            print(f"  • {os.path.join(base_dir, 'input_pdfs', 'policy_copy')}")
            print(f"  • {os.path.join(base_dir, 'input_pdfs', 'discharge_summary')}")
            print(f"  • {os.path.join(base_dir, 'input_pdfs', 'rejection_letter')}")
            return

    except Exception as e:
        print(f"\n OCR EXTRACTION FAILED: {e}")
        import traceback
        traceback.print_exc()
        return

    # PHASE 2: LLM EXTRACTION

    print("\n" + "=" * 60)
    print("PHASE 2: LLM EXTRACTION")
    print("=" * 60)
    print()

    if not check_local_llm():
        print("\n OLLAMA NOT AVAILABLE")
        print("\nPlease ensure Ollama is running:")
        print("  1. Install Ollama: https://ollama.ai")
        print("  2. Pull the model: ollama pull llama3.1:8b")
        print("  3. Start Ollama: ollama serve")
        print("\nOCR extraction completed, but LLM processing skipped.")
        return

    try:
        llm_results = process_all_extractions()

        if not llm_results:
            print("\n LLM PROCESSING FAILED")
            print("Check the extracted text quality in the 'extracted_text' folder")
            return

    except Exception as e:
        print(f"\n LLM PROCESSING FAILED: {e}")
        import traceback
        traceback.print_exc()
        return


    # FINAL SUMMARY

    print_summary(ocr_results, llm_results)

    print("\n PIPELINE COMPLETED SUCCESSFULLY!")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠ Pipeline interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)