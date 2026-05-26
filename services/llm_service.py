"""
AI Provider Service

Primary: Gemini 1.5 Flash (vision-capable, free, handles Hindi)
Fallback: Groq llama-3.1-8b (text-only, ultra fast)

Architecture:
    Gemini/Groq Response
        ↓
    normalize_document_data()
        ↓
    create_document() (typed schema)
        ↓
    Typed Document (AadhaarDocument, PANDocument, etc.)
"""

import os
import json
import logging
import re
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# google-generativeai handles its own imports inside the class
from PIL import Image

# NEW: Import normalizer and schema factory
from services.normalizer import normalize_document_data
from models.schemas import create_document, ExtractedDocument, ProcessingStatus

load_dotenv()

logger = logging.getLogger(__name__)

JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)

# ============================================================
# PROMPTS — One per document type. Specific. No fluff.
# ============================================================

PROMPTS = {
    "aadhaar": """***You are analyzing an Aadhaar card.
Extract ONLY what is clearly visible. Return null for anything unclear.
NEVER guess. NEVER make up data.

CRITICAL RULES:
- If card shows ONLY year (e.g. "Year of Birth: 1990"), return ONLY "1990" for date_of_birth
- Gender: Look for English text FIRST. पुरुष = Male. If both Hindi and English present, use English.
- Name: Return ONLY a clean human name. If the line contains OCR junk, merged fragments, stray prefixes, or uncertain characters, return null instead of guessing.
- Do NOT reconstruct missing letters in names. Do NOT return partial noisy names.
- Address: Extract ONLY actual address with house/flat number, street, city. IGNORE short fragments.
- PIN code: 6-digit number only. If not clearly visible, return null.

AADHAAR NUMBER MASKING (CRITICAL - SECURITY REQUIREMENT):
You MUST mask the Aadhaar number for privacy and security. This is a legal requirement.
- If the visible Aadhaar number is "3511 2297 5747", you MUST return "XXXX XXXX 5747"
- If the visible Aadhaar number is "3179 3974 5818", you MUST return "XXXX XXXX 5818"
- If the visible Aadhaar number is "1234 5678 9012", you MUST return "XXXX XXXX 9012"
- ALWAYS replace the first 8 digits with "XXXX XXXX"
- ONLY show the last 4 digits
- Format: "XXXX XXXX" followed by space and the actual last 4 digits
- NEVER return the full Aadhaar number in ANY field
- Do NOT put unmasked Aadhaar in raw_fields or any other field
- Example: For card showing "3511 2297 5747", you MUST return "XXXX XXXX 5747" in aadhaar_number_masked

Return ONLY this JSON (do NOT add extra fields):
{
  "document_type": "aadhaar",
  "name": "clean name only or null",
  "date_of_birth": "DD/MM/YYYY or YYYY if only year available or null",
  "gender": "Male or Female or null",
  "aadhaar_number_masked": "XXXX XXXX followed by space and the actual last 4 digits, or null",
  "address": "real address only or null",
  "pin_code": "6-digit string or null",
  "side_detected": "front or back or both"
}***

IMPORTANT: Do NOT include raw_fields, summary, or confidence in your response. Only return the exact JSON structure shown above.""",
    
    "pan": """You are analyzing a PAN card — India's tax ID document. Extract ONLY what is clearly visible. Return null for anything unclear. NEVER guess or make up data.

RULES:
- PAN number is exactly 10 characters: 5 letters, 4 digits, 1 letter (e.g. ABCDE1234F)
- DOB format: DD/MM/YYYY
- PAN numbers are NOT masked — show full number

Return ONLY this JSON, nothing else:
{
  "document_type": "pan",
  "name": "string or null",
  "father_name": "string or null",
  "date_of_birth": "DD/MM/YYYY or null",
  "pan_number": "10-char string or null"
}""",

    "driving_licence": """You are analyzing an Indian Driving License.
Extract ONLY what is clearly visible. Return null for unclear fields.
NEVER guess or make up data.

RULES:
- License number format: State(2) + RTO(2) + Year(4) + Sequence(7). Example: TNBB2019000099
- Date format: DD/MM/YYYY
- Issuing authority is the RTO (Regional Transport Office)

Return ONLY this JSON:
{
  "document_type": "driving_licence",
  "name": "string or null",
  "date_of_birth": "DD/MM/YYYY or null",
  "licence_number": "string or null",
  "date_of_issue": "DD/MM/YYYY or null",
  "date_of_expiry": "DD/MM/YYYY or null",
  "address": "string or null",
  "vehicle_classes": "string or null",
  "issuing_rto": "string or null"
}""",

    "passport": """You are analyzing an Indian Passport.
Extract ONLY what is clearly visible. Return null for unclear fields.
NEVER guess or make up data.

RULES:
- Passport number: 1 letter + 7 digits. Example: K8016274
- MRZ (Machine Readable Zone) is the two lines at the bottom — most reliable part
- Date format: DD/MM/YYYY
- Extract from MRZ if main fields are unclear

Return ONLY this JSON:
{
  "document_type": "passport",
  "surname": "string or null",
  "given_name": "string or null",
  "date_of_birth": "DD/MM/YYYY or null",
  "gender": "Male or Female or null",
  "passport_number": "string or null",
  "date_of_issue": "DD/MM/YYYY or null",
  "date_of_expiry": "DD/MM/YYYY or null",
  "place_of_birth": "string or null",
  "nationality": "Indian or null",
  "mrz_line1": "string or null",
  "mrz_line2": "string or null"
}""",
    
    "invoice": """You are analyzing an Indian TAX INVOICE or GST INVOICE. This is a business document showing goods/services sold.

Extract ONLY what is clearly visible. Return null for anything unclear. NEVER guess.

CRITICAL RULES:
- Look for "TAX INVOICE" or "INVOICE" at the top
- Vendor = Seller/Supplier (top section, has "YOUR COMPANY" or company name)
- Buyer = Customer/Recipient (section with "Buyer" or customer details)
- GSTIN format: 15 characters (e.g., 19BB577660S, 29AABCN9911K)
- Invoice number: Look for "Invoice No." or "LMT.0893.2023-24"
- Date format: DD-MM-YYYY or DD/MM/YYYY
- Amounts: Look for "Total", "CGST", "SGST", "IGST"
- Total amount is the FINAL amount (after all taxes)
- Line items: Extract from table with Description, Quantity, Rate, Amount

IMPORTANT:
- Vendor GSTIN and Buyer GSTIN are DIFFERENT
- Don't confuse vendor with buyer
- Total amount includes all taxes (CGST + SGST or IGST)
- Currency is always INR for Indian invoices

Return ONLY this JSON, nothing else:
{
  "document_type": "invoice",
  "vendor_name": "string or null",
  "vendor_gstin": "15-char string or null",
  "invoice_number": "string or null",
  "invoice_date": "DD-MM-YYYY or null",
  "buyer_name": "string or null",
  "buyer_gstin": "15-char string or null",
  "subtotal": "number (before tax) or null",
  "gst_amount": "number (CGST+SGST or IGST) or null",
  "total_amount": "number (final amount) or null",
  "currency": "INR",
  "line_items": []
}""",
    
    "voter_id": """You are analyzing an Indian Voter ID card (EPIC - Electors Photo Identity Card).
Extract ONLY what is clearly visible. Return null for unclear fields.
NEVER guess or make up data.

RULES:
- Voter ID number format varies by state but typically 3 letters + 7 digits (e.g., ABC1234567)
- Date format: DD/MM/YYYY
- Card has front and back - extract from visible side

Return ONLY this JSON:
{
  "document_type": "voter_id",
  "name": "string or null",
  "father_name": "string or null",
  "date_of_birth": "DD/MM/YYYY or null",
  "gender": "Male or Female or null",
  "voter_id_number": "string or null",
  "address": "string or null",
  "polling_station": "string or null",
  "assembly_constituency": "string or null",
  "side_detected": "front or back or both"
}""",
    
    "ekyc": """You are analyzing a KYC (Know Your Customer) form - bank account opening, investment, or financial services application form.

IMPORTANT: This is NOT a passport, even if passport is mentioned as ID proof.

Extract ONLY what is clearly visible. Return null for anything unclear.

RULES:
- This is a FORM, not an identity document
- Look for: Customer ID, Account Number, Applicant Name, Father/Spouse Name
- Mobile number: 10 digits with +91 or without
- Email: standard email format
- Bank/Organization name: Look for bank name or organization
- Account type: Savings, Current, Demat, Trading, etc.
- Address: Residential or correspondence address
- If form has multiple sections, extract from "Personal Details" or "Identity Details" section

Return ONLY this JSON, nothing else:
{
  "document_type": "ekyc",
  "applicant_name": "string or null",
  "date_of_birth": "DD/MM/YYYY or null",
  "gender": "Male or Female or null",
  "address": "string or null",
  "mobile_number": "10-digit string or null",
  "email": "string or null",
  "account_type": "string or null",
  "bank_name": "string or null"
}""",
    
    "unknown": """You are analyzing a document. Identify what type it is and extract key information. Extract ONLY what is clearly visible. Return null for anything unclear.

Return ONLY this JSON, nothing else:
{
  "document_type": "detected type (aadhaar/pan/invoice/ekyc/other)",
  "raw_fields": {},
  "summary": "one sentence describing what this document is"
}"""
}


def _strip_response_wrappers(text: str) -> str:
    cleaned = (text or "").strip()
    if not cleaned:
        return ""

    fence_match = JSON_FENCE_RE.search(cleaned)
    if fence_match:
        cleaned = fence_match.group(1).strip()

    if cleaned.lower().startswith("json"):
        cleaned = cleaned[4:].strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start:end + 1]

    return cleaned.strip()


def _repair_json_candidate(text: str) -> str:
    candidate = text.strip()
    if not candidate:
        return candidate

    candidate = re.sub(r",\s*([}\]])", r"\1", candidate)

    open_braces = candidate.count("{")
    close_braces = candidate.count("}")
    if open_braces > close_braces:
        candidate += "}" * (open_braces - close_braces)

    open_brackets = candidate.count("[")
    close_brackets = candidate.count("]")
    if open_brackets > close_brackets:
        candidate += "]" * (open_brackets - close_brackets)

    return candidate


def _decode_json_value(raw: str):
    raw = raw.strip()
    if raw == "null":
        return None
    if raw.startswith('"') and raw.endswith('"'):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw.strip('"')
    return raw


def _parse_relaxed_aadhaar_json(text: str) -> dict | None:
    parsed: dict = {"document_type": "aadhaar", "confidence": {"overall": 0.0}}
    field_patterns = {
        "name": r'"?name"?\s*:\s*(null|"[^"]*"|[^,\n}]+)',
        "date_of_birth": r'"?date_of_birth"?\s*:\s*(null|"[^"]*"|[^,\n}]+)',
        "gender": r'"?gender"?\s*:\s*(null|"[^"]*"|[^,\n}]+)',
        "aadhaar_number_masked": r'"?aadhaar_number_masked"?\s*:\s*(null|"[^"]*"|[^,\n}]+)',
        "address": r'"?address"?\s*:\s*(null|"[^"]*"|[^,\n}]+)',
        "pin_code": r'"?pin_code"?\s*:\s*(null|"[^"]*"|[^,\n}]+)',
        "side_detected": r'"?side_detected"?\s*:\s*(null|"[^"]*"|[^,\n}]+)',
    }

    found_any = False
    for field, pattern in field_patterns.items():
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            parsed[field] = _decode_json_value(match.group(1))
            found_any = True

    confidence_fields = ("name", "date_of_birth", "gender", "aadhaar_number", "address")
    confidence: dict[str, float] = {}
    for field in confidence_fields:
        match = re.search(rf'"?{field}"?\s*:\s*([0-9]+(?:\.[0-9]+)?)', text, flags=re.IGNORECASE)
        if match:
            try:
                confidence[field] = float(match.group(1))
            except ValueError:
                pass
    if confidence:
        parsed["confidence"] = confidence

    return parsed if found_any else None


def _parse_model_json(
    text: str,
    doc_type: str,
    request_id: Optional[str] = None
) -> ExtractedDocument:
    """
    Parse Gemini/Groq JSON response into typed document.
    
    NEW ARCHITECTURE:
    1. Parse raw JSON
    2. Normalize data
    3. Create typed document via factory
    
    Args:
        text: Raw JSON response from LLM
        doc_type: Document type
        request_id: Correlation ID for logging
    
    Returns:
        Typed document (AadhaarDocument, PANDocument, etc.)
    """
    log_prefix = f"[{request_id}]" if request_id else ""
    
    # Step 1: Parse raw JSON
    cleaned = _strip_response_wrappers(text)
    candidates = [cleaned]

    repaired = _repair_json_candidate(cleaned)
    if repaired and repaired not in candidates:
        candidates.append(repaired)

    raw_data = None
    for candidate in candidates:
        if not candidate:
            continue
        try:
            raw_data = json.loads(candidate)
            logger.info(f"{log_prefix} Raw LLM response parsed successfully")
            break
        except json.JSONDecodeError:
            continue

    # Fallback: Try relaxed Aadhaar parsing
    if not raw_data and doc_type == "aadhaar":
        raw_data = _parse_relaxed_aadhaar_json(cleaned or text)
        if raw_data:
            logger.warning(f"{log_prefix} Recovered Aadhaar fields from malformed JSON")

    # If still no data, return failed UnknownDocument
    if not raw_data:
        logger.error(f"{log_prefix} Unable to parse LLM JSON response")
        return create_document(
            document_type="unknown",
            data={
                "detected_document_type": doc_type,
                "summary": "Failed to parse LLM response",
                "processing_status": ProcessingStatus.FAILED
            },
            request_id=request_id
        )
    
    # Log raw response (for debugging)
    logger.debug(f"{log_prefix} Raw parsed data: {raw_data}")
    
    # Step 2: Detect document type
    detected_type = raw_data.get("document_type", doc_type)
    
    # Step 3: Normalize data BEFORE schema validation
    logger.info(f"{log_prefix} Normalizing {detected_type} data")
    normalized_data = normalize_document_data(detected_type, raw_data)
    logger.debug(f"{log_prefix} Normalized data: {normalized_data}")
    
    # Step 4: Create typed document via factory
    logger.info(f"{log_prefix} Creating typed document: {detected_type}")
    document = create_document(
        document_type=detected_type,
        data=normalized_data,
        request_id=request_id
    )
    
    # Log document type for verification
    logger.info(f"{log_prefix} Created document type: {type(document).__name__}")
    
    return document


# ============================================================
# BASE PROVIDER
# ============================================================

class BaseAIProvider(ABC):
    @abstractmethod
    def extract_from_image(
        self,
        image_path: str,
        doc_type: str,
        request_id: Optional[str] = None
    ) -> ExtractedDocument:
        """Extract fields from document image"""
        pass
    
    @abstractmethod
    def extract_from_text(
        self,
        text: str,
        doc_type: str = "unknown",
        request_id: Optional[str] = None
    ) -> ExtractedDocument:
        """Extract fields from OCR text"""
        pass
    
    def get_prompt(self, doc_type: str) -> str:
        return PROMPTS.get(doc_type, PROMPTS["unknown"])


# ============================================================
# GEMINI PROVIDER (PRIMARY)
# ============================================================

class GeminiProvider(BaseAIProvider):
    def __init__(self):
        import google.generativeai as genai
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set in .env")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        logger.info("GeminiProvider initialized with gemini-2.5-flash")
    
    def extract_from_image(
        self,
        image_path: str,
        doc_type: str,
        request_id: Optional[str] = None
    ) -> ExtractedDocument:
        """
        Extract from image using Gemini Vision.
        
        NEW: Returns typed document (not dict)
        """
        log_prefix = f"[{request_id}]" if request_id else ""
        
        try:
            from PIL import Image
            image = Image.open(image_path)
            prompt = self.get_prompt(doc_type)
            
            response = None  # Initialize response
            
            try:
                logger.info(f"{log_prefix} Calling Gemini Vision for {doc_type}")
                response = self.model.generate_content(
                    [prompt, image],
                    generation_config={
                        "temperature": 0.0,
                        "max_output_tokens": 1024,
                        "response_mime_type": "application/json",  # Force JSON output
                    }
                )
                
                # Validate response is not empty/bad
                if not response or not response.text or len(response.text.strip()) < 10:
                    raise ValueError("Gemini returned empty or invalid response")
                
                # Log raw response (truncated)
                logger.debug(f"{log_prefix} Raw Gemini response: {response.text[:200]}...")
                
                # NEW: Parse into typed document
                document = _parse_model_json(response.text, doc_type, request_id)
                
                # Validate result is not garbage (basic check)
                if document.processing_status == ProcessingStatus.FAILED:
                    raise ValueError("Gemini returned failed document")
                
                logger.info(f"{log_prefix} Gemini extraction successful: {type(document).__name__}")
                return document
            
            finally:
                # Cleanup: close image to free memory
                if image:
                    try:
                        image.close()
                    except Exception:
                        pass
        
        except Exception as e:
            logger.error(f"{log_prefix} Gemini extraction failed: {e}")
            # Return failed UnknownDocument
            return create_document(
                document_type="unknown",
                data={
                    "detected_document_type": doc_type,
                    "summary": f"Gemini extraction failed: {str(e)}",
                    "processing_status": ProcessingStatus.FAILED
                },
                request_id=request_id
            )
    
    def extract_from_text(
        self,
        text: str,
        doc_type: str = "unknown",
        request_id: Optional[str] = None
    ) -> ExtractedDocument:
        """
        Extract from OCR text using Gemini.
        
        NEW: Returns typed document (not dict)
        """
        log_prefix = f"[{request_id}]" if request_id else ""
        
        try:
            prompt = self.get_prompt(doc_type)
            full_prompt = f"{prompt}\n\nDocument text:\n{text}"
            
            logger.info(f"{log_prefix} Calling Gemini for text extraction: {doc_type}")
            response = self.model.generate_content(
                full_prompt,
                generation_config={
                    "temperature": 0.0,
                    "max_output_tokens": 1024,
                    "response_mime_type": "application/json",  # Force JSON output
                }
            )
            
            # Validate response
            if not response or not response.text or len(response.text.strip()) < 10:
                raise ValueError("Gemini returned empty or invalid response")
            
            # NEW: Parse into typed document
            document = _parse_model_json(response.text, doc_type, request_id)
            
            logger.info(f"{log_prefix} Gemini text extraction successful: {type(document).__name__}")
            return document
        
        except Exception as e:
            logger.error(f"{log_prefix} Gemini text extraction failed: {e}")
            # Return failed UnknownDocument
            return create_document(
                document_type="unknown",
                data={
                    "detected_document_type": doc_type,
                    "summary": f"Gemini text extraction failed: {str(e)}",
                    "processing_status": ProcessingStatus.FAILED
                },
                request_id=request_id
            )


# ============================================================
# GROQ PROVIDER (TEXT-ONLY FALLBACK)
# ============================================================

class GroqProvider(BaseAIProvider):
    def __init__(self):
        try:
            from groq import Groq
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise ValueError("GROQ_API_KEY not set in .env")
            self.client = Groq(api_key=api_key)
            logger.info("GroqProvider initialized")
        except ImportError:
            raise ImportError("groq not installed. Run: pip install groq")
    
    def extract_from_image(self, image_path: str, doc_type: str) -> dict:
        """Groq cannot process images — use OCR first then extract_from_text"""
        raise NotImplementedError("Groq is text-only. Run OCR first, then use extract_from_text()")
    
    def extract_from_text(
        self,
        text: str,
        doc_type: str = "unknown",
        request_id: Optional[str] = None
    ) -> ExtractedDocument:
        """
        Extract from OCR text using Groq.
        
        NEW: Returns typed document (not dict)
        """
        log_prefix = f"[{request_id}]" if request_id else ""
        
        try:
            prompt = self.get_prompt(doc_type)
            full_prompt = f"{prompt}\n\nDocument text:\n{text}"
            
            logger.info(f"{log_prefix} Calling Groq for text extraction: {doc_type}")
            response = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": full_prompt}],
                response_format={"type": "json_object"},
                temperature=0.0,
                max_tokens=1024,
            )
            
            # Validate response
            if not response or not response.choices or not response.choices[0].message.content:
                raise ValueError("Groq returned empty or invalid response")
            
            # NEW: Parse into typed document
            document = _parse_model_json(response.choices[0].message.content, doc_type, request_id)
            
            logger.info(f"{log_prefix} Groq text extraction successful: {type(document).__name__}")
            return document
        
        except Exception as e:
            logger.error(f"{log_prefix} Groq text extraction failed: {e}")
            # Return failed UnknownDocument
            return create_document(
                document_type="unknown",
                data={
                    "detected_document_type": doc_type,
                    "summary": f"Groq text extraction failed: {str(e)}",
                    "processing_status": ProcessingStatus.FAILED
                },
                request_id=request_id
            )


# ============================================================
# PROVIDER FACTORY — Call this everywhere
# ============================================================

def get_ai_provider() -> BaseAIProvider:
    provider = os.getenv("AI_PROVIDER", "gemini")
    
    if provider == "gemini":
        return GeminiProvider()
    elif provider == "groq":
        return GroqProvider()
    elif provider == "ollama":
        raise RuntimeError("Ollama disabled. Set AI_PROVIDER=gemini or groq.")
    else:
        logger.warning(f"Unknown provider '{provider}', defaulting to Gemini")
        return GeminiProvider()


# ============================================================
# MAIN EXTRACTION FUNCTION — Use this in document_service.py
# ============================================================

def extract_document(image_path: str, doc_type: str = "unknown") -> tuple[ExtractedDocument, dict]:
    """
    Main entry point for document extraction.
    
    NEW ARCHITECTURE:
    - Returns typed document (not dict)
    - Generates request_id for correlation
    - Returns metadata separately
    
    Tries Gemini Vision first (no OCR needed).
    Falls back to OCR + Groq if Gemini fails.
    
    Args:
        image_path: Path to image or PDF file
        doc_type: Document type (aadhaar/pan/invoice/ekyc/unknown)
    
    Returns:
        Tuple of (ExtractedDocument, metadata_dict)
    """
    import time
    
    # Generate request ID at entry (correlation backbone)
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    logger.info(f"[{request_id}] Starting extraction: {doc_type} from {image_path}")
    
    # Try Gemini Vision first
    try:
        provider = GeminiProvider()
        document = provider.extract_from_image(image_path, doc_type, request_id)
        
        # Check if extraction failed
        if document.processing_status == ProcessingStatus.FAILED:
            raise RuntimeError("Gemini extraction returned failed status")
        
        # Build metadata
        metadata = {
            "request_id": request_id,
            "provider": "gemini_vision",
            "model_used": "gemini-2.5-flash",
            "processing_time_ms": round((time.time() - start_time) * 1000, 2),
            "ocr_used": False,
            "fallback_used": False,
        }
        
        logger.info(f"[{request_id}] Extraction successful via Gemini Vision")
        return document, metadata
    
    except Exception as e:
        logger.warning(f"[{request_id}] Gemini Vision failed: {e}. Trying OCR + Groq fallback.")
    
    # Fallback: OCR + Groq
    try:
        from services.ocr_service import extract_text
        ocr_text, ocr_confidence = extract_text(image_path)
        logger.info(f"[{request_id}] OCR done: {len(ocr_text)} chars, confidence {ocr_confidence:.2f}")
        
        if ocr_text and len(ocr_text.strip()) > 20:
            provider = GroqProvider()
            document = provider.extract_from_text(ocr_text, doc_type, request_id)
            
            # Check if extraction failed
            if document.processing_status == ProcessingStatus.FAILED:
                raise RuntimeError("Groq extraction returned failed status")
            
            # Build metadata
            metadata = {
                "request_id": request_id,
                "provider": "groq",
                "model_used": "llama-3.1-8b-instant",
                "processing_time_ms": round((time.time() - start_time) * 1000, 2),
                "ocr_used": True,
                "ocr_confidence": ocr_confidence,
                "fallback_used": True,
            }
            
            logger.info(f"[{request_id}] Extraction successful via Groq fallback")
            return document, metadata
        else:
            raise RuntimeError("OCR text too short or empty")
    
    except Exception as e:
        logger.error(f"[{request_id}] Groq fallback also failed: {e}")
    
    # Everything failed - return failed UnknownDocument
    logger.error(f"[{request_id}] All extraction methods failed")
    
    failed_document = create_document(
        document_type="unknown",
        data={
            "detected_document_type": doc_type,
            "summary": "All extraction providers failed",
            "processing_status": ProcessingStatus.FAILED
        },
        request_id=request_id
    )
    
    metadata = {
        "request_id": request_id,
        "provider": "none",
        "model_used": None,
        "processing_time_ms": round((time.time() - start_time) * 1000, 2),
        "ocr_used": False,
        "fallback_used": True,
    }
    
    return failed_document, metadata
