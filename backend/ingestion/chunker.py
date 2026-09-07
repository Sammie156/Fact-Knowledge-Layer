from dataclasses import dataclass

from ingestion.pdf_extractor import ExtractedPage


@dataclass
class ChunkData:
    page: ExtractedPage
    chunk_index: int
    content: str
    chunk_type: str


MIN_CHUNK_CHARS = 200
MAX_CHUNK_CHARS = 1500


def chunk_page(page: ExtractedPage) -> list[ChunkData]:
    chunks = []

    current_blocks = []
    current_length = 0

    for block in page.blocks:
        text = block["text"].strip()

        if not text:
            continue

        current_blocks.append(text)
        current_length += len(text)

        # Keep accumulating until the chunk has
        # enough content to be useful.
        if current_length < MIN_CHUNK_CHARS:
            continue

        # Once we reach our target size, emit it.
        if current_length >= MAX_CHUNK_CHARS:
            chunks.append(
                make_chunk(
                    page,
                    len(chunks),
                    current_blocks,
                )
            )

            current_blocks = []
            current_length = 0

    # Don't lose the final partial chunk.
    if current_blocks:
        chunks.append(
            make_chunk(
                page,
                len(chunks),
                current_blocks,
            )
        )

    return chunks


def make_chunk(
    page: ExtractedPage,
    chunk_index: int,
    blocks: list[str],
) -> ChunkData:

    return ChunkData(
        page=page,
        chunk_index=chunk_index,
        content="\n\n".join(blocks),
        chunk_type="text",
    )