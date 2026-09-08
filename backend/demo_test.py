import pymupdf
from ingestion.pdf_extractor import extract_pdf
from ingestion.chunker import chunk_page

pages = extract_pdf("C:/Users/saman/Downloads/starter-datasets/delhivery/01-delhivery-prospectus-2022-excerpt.pdf")
total_chunks = sum(len(chunk_page(p)) for p in pages)
fact_bearing = 0

from facts.filter import looks_fact_bearing
for page in pages:
    for chunk in chunk_page(page):
        if looks_fact_bearing(chunk.content):
            fact_bearing += 1

print(f"Total pages  : {len(pages)}")
print(f"Total chunks : {total_chunks}")
print(f"Fact-bearing : {fact_bearing}")
print(f"Skipped      : {total_chunks - fact_bearing}")