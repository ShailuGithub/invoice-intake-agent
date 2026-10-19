import pytest

from app.extract import RuleBasedExtractor, parse_amount, parse_date
from conftest import load_samples

SAMPLES = load_samples()


@pytest.mark.parametrize("name", sorted(SAMPLES))
def test_sample_invoices_are_extracted_exactly(name):
    text, expected = SAMPLES[name]
    assert RuleBasedExtractor().extract(text=text) == expected


def test_images_are_not_supported_by_the_rules_extractor():
    with pytest.raises(ValueError):
        RuleBasedExtractor().extract(image_png=b"x")


@pytest.mark.parametrize("raw, expected", [
    ("₹1,180.00", 1180.0), ("Rs. 450", 450.0), ("CGST (9%): 90.00", 90.0), ("n/a", None),
])
def test_parse_amount(raw, expected):
    got = parse_amount(raw)
    assert (float(got) if got is not None else None) == expected


@pytest.mark.parametrize("raw, expected", [
    ("01/10/2026", "2026-10-01"), ("12 Oct 2026", "2026-10-12"), ("Oct 05, 2026", "2026-10-05"),
    ("2026-09-28", "2026-09-28"), ("03-10-2026", "2026-10-03"), ("someday", None),
])
def test_parse_date(raw, expected):
    assert parse_date(raw) == expected
