from ingestion.pdf_extractor import extract_pdf


PDF_PATH = "C:/Users/saman/Downloads/02-delhivery-annual-report-fy24-excerpt.pdf"


pages = extract_pdf(PDF_PATH)

print(f"Logical pages extracted: {len(pages)}")

for page in pages:
    print("\n" + "=" * 80)

    print(
        f"PHYSICAL PAGE: {page.physical_page_number} | "
        f"LOGICAL PAGE: {page.logical_page_index} | "
        f"REGION: {page.region}"
    )

    print(f"BBOX: {page.bbox}")
    print(f"BLOCKS: {len(page.blocks)}")

    print("\nCONTENT:")
    print(page.content[:1000])

    print("\nFIRST FEW BLOCKS:")

    for i, block in enumerate(page.blocks[:5]):
        print(f"\n--- BLOCK {i} ---")
        print(
            f"bbox=({block['x0']:.1f}, "
            f"{block['y0']:.1f}, "
            f"{block['x1']:.1f}, "
            f"{block['y1']:.1f})"
        )
        print(f"type={block['block_type']}")
        print(block["text"])