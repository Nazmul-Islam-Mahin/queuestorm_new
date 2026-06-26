# QueueStorm Investigator

> AI/API copilot for digital finance customer support — SUST CSE Carnival 2026 · Codex Community Hackathon

---

## Overview

**QueueStorm Investigator** is a FastAPI service that reads a customer complaint together with a short snippet of their recent transaction history, investigates what actually happened, and returns a fully structured routing and response payload for support agents.

| Endpoint | Method | Purpose |
|---|---|---|
| `/health` | GET | Returns `{"status":"ok"}` within 60 s of startup |
| `/analyze-ticket` | POST | Full complaint investigation and routing |
| `/docs` | GET | Interactive Swagger UI |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Runtime | Python 3.11 |
| Framework | FastAPI + Uvicorn |
| Validation | Pydantic v2 |
| HTTP client | httpx |
| Classification | Deterministic regex rules (priority-ordered) |
| LLM enrichment | Optional — Google Gemini 1.5 Flash / OpenAI GPT-4o-mini |
| Safety | Post-generation regex sanitiser (always applied) |
| Testing | pytest + FastAPI TestClient |

---

## Architecture

```
POST /analyze-ticket
        │
        ▼
┌─────────────────────────────────────────┐
│  Pydantic validation (app.py)           │
│  - Required fields, enum checks         │
│  - Empty complaint → 422                │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│  investigator.py — Decision Engine      │
│                                         │
│  1. Language detection (en/bn/mixed)    │
│  2. Complaint classification            │
│     └─ Priority regex rules             │
│     └─ Prompt-injection guard           │
│  3. Transaction matching                │
│     └─ Duplicate detection (≤60 min)   │
│     └─ Amount + type + status scoring  │
│     └─ Ambiguous → insufficient_data   │
│  4. Evidence verdict                    │
│     └─ Established recipient check     │
│     └─ Status vs complaint analysis    │
│  5. Severity / department / review      │
│  6. Template response generation        │
└────────────────┬────────────────────────┘
                 │
          (if API key set)
                 │
                 ▼
┌─────────────────────────────────────────┐
│  llm.py — Optional LLM enrichment       │
│  Gemini 1.5 Flash → OpenAI GPT-4o-mini  │
│  Falls back silently on failure         │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│  safety.py — Final sanitiser            │
│  - Credential request detection         │
│  - Unauthorized refund promise check    │
│  - Third-party redirect check           │
│  - Overrides with safe fallback if fail │
└─────────────────────────────────────────┘
```

---

## Safety Logic

Three hard rules enforced by `safety.py` on every `customer_reply`:

1. **No credential requests** — Never ask for PIN, OTP, password, or card number. Safe negation warnings ("do not share your PIN") pass validation.
2. **No unauthorized promises** — Phrases like "we will refund you" are blocked. Safe language: *"any eligible amount will be returned through official channels."*
3. **No third-party redirects** — Customers are never directed to WhatsApp, Telegram, or similar platforms.

Any output failing these checks is replaced with a pre-validated fallback in the appropriate language (English or Bangla).

Prompt-injection attempts embedded in complaint text are logged and ignored — classification proceeds on the actual complaint content only.

---

## AI / Model Usage (MODELS)

| Model | Provider | Usage | Why chosen |
|---|---|---|---|
| Gemini 1.5 Flash | Google AI | Optional enrichment of `agent_summary` and `customer_reply` | Fast, low-cost, JSON mode |
| GPT-4o-mini | OpenAI | Fallback enrichment if Gemini unavailable | Reliable JSON output |
| Deterministic templates | None (local) | Primary/fallback response generation | Zero latency, zero cost, 100% safe |

> An LLM is **not required** to run this service. All responses are generated deterministically if no API key is set.

---

## Local Setup

### Requirements
- Python 3.11+

### Install

```bash
cd queuestorm_investigator
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configure (optional)

```bash
cp .env.example .env
# Edit .env to add GEMINI_API_KEY or OPENAI_API_KEY if desired
```

### Run

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
# or
python app.py
```

### Test

```bash
pytest tests/ -v
```

### Quick smoke test

```bash
curl http://localhost:8000/health
# {"status":"ok"}

curl -X POST http://localhost:8000/analyze-ticket \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_id": "TKT-001",
    "complaint": "I sent 5000 taka to a wrong number around 2pm today.",
    "language": "en",
    "channel": "in_app_chat",
    "user_type": "customer",
    "transaction_history": [{
      "transaction_id": "TXN-9101",
      "timestamp": "2026-04-14T14:08:22Z",
      "type": "transfer",
      "amount": 5000,
      "counterparty": "+8801719876543",
      "status": "completed"
    }]
  }'
```

---

## Docker

### Build and run

```bash
docker build -t queuestorm-investigator .
docker run -p 8000:8000 \
  -e GEMINI_API_KEY=your_key_here \
  queuestorm-investigator
```

### Or pull and run (once published)

```bash
docker pull <username>/queuestorm-investigator:latest
docker run -p 8000:8000 queuestorm-investigator
```

---

## Assumptions & Known Limitations

- **Ambiguous multi-match** → `relevant_transaction_id=null`, `evidence_verdict=insufficient_data`. This is intentional and correct per the spec (safer than guessing).
- **Duplicate detection window** is 1 hour. Pairs >1 hour apart are scored normally.
- **Established recipient pattern** requires ≥2 prior completed transfers to the same counterparty to flag as `inconsistent`.
- **Bangla detection** uses Unicode range U+0980–U+09FF; Banglish (Roman-script Bangla) is treated as `en`.
- **LLM timeout** is 8 seconds; on timeout the deterministic template is used silently.
- **No persistent storage** — all state is per-request; no database required.
