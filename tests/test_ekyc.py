"""
Test script for eKYC document extraction
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from services.document_service import process_document


async def test_ekyc():
    """Test eKYC document processing"""
    
    print("=" * 80)
    print("eKYC DOCUMENT EXTRACTION TEST")
    print("=" * 80)
    
    # You need to place an eKYC document image in uploads/ folder
    test_file = "uploads/ekyc_sample.jpg"  # Change this to your actual file
    
    if not Path(test_file).exists():
        print(f"\n❌ ERROR: Test file not found: {test_file}")
        print("\nPlease:")
        print("1. Place an eKYC document image in the uploads/ folder")
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
        
        fields_to_display = [
            ('applicant_name', 'Applicant Name'),
            ('date_of_birth', 'Date of Birth'),
            ('gender', 'Gender'),
            ('mobile_number', 'Mobile Number'),
            ('email', 'Email'),
            ('address', 'Address'),
            ('account_type', 'Account Type'),
            ('bank_name', 'Bank Name'),
        ]
        
        for field_key, field_label in fields_to_display:
            value = data.get(field_key)
            if value:
                print(f"  {field_label:20s}: {value}")
            else:
                print(f"  {field_label:20s}: [Not found]")
        
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
    asyncio.run(test_ekyc())
