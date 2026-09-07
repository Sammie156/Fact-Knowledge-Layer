from dataclasses import dataclass

import pymupdf

from ingestion.page_normalizer import normalize_page


@dataclass
class ExtractedPage:
    physical_page_number: int
    logical_page_index: int
    region: str
    bbox: pymupdf.Rect
    content: str
    blocks: list[dict]


def extract_pdf(pdf_path: str) -> list[ExtractedPage]:
    document = pymupdf.open(pdf_path)

    pages = []

    for physical_page in document:

        logical_pages = normalize_page(physical_page)

        for logical_page in logical_pages:

            # Extract all text belonging to this logical page.
            text = physical_page.get_text(
                "text",
                clip=logical_page.bbox,
            )

            # Extract layout blocks as well.
            raw_blocks = physical_page.get_text(
                "blocks",
                clip=logical_page.bbox,
            )

            blocks = []

            for block in raw_blocks:
                x0, y0, x1, y1, block_text, block_number, block_type = block[:7]

                if not block_text.strip():
                    continue

                blocks.append(
                    {
                        "x0": x0,
                        "y0": y0,
                        "x1": x1,
                        "y1": y1,
                        "text": block_text.strip(),
                        "block_number": block_number,
                        "block_type": block_type,
                    }
                )

            pages.append(
                ExtractedPage(
                    physical_page_number=logical_page.physical_page_number,
                    logical_page_index=logical_page.logical_page_index,
                    region=logical_page.region,
                    bbox=logical_page.bbox,
                    content=text.strip(),
                    blocks=blocks,
                )
            )

    document.close()

    return pages