"""
Micro-benchmark script comparing original nested linear search classification
against the new TokenTrie-based document classification, including ruleset scaling behavior.
"""

import sys
import os
import time
from typing import Dict, List, Tuple, Set

# Ensure project root is in the path so we can import services
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.document_classifier import CLASSIFICATION_RULES, classify_document
from services.trie import TokenTrie

# Original classification implementation (nested loop substring scan)
def classify_document_original(text: str, rules: Dict[str, List[str]] = CLASSIFICATION_RULES) -> Tuple[str, float]:
    if not text or len(text.strip()) < 10:
        return "unknown", 0.0

    text_lower = text.lower()
    scores = {}

    for doc_type, keywords in rules.items():
        matched_count = 0
        for keyword in keywords:
            if keyword in text_lower:
                matched_count += 1
        
        if matched_count > 0:
            scores[doc_type] = min(0.95, 0.6 + (matched_count / len(keywords)))

    if not scores:
        return "unknown", 0.0

    best_type = max(scores, key=scores.get)
    best_confidence = scores[best_type]
    return best_type, best_confidence


# TokenTrie search helper that takes custom Trie and Rules
def classify_document_trie(text: str, trie: TokenTrie, rules: Dict[str, List[str]]) -> Tuple[str, float]:
    if not text or len(text.strip()) < 10:
        return "unknown", 0.0

    scores = {}
    matched_results = trie.search_all_matches(text)

    for doc_type, keywords in rules.items():
        matched_keywords = matched_results.get(doc_type, set())
        matched_count = len(matched_keywords)
        
        if matched_count > 0:
            scores[doc_type] = min(0.95, 0.6 + (matched_count / len(keywords)))

    if not scores:
        return "unknown", 0.0

    best_type = max(scores, key=scores.get)
    best_confidence = scores[best_type]
    return best_type, best_confidence


# Generate test cases representing different types of documents and sizes
TEST_CASES = {
    "Aadhaar OCR (Short)": (
        "government of india unique identification authority uidai enrollment no 1234/56789/01234 "
        "to aadhar card holder name rajesh kumar dob: 15/08/1990 male virtual id address delhi india"
    ),
    "PAN OCR (Medium)": (
        "income tax department govt. of india permanent account number card holder name sumit sharma "
        "father name rajendra sharma date of birth 21/04/1985 signature of cardholder pan_number ABCDE1234F"
    ),
    "Invoice OCR (Large)": (
        "tax invoice bill to xyz solutions pvt ltd ship to same gstin 27aaaaa1111a1z1 invoice no inv-2026-001 "
        "date 2026-05-27 item descriptions computer hardware unit price 45000.00 quantity 2 cgst 9% sgst 9% "
        "igst 0% total amount 106200.00 terms and conditions pay within 30 days subtotal 90000 gst_amount 16200"
    ),
    "eKYC Application (Extra Large)": (
        "know your customer kyc updation form sebi annexure. in person verification ipv record sheet. "
        "customer due diligence ckyc registry process customer id 987654321 account no 123456789 "
        "applicant name priya patel father/spouse name arvind patel monthly income range occupation type business "
        "pep status none net worth details organization name patel enterprise sebi registered entity "
        "and other legal declarations with signed documents attached. please verify the client identity and "
        "submit kyc form for processing."
    ),
    "Unrelated News Text (No Matches, Large)": (
        "the stock market reached a record high today as technology shares rallied on optimistic economic indicators. "
        "analysts expect continued growth through the next quarter, citing robust consumer spending and strong corporate "
        "earnings reports. energy and financial sectors also posted gains, while gold and treasury bonds remained stable "
        "as inflation worries subsided. international markets showed mixed results, with european exchanges closing slightly "
        "higher and asian markets finishing in negative territory. economists warn about potential supply chain bottlenecks."
    )
}


def run_standard_benchmark(iterations: int = 2000):
    print("=" * 70)
    print(f"STANDARD BENCHMARK ({iterations} iterations per test)")
    print("=" * 70)
    print(f"{'Test Case':<35} | {'Original (s)':<12} | {'Trie-Based (s)':<14} | {'Speedup':<8}")
    print("-" * 70)

    for name, text in TEST_CASES.items():
        # Warmup
        classify_document_original(text)
        classify_document(text)

        # Benchmark Original
        start_orig = time.perf_counter()
        for _ in range(iterations):
            orig_type, orig_conf = classify_document_original(text)
        orig_time = time.perf_counter() - start_orig

        # Benchmark Trie-based
        start_trie = time.perf_counter()
        for _ in range(iterations):
            trie_type, trie_conf = classify_document(text)
        trie_time = time.perf_counter() - start_trie

        # Correctness check
        if orig_type != trie_type:
            print(f"WARNING: Classification mismatch for '{name}': Original='{orig_type}', Trie='{trie_type}'")

        speedup = orig_time / trie_time if trie_time > 0 else float('inf')
        print(f"{name:<35} | {orig_time:12.4f} | {trie_time:14.4f} | {speedup:7.2f}x")


def run_scaling_benchmark(iterations: int = 1000, num_extra_keywords: int = 2000):
    print("\n" + "=" * 70)
    print(f"SCALING BENCHMARK: Adding {num_extra_keywords} dummy rules to ruleset")
    print("=" * 70)
    
    # Construct scaled rules
    scaled_rules = {k: list(v) for k, v in CLASSIFICATION_RULES.items()}
    # Add dummy document types and keywords
    for i in range(num_extra_keywords):
        doc_idx = i % 10
        doc_name = f"dummy_doc_type_{doc_idx}"
        if doc_name not in scaled_rules:
            scaled_rules[doc_name] = []
        scaled_rules[doc_name].append(f"unrelated dummy phrase word text key label {i}")

    # Build TokenTrie for scaled rules
    start_trie_build = time.perf_counter()
    scaled_trie = TokenTrie()
    for doc_type, keywords in scaled_rules.items():
        for keyword in keywords:
            scaled_trie.insert(keyword, doc_type)
    trie_build_time = time.perf_counter() - start_trie_build
    print(f"TokenTrie built with {num_extra_keywords} extra rules in {trie_build_time:.4f}s")
    print("-" * 70)
    print(f"{'Test Case':<35} | {'Original (s)':<12} | {'Trie-Based (s)':<14} | {'Speedup':<8}")
    print("-" * 70)

    # Benchmark on Large document
    text = TEST_CASES["eKYC Application (Extra Large)"]
    
    # Warmups
    classify_document_original(text, scaled_rules)
    classify_document_trie(text, scaled_trie, scaled_rules)

    # Original
    start_orig = time.perf_counter()
    for _ in range(iterations):
        orig_type, orig_conf = classify_document_original(text, scaled_rules)
    orig_time = time.perf_counter() - start_orig

    # Trie
    start_trie = time.perf_counter()
    for _ in range(iterations):
        trie_type, trie_conf = classify_document_trie(text, scaled_trie, scaled_rules)
    trie_time = time.perf_counter() - start_trie

    speedup = orig_time / trie_time if trie_time > 0 else float('inf')
    print(f"{'eKYC Scaled (Extra Large)':<35} | {orig_time:12.4f} | {trie_time:14.4f} | {speedup:7.2f}x")
    print("=" * 70)


if __name__ == "__main__":
    run_standard_benchmark()
    run_scaling_benchmark(iterations=1000, num_extra_keywords=1000)
    run_scaling_benchmark(iterations=1000, num_extra_keywords=5000)
