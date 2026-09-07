from ingestion.pdf_extractor import extract_pdf
from ingestion.chunker import chunk_page


PDF_PATH = "C:/Users/saman/Downloads/02-delhivery-annual-report-fy24-excerpt.pdf"


pages = extract_pdf(PDF_PATH)

for page in pages:
    chunks = chunk_page(page)

    print("\n" + "=" * 80)
    print(
        f"PHYSICAL PAGE: {page.physical_page_number} | "
        f"LOGICAL PAGE: {page.logical_page_index} | "
        f"REGION: {page.region}"
    )

    print(f"CHUNKS: {len(chunks)}")

    for chunk in chunks:
        print("\n" + "-" * 80)
        print(f"CHUNK {chunk.chunk_index}")
        print(f"TYPE: {chunk.chunk_type}")
        print(f"CHARACTERS: {len(chunk.content)}")
        print("-" * 80)
        print(chunk.content)