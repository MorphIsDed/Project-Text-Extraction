"""
Helper script to split multi-page PDF into separate files
"""
import sys
from pathlib import Path

try:
    import pypdfium2 as pdfium
    from PIL import Image
except ImportError:
    print("Installing required packages...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pypdfium2", "pillow"])
    import pypdfium2 as pdfium
    from PIL import Image


def split_pdf_to_images(pdf_path: str, output_dir: str = "uploads"):
    """Split PDF into separate image files (one per page)"""
    
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    if not pdf_path.exists():
        print(f"❌ Error: File not found - {pdf_path}")
        return
    
    print(f"📄 Processing: {pdf_path.name}")
    print(f"📁 Output directory: {output_dir}")
    print("-" * 60)
    
    try:
        # Open PDF
        pdf = pdfium.PdfDocument(pdf_path)
        total_pages = len(pdf)
        
        print(f"📊 Total pages: {total_pages}")
        print()
        
        # Process each page
        for page_num in range(total_pages):
            page = pdf[page_num]
            
            # Render page to image (2x scale for better quality)
            bitmap = page.render(scale=2)
            pil_image = bitmap.to_pil()
            
            # Save as JPG
            base_name = pdf_path.stem
            output_file = output_dir / f"{base_name}_page_{page_num + 1}.jpg"
            pil_image.save(output_file, "JPEG", quality=95)
            
            print(f"✅ Page {page_num + 1}/{total_pages} saved: {output_file.name}")
        
        print()
        print("=" * 60)
        print(f"✅ SUCCESS: Split {total_pages} pages")
        print("=" * 60)
        print()
        print("📝 Next steps:")
        print("1. Check the uploads/ folder for generated images")
        print("2. Rename files if needed:")
        for i in range(1, total_pages + 1):
            print(f"   - {base_name}_page_{i}.jpg")
        print("3. Test each file separately")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python split_pdf.py <pdf_file>")
        print()
        print("Example:")
        print("  python split_pdf.py uploads/Filled-KYC-Forms-Package.pdf")
        print()
        print("This will create:")
        print("  uploads/Filled-KYC-Forms-Package_page_1.jpg")
        print("  uploads/Filled-KYC-Forms-Package_page_2.jpg")
        print("  uploads/Filled-KYC-Forms-Package_page_3.jpg")
        print("  uploads/Filled-KYC-Forms-Package_page_4.jpg")
    else:
        pdf_file = sys.argv[1]
        split_pdf_to_images(pdf_file)
