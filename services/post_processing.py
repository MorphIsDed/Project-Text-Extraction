"""
Post-processing and validation rules for extracted documents.

This layer is intentionally conservative:
- prefer null over a risky guess
- normalize known formats
- mark suspicious fields for review

NEW ARCHITECTURE:
- Works with typed documents (ExtractedDocument)
- Returns typed documents (not dicts)
- Uses structured ReviewFlag model
"""

from __future__ import annotations

import re
import logging
from datetime import datetime
from typing import Optional

# NEW: Import typed schemas
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


def post_process_document(
    document: ExtractedDocument,
    ocr_text: str = "",
    request_id: Optional[str] = None
) -> ExtractedDocument:
    """
    Post-process extracted document.
    
    NEW ARCHITECTURE:
    - Accepts typed document (not dict)
    - Returns typed document (not dict)
    - Uses structured ReviewFlag model
    
    Args:
        document: Typed document from extraction
        ocr_text: Raw OCR text for fallback extraction
        request_id: Correlation ID for logging
    
    Returns:
        Post-processed typed document
    """
    log_prefix = f"[{request_id}]" if request_id else ""
    
    # Check if document failed extraction
    if document.processing_status == ProcessingStatus.FAILED:
        logger.warning(f"{log_prefix} Skipping post-processing for failed document")
        return document
    
    # Route to document-type-specific post-processing
    doc_type = document.document_type.lower()
    
    if doc_type == "aadhaar" and isinstance(document, AadhaarDocument):
        logger.info(f"{log_prefix} Post-processing Aadhaar document")
        return _post_process_aadhaar(document, ocr_text, request_id)
    
    # TODO: Add post-processing for other document types
    # elif doc_type == "pan" and isinstance(document, PANDocument):
    #     return _post_process_pan(document, ocr_text, request_id)
    
    # No post-processing needed for this document type
    logger.info(f"{log_prefix} No post-processing rules for {doc_type}")
    return document


def _post_process_aadhaar(
    document: AadhaarDocument,
    ocr_text: str,
    request_id: Optional[str] = None
) -> AadhaarDocument:
    """
    Post-process Aadhaar document.
    
    NEW ARCHITECTURE:
    - Works with typed AadhaarDocument
    - Uses structured ReviewFlag model
    - Returns typed document
    
    Args:
        document: Aadhaar document from extraction
        ocr_text: Raw OCR text for fallback
        request_id: Correlation ID
    
    Returns:
        Post-processed Aadhaar document
    """
    log_prefix = f"[{request_id}]" if request_id else ""
    
    # Collect review flags
    review_flags: list[ReviewFlag] = list(document.review_flags)  # Preserve existing flags
    review_notes: list[str] = list(document.review_notes)  # Preserve existing notes
    
    # Process name
    extracted_name = _normalize_spaces(document.name)
    cleaned_name = _clean_name(extracted_name)
    name_reasons = _name_review_reasons(cleaned_name)
    
    if name_reasons:
        ocr_candidate = _best_ocr_name_candidate(ocr_text)
        if ocr_candidate and not _name_review_reasons(ocr_candidate):
            review_flags.append(ReviewFlag(
                field="name",
                severity=ReviewSeverity.MEDIUM,
                reason=f"Name replaced with OCR candidate. Issues: {', '.join(name_reasons)}"
            ))
            review_notes.append("Name was normalized using OCR-supported text.")
            document.name = ocr_candidate
            logger.info(f"{log_prefix} Name replaced with OCR candidate: {ocr_candidate}")
        else:
            review_flags.append(ReviewFlag(
                field="name",
                severity=ReviewSeverity.HIGH,
                reason=f"Name cleared due to: {', '.join(name_reasons)}"
            ))
            review_notes.append("Name was cleared because it looked noisy or unreliable.")
            document.name = None
            logger.warning(f"{log_prefix} Name cleared due to quality issues")
    else:
        document.name = cleaned_name
    
    # Process date of birth
    normalized_dob, dob_reason = _normalize_aadhaar_dob(document.date_of_birth, ocr_text)
    if document.date_of_birth != normalized_dob:
        document.date_of_birth = normalized_dob
        if dob_reason:
            review_flags.append(ReviewFlag(
                field="date_of_birth",
                severity=ReviewSeverity.MEDIUM,
                reason=dob_reason
            ))
            logger.info(f"{log_prefix} DOB normalized: {normalized_dob}")
    
    # Process gender
    normalized_gender, gender_reason = _normalize_gender(document.gender, ocr_text)
    if normalized_gender != document.gender:
        if gender_reason:
            review_flags.append(ReviewFlag(
                field="gender",
                severity=ReviewSeverity.MEDIUM,
                reason=gender_reason
            ))
        if document.gender and normalized_gender is None:
            review_flags.append(ReviewFlag(
                field="gender",
                severity=ReviewSeverity.HIGH,
                reason="Gender value was not reliable enough to keep."
            ))
        document.gender = normalized_gender
        logger.info(f"{log_prefix} Gender normalized: {normalized_gender}")
    
    # Process Aadhaar number (CRITICAL: Security)
    aadhaar_value = document.aadhaar_number_masked
    if not aadhaar_value and document.raw_fields:
        # Gemini sometimes puts unmasked number in raw_fields
        aadhaar_value = document.raw_fields.get("aadhaar_number")
    
    normalized_aadhaar, aadhaar_reason = _normalize_masked_aadhaar(
        aadhaar_value,
        ocr_text,
    )
    if document.aadhaar_number_masked != normalized_aadhaar:
        document.aadhaar_number_masked = normalized_aadhaar
        if aadhaar_reason:
            review_flags.append(ReviewFlag(
                field="aadhaar_number_masked",
                severity=ReviewSeverity.HIGH,
                reason=aadhaar_reason
            ))
            logger.warning(f"{log_prefix} Aadhaar number: {aadhaar_reason}")
    
    # Process PIN code
    normalized_pin = _normalize_pin_code(document.pin_code, document.address, ocr_text)
    if document.pin_code and normalized_pin is None:
        review_flags.append(ReviewFlag(
            field="pin_code",
            severity=ReviewSeverity.LOW,
            reason="PIN code was not a valid 6-digit value."
        ))
    document.pin_code = normalized_pin
    
    # Process address
    normalized_address = _normalize_address(document.address)
    if document.address and normalized_address is None:
        review_flags.append(ReviewFlag(
            field="address",
            severity=ReviewSeverity.MEDIUM,
            reason="Address looked too fragmentary to trust."
        ))
    document.address = normalized_address
    
    # Process side detected
    side = _normalize_side_detected(document.side_detected)
    if document.side_detected and side is None:
        review_flags.append(ReviewFlag(
            field="side_detected",
            severity=ReviewSeverity.LOW,
            reason="Side detection value was not recognized."
        ))
    document.side_detected = side
    
    # Update review flags and notes
    document.review_flags = review_flags
    document.review_notes = review_notes
    
    # Update processing status based on review flags
    if document.needs_review:
        document.processing_status = ProcessingStatus.NEEDS_REVIEW
    
    logger.info(f"{log_prefix} Aadhaar post-processing complete: {len(review_flags)} flags")
    return document


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
        reasons.append("Aadhaar name did not look like a clean 2-4 token name.")
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


def _normalize_aadhaar_dob(value, ocr_text: str) -> tuple[str | None, str | None]:
    candidate = _normalize_spaces(value)
    normalized = _coerce_dob(candidate)
    if normalized:
        return normalized, None

    ocr_match = _extract_year_or_date_from_text(ocr_text)
    if ocr_match:
        return ocr_match, "Date of birth was normalized from OCR text."

    if candidate:
        return None, "Date of birth did not match DD/MM/YYYY or YYYY."
    return None, None


def _coerce_dob(value: str | None) -> str | None:
    if not value:
        return None

    value = value.replace("-", "/").replace(".", "/")
    value = re.sub(r"\s+", "", value)

    year_match = re.fullmatch(r"(19\d{2}|20\d{2})", value)
    if year_match:
        year = int(year_match.group(1))
        if 1900 <= year <= datetime.now().year:
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

    if parsed.year > datetime.now().year:
        return None

    return f"{day:02d}/{month:02d}/{year:04d}"


def _extract_year_or_date_from_text(text: str) -> str | None:
    if not text:
        return None

    date_match = re.search(r"\b(\d{2})[\/\-\.](\d{2})[\/\-\.](\d{4})\b", text)
    if date_match:
        return _coerce_dob("/".join(date_match.groups()))

    year_match = re.search(r"\b(19\d{2}|20\d{2})\b", text)
    if year_match:
        return _coerce_dob(year_match.group(1))

    return None


def _normalize_gender(value, ocr_text: str) -> tuple[str | None, str | None]:
    ocr_gender = _extract_gender_from_ocr(ocr_text)
    if ocr_gender:
        candidate = _normalize_spaces(value)
        if candidate and _normalize_gender_token(candidate) not in {None, ocr_gender}:
            return ocr_gender, "Gender was corrected using OCR text evidence."
        return ocr_gender, None

    candidate = _normalize_spaces(value)
    return _normalize_gender_token(candidate), None


def _normalize_masked_aadhaar(value, ocr_text: str) -> tuple[str | None, str | None]:
    # CRITICAL: Force masking if Gemini returned full unmasked number
    if value:
        # Check if value contains a full 12-digit Aadhaar (unmasked)
        digits_only = re.sub(r"\D", "", str(value))
        if len(digits_only) == 12:
            # Force mask it - only show last 4 digits
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


def _normalize_gender_token(value: str | None) -> str | None:
    if not value:
        return None
    lower = value.lower()
    if lower in {"male", "m", HINDI_MALE.lower()}:
        return "Male"
    if lower in {"female", "f", HINDI_FEMALE.lower()}:
        return "Female"
    return None


def _extract_gender_from_ocr(text: str) -> str | None:
    if not text:
        return None

    lowered = text.lower()
    
    # Handle common OCR corruptions like 'fe male'
    is_female = bool(re.search(r"\bfemale\b", lowered) or "fe male" in lowered or HINDI_FEMALE in text)
    if is_female:
        return "Female"
        
    is_male = bool(re.search(r"\bmale\b", lowered) or HINDI_MALE in text)
    if is_male:
        return "Male"
        
    return None


def _normalize_pin_code(value, address, ocr_text: str) -> str | None:
    candidate = _extract_six_digits(value)
    if candidate:
        return candidate

    candidate = _extract_six_digits(address)
    if candidate:
        return candidate

    return _extract_six_digits(ocr_text)


def _extract_six_digits(value) -> str | None:
    text = _normalize_spaces(value)
    if not text:
        return None
    match = re.search(r"\b(\d{6})\b", text)
    return match.group(1) if match else None


def _normalize_address(value) -> str | None:
    address = _normalize_spaces(value)
    if not address:
        return None
    if len(address) < 10:
        return None
    if len(re.findall(r"[A-Za-z]", address)) < 6:
        return None
    return address


def _normalize_side_detected(value) -> str | None:
    text = _normalize_spaces(value)
    if not text:
        return None
    lower = text.lower()
    if lower in {"front", "back", "both"}:
        return lower
    return None
