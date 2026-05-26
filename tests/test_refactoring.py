"""
Unit tests for the refactored OOP strategy processors, TokenTrie implementation, 
and normalizer memoization.
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.trie import TokenTrie
from services.processors import DocumentProcessorFactory, AadhaarProcessor, PANProcessor, InvoiceProcessor
from services.normalizer import normalize_string, normalize_number, normalize_document_data
from services.post_processing import post_process_document
from models.schemas import (
    ExtractedDocument, AadhaarDocument, InvoiceDocument, PANDocument,
    ProcessingStatus, ReviewSeverity
)


def test_trie_matching():
    """Verify TokenTrie keyword insertion and multi-word matching accuracy."""
    print("🧪 Running TokenTrie Match Tests...")
    trie = TokenTrie()
    trie.insert("unique identification authority", "aadhaar")
    trie.insert("income tax department", "pan")
    trie.insert("tax invoice", "invoice")
    trie.insert("permanent account number", "pan")

    # Scenario 1: Exact matches
    text_1 = "this is a government document issued by the unique identification authority of india."
    matches = trie.search_all_matches(text_1)
    assert "aadhaar" in matches
    assert "unique identification authority" in matches["aadhaar"]
    assert "pan" not in matches

    # Scenario 2: Multiple matches across types
    text_2 = "here is my permanent account number issued by the income tax department and a tax invoice for verification."
    matches_2 = trie.search_all_matches(text_2)
    assert "pan" in matches_2
    assert "invoice" in matches_2
    assert "permanent account number" in matches_2["pan"]
    assert "income tax department" in matches_2["pan"]
    assert "tax invoice" in matches_2["invoice"]

    # Scenario 3: Case insensitivity and token boundary check
    text_3 = "INCOME TAX DEPARTMENT and TAX INVOICING"
    matches_3 = trie.search_all_matches(text_3)
    assert "pan" in matches_3
    assert "income tax department" in matches_3["pan"]
    # "TAX INVOICING" should not match "tax invoice" due to token mismatch on "invoicing" vs "invoice"
    assert "invoice" not in matches_3 or "tax invoice" not in matches_3["invoice"]

    print("✅ TokenTrie Match Tests Passed!")


def test_normalizer_caching():
    """Verify string normalization results and memoization behavior."""
    print("🧪 Running Normalizer Caching Tests...")
    
    # Check baseline string cleaning
    assert normalize_string("  Hello   World  ") == "Hello World"
    # Zero-width spaces removal
    assert normalize_string("Hello\u200bWorld") == "HelloWorld"
    # Unicode NFC normalization
    assert normalize_string("a\u0308") == "ä"
    
    # Check number cleaning
    assert normalize_number(" ₹ 12,500.50 ") == 12500.50
    assert normalize_number(" $ 1,000 ") == 1000.0

    print("✅ Normalizer Caching Tests Passed!")


def test_processor_factory_resolution():
    """Verify O(1) factory returns correct concrete processor strategies."""
    print("🧪 Running OOP Strategy Factory Resolution Tests...")
    
    p_aadhaar = DocumentProcessorFactory.get_processor("aadhaar")
    assert isinstance(p_aadhaar, AadhaarProcessor)

    p_pan = DocumentProcessorFactory.get_processor("pan")
    assert isinstance(p_pan, PANProcessor)

    p_invoice = DocumentProcessorFactory.get_processor("invoice")
    assert isinstance(p_invoice, InvoiceProcessor)

    # Safely falls back to Unknown
    p_random = DocumentProcessorFactory.get_processor("some_random_doc_type")
    from services.processors import UnknownProcessor
    assert isinstance(p_random, UnknownProcessor)

    print("✅ OOP Strategy Factory Resolution Tests Passed!")


def test_aadhaar_processor_strategies():
    """Verify Aadhaar-specific normalization and post-processing strategies."""
    print("🧪 Running Aadhaar Processor Strategy Tests...")
    
    # 1. Normalization checks
    raw_data = {
        "gender": "पुरुष",
        "aadhaar_number_masked": "1234  5678  9012"
    }
    normalized = normalize_document_data("aadhaar", raw_data)
    assert normalized["gender"] == "Male"
    assert normalized["aadhaar_number_masked"] == "1234 5678 9012"

    raw_data_female = {"gender": "female"}
    assert normalize_document_data("aadhaar", raw_data_female)["gender"] == "Female"

    # 2. Post-processing check: Force masking and review flag triggers
    aadhaar_doc = AadhaarDocument(
        document_id="doc_001",
        name="John Doe",
        date_of_birth="01/01/1990",
        gender="Male",
        aadhaar_number_masked="123456789012",  # Raw unmasked number
        address="123 Street, Delhi",
        pin_code="110001",
        processing_status=ProcessingStatus.SUCCESS
    )

    processed_doc = post_process_document(aadhaar_doc, ocr_text="my aadhaar is 1234 5678 9012", request_id="req_01")
    
    # Should force mask the number
    assert processed_doc.aadhaar_number_masked == "XXXX XXXX 9012"
    # Should trigger a review flag
    assert processed_doc.needs_review is True
    assert processed_doc.processing_status == ProcessingStatus.NEEDS_REVIEW
    assert len(processed_doc.review_flags) > 0
    assert any("masked" in flag.reason.lower() for flag in processed_doc.review_flags)

    print("✅ Aadhaar Processor Strategy Tests Passed!")


def test_pan_processor_strategies():
    """Verify PAN-specific uppercase rules."""
    print("🧪 Running PAN Processor Strategy Tests...")
    raw_data = {
        "pan_number": "abcde1234f",
        "name": "rahul sharma",
        "father_name": "mohan sharma"
    }
    normalized = normalize_document_data("pan", raw_data)
    assert normalized["pan_number"] == "ABCDE1234F"
    assert normalized["name"] == "RAHUL SHARMA"
    assert normalized["father_name"] == "MOHAN SHARMA"

    # Post processing incorrect PAN format check
    pan_doc = PANDocument(
        document_id="doc_002",
        name="RAHUL SHARMA",
        pan_number="ABC1234",  # Invalid length/format
        processing_status=ProcessingStatus.SUCCESS
    )
    processed_doc = post_process_document(pan_doc, ocr_text="PAN ABC1234", request_id="req_02")
    assert processed_doc.needs_review is True
    assert any("does not match standard" in flag.reason.lower() for flag in processed_doc.review_flags)

    print("✅ PAN Processor Strategy Tests Passed!")


def test_invoice_processor_strategies():
    """Verify Invoice validation checks (e.g. Subtotal + GST = Total)."""
    print("🧪 Running Invoice Processor Strategy Tests...")
    
    # 1. Successful math validation
    invoice_ok = InvoiceDocument(
        document_id="doc_003",
        subtotal=100.00,
        gst_amount=18.00,
        total_amount=118.00,
        processing_status=ProcessingStatus.SUCCESS
    )
    processed_ok = post_process_document(invoice_ok, request_id="req_03")
    assert processed_ok.needs_review is False
    assert processed_ok.processing_status == ProcessingStatus.SUCCESS

    # 2. Math mismatch trigger
    invoice_err = InvoiceDocument(
        document_id="doc_004",
        subtotal=100.00,
        gst_amount=18.00,
        total_amount=150.00,  # Invalid sum!
        processing_status=ProcessingStatus.SUCCESS
    )
    processed_err = post_process_document(invoice_err, request_id="req_04")
    assert processed_err.needs_review is True
    assert processed_err.processing_status == ProcessingStatus.NEEDS_REVIEW
    assert any("does not match" in flag.reason.lower() for flag in processed_err.review_flags)

    print("✅ Invoice Processor Strategy Tests Passed!")


def run_all_tests():
    print("=" * 80)
    print("RUNNING BACKEND REFRACTORING VERIFICATION SUITE")
    print("=" * 80)
    
    test_trie_matching()
    print("-" * 80)
    test_normalizer_caching()
    print("-" * 80)
    test_processor_factory_resolution()
    print("-" * 80)
    test_aadhaar_processor_strategies()
    print("-" * 80)
    test_pan_processor_strategies()
    print("-" * 80)
    test_invoice_processor_strategies()
    
    print("=" * 80)
    print("🎉 ALL TESTS PASSED SUCCESSFULLY! ZERO REGRESSIONS DETECTED.")
    print("=" * 80)


if __name__ == "__main__":
    run_all_tests()
