from dataclasses import dataclass

from ingestion.pdf_extractor import ExtractedPage


@dataclass
class ChunkData:
    page: ExtractedPage
    chunk_index: int
    content: str
    chunk_type: str


MIN_CHUNK_CHARS = 600
MAX_CHUNK_CHARS = 4500


def chunk_page(page: ExtractedPage) -> list[ChunkData]:
    """
    Chunks an extracted logical page.
    - If the page in total is <= MAX_CHUNK_CHARS, emit it as a single chunk.
    - If the page exceeds MAX_CHUNK_CHARS, split along layout block boundaries.
    - Merges small trailing blocks (< MIN_CHUNK_CHARS) into the preceding chunk
      to prevent fragmented micro-chunks that cause excessive LLM calls.
    """
    valid_blocks = [
        b["text"].strip()
        for b in page.blocks
        if b.get("text") and b["text"].strip()
    ]

    if not valid_blocks:
        return []

    total_page_chars = sum(len(b) for b in valid_blocks)
    if total_page_chars <= MAX_CHUNK_CHARS:
        return [make_chunk(page, 0, valid_blocks)]

    chunks = []
    current_blocks = []
    current_length = 0

    for text in valid_blocks:
        current_blocks.append(text)
        current_length += len(text)

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

    if current_blocks:
        # If the leftover text is too short and we already have a previous chunk,
        # merge it into the previous chunk instead of emitting an orphan micro-chunk.
        if chunks and current_length < MIN_CHUNK_CHARS:
            prev = chunks[-1]
            merged_content = prev.content + "\n\n" + "\n\n".join(current_blocks)
            chunks[-1] = ChunkData(
                page=prev.page,
                chunk_index=prev.chunk_index,
                content=merged_content,
                chunk_type=prev.chunk_type,
            )
        else:
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