from dataclasses import dataclass

import pymupdf


@dataclass
class ExtractedTable:
    bbox: pymupdf.Rect
    rows: list[list[str]]
    extraction_method: str


def extract_tables(page: pymupdf.Page) -> list[ExtractedTable]:
    """
    Extract tables from a PyMuPDF page.

    Strategy:
    1. Let PyMuPDF detect tables and attempt normal extraction.
    2. Validate the extracted result.
    3. If extraction is unreliable, reconstruct the table
       using word-level coordinates.
    """

    finder = page.find_tables()

    tables = []

    for table in finder.tables:
        extracted = table.extract()

        if is_valid_table(extracted):
            tables.append(
                ExtractedTable(
                    bbox=pymupdf.Rect(table.bbox),
                    rows=clean_rows(extracted),
                    extraction_method="pymupdf",
                )
            )
        else:
            rows = reconstruct_table(
                page,
                pymupdf.Rect(table.bbox),
            )

            if rows:
                tables.append(
                    ExtractedTable(
                        bbox=pymupdf.Rect(table.bbox),
                        rows=rows,
                        extraction_method="word_coordinates",
                    )
                )

    return tables


def is_valid_table(rows: list[list[str | None]]) -> bool:
    """
    Decide whether PyMuPDF's table extraction produced
    something useful.
    """

    if not rows:
        return False

    if len(rows) < 2:
        return False

    column_count = max(len(row) for row in rows)

    if column_count < 2:
        return False

    total_cells = 0
    non_empty_cells = 0

    for row in rows:
        for cell in row:
            total_cells += 1

            if cell is not None and str(cell).strip():
                non_empty_cells += 1

    if total_cells == 0:
        return False

    density = non_empty_cells / total_cells

    return density >= 0.30


def clean_rows(
    rows: list[list[str | None]],
) -> list[list[str]]:
    """
    Normalize PyMuPDF's extracted cells.
    """

    cleaned = []

    for row in rows:
        cleaned_row = []

        for cell in row:
            if cell is None:
                cleaned_row.append("")
            else:
                cleaned_row.append(" ".join(str(cell).split()))

        cleaned.append(cleaned_row)

    return cleaned


def reconstruct_table(
    page: pymupdf.Page,
    bbox: pymupdf.Rect,
) -> list[list[str]]:
    """
    Reconstruct a table from word coordinates.

    This assumes:
    - words on approximately the same Y coordinate belong
      to the same visual row
    - X-coordinate clusters represent columns
    """

    words = page.get_text(
        "words",
        clip=bbox,
    )

    if not words:
        return []

    # ---------------------------------------------------------
    # Step 1: convert PyMuPDF words into a simpler structure
    # ---------------------------------------------------------

    items = []

    for word in words:
        x0, y0, x1, y1, text, *_ = word

        if not text.strip():
            continue

        items.append(
            {
                "x0": x0,
                "x1": x1,
                "y0": y0,
                "y1": y1,
                "text": text.strip(),
                "center_x": (x0 + x1) / 2,
                "center_y": (y0 + y1) / 2,
            }
        )

    if not items:
        return []

    # ---------------------------------------------------------
    # Step 2: group words into visual lines
    # ---------------------------------------------------------

    items.sort(key=lambda item: (item["center_y"], item["x0"]))

    lines = []

    # Tolerance in PDF points.
    # Words on the same visual line generally have
    # very similar Y coordinates.
    y_tolerance = 3.0

    for item in items:

        matched_line = None

        for line in reversed(lines):
            if abs(
                item["center_y"] - line["center_y"]
            ) <= y_tolerance:
                matched_line = line
                break

        if matched_line is None:
            matched_line = {
                "center_y": item["center_y"],
                "words": [],
            }

            lines.append(matched_line)

        matched_line["words"].append(item)

    # Sort words inside each line.
    for line in lines:
        line["words"].sort(key=lambda item: item["x0"])

    # ---------------------------------------------------------
    # Step 3: infer column positions
    # ---------------------------------------------------------

    # We don't know how many columns the table has.
    #
    # Instead, look at the X positions of words and find
    # recurring horizontal regions.
    #
    # This is deliberately heuristic rather than
    # hard-coded for this particular financial table.

    x_positions = sorted(
        item["x0"]
        for item in items
    )

    x_tolerance = 12.0

    column_groups = []

    for x in x_positions:

        if not column_groups:
            column_groups.append([x])
            continue

        previous_group = column_groups[-1]

        if abs(x - sum(previous_group) / len(previous_group)) <= x_tolerance:
            previous_group.append(x)
        else:
            column_groups.append([x])

    column_starts = [
        sum(group) / len(group)
        for group in column_groups
    ]

    # ---------------------------------------------------------
    # Step 4: merge nearby X groups into actual columns
    # ---------------------------------------------------------

    #
    # The above grouping operates on word starts.
    # A textual cell such as:
    #
    #   Revenue from Operations
    #
    # naturally creates several nearby X positions.
    #
    # We therefore need to distinguish:
    #
    #   "words belonging to one text cell"
    #
    # from:
    #
    #   "words belonging to separate columns".
    #
    # For this prototype, numeric-looking values are especially
    # useful anchors for determining numeric columns.
    #

    numeric_items = [
        item
        for item in items
        if looks_numeric(item["text"])
    ]

    if len(numeric_items) >= 2:

        numeric_x = sorted(
            item["center_x"]
            for item in numeric_items
        )

        numeric_columns = cluster_positions(
            numeric_x,
            tolerance=25.0,
        )

        if len(numeric_columns) >= 2:

            column_centers = numeric_columns

            # Add a left-most textual column.
            left_x = min(
                item["x0"]
                for item in items
            )

            column_centers = [
                left_x
            ] + column_centers

        else:
            column_centers = infer_columns_from_layout(
                items
            )

    else:
        column_centers = infer_columns_from_layout(
            items
        )

    # ---------------------------------------------------------
    # Step 5: assign each word to the nearest column
    # ---------------------------------------------------------

    reconstructed_rows = []

    for line in lines:

        cells = [
            []
            for _ in column_centers
        ]

        for item in line["words"]:

            column_index = min(
                range(len(column_centers)),
                key=lambda i: abs(
                    item["center_x"]
                    - column_centers[i]
                ),
            )

            cells[column_index].append(
                item["text"]
            )

        row = [
            " ".join(cell).strip()
            for cell in cells
        ]

        if any(row):
            reconstructed_rows.append(row)

    return reconstructed_rows


def looks_numeric(text: str) -> bool:
    """
    Rough test for numerical table values.

    Handles examples such as:
        74,540.82
        (1,679.68)
        -
        2024
        11.95%
    """

    cleaned = (
        text
        .replace(",", "")
        .replace("%", "")
        .replace("₹", "")
        .strip()
    )

    if cleaned == "-":
        return True

    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = cleaned[1:-1]

    try:
        float(cleaned)
        return True
    except ValueError:
        return False


def cluster_positions(
    positions: list[float],
    tolerance: float,
) -> list[float]:
    """
    Cluster nearby X positions and return the center
    of each cluster.
    """

    if not positions:
        return []

    positions = sorted(positions)

    clusters = [[positions[0]]]

    for position in positions[1:]:

        current = clusters[-1]

        center = sum(current) / len(current)

        if abs(position - center) <= tolerance:
            current.append(position)
        else:
            clusters.append([position])

    return [
        sum(cluster) / len(cluster)
        for cluster in clusters
    ]


def infer_columns_from_layout(
    items: list[dict],
) -> list[float]:
    """
    Fallback column inference.

    Uses large horizontal gaps between word positions.
    """

    starts = sorted(
        item["x0"]
        for item in items
    )

    if not starts:
        return []

    clusters = [[starts[0]]]

    for x in starts[1:]:

        current = clusters[-1]

        center = sum(current) / len(current)

        if abs(x - center) <= 30:
            current.append(x)
        else:
            clusters.append([x])

    return [
        sum(cluster) / len(cluster)
        for cluster in clusters
    ]


def table_to_markdown(
    table: ExtractedTable,
) -> str:
    """
    Convert reconstructed table rows into Markdown.
    """

    rows = table.rows

    if not rows:
        return ""

    # Normalize row lengths.
    column_count = max(
        len(row)
        for row in rows
    )

    normalized = []

    for row in rows:
        normalized.append(
            row + [""] * (
                column_count - len(row)
            )
        )

    header = normalized[0]

    markdown = []

    markdown.append(
        "| " + " | ".join(header) + " |"
    )

    markdown.append(
        "| "
        + " | ".join("---" for _ in header)
        + " |"
    )

    for row in normalized[1:]:
        markdown.append(
            "| " + " | ".join(row) + " |"
        )

    return "\n".join(markdown)