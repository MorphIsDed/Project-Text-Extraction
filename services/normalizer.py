"""
Document Data Normalizer

Purpose: Clean and normalize LLM/OCR output BEFORE schema validation.

IMPORTANT RULES:
1. CLEAN data, do NOT validate truth
2. Never silently discard fields
3. Degrade transparently, not invisibly
4. Keep it simple - avoid over-engineering

Pipeline:
    Raw Gemini/OCR Output
        ↓
    normalize_document_data()
        ↓
    Clean Predictable Dict
        ↓
    create_document() (schema validation)
"""

import re
import unicodedata
import logging
from typing import Any, Optional, Dict, List

logger = logging.getLogger(__name__)


# ============================================================
# EMPTY VALUE PATTERNS
# ============================================================

EMPTY_PATTERNS = {
    "",
    "   ",
    "N/A",
    "n/a",
    "NA",
    "null",
    "NULL",
    "None",
    "NONE",
    "-",
    "--",
    "___",
}


# ============================================================
# STRING NORMALIZATION
# ============================================================

def normalize_string(value: Any) -> Optional[str]:
    """
    Normalize string values.
    
    Handles:
    - Empty strings → None
    - Whitespace trimming
    - Unicode normalization
    - Empty patterns (N/A, null, etc.)
    
    Args:
        value: Any value to normalize
    
    Returns:
        Cleaned string or None
    """
    if value is None:
        return None
    
    # Convert to string
    if not isinstance(value, str):
        value = str(value)
    
    # Trim whitespace
    value = value.strip()
    
    # Check empty patterns
    if value in EMPTY_PATTERNS:
        return None
    
    # Unicode normalization (NFC form)
    # Fixes: weird OCR unicode, invisible characters, smart quotes
    try:
        value = unicodedata.normalize('NFC', value)
    except Exception as e:
        logger.warning(f"Unicode normalization failed: {e}")
    
    # Remove zero-width spaces and invisible characters
    value = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', value)
    
    # Normalize whitespace (multiple spaces → single space)
    value = re.sub(r'\s+', ' ', value)
    
    # Final trim
    value = value.strip()
    
    # Return None if empty after cleaning
    return value if value else None


# ============================================================
# LIST NORMALIZATION
# ============================================================

def normalize_list(value: Any) -> Any:
    """
    Normalize list values.
    
    Handles:
    - Single-item list → extract item
    - Empty list → None
    - List of strings → join with space
    
    Args:
        value: Any value (may be list)
    
    Returns:
        Normalized value (string, list, or None)
    """
    if not isinstance(value, list):
        return value
    
    # Empty list → None
    if not value:
        return None
    
    # Single item list → extract item
    if len(value) == 1:
        return value[0]
    
    # Multiple items - check if all strings
    if all(isinstance(item, str) for item in value):
        # Join with space (common for names, addresses)
        joined = ' '.join(item.strip() for item in value if item.strip())
        return joined if joined else None
    
    # Keep as list if mixed types or complex
    return value


# ============================================================
# NESTED OBJECT FLATTENING
# ============================================================

def normalize_nested_object(value: Any) -> Any:
    """
    Flatten simple nested objects.
    
    Handles:
    - {"value": "X"} → "X"
    - {"first": "John", "last": "Doe"} → "John Doe"
    
    IMPORTANT: Only flattens simple cases, preserves complex structures.
    
    Args:
        value: Any value (may be dict)
    
    Returns:
        Flattened value or original dict
    """
    if not isinstance(value, dict):
        return value
    
    # Empty dict → None
    if not value:
        return None
    
    # Single key "value" → extract value
    if len(value) == 1 and "value" in value:
        return value["value"]
    
    # Name-like structure → join
    if all(k in ["first", "last", "middle"] for k in value.keys()):
        parts = []
        if "first" in value and value["first"]:
            parts.append(str(value["first"]))
        if "middle" in value and value["middle"]:
            parts.append(str(value["middle"]))
        if "last" in value and value["last"]:
            parts.append(str(value["last"]))
        return ' '.join(parts) if parts else None
    
    # Keep complex structures as-is
    return value


# ============================================================
# NUMERIC NORMALIZATION
# ============================================================

def normalize_number(value: Any) -> Optional[float]:
    """
    Normalize numeric values.
    
    Handles:
    - "1,234.00" → 1234.0
    - "₹1234" → 1234.0
    - String numbers → float
    
    Args:
        value: Any value that should be numeric
    
    Returns:
        Float or None
    """
    if value is None:
        return None
    
    # Already a number
    if isinstance(value, (int, float)):
        return float(value)
    
    # Convert to string and clean
    if isinstance(value, str):
        value = value.strip()
        
        # Remove currency symbols
        value = re.sub(r'[₹$€£¥]', '', value)
        
        # Remove commas (thousand separators)
        value = value.replace(',', '')
        
        # Remove spaces
        value = value.replace(' ', '')
        
        # Try to convert
        try:
            return float(value)
        except ValueError:
            logger.warning(f"Could not convert to number: {value}")
            return None
    
    return None


# ============================================================
# DOCUMENT-TYPE-AWARE NORMALIZATION
# ============================================================

def normalize_document_data(document_type: str, data: dict) -> dict:
    """
    Normalize document data based on document type.
    
    IMPORTANT: This is the main entry point for normalization.
    
    Args:
        document_type: Type of document (aadhaar, pan, etc.)
        data: Raw extracted data dict
    
    Returns:
        Normalized data dict (ready for schema validation)
    """
    if not data or not isinstance(data, dict):
        return {}
    
    # Create normalized copy (don't modify original)
    normalized = {}
    
    # Normalize each field
    for key, value in data.items():
        # Skip internal fields
        if key.startswith('_'):
            normalized[key] = value
            continue
        
        # Apply normalization pipeline
        value = normalize_nested_object(value)
        value = normalize_list(value)
        
        # Type-specific normalization
        if key in ['subtotal', 'gst_amount', 'total_amount', 'quantity', 'unit_price', 'total_price']:
            # Numeric fields
            value = normalize_number(value)
        else:
            # String fields
            value = normalize_string(value)
        
        # Only include non-None values
        if value is not None:
            normalized[key] = value
    
    # Document-type-specific normalization
    if document_type == "aadhaar":
        normalized = _normalize_aadhaar_specific(normalized)
    elif document_type == "pan":
        normalized = _normalize_pan_specific(normalized)
    elif document_type == "invoice":
        normalized = _normalize_invoice_specific(normalized)
    elif document_type == "passport":
        normalized = _normalize_passport_specific(normalized)
    elif document_type == "driving_licence":
        normalized = _normalize_driving_licence_specific(normalized)
    elif document_type == "voter_id":
        normalized = _normalize_voter_id_specific(normalized)
    
    return normalized


# ============================================================
# DOCUMENT-SPECIFIC NORMALIZERS
# ============================================================

def _normalize_aadhaar_specific(data: dict) -> dict:
    """Aadhaar-specific normalization"""
    # Ensure aadhaar_number_masked format
    if 'aadhaar_number_masked' in data:
        masked = data['aadhaar_number_masked']
        if masked:
            # Remove extra spaces, normalize format
            masked = re.sub(r'\s+', ' ', str(masked).strip())
            data['aadhaar_number_masked'] = masked
    
    # Normalize gender
    if 'gender' in data and data['gender']:
        gender = str(data['gender']).strip().lower()
        if gender in ['m', 'male', 'पुरुष']:
            data['gender'] = 'Male'
        elif gender in ['f', 'female', 'महिला']:
            data['gender'] = 'Female'
    
    return data


def _normalize_pan_specific(data: dict) -> dict:
    """PAN-specific normalization"""
    # Uppercase PAN number
    if 'pan_number' in data and data['pan_number']:
        data['pan_number'] = str(data['pan_number']).upper().strip()
    
    # Uppercase name (PAN cards are usually uppercase)
    if 'name' in data and data['name']:
        data['name'] = str(data['name']).upper().strip()
    
    if 'father_name' in data and data['father_name']:
        data['father_name'] = str(data['father_name']).upper().strip()
    
    return data


def _normalize_invoice_specific(data: dict) -> dict:
    """Invoice-specific normalization"""
    # Uppercase GSTIN
    if 'vendor_gstin' in data and data['vendor_gstin']:
        data['vendor_gstin'] = str(data['vendor_gstin']).upper().strip()
    
    if 'buyer_gstin' in data and data['buyer_gstin']:
        data['buyer_gstin'] = str(data['buyer_gstin']).upper().strip()
    
    # Ensure currency is INR
    if 'currency' not in data or not data['currency']:
        data['currency'] = 'INR'
    
    # Normalize line items if present
    if 'line_items' in data:
        line_items = data['line_items']
        
        # Handle string representation of list (from Groq)
        if isinstance(line_items, str):
            try:
                import json
                line_items = json.loads(line_items)
            except Exception as e:
                logger.warning(f"Could not parse line_items string: {e}")
                line_items = []
        
        # Normalize list of items
        if isinstance(line_items, list):
            normalized_items = []
            for item in line_items:
                if isinstance(item, dict):
                    normalized_item = {}
                    for k, v in item.items():
                        if k in ['quantity', 'unit_price', 'total_price']:
                            normalized_item[k] = normalize_number(v)
                        else:
                            normalized_item[k] = normalize_string(v)
                    normalized_items.append(normalized_item)
            data['line_items'] = normalized_items
        else:
            data['line_items'] = []
    
    return data


def _normalize_passport_specific(data: dict) -> dict:
    """Passport-specific normalization"""
    # Uppercase passport number
    if 'passport_number' in data and data['passport_number']:
        data['passport_number'] = str(data['passport_number']).upper().strip()
    
    # Uppercase surname/given_name (passports are usually uppercase)
    if 'surname' in data and data['surname']:
        data['surname'] = str(data['surname']).upper().strip()
    
    if 'given_name' in data and data['given_name']:
        data['given_name'] = str(data['given_name']).upper().strip()
    
    # Clean MRZ lines (remove extra spaces)
    if 'mrz_line1' in data and data['mrz_line1']:
        data['mrz_line1'] = str(data['mrz_line1']).replace(' ', '').upper()
    
    if 'mrz_line2' in data and data['mrz_line2']:
        data['mrz_line2'] = str(data['mrz_line2']).replace(' ', '').upper()
    
    return data


def _normalize_driving_licence_specific(data: dict) -> dict:
    """Driving License-specific normalization"""
    # Uppercase license number
    if 'licence_number' in data and data['licence_number']:
        data['licence_number'] = str(data['licence_number']).upper().strip()
    
    # Normalize vehicle_classes to list
    if 'vehicle_classes' in data:
        classes = data['vehicle_classes']
        if isinstance(classes, str):
            # Split by comma or space
            classes = re.split(r'[,\s]+', classes)
            classes = [c.strip().upper() for c in classes if c.strip()]
            data['vehicle_classes'] = classes
        elif not isinstance(classes, list):
            data['vehicle_classes'] = []
    
    return data


def _normalize_voter_id_specific(data: dict) -> dict:
    """Voter ID-specific normalization"""
    # Uppercase voter ID number
    if 'voter_id_number' in data and data['voter_id_number']:
        data['voter_id_number'] = str(data['voter_id_number']).upper().strip()
    
    # Normalize gender
    if 'gender' in data and data['gender']:
        gender = str(data['gender']).strip().lower()
        if gender in ['m', 'male']:
            data['gender'] = 'Male'
        elif gender in ['f', 'female']:
            data['gender'] = 'Female'
    
    return data


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def is_empty_value(value: Any) -> bool:
    """
    Check if value is considered empty.
    
    Args:
        value: Any value to check
    
    Returns:
        True if empty, False otherwise
    """
    if value is None:
        return True
    
    if isinstance(value, str):
        return value.strip() in EMPTY_PATTERNS
    
    if isinstance(value, (list, dict)):
        return len(value) == 0
    
    return False


def clean_dict(data: dict) -> dict:
    """
    Remove all empty values from dict.
    
    Args:
        data: Dict to clean
    
    Returns:
        Dict with no empty values
    """
    return {k: v for k, v in data.items() if not is_empty_value(v)}
