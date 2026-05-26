"""
Document classifier based on OCR keyword matching.
"""

import logging

logger = logging.getLogger(__name__)


CLASSIFICATION_RULES = {
    "aadhaar": [
        "unique identification authority",
        "uidai",
        "aadhaar",
        "aadhar",
        "government of india",
        "enrollment no",
        "vid:",
        "virtual id",
        "year of birth",
        "date of birth",
        "dob:",
    ],
    "pan": [
        "income tax department",
        "permanent account number",
        "govt. of india",
    ],
    "voter_id": [
        "election commission",
        "epic",
        "electors photo identity",
    ],
    "driving_licence": [
        "driving licence",
        "driver licence",
        "transport authority",
        "regional transport",
        "rto",
        "vehicle class",
        "date of expiry",
        "badge no",
        "dl no",
    ],
    "passport": [
        "republic of india",
        "passport",
        "place of birth",
        "date of expiry",
        "nationality",
        "ministry of external affairs",
        "surname",
        "given name",
    ],
    "invoice": [
        "gstin",
        "tax invoice",
        "invoice no",
        "invoice number",
        "bill to",
        "ship to",
        "cgst",
        "sgst",
        "igst",
        "total amount",
    ],
    "ekyc": [
        "know your customer",
        "kyc form",
        "kyc application",
        "kyc updation",
        "in person verification",
        "ipv",
        "customer due diligence",
        "ckyc",
        "customer id",
        "account no",
        "applicant name",
        "father/spouse name",
        "monthly income",
        "occupation type",
        "pep status",
        "net worth",
        "organization name",
        "sebi",
        "annexure",
    ],
}


def classify_document(text: str) -> tuple[str, float]:
    """
    Classify document type from OCR text.
    """
    if not text or len(text.strip()) < 10:
        logger.warning("Text too short for classification")
        return "unknown", 0.0

    text_lower = text.lower()
    scores = {}

    for doc_type, keywords in CLASSIFICATION_RULES.items():
        matched = sum(1 for keyword in keywords if keyword in text_lower)
        if matched > 0:
            scores[doc_type] = min(0.95, 0.6 + (matched / len(keywords)))

    if not scores:
        logger.info("No keywords matched, returning unknown")
        return "unknown", 0.0

    best_type = max(scores, key=scores.get)
    best_confidence = scores[best_type]

    logger.info(f"Document classified as '{best_type}' with confidence {best_confidence:.2f}")
    return best_type, best_confidence


def classify_from_image_path(image_path: str) -> tuple[str, float]:
    """
    Helper used by tests and debugging scripts.
    """
    try:
        from services.ocr_service import extract_text

        text, _ = extract_text(image_path)
        return classify_document(text)
    except Exception as exc:
        logger.error(f"Classification from image failed: {exc}")
        return "unknown", 0.0
