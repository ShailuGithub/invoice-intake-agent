"""Validation of extracted invoices.

HttpValidator calls the Java Lambda (the source of truth for the rules). LocalValidator mirrors the
same rules in Python so the service can run and be tested without the Lambda deployed; keep the two
in sync with lambda-validator/.../InvoiceValidator.java.
"""
import re
from datetime import date
from typing import Optional, Protocol, Tuple

import httpx

Result = Tuple[bool, list]  # (is_valid, errors)

_GSTIN = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")


class Validator(Protocol):
    def validate(self, invoice: dict) -> Result: ...


class LocalValidator:
    def __init__(self, today: Optional[date] = None):
        self._today = today

    def validate(self, d: dict) -> Result:
        errors = []
        if not (d.get("vendor") or "").strip():
            errors.append("vendor is required")
        if not (d.get("invoiceNumber") or "").strip():
            errors.append("invoiceNumber is required")

        raw_date = d.get("invoiceDate")
        if not raw_date:
            errors.append("invoiceDate is required")
        else:
            try:
                if date.fromisoformat(raw_date) > (self._today or date.today()):
                    errors.append("invoiceDate is in the future")
            except ValueError:
                errors.append("invoiceDate must be yyyy-MM-dd")

        sub, tax, total = d.get("subtotal"), d.get("taxAmount"), d.get("total")
        if sub is None or sub < 0:
            errors.append("subtotal must be zero or more")
        if tax is None or tax < 0:
            errors.append("taxAmount must be zero or more")
        if total is None or total <= 0:
            errors.append("total must be greater than zero")
        if None not in (sub, tax, total) and sub >= 0 and tax >= 0 and total > 0:
            if abs(sub + tax - total) > 0.01 + 1e-9:
                errors.append("total must equal subtotal + taxAmount")

        gstin = d.get("gstin")
        if gstin and not _GSTIN.match(gstin.strip().upper()):
            errors.append("gstin is not a valid 15-character GSTIN")
        return (not errors, errors)


class HttpValidator:
    """POSTs the invoice to the deployed Lambda (API Gateway URL)."""

    def __init__(self, url: str, client: Optional[httpx.Client] = None):
        self.url = url
        self._client = client or httpx.Client(timeout=10)

    def validate(self, invoice: dict) -> Result:
        res = self._client.post(self.url, json=invoice)
        if res.status_code == 200:
            return True, []
        if res.status_code == 422:
            return False, res.json().get("errors", [])
        raise RuntimeError(f"validator returned HTTP {res.status_code}")
