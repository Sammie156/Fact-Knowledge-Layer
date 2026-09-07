from dataclasses import dataclass

import fitz


@dataclass
class LogicalPage:
    physical_page_number: int
    region: str
    bbox: fitz.Rect


def normalize_page(
    page: fitz.Page,
) -> list[LogicalPage]:
    width = page.rect.width
    height = page.rect.height
    midpoint = width / 2

    blocks = [
        block
        for block in page.get_text("blocks")
        if block[4].strip()
    ]

    left_blocks = 0
    right_blocks = 0

    for block in blocks:
        x0, y0, x1, y1, *_ = block
        center_x = (x0 + x1) / 2

        if center_x < midpoint:
            left_blocks += 1
        else:
            right_blocks += 1

    # Simple MVP heuristic for a two-up page.
    is_two_up = (
        width > height
        and left_blocks >= 5
        and right_blocks >= 5
    )

    if not is_two_up:
        return [
            LogicalPage(
                physical_page_number=page.number + 1,
                region="full",
                bbox=page.rect,
            )
        ]

    return [
        LogicalPage(
            physical_page_number=page.number + 1,
            region="left",
            bbox=fitz.Rect(
                0,
                0,
                midpoint,
                height,
            ),
        ),
        LogicalPage(
            physical_page_number=page.number + 1,
            region="right",
            bbox=fitz.Rect(
                midpoint,
                0,
                width,
                height,
            ),
        ),
    ]