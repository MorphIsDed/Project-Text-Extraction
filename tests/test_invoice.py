"""
Test script for Invoice document extraction
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from services.document_service import process_document


async def test_invoice():
    """Test Invoice document processing"""
    
    print("=" * 80)
    print("INVOICE DOCUMENT EXTRACTION TEST")
    print("=" * 80)
    
    # You need to place an invoice image in uploads/ folder
    test_file = "uploads/invoice_sample.jpg"  # Change this to your actual file
    
    if not Path(test_file).exists():
        print(f"\n❌ ERROR: Test file not found: {test_file}")
        print("\nPlease:")
        print("1. Place an invoice image in the uploads/ folder")
        print("2. Update the 'test_file' variable in this script")
        print("3. Run this script again")
        return
    
    print(f"\n📄 Processing: {test_file}")
    print("-" * 80)
    
    try:
        # Process document
        result = await process_document(test_file)
        
        # Check if result is dict or object
        if isinstance(result, dict):
            data = result
        else:
            data = result.model_dump() if hasattr(result, 'model_dump') else result.__dict__
        
        # Display results
        print("\n✅ EXTRACTION SUCCESSFUL")
        print("=" * 80)
        
        print(f"\n📋 Document Type: {data.get('document_type', 'unknown')}")
        print(f"🔍 Processing Status: {data.get('processing_status', 'unknown')}")
        
        # Display extracted fields
        print("\n📊 EXTRACTED FIELDS:")
        print("-" * 80)
        
        # Vendor info
        print("\n  VENDOR INFORMATION:")
        vendor_name = data.get('vendor_name')
        vendor_gstin = data.get('vendor_gstin')
        if vendor_name:
            print(f"    Name  : {vendor_name}")
        if vendor_gstin:
            print(f"    GSTIN : {vendor_gstin}")
        
        # Buyer info
        print("\n  BUYER INFORMATION:")
        buyer_name = data.get('buyer_name')
        buyer_gstin = data.get('buyer_gstin')
        if buyer_name:
            print(f"    Name  : {buyer_name}")
        if buyer_gstin:
            print(f"    GSTIN : {buyer_gstin}")
        
        # Invoice details
        print("\n  INVOICE DETAILS:")
        invoice_number = data.get('invoice_number')
        invoice_date = data.get('invoice_date')
        if invoice_number:
            print(f"    Number: {invoice_number}")
        if invoice_date:
            print(f"    Date  : {invoice_date}")
        
        # Amounts
        print("\n  AMOUNTS:")
        subtotal = data.get('subtotal')
        gst_amount = data.get('gst_amount')
        total_amount = data.get('total_amount')
        currency = data.get('currency', 'INR')
        
        if subtotal:
            print(f"    Subtotal   : {currency} {subtotal:,.2f}")
        if gst_amount:
            print(f"    GST Amount : {currency} {gst_amount:,.2f}")
        if total_amount:
            print(f"    Total      : {currency} {total_amount:,.2f}")
        
        # Line items
        line_items = data.get('line_items', [])
        if line_items:
            print("\n  LINE ITEMS:")
            for i, item in enumerate(line_items, 1):
                if isinstance(item, dict):
                    item_name = item.get('item_name', 'Unknown')
                    quantity = item.get('quantity', 0)
                    unit_price = item.get('unit_price', 0)
                    total_price = item.get('total_price', 0)
                    print(f"    {i}. {item_name}")
                    print(f"       Qty: {quantity} × {currency} {unit_price:,.2f} = {currency} {total_price:,.2f}")
        
        # Display review flags if any
        review_flags = data.get('review_flags', [])
        if review_flags:
            print("\n⚠️  REVIEW FLAGS:")
            print("-" * 80)
            for flag in review_flags:
                if isinstance(flag, dict):
                    print(f"  • {flag.get('field')}: {flag.get('reason')} (Severity: {flag.get('severity')})")
                else:
                    print(f"  • {flag}")
        else:
            print("\n✅ No review flags - extraction looks good!")
        
        # Display confidence scores if available
        confidence = data.get('confidence')
        if confidence:
            print("\n📈 CONFIDENCE SCORES:")
            print("-" * 80)
            if isinstance(confidence, dict):
                for field, score in confidence.items():
                    if isinstance(score, (int, float)):
                        print(f"  {field:20s}: {score:.2%}")
            elif isinstance(confidence, (int, float)):
                print(f"  Overall: {confidence:.2%}")
        
        print("\n" + "=" * 80)
        print("✅ TEST COMPLETED SUCCESSFULLY")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_invoice())
