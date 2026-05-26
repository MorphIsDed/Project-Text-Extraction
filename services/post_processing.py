"""
Post-processing and validation rules for extracted documents.

Modularized and integrated with OOPS Strategy pattern delegates.
"""

from __future__ import annotations

import re
import logging
from datetime import datetime
from typing import Optional, List

from models.schemas import (
    ExtractedDocument,
    AadhaarDocument,
    ReviewFlag,
    ReviewSeverity,
    ProcessingStatus
)

logger = logging.getLogger(__name__)

AADHAAR_KEYWORDS = {
    "government",
    "india",
    "dob",
    "date",
    "birth",
    "year",
    "male",
    "female",
    "address",
    "aadhaar",
    "authority",
    "identification",
    "enrolment",
    "vid",
}

HINDI_MALE = "\u092a\u0941\u0930\u0941\u0937"
HINDI_FEMALE = "\u092e\u0939\u093f\u0932\u093e"


# ============================================================
# MAIN ENTRY POINT (OOP DELEGATION)
# ============================================================

def post_process_document(
    document: ExtractedDocument,
    ocr_text: str = "",
    request_id: Optional[str] = None
) -> ExtractedDocument:
    """
    Post-process extracted document using Strategy Processor Factory.
    
    Args:
        document: Typed document from extraction
        ocr_text: Raw OCR text for verification and fallback
        request_id: Correlation ID for logging
        
    Returns:
        Post-processed and validated document
    """
    log_prefix = f"[{request_id}]" if request_id else ""
    
    if document.processing_status == ProcessingStatus.FAILED:
        logger.warning(f"{log_prefix} Skipping post-processing for failed document")
        return document
        
    from services.processors import DocumentProcessorFactory
    
    # Resolve strategy from O(1) factory registry
    doc_type = document.document_type.value if hasattr(document.document_type, "value") else str(document.document_type)
    processor = DocumentProcessorFactory.get_processor(doc_type)
    
    logger.info(f"{log_prefix} Executing OOP post-processing strategy for '{doc_type}'")
    return processor.post_process(document, ocr_text, request_id or "")


# ============================================================
# REUSABLE VALIDATION HELPERS (DSA ALGORITHMS)
# ============================================================

def add_review_flag(
    document: ExtractedDocument,
    field: str,
    severity: ReviewSeverity,
    reason: str,
    request_id: str = ""
) -> None:
    """Safely appends a new structured review flag to the document."""
    log_prefix = f"[{request_id}]" if request_id else ""
    
    # Check if this flag already exists to prevent duplicate additions
    exists = any(f.field == field and f.reason == reason for f in document.review_flags)
    if not exists:
        flag = ReviewFlag(field=field, severity=severity, reason=reason)
        document.review_flags.append(flag)
        logger.info(f"{log_prefix} Added {severity.value} flag on '{field}': {reason}")


def check_needs_review_logical(document: ExtractedDocument, request_id: str = "") -> ExtractedDocument:
    """
    Evaluates logical flags to determine if the document requires manual review.
    Upgrades the overall document processing status accordingly.
    """
    log_prefix = f"[{request_id}]" if request_id else ""
    
    # If any HIGH or MEDIUM severity flags exist, the document needs review
    has_critical_flags = any(
        f.severity in [ReviewSeverity.HIGH, ReviewSeverity.MEDIUM]
        for f in document.review_flags
    )
    
    if has_critical_flags or document.needs_review:
        document.processing_status = ProcessingStatus.NEEDS_REVIEW
        logger.warning(f"{log_prefix} Document marked as NEEDS_REVIEW")
    else:
        document.processing_status = ProcessingStatus.SUCCESS
        
    return document


def validate_name_ocr(document: ExtractedDocument, ocr_text: str, request_id: str = "") -> ExtractedDocument:
    """Verifies extracted name against OCR text to find discrepancy flags."""
    if not hasattr(document, "name") or not getattr(document, "name"):
        return document
        
    extracted_name = _normalize_spaces(getattr(document, "name"))
    cleaned_name = _clean_name(extracted_name)
    name_reasons = _name_review_reasons(cleaned_name)
    
    if name_reasons:
        # OCR fallback extraction
        ocr_candidate = _best_ocr_name_candidate(ocr_text)
        if ocr_candidate and not _name_review_reasons(ocr_candidate):
            add_review_flag(
                document,
                field="name",
                severity=ReviewSeverity.MEDIUM,
                reason=f"Name normalized using OCR candidate due to: {', '.join(name_reasons)}",
                request_id=request_id
            )
            document.review_notes.append("Name was normalized using OCR text.")
            setattr(document, "name", ocr_candidate)
        else:
            add_review_flag(
                document,
                field="name",
                severity=ReviewSeverity.HIGH,
                reason=f"Name cleared due to validation issues: {', '.join(name_reasons)}",
                request_id=request_id
            )
            document.review_notes.append("Name was cleared because it was flagged as unreliable.")
            setattr(document, "name", None)
    else:
        setattr(document, "name", cleaned_name)
        
    return document


def validate_document_numbers(document: ExtractedDocument, ocr_text: str, request_id: str = "") -> ExtractedDocument:
    """Validates document numbers and enforces security masking where applicable."""
    doc_type = document.document_type.value if hasattr(document.document_type, "value") else str(document.document_type)
    
    # Aadhaar Masked Verification
    if doc_type == "aadhaar" and hasattr(document, "aadhaar_number_masked"):
        aadhaar_value = getattr(document, "aadhaar_number_masked")
        if not aadhaar_value and document.raw_fields:
            aadhaar_value = document.raw_fields.get("aadhaar_number")
            
        normalized_aadhaar, aadhaar_reason = _normalize_masked_aadhaar(aadhaar_value, ocr_text)
        if getattr(document, "aadhaar_number_masked") != normalized_aadhaar:
            setattr(document, "aadhaar_number_masked", normalized_aadhaar)
            if aadhaar_reason:
                add_review_flag(
                    document,
                    field="aadhaar_number_masked",
                    severity=ReviewSeverity.HIGH,
                    reason=aadhaar_reason,
                    request_id=request_id
                )
                
    # PAN Verification
    elif doc_type == "pan" and hasattr(document, "pan_number"):
        pan = getattr(document, "pan_number")
        if pan:
            pan_str = str(pan).upper().replace(" ", "")
            # Standard PAN format: 5 letters, 4 digits, 1 letter
            if not re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]$", pan_str):
                add_review_flag(
                    document,
                    field="pan_number",
                    severity=ReviewSeverity.HIGH,
                    reason=f"PAN number '{pan}' does not match standard 10-character alphanumeric format.",
                    request_id=request_id
                )
                
    return document


def validate_dates(document: ExtractedDocument, request_id: str = "") -> ExtractedDocument:
    """Validates extracted birth, issue, or expiry dates."""
    doc_type = document.document_type.value if hasattr(document.document_type, "value") else str(document.document_type)
    
    # DOB Verification
    if hasattr(document, "date_of_birth"):
        dob = getattr(document, "date_of_birth")
        if dob:
            normalized_dob = _coerce_dob(str(dob))
            if not normalized_dob:
                add_review_flag(
                    document,
                    field="date_of_birth",
                    severity=ReviewSeverity.MEDIUM,
                    reason=f"Date of birth '{dob}' did not match DD/MM/YYYY or YYYY format.",
                    request_id=request_id
                )
            else:
                setattr(document, "date_of_birth", normalized_dob)
                
    # Expiry Date Verification (Passports, Driving Licenses)
    if hasattr(document, "date_of_expiry"):
        expiry = getattr(document, "date_of_expiry")
        if expiry:
            normalized_expiry = _coerce_dob(str(expiry))
            if not normalized_expiry:
                add_review_flag(
                    document,
                    field="date_of_expiry",
                    severity=ReviewSeverity.MEDIUM,
                    reason=f"Expiry date '{expiry}' did not match DD/MM/YYYY format.",
                    request_id=request_id
                )
            else:
                setattr(document, "date_of_expiry", normalized_expiry)
                
    return document


# ============================================================
# INTERNAL CLEANING FUNCTIONS
# ============================================================

def _normalize_spaces(value) -> str | None:
    if value is None:
        return None
    text = str(value).replace("\n", " ").strip()
    text = re.sub(r"\s+", " ", text)
    return text or None


def _clean_name(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.replace("|", " ").replace("_", " ")
    cleaned = re.sub(r"[^A-Za-z .'-]", " ", cleaned)
    cleaned = _normalize_spaces(cleaned)
    if not cleaned:
        return None
    return " ".join(part.capitalize() for part in cleaned.split())


def _name_review_reasons(name: str | None) -> list[str]:
    reasons: list[str] = []
    if not name:
        reasons.append("Name is missing after cleanup.")
        return reasons

    tokens = [token for token in name.split() if token]
    if len(tokens) < 2 or len(tokens) > 4:
        reasons.append("Name did not look like a clean 2-4 token name.")
    if any(len(token) < 2 for token in tokens):
        reasons.append("Name contains very short fragments.")
    if any(re.search(r"(.)\1\1", token.lower()) for token in tokens):
        reasons.append("Name contains repeated OCR-like character noise.")
    if len(name) < 5:
        reasons.append("Name is too short to trust.")
    return reasons


def _best_ocr_name_candidate(ocr_text: str) -> str | None:
    if not ocr_text:
        return None

    candidates: list[str] = []
    for raw_line in ocr_text.splitlines():
        line = _normalize_spaces(raw_line)
        if not line:
            continue
        lower = line.lower()
        if any(keyword in lower for keyword in AADHAAR_KEYWORDS):
            continue
        if any(char.isdigit() for char in line):
            continue

        cleaned = _clean_name(line)
        if not cleaned:
            continue
        if _name_review_reasons(cleaned):
            continue
        candidates.append(cleaned)

    if not candidates:
        return None

    candidates.sort(key=lambda item: (len(item.split()), len(item)), reverse=True)
    return candidates[0]


def _coerce_dob(value: str | None) -> str | None:
    if not value:
        return None

    value = value.replace("-", "/").replace(".", "/")
    value = re.sub(r"\s+", "", value)

    year_match = re.fullmatch(r"(19\d{2}|20\d{2})", value)
    if year_match:
        year = int(year_match.group(1))
        if 1900 <= year <= datetime.now().year + 20: # Expiry dates could be in the future
            return str(year)
        return None

    date_match = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", value)
    if not date_match:
        return None

    day, month, year = map(int, date_match.groups())
    try:
        parsed = datetime(year, month, day)
    except ValueError:
        return None

    return f"{day:02d}/{month:02d}/{year:04d}"


def _normalize_masked_aadhaar(value, ocr_text: str) -> tuple[str | None, str | None]:
    if value:
        digits_only = re.sub(r"\D", "", str(value))
        if len(digits_only) == 12:
            last4 = digits_only[-4:]
            return f"XXXX XXXX {last4}", "Aadhaar number was force-masked for security."
    
    extracted_last4 = _extract_last4_from_value(value)
    ocr_last4 = _extract_last4_from_ocr(ocr_text)

    if ocr_last4 and extracted_last4 and extracted_last4 != ocr_last4:
        return f"XXXX XXXX {ocr_last4}", "Aadhaar last four digits were corrected from OCR text."

    if ocr_last4:
        return f"XXXX XXXX {ocr_last4}", None

    if extracted_last4:
        return f"XXXX XXXX {extracted_last4}", None

    if value:
        return None, "Aadhaar number did not match the expected masked format."

    return None, None


def _extract_last4_from_value(value) -> str | None:
    text = _normalize_spaces(value)
    if not text:
        return None

    text = text.replace("-", " ")
    masked_match = re.search(r"X{4}\s*X{4}\s*(\d{4})", text, flags=re.IGNORECASE)
    if masked_match:
        return masked_match.group(1)

    digits = re.sub(r"\D", "", text)
    if len(digits) == 12:
        return digits[-4:]
    if len(digits) == 4:
        return digits
    return None


def _extract_last4_from_ocr(text: str) -> str | None:
    best_candidate = _best_aadhaar_number_candidate(text)
    return best_candidate[-4:] if best_candidate else None


def _best_aadhaar_number_candidate(text: str) -> str | None:
    if not text:
        return None

    lines = [_normalize_spaces(line) for line in text.splitlines()]
    lines = [line for line in lines if line]
    candidates: list[tuple[int, str]] = []

    for index, line in enumerate(lines):
        context = " ".join(lines[max(0, index - 1): min(len(lines), index + 2)]).lower()
        for candidate in _extract_aadhaar_candidates_from_line(line):
            score = 0
            if re.fullmatch(r"\d{4}[\s-]\d{4}[\s-]\d{4}", line):
                score += 8
            elif re.search(r"\d{4}[\s-]\d{4}[\s-]\d{4}", line):
                score += 6
            else:
                score += 4

            if any(keyword in context for keyword in ("aadhaar", "uidai", "government of india", "govt")):
                score += 2

            if any(keyword in context for keyword in ("dob", "birth", "year", "male", "female", "gender", "pin", "address")):
                score -= 2

            digit_density = len(re.sub(r"\D", "", line))
            if digit_density == 12:
                score += 2
            elif digit_density > 16:
                score -= 1

            normalized = re.sub(r"\D", "", candidate)
            if len(normalized) == 12:
                candidates.append((score, normalized))

    if not candidates:
        return None

    candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    best_score, best_candidate = candidates[0]
    if best_score < 4:
        return None
    return best_candidate


def _extract_aadhaar_candidates_from_line(line: str) -> list[str]:
    candidates: list[str] = []
    candidates.extend(re.findall(r"(?<!\d)(\d{4}[\s-]\d{4}[\s-]\d{4})(?!\d)", line))
    candidates.extend(re.findall(r"(?<!\d)(\d{12})(?!\d)", line))
    
    masked_matches = re.findall(r"(?:X{4}|x{4})[\s-]*(?:X{4}|x{4})[\s-]*(\d{4})", line)
    for m in masked_matches:
        candidates.append(f"00000000{m}")
        
    return candidates
