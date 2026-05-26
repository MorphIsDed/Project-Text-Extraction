from pydantic import BaseModel
from typing import Optional, List, Any, Union


class ExtractedDocument(BaseModel):
    document_type: str
    # Core fields (existing)
    name: Optional[str] = None
    date_of_birth: Optional[str] = None
    id_number: Optional[str] = None
    address: Optional[str] = None
    issue_date: Optional[str] = None
    expiry_date: Optional[str] = None
    invoice_number: Optional[str] = None
    total_amount: Optional[str] = None
    summary: Optional[str] = None
    raw_text: Optional[str] = None
    # DEPRECATED: Confidence scores removed as arbitrary/meaningless
    # Field kept for backward compatibility - always None
    confidence: Optional[Union[float, dict]] = None
    
    # NEW - Gemini-specific fields
    gender: Optional[str] = None
    aadhaar_number_masked: Optional[str] = None
    pin_code: Optional[str] = None
    father_name: Optional[str] = None
    pan_number: Optional[str] = None
    side_detected: Optional[str] = None
    vendor_name: Optional[str] = None
    vendor_gstin: Optional[str] = None
    buyer_name: Optional[str] = None
    buyer_gstin: Optional[str] = None
    subtotal: Optional[float] = None
    gst_amount: Optional[float] = None
    invoice_date: Optional[str] = None
    currency: Optional[str] = None
    line_items: Optional[List[dict]] = None
    mobile_number: Optional[str] = None
    email: Optional[str] = None
    account_type: Optional[str] = None
    bank_name: Optional[str] = None
    applicant_name: Optional[str] = None
    licence_number: Optional[str] = None
    date_of_expiry: Optional[str] = None
    date_of_issue: Optional[str] = None
    vehicle_classes: Optional[str] = None
    issuing_rto: Optional[str] = None
    surname: Optional[str] = None
    given_name: Optional[str] = None
    passport_number: Optional[str] = None
    place_of_birth: Optional[str] = None
    nationality: Optional[str] = None
    mrz_line1: Optional[str] = None
    mrz_line2: Optional[str] = None
    raw_fields: Optional[dict] = None
    # Voter ID specific fields
    voter_id_number: Optional[str] = None
    polling_station: Optional[str] = None
    assembly_constituency: Optional[str] = None
    needs_review: Optional[bool] = None
    review_flags: Optional[dict] = None
    review_notes: Optional[List[str]] = None
    
    # Accept any extra fields Gemini returns without crashing
    model_config = {"extra": "allow"}


class DocumentResponse(BaseModel):
    success: bool
    filename: str
    extracted_data: Optional[ExtractedDocument] = None  # Optional for manual review
    message: Optional[str] = None
    json_output_file: Optional[str] = None
    download_url: Optional[str] = None
    file_hash: Optional[str] = None
