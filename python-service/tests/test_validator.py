from datetime import date

import httpx
import pytest

from app.validator import HttpValidator, LocalValidator

TODAY = date(2026, 10, 19)


def valid():
    return {"vendor": "Acme", "invoiceNumber": "A-1", "invoiceDate": "2026-10-01",
            "subtotal": 1000.0, "taxAmount": 180.0, "total": 1180.0, "gstin": "29ABCDE1234F1Z5"}


def test_valid_invoice_passes():
    assert LocalValidator(TODAY).validate(valid()) == (True, [])


def test_total_mismatch_future_date_and_bad_gstin_are_reported():
    d = valid() | {"total": 1200.0, "invoiceDate": "2026-12-01", "gstin": "BAD"}
    ok, errors = LocalValidator(TODAY).validate(d)
    assert not ok
    assert "total must equal subtotal + taxAmount" in errors
    assert "invoiceDate is in the future" in errors
    assert "gstin is not a valid 15-character GSTIN" in errors


def test_missing_fields_are_all_reported():
    ok, errors = LocalValidator(TODAY).validate({})
    assert not ok
    assert {"vendor is required", "invoiceNumber is required", "invoiceDate is required",
            "total must be greater than zero"} <= set(errors)


def test_one_paisa_rounding_is_accepted():
    assert LocalValidator(TODAY).validate(valid() | {"total": 1180.01})[0]


def _http(status, body):
    transport = httpx.MockTransport(lambda request: httpx.Response(status, json=body))
    return HttpValidator("http://lambda.test/validate", httpx.Client(transport=transport))


def test_http_validator_maps_200_to_valid():
    assert _http(200, {"valid": True}).validate(valid()) == (True, [])


def test_http_validator_maps_422_to_errors():
    assert _http(422, {"valid": False, "errors": ["total must equal subtotal + taxAmount"]}).validate(valid()) \
        == (False, ["total must equal subtotal + taxAmount"])


def test_http_validator_raises_on_server_error():
    with pytest.raises(RuntimeError):
        _http(500, {}).validate(valid())
