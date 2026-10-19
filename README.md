# invoice-intake-agent

Turns an invoice (text or a photo/scan) into validated, structured data.

```
 image/text ──► Python service ──► extractor ──► agent loop ──► result
                (FastAPI)          (rules | LLM)   │  ▲
                OpenCV clean-up                     ▼  │ errors fed back
                                              validator (Java Lambda or local)
```

| Part | Tech | What it does |
|---|---|---|
| `python-service/` | Python 3.12, FastAPI, OpenCV | Cleans and de-skews invoice photos, extracts fields, runs the agent loop |
| `lambda-validator/` | Java 17, AWS Lambda, Maven | Business rules: required fields, date, total = subtotal + tax, GSTIN format |
| `python-service/notebooks/` | Jupyter | Accuracy per field, de-skew check, agent trace |
| `.github/workflows/ci.yml` | GitHub Actions | Tests both parts and builds the Docker image |

## How the agent works
1. **Extract** the fields (`vendor, invoiceNumber, invoiceDate, subtotal, taxAmount, total, gstin, currency`).
2. **Validate** them (the Lambda is the source of truth; `LocalValidator` mirrors it for offline runs).
3. If invalid, send the validator's error list back to the extractor and retry (max 3 attempts), stopping early
   if the extractor repeats itself. Invoices that still fail are returned as `needs_review` with the reasons,
   never silently "fixed".

Two extractors share one interface:
* `rules` (default): regex parser for text invoices; needs no key and is fully deterministic.
* `llm`: sends text or the cleaned image to a language model (needs `ANTHROPIC_API_KEY`; the model client is
  injected, so tests use a fake). Swap `app/llm.py`'s adapter to use a different provider.

## Run it
```powershell
# Python service
cd python-service
python -m venv .venv; .\.venv\Scripts\pip install -r requirements-dev.txt
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\uvicorn app.main:app --reload        # http://localhost:8000/docs

# Java Lambda
cd lambda-validator; .\mvnw.cmd test                  # fat jar: .\mvnw.cmd package
```
Environment: `INTAKE_EXTRACTOR=rules|llm`, `VALIDATOR_URL=<API Gateway URL>` (unset = local validator).

Try it:
```powershell
curl.exe -X POST http://localhost:8000/intake -F "text=<tests/samples/cgst_sgst.txt"
```

## Deploying the Lambda (not done yet)
Runtime Java 17, handler `com.invoiceintake.validator.Handler::handleRequest`, upload
`lambda-validator/target/lambda-validator-0.1.0.jar`, put API Gateway (proxy integration) in front, then set
`VALIDATOR_URL` on the Python service.

## Known limits
* Sample set is five hand-written invoices, so 100% accuracy there is a smoke test, not a benchmark.
* The rule-based extractor reads text only; images need the `llm` extractor.
* The Dockerfile is built in CI; Kubernetes manifests are out of scope.
