"""Field extraction. Two interchangeable extractors share one interface:

    extract(text=None, image_png=None, feedback=None) -> dict

* RuleBasedExtractor: deterministic regex parser for text invoices. Needs no API key, so tests and
  local runs work offline.
* LlmExtractor (app/llm.py): sends text or the cleaned image to a language model.
"""
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional, Protocol

FIELDS = ["vendor", "invoiceNumber", "invoiceDate", "subtotal", "taxAmount", "total", "gstin", "currency"]

_GSTIN = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b")
_AMOUNT = re.compile(r"(\d[\d,]*(?:\.\d{1,2})?)")
_PERCENT = re.compile(r"\(?\d+(?:\.\d+)?\s*%\)?")
_DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d %b %Y", "%d %B %Y",
                 "%b %d, %Y", "%B %d, %Y", "%d-%b-%Y", "%d/%m/%y"]


class Extractor(Protocol):
    def extract(self, text: Optional[str] = None, image_png: Optional[bytes] = None,
                feedback: Optional[list] = None) -> dict: ...


def parse_amount(s: str) -> Optional[Decimal]:
    m = _AMOUNT.search(_PERCENT.sub("", s))
    if not m:
        return None
    try:
        return Decimal(m.group(1).replace(",", "")).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def parse_date(s: str) -> Optional[str]:
    s = s.strip().strip(".,")
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _money(value: Optional[Decimal]) -> Optional[float]:
    return float(value) if value is not None else None


class RuleBasedExtractor:
    """Regex/heuristic parser. It ignores `feedback`; retries only make sense for the LLM extractor."""

    def extract(self, text: Optional[str] = None, image_png: Optional[bytes] = None,
                feedback: Optional[list] = None) -> dict:
        if not text:
            raise ValueError("RuleBasedExtractor needs text; use the LLM extractor for images")
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

        vendor = next((ln for ln in lines if not re.fullmatch(r"(tax\s+)?invoice", ln, re.I)), None)

        number = None
        date = None
        subtotal = tax = total = None
        tax_parts = []
        for ln in lines:
            low = ln.lower()
            if number is None:
                m = re.search(r"invoice\s*(?:no\.?|number|#)\s*[:\-]?\s*([A-Za-z0-9/\-]+)", ln, re.I)
                if m:
                    number = m.group(1)
                    continue
            if date is None:
                m = re.search(r"date\s*[:\-]?\s*(.+)$", ln, re.I)
                if m and parse_date(m.group(1)):
                    date = parse_date(m.group(1))
                    continue
            label = low.split(":")[0]
            if re.match(r"(sub\s*-?\s*total|taxable)", low):
                subtotal = parse_amount(ln.split(":")[-1] if ":" in ln else ln)
            elif re.match(r"(total\s+)?(cgst|sgst|igst|gst|vat|tax)\b", low) and "invoice" not in label:
                amount = parse_amount(ln.split(":")[-1] if ":" in ln else ln)
                if amount is not None:
                    tax_parts.append(amount)
            elif re.match(r"(grand\s+total|total\s+amount|total|amount\s+(payable|due)|net\s+payable)", low):
                total = parse_amount(ln.split(":")[-1] if ":" in ln else ln) or total

        if tax_parts:
            tax = sum(tax_parts, Decimal("0.00"))
        if subtotal is None and total is not None and tax is not None:
            subtotal = total - tax  # many invoices only print total and tax
        if tax is None and subtotal is not None and total is not None:
            tax = total - subtotal

        gstin = _GSTIN.search(text)
        has_rupee = bool(re.search(r"₹|\bRs\b\.?|\bINR\b", text))
        return {
            "vendor": vendor,
            "invoiceNumber": number,
            "invoiceDate": date,
            "subtotal": _money(subtotal),
            "taxAmount": _money(tax),
            "total": _money(total),
            "gstin": gstin.group(0) if gstin else None,
            "currency": "INR" if has_rupee else None,
        }
