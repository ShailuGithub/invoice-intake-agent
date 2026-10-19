"""The intake agent: a small multi-step loop.

  extract -> validate -> (if invalid) feed the validator's errors back to the extractor -> retry

It stops when the invoice validates, when the extractor returns the same answer twice (retrying
cannot help), or after `max_attempts`. Every step is recorded in `trace` for debugging and the
evaluation notebook.
"""
from dataclasses import dataclass, field
from typing import Optional

from app.extract import Extractor
from app.validator import Validator


@dataclass
class AgentResult:
    status: str                      # "valid" or "needs_review"
    invoice: dict
    errors: list
    attempts: int
    trace: list = field(default_factory=list)


class InvoiceAgent:
    def __init__(self, extractor: Extractor, validator: Validator, max_attempts: int = 3):
        self.extractor = extractor
        self.validator = validator
        self.max_attempts = max_attempts

    def run(self, text: Optional[str] = None, image_png: Optional[bytes] = None) -> AgentResult:
        feedback = None
        previous = None
        invoice, errors, trace = {}, [], []
        for attempt in range(1, self.max_attempts + 1):
            invoice = self.extractor.extract(text=text, image_png=image_png, feedback=feedback)
            valid, errors = self.validator.validate(invoice)
            trace.append({"attempt": attempt, "feedback": feedback, "invoice": invoice, "errors": errors})
            if valid:
                return AgentResult("valid", invoice, [], attempt, trace)
            if invoice == previous:
                break
            previous, feedback = invoice, errors
        return AgentResult("needs_review", invoice, errors, len(trace), trace)
