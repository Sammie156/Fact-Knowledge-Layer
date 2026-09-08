from facts.filter import looks_fact_bearing


SHOULD_PASS = [
    "Revenue increased by 20% during FY2024.",
    "The company expanded its delivery network.",
    "The company acquired 51% of XYZ Logistics.",
    "Profit for the year was ₹1,250 million.",
    "The company had 45,000 employees.",
    "Revenue from operations was $2.4 billion.",
    "The company entered the European market.",
    "The number of customers grew significantly.",
]


SHOULD_SKIP = [
    "Annual Report 2023-24",
    "Financial Statements",
    "Corporate Overview",
    "Table of Contents",
    "43",
    "Management Discussion and Analysis",
    "Notes to the Financial Statements",
    "This page has been intentionally left blank.",
]


def test_should_pass():
    for text in SHOULD_PASS:
        result = looks_fact_bearing(text)

        assert result, f"Expected PASS but got SKIP: {text}"

    print(f"✓ {len(SHOULD_PASS)} fact-bearing tests passed")


def test_should_skip():
    for text in SHOULD_SKIP:
        result = looks_fact_bearing(text)

        assert not result, f"Expected SKIP but got PASS: {text}"

    print(f"✓ {len(SHOULD_SKIP)} noise tests passed")


if __name__ == "__main__":
    test_should_pass()
    test_should_skip()

    print("\nAll filter tests passed.")