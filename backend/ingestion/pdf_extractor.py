import fitz

from ingestion.page_normalizer import normalize_page


def extract_pdf(pdf_path: str) -> list[dict]:
    document = fitz.open(pdf_path)

    pages = []

    for page in document:
        logical_pages = normalize_page(page)

        for logical_index, logical_page in enumerate(logical_pages):
            text = page.get_text(
                "text",
                clip=logical_page.bbox,
            )

            pages.append({
                "physical_page_number": logical_page.physical_page_number,
                "logical_page_index": logical_index,
                "region": logical_page.region,
                "content": text,
            })

    document.close()

    return pages