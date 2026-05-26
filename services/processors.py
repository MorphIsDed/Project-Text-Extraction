"""
Object-Oriented Document Processors implementing the Strategy and Factory Patterns.

This module replaces large switch-case conditionals with clean polymorphism.
Developers can add a new document type by defining a new processor strategy subclass.
"""

from abc import ABC, abstractmethod
import re
import logging
from typing import Dict, Any, Type, Optional
from models.schemas import ExtractedDocument
from services.normalizer import normalize_nested_object, normalize_list, normalize_string, normalize_number

logger = logging.getLogger(__name__)


class BaseDocumentProcessor(ABC):
    """
    Abstract Base Class representing a document processing strategy.
    Implements the Template Method Pattern.
    """
    
    def normalize(self, data: dict) -> dict:
        """
        Template method for normalization. Performs common baseline field cleaning
        before invoking custom subclass strategies.
        """
        if not data or not isinstance(data, dict):
            return {}

        normalized = {}
        for key, value in data.items():
            if key.startswith('_'):
                normalized[key] = value
                continue
            
            value = normalize_nested_object(value)
            value = normalize_list(value)
            
            # Numeric field categorization
            if key in ['subtotal', 'gst_amount', 'total_amount', 'quantity', 'unit_price', 'total_price']:
                value = normalize_number(value)
            else:
                value = normalize_string(value)
            
            if value is not None:
                normalized[key] = value
                
        # Invoke polymorphism hooks in strategy subclasses
        return self._normalize_specific(normalized)

    def post_process(self, doc: ExtractedDocument, ocr_text: str, request_id: str) -> ExtractedDocument:
        """
        Template method for post-processing.
        Runs baseline generic cleanup, then invokes subclass strategies.
        """
        # Baseline generic validations/cleanups
        if doc.needs_review is None:
            doc.needs_review = False
        if doc.review_flags is None:
            doc.review_flags = []
        if doc.review_notes is None:
            doc.review_notes = []
            
        return self._post_process_specific(doc, ocr_text, request_id)

    @abstractmethod
    def _normalize_specific(self, data: dict) -> dict:
        """Hook for document-specific normalization"""
        pass

    @abstractmethod
    def _post_process_specific(self, doc: ExtractedDocument, ocr_text: str, request_id: str) -> ExtractedDocument:
        """Hook for document-specific post-processing"""
        pass


# ============================================================
# CONCRETE PROCESSOR STRATEGIES
# ============================================================

class AadhaarProcessor(BaseDocumentProcessor):
    """Processor strategy for Aadhaar Card documents."""
    
    def _normalize_specific(self, data: dict) -> dict:
        # Masked Aadhaar layout normalizations
        if 'aadhaar_number_masked' in data:
            masked = data['aadhaar_number_masked']
            if masked:
                masked = re.sub(r'\s+', ' ', str(masked).strip())
                data['aadhaar_number_masked'] = masked
        
        # Gender mapping normalizer
        if 'gender' in data and data['gender']:
            gender = str(data['gender']).strip().lower()
            if gender in ['m', 'male', 'पुरुष']:
                data['gender'] = 'Male'
            elif gender in ['f', 'female', 'महिला']:
                data['gender'] = 'Female'
        return data

    def _post_process_specific(self, doc: ExtractedDocument, ocr_text: str, request_id: str) -> ExtractedDocument:
        # Import post-processing modules dynamically to prevent circular imports
        from services.post_processing import (
            validate_name_ocr, validate_document_numbers, validate_dates,
            check_needs_review_logical, add_review_flag
        )
        from models.schemas import ReviewSeverity
        
        doc = validate_name_ocr(doc, ocr_text, request_id)
        doc = validate_document_numbers(doc, ocr_text, request_id)
        doc = validate_dates(doc, request_id)
        
        # Aadhaar-specific validation: Masked check
        number = getattr(doc, 'aadhaar_number_masked', None)
        if number:
            cleaned_number = str(number).replace(" ", "")
            if len(cleaned_number) == 12 and cleaned_number.isdigit():
                # Plain numbers extracted, flag for masking
                doc.aadhaar_number_masked = f"XXXX XXXX {cleaned_number[-4:]}"
                add_review_flag(
                    doc,
                    field="aadhaar_number_masked",
                    severity=ReviewSeverity.MEDIUM,
                    reason="Aadhaar number was extracted unmasked. Automatic masking applied.",
                    request_id=request_id
                )
        
        return check_needs_review_logical(doc, request_id)


class PANProcessor(BaseDocumentProcessor):
    """Processor strategy for PAN Card documents."""
    
    def _normalize_specific(self, data: dict) -> dict:
        # Force uppercase PAN and names
        if 'pan_number' in data and data['pan_number']:
            data['pan_number'] = str(data['pan_number']).upper().strip()
        if 'name' in data and data['name']:
            data['name'] = str(data['name']).upper().strip()
        if 'father_name' in data and data['father_name']:
            data['father_name'] = str(data['father_name']).upper().strip()
        return data

    def _post_process_specific(self, doc: ExtractedDocument, ocr_text: str, request_id: str) -> ExtractedDocument:
        from services.post_processing import (
            validate_name_ocr, validate_document_numbers, validate_dates,
            check_needs_review_logical
        )
        doc = validate_name_ocr(doc, ocr_text, request_id)
        doc = validate_document_numbers(doc, ocr_text, request_id)
        doc = validate_dates(doc, request_id)
        return check_needs_review_logical(doc, request_id)


class VoterIDProcessor(BaseDocumentProcessor):
    """Processor strategy for Voter ID Card documents."""
    
    def _normalize_specific(self, data: dict) -> dict:
        if 'voter_id_number' in data and data['voter_id_number']:
            data['voter_id_number'] = str(data['voter_id_number']).upper().strip()
        
        if 'gender' in data and data['gender']:
            gender = str(data['gender']).strip().lower()
            if gender in ['m', 'male']:
                data['gender'] = 'Male'
            elif gender in ['f', 'female']:
                data['gender'] = 'Female'
        return data

    def _post_process_specific(self, doc: ExtractedDocument, ocr_text: str, request_id: str) -> ExtractedDocument:
        from services.post_processing import (
            validate_name_ocr, validate_document_numbers, validate_dates,
            check_needs_review_logical
        )
        doc = validate_name_ocr(doc, ocr_text, request_id)
        doc = validate_document_numbers(doc, ocr_text, request_id)
        doc = validate_dates(doc, request_id)
        return check_needs_review_logical(doc, request_id)


class DrivingLicenseProcessor(BaseDocumentProcessor):
    """Processor strategy for Driving License documents."""
    
    def _normalize_specific(self, data: dict) -> dict:
        if 'licence_number' in data and data['licence_number']:
            data['licence_number'] = str(data['licence_number']).upper().strip()
            
        if 'vehicle_classes' in data:
            classes = data['vehicle_classes']
            if isinstance(classes, str):
                classes = re.split(r'[,\s]+', classes)
                classes = [c.strip().upper() for c in classes if c.strip()]
                data['vehicle_classes'] = classes
            elif not isinstance(classes, list):
                data['vehicle_classes'] = []
        return data

    def _post_process_specific(self, doc: ExtractedDocument, ocr_text: str, request_id: str) -> ExtractedDocument:
        from services.post_processing import (
            validate_name_ocr, validate_document_numbers, validate_dates,
            check_needs_review_logical
        )
        doc = validate_name_ocr(doc, ocr_text, request_id)
        doc = validate_document_numbers(doc, ocr_text, request_id)
        doc = validate_dates(doc, request_id)
        return check_needs_review_logical(doc, request_id)


class PassportProcessor(BaseDocumentProcessor):
    """Processor strategy for Passport documents."""
    
    def _normalize_specific(self, data: dict) -> dict:
        if 'passport_number' in data and data['passport_number']:
            data['passport_number'] = str(data['passport_number']).upper().strip()
        if 'surname' in data and data['surname']:
            data['surname'] = str(data['surname']).upper().strip()
        if 'given_name' in data and data['given_name']:
            data['given_name'] = str(data['given_name']).upper().strip()
        if 'mrz_line1' in data and data['mrz_line1']:
            data['mrz_line1'] = str(data['mrz_line1']).replace(' ', '').upper()
        if 'mrz_line2' in data and data['mrz_line2']:
            data['mrz_line2'] = str(data['mrz_line2']).replace(' ', '').upper()
        return data

    def _post_process_specific(self, doc: ExtractedDocument, ocr_text: str, request_id: str) -> ExtractedDocument:
        from services.post_processing import (
            validate_name_ocr, validate_document_numbers, validate_dates,
            check_needs_review_logical
        )
        # Passport name consists of given_name + surname
        doc = validate_name_ocr(doc, ocr_text, request_id)
        doc = validate_document_numbers(doc, ocr_text, request_id)
        doc = validate_dates(doc, request_id)
        return check_needs_review_logical(doc, request_id)


class InvoiceProcessor(BaseDocumentProcessor):
    """Processor strategy for Invoice billing documents."""
    
    def _normalize_specific(self, data: dict) -> dict:
        if 'vendor_gstin' in data and data['vendor_gstin']:
            data['vendor_gstin'] = str(data['vendor_gstin']).upper().strip()
        if 'buyer_gstin' in data and data['buyer_gstin']:
            data['buyer_gstin'] = str(data['buyer_gstin']).upper().strip()
        if 'currency' not in data or not data['currency']:
            data['currency'] = 'INR'
            
        if 'line_items' in data:
            line_items = data['line_items']
            if isinstance(line_items, str):
                try:
                    import json
                    line_items = json.loads(line_items)
                except Exception as e:
                    logger.warning(f"Could not parse line_items string: {e}")
                    line_items = []
            
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

    def _post_process_specific(self, doc: ExtractedDocument, ocr_text: str, request_id: str) -> ExtractedDocument:
        from services.post_processing import (
            validate_document_numbers, validate_dates, check_needs_review_logical, add_review_flag
        )
        from models.schemas import ReviewSeverity
        
        doc = validate_document_numbers(doc, ocr_text, request_id)
        doc = validate_dates(doc, request_id)
        
        # Invoice-specific logic validation: Check subtotal + GST = Total Amount
        subtotal = getattr(doc, 'subtotal', None)
        gst = getattr(doc, 'gst_amount', None)
        total = getattr(doc, 'total_amount', None)
        
        if subtotal is not None and gst is not None and total is not None:
            # Round calculations to 2 decimal points
            expected_total = round(float(subtotal) + float(gst), 2)
            actual_total = round(float(total), 2)
            
            if abs(expected_total - actual_total) > 0.05:
                add_review_flag(
                    doc,
                    field="total_amount",
                    severity=ReviewSeverity.HIGH,
                    reason=f"Calculated sum (Subtotal: {subtotal} + GST: {gst} = {expected_total}) does not match Total Amount: {total}",
                    request_id=request_id
                )
                
        return check_needs_review_logical(doc, request_id)


class EKYCProcessor(BaseDocumentProcessor):
    """Processor strategy for eKYC Summary forms."""
    
    def _normalize_specific(self, data: dict) -> dict:
        return data

    def _post_process_specific(self, doc: ExtractedDocument, ocr_text: str, request_id: str) -> ExtractedDocument:
        from services.post_processing import (
            validate_name_ocr, validate_dates, check_needs_review_logical
        )
        doc = validate_name_ocr(doc, ocr_text, request_id)
        doc = validate_dates(doc, request_id)
        return check_needs_review_logical(doc, request_id)


class UnknownProcessor(BaseDocumentProcessor):
    """Processor strategy fallback for uncategorized generic text files."""
    
    def _normalize_specific(self, data: dict) -> dict:
        return data

    def _post_process_specific(self, doc: ExtractedDocument, ocr_text: str, request_id: str) -> ExtractedDocument:
        from services.post_processing import check_needs_review_logical
        return check_needs_review_logical(doc, request_id)


# ============================================================
# CENTRALIZED PROCESSOR FACTORY (O(1) RESOLVER)
# ============================================================

class DocumentProcessorFactory:
    """
    Central Factory Registry linking document types to their processing strategies.
    Provides O(1) resolution via hashing.
    """
    _processors: Dict[str, BaseDocumentProcessor] = {
        "aadhaar": AadhaarProcessor(),
        "pan": PANProcessor(),
        "voter_id": VoterIDProcessor(),
        "driving_licence": DrivingLicenseProcessor(),
        "passport": PassportProcessor(),
        "invoice": InvoiceProcessor(),
        "ekyc": EKYCProcessor(),
        "unknown": UnknownProcessor(),
    }
    
    @classmethod
    def get_processor(cls, doc_type: str) -> BaseDocumentProcessor:
        """
        Retrieves the strategy processor for a document type.
        Falls back safely to the UnknownProcessor if type is not registered.
        """
        normalized_type = str(doc_type).strip().lower()
        processor = cls._processors.get(normalized_type)
        if not processor:
            logger.warning(f"No processor registered for document type '{doc_type}', falling back to UnknownProcessor")
            return cls._processors["unknown"]
        return processor

    @classmethod
    def register_processor(cls, doc_type: str, processor: BaseDocumentProcessor) -> None:
        """Enables runtime extension by registering new strategy processors dynamically."""
        cls._processors[doc_type.lower()] = processor
        logger.info(f"Registered custom document processor strategy for '{doc_type}'")
