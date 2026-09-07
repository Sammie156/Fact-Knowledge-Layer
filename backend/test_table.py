import pymupdf

from ingestion.table_extractor import (
    extract_tables,
    table_to_markdown,
)


PDF_PATH = "C:/Users/saman/Downloads/02-delhivery-annual-report-fy24-excerpt.pdf"


document = pymupdf.open(PDF_PATH)

for page_number, page in enumerate(document, start=1):

    print("\n")
    print("=" * 80)
    print(f"PHYSICAL PAGE {page_number}")
    print("=" * 80)

    tables = extract_tables(page)

    print("Tables found:", len(tables))

    for i, table in enumerate(tables):

        print("\n")
        print("-" * 80)
        print(f"TABLE {i}")
        print("Method:", table.extraction_method)
        print("BBox:", table.bbox)
        print("-" * 80)

        print(table_to_markdown(table))

document.close()