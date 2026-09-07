import sys

import fitz

from ingestion.page_normalizer import normalize_page


pdf_path = sys.argv[1]

doc = fitz.open(pdf_path)

for page in doc:
    logical_pages = normalize_page(page)

    print(
        f"Physical page {page.number + 1}: "
        f"{len(logical_pages)} logical page(s)"
    )

    for logical_page in logical_pages:
        print(
            f"  {logical_page.region}: "
            f"{logical_page.bbox}"
        )

doc.close()