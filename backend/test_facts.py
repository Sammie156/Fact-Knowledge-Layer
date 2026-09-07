from ingestion.pdf_extractor import extract_pdf
from ingestion.chunker import chunk_page
from facts.extractor import extract_facts


PDF_PATH = "C:/Users/saman/Downloads/02-delhivery-annual-report-fy24-excerpt.pdf"


pages = extract_pdf(PDF_PATH)

for page in pages:

    chunks = chunk_page(page)

    for chunk in chunks:

        print("\n" + "=" * 80)
        print(
            f"PAGE {page.physical_page_number} | "
            f"LOGICAL PAGE {page.logical_page_index} | "
            f"CHUNK {chunk.chunk_index}"
        )
        print("=" * 80)

        result = extract_facts(chunk.content)

        print(f"Facts found: {len(result.facts)}")

        for fact in result.facts:
            print("\nFACT")
            print(f"  Entity:      {fact.entity}")
            print(f"  Attribute:   {fact.attribute}")
            print(f"  Value:       {fact.value}")
            print(f"  Unit:        {fact.unit}")
            print(f"  Time:        {fact.time_scope}")
            print(
                    "  Qualifiers: ",
                        [
                            f"{q.key}={q.value}"
                            for q in fact.qualifiers
                        ]
                )
            print(f"  Confidence:  {fact.confidence}")
            print(f"  Evidence:    {fact.raw_text}")