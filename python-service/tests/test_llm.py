import pytest

from app.extract import FIELDS
from app.llm import LlmExtractor


class FakeClient:
    def __init__(self, reply):
        self.reply, self.calls = reply, []

    def complete(self, system, user_text, image_png=None):
        self.calls.append((system, user_text, image_png))
        return self.reply


GOOD = ('```json\n{"vendor": "Acme", "invoiceNumber": "A-1", "invoiceDate": "2026-10-01", "subtotal": 100,'
        ' "taxAmount": 18, "total": 118, "gstin": null, "currency": "INR", "extra": "dropped"}\n```')


def test_reply_inside_code_fences_is_parsed_and_extra_keys_dropped():
    out = LlmExtractor(FakeClient(GOOD)).extract(text="invoice text")
    assert list(out) == FIELDS
    assert out["total"] == 118 and out["vendor"] == "Acme"


def test_feedback_is_added_to_the_prompt():
    client = FakeClient(GOOD)
    LlmExtractor(client).extract(text="invoice text", feedback=["total must equal subtotal + taxAmount"])
    assert "total must equal subtotal + taxAmount" in client.calls[0][1]


def test_image_is_passed_through():
    client = FakeClient(GOOD)
    LlmExtractor(client).extract(image_png=b"\x89PNG")
    assert client.calls[0][2] == b"\x89PNG"


def test_reply_without_json_raises():
    with pytest.raises(ValueError):
        LlmExtractor(FakeClient("sorry, I cannot read that")).extract(text="x")


def test_needs_some_input():
    with pytest.raises(ValueError):
        LlmExtractor(FakeClient(GOOD)).extract()
