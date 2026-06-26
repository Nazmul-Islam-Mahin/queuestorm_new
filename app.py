"""
QueueStorm Investigator — FastAPI Service
POST /analyze-ticket  |  GET /health
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from config import HOST, PORT, logger
from investigator import analyze_ticket_logic

# ---------------------------------------------------------------------------
# App initialisation
# ---------------------------------------------------------------------------

app = FastAPI(
    title="QueueStorm Investigator",
    description=(
        "AI/API copilot that classifies, investigates, and routes customer "
        "support tickets for a digital finance platform."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# Custom exception handlers — never leak stack traces or secrets
# ---------------------------------------------------------------------------

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return a clean 422 on Pydantic validation errors."""
    errors = []
    for error in exc.errors():
        errors.append({"field": " -> ".join(str(loc) for loc in error["loc"]), "message": error["msg"]})
    return JSONResponse(status_code=422, content={"error": "Validation failed", "details": errors})


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Catch-all — return 500 without exposing internals."""
    logger.error(f"Unhandled exception: {type(exc).__name__}", exc_info=False)
    return JSONResponse(
        status_code=500,
        content={"error": "An internal error occurred. Please try again later."},
    )


# ---------------------------------------------------------------------------
# Request / Response Pydantic Models
# ---------------------------------------------------------------------------

class TransactionHistoryEntry(BaseModel):
    """A single entry in a customer's recent transaction history."""
    transaction_id: str = Field(..., description="Unique transaction identifier")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    type: str = Field(..., description="One of: transfer, payment, cash_in, cash_out, settlement, refund")
    amount: float = Field(..., description="Amount in BDT")
    counterparty: str = Field(..., description="Recipient phone, merchant ID, or agent ID")
    status: str = Field(..., description="One of: completed, failed, pending, reversed")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        allowed = {"transfer", "payment", "cash_in", "cash_out", "settlement", "refund"}
        if v not in allowed:
            raise ValueError(f"type must be one of {sorted(allowed)}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {"completed", "failed", "pending", "reversed"}
        if v not in allowed:
            raise ValueError(f"status must be one of {sorted(allowed)}")
        return v


class TicketRequest(BaseModel):
    """Inbound ticket payload for POST /analyze-ticket."""
    ticket_id: str = Field(..., description="Unique ticket identifier")
    complaint: str = Field(..., description="Customer complaint text (en / bn / mixed)")
    language: Optional[str] = Field(None, description="One of: en, bn, mixed")
    channel: Optional[str] = Field(None, description="One of: in_app_chat, call_center, email, merchant_portal, field_agent")
    user_type: Optional[str] = Field(None, description="One of: customer, merchant, agent, unknown")
    campaign_context: Optional[str] = Field(None, description="Campaign identifier provided by the harness")
    transaction_history: Optional[List[TransactionHistoryEntry]] = Field(
        default_factory=list,
        description="List of recent transactions (typically 2–5 entries)",
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional simulated context")

    @field_validator("complaint")
    @classmethod
    def complaint_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("complaint must not be empty")
        return v.strip()

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in {"en", "bn", "mixed"}:
            raise ValueError("language must be one of: en, bn, mixed")
        return v

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, v: Optional[str]) -> Optional[str]:
        allowed = {"in_app_chat", "call_center", "email", "merchant_portal", "field_agent"}
        if v is not None and v not in allowed:
            raise ValueError(f"channel must be one of {sorted(allowed)}")
        return v

    @field_validator("user_type")
    @classmethod
    def validate_user_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in {"customer", "merchant", "agent", "unknown"}:
            raise ValueError("user_type must be one of: customer, merchant, agent, unknown")
        return v


class TicketResponse(BaseModel):
    """Structured analysis response for POST /analyze-ticket."""
    ticket_id: str
    relevant_transaction_id: Optional[str]
    evidence_verdict: str  # consistent | inconsistent | insufficient_data
    case_type: str
    severity: str          # low | medium | high | critical
    department: str
    agent_summary: str
    recommended_next_action: str
    customer_reply: str
    human_review_required: bool
    confidence: Optional[float] = None
    reason_codes: Optional[List[str]] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", summary="Health check", tags=["System"])
def health_check():
    """Returns {\"status\": \"ok\"} within 60 s of service start."""
    return {"status": "ok"}


@app.post(
    "/analyze-ticket",
    response_model=TicketResponse,
    summary="Analyze a support ticket",
    tags=["Tickets"],
    status_code=200,
)
def analyze_ticket(request: TicketRequest):
    """
    Accept one ticket, analyze complaint + transaction history,
    and return a structured routing and investigation response.
    """
    try:
        # Build a plain dict so the investigator module is framework-agnostic
        request_dict = {
            "ticket_id": request.ticket_id,
            "complaint": request.complaint,
            "language": request.language,
            "channel": request.channel,
            "user_type": request.user_type,
            "campaign_context": request.campaign_context,
            "transaction_history": (
                [tx.model_dump() for tx in request.transaction_history]
                if request.transaction_history
                else []
            ),
            "metadata": request.metadata or {},
        }

        result = analyze_ticket_logic(request_dict)

        logger.info(
            "Processed ticket=%s case=%s verdict=%s dept=%s severity=%s review=%s conf=%.2f",
            result["ticket_id"],
            result["case_type"],
            result["evidence_verdict"],
            result["department"],
            result["severity"],
            result["human_review_required"],
            result.get("confidence", 0.0),
        )

        return TicketResponse(**result)

    except HTTPException:
        raise  # Let FastAPI handle these as-is
    except ValueError as ve:
        logger.warning("Semantic validation error for ticket %s: %s", request.ticket_id, ve)
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as exc:
        logger.error(
            "Failed to process ticket %s: %s",
            request.ticket_id,
            type(exc).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="An error occurred while analyzing the ticket.",
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host=HOST, port=PORT, reload=False)
