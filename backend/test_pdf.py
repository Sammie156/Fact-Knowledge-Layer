import sys

from ingestion.pdf_extractor import extract_pdf


pdf_path = sys.argv[1]

pages = extract_pdf(pdf_path)

print(f"Logical pages extracted: {len(pages)}")

for page in pages:
    print("\n" + "=" * 80)
    print(
        f"PHYSICAL PAGE: {page['physical_page_number']} | "
        f"REGION: {page['region']}"
    )
    print("=" * 80)

    print(page["content"][:2000])