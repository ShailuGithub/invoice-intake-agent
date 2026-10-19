"""FastAPI service. POST /intake with either `text` or an image `file`.

Environment:
  INTAKE_EXTRACTOR  rules (default) | llm
  VALIDATOR_URL     API Gateway URL of the Java Lambda; if unset, the Python LocalValidator is used
  ANTHROPIC_API_KEY required only when INTAKE_EXTRACTOR=llm
"""
import os
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from app.agent import InvoiceAgent
from app.extract import RuleBasedExtractor
from app.preprocess import preprocess
from app.validator import HttpValidator, LocalValidator


def build_agent() -> InvoiceAgent:
    if os.environ.get("INTAKE_EXTRACTOR", "rules") == "llm":
        from app.llm import LlmExtractor, make_default_client
        extractor = LlmExtractor(make_default_client())
    else:
        extractor = RuleBasedExtractor()
    url = os.environ.get("VALIDATOR_URL")
    return InvoiceAgent(extractor, HttpValidator(url) if url else LocalValidator())


def create_app(agent: Optional[InvoiceAgent] = None) -> FastAPI:
    app = FastAPI(title="invoice-intake-agent")
    state = {"agent": agent}

    def get_agent() -> InvoiceAgent:
        if state["agent"] is None:
            state["agent"] = build_agent()
        return state["agent"]

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/intake")
    async def intake(text: Optional[str] = Form(None), file: Optional[UploadFile] = File(None)):
        if not text and file is None:
            raise HTTPException(400, "send `text` or an image `file`")
        image_png = None
        if file is not None:
            try:
                image_png = preprocess(await file.read())
            except ValueError as e:
                raise HTTPException(400, str(e))
        try:
            result = get_agent().run(text=text, image_png=image_png)
        except ValueError as e:  # e.g. rules extractor given an image
            raise HTTPException(422, str(e))
        return {"status": result.status, "invoice": result.invoice, "errors": result.errors,
                "attempts": result.attempts}

    return app


app = create_app()
