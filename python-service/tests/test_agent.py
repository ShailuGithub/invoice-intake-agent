from datetime import date

from app.agent import InvoiceAgent
from app.extract import RuleBasedExtractor
from app.validator import LocalValidator
from conftest import load_samples

SAMPLES = load_samples()
VALIDATOR = LocalValidator(date(2026, 10, 19))

GOOD = {"vendor": "Acme", "invoiceNumber": "A-1", "invoiceDate": "2026-10-01",
        "subtotal": 100.0, "taxAmount": 18.0, "total": 118.0, "gstin": None, "currency": "INR"}


class Scripted:
    """Returns the queued answers in order and records the feedback it was given."""

    def __init__(self, *answers):
        self.answers, self.feedback_seen = list(answers), []

    def extract(self, text=None, image_png=None, feedback=None):
        self.feedback_seen.append(feedback)
        return self.answers.pop(0)


def test_valid_invoice_needs_one_attempt():
    text, _ = SAMPLES["cgst_sgst.txt"]
    result = InvoiceAgent(RuleBasedExtractor(), VALIDATOR).run(text=text)
    assert result.status == "valid" and result.attempts == 1


def test_validation_errors_are_fed_back_and_the_second_attempt_fixes_it():
    extractor = Scripted(GOOD | {"total": 500.0}, GOOD)
    result = InvoiceAgent(extractor, VALIDATOR).run(text="x")
    assert result.status == "valid" and result.attempts == 2
    assert extractor.feedback_seen[0] is None
    assert extractor.feedback_seen[1] == ["total must equal subtotal + taxAmount"]
    assert len(result.trace) == 2


def test_agent_stops_when_the_extractor_repeats_itself():
    text, _ = SAMPLES["total_mismatch.txt"]
    result = InvoiceAgent(RuleBasedExtractor(), VALIDATOR, max_attempts=5).run(text=text)
    assert result.status == "needs_review"
    assert result.attempts == 2  # second identical answer ends the loop
    assert result.errors == ["total must equal subtotal + taxAmount"]


def test_agent_gives_up_after_max_attempts():
    answers = [GOOD | {"total": 500.0 + i} for i in range(3)]
    result = InvoiceAgent(Scripted(*answers), VALIDATOR, max_attempts=3).run(text="x")
    assert result.status == "needs_review" and result.attempts == 3
