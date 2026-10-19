from datetime import date

import cv2
import numpy as np
from fastapi.testclient import TestClient

from app.agent import InvoiceAgent
from app.extract import RuleBasedExtractor
from app.main import create_app
from app.validator import LocalValidator
from conftest import load_samples

SAMPLES = load_samples()
client = TestClient(create_app(InvoiceAgent(RuleBasedExtractor(), LocalValidator(date(2026, 10, 19)))))


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_text_invoice_is_extracted_and_validated():
    res = client.post("/intake", data={"text": SAMPLES["igst_total_only.txt"][0]})
    body = res.json()
    assert res.status_code == 200
    assert body["status"] == "valid" and body["invoice"]["subtotal"] == 2500.0 and body["attempts"] == 1


def test_inconsistent_invoice_is_flagged_for_review():
    body = client.post("/intake", data={"text": SAMPLES["total_mismatch.txt"][0]}).json()
    assert body["status"] == "needs_review"
    assert body["errors"] == ["total must equal subtotal + taxAmount"]


def test_empty_request_is_rejected():
    assert client.post("/intake").status_code == 400


def test_non_image_upload_is_rejected():
    res = client.post("/intake", files={"file": ("x.png", b"not an image", "image/png")})
    assert res.status_code == 400


def test_image_upload_with_rules_extractor_returns_422():
    png = cv2.imencode(".png", np.full((50, 50), 255, np.uint8))[1].tobytes()
    res = client.post("/intake", files={"file": ("x.png", png, "image/png")})
    assert res.status_code == 422
