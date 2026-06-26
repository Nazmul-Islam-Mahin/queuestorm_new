"""
investigator.py — Core evidence-reasoning and ticket analysis engine.

Pipeline:
  1. Language detection (en / bn / mixed)
  2. Complaint classification via prioritised regex rules
  3. Transaction scoring + duplicate detection
  4. Evidence verdict (consistent | inconsistent | insufficient_data)
  5. Severity / department / human-review mapping
  6. Template-based response generation
  7. Safety sanitisation (final pass)
"""

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from config import logger
from safety import sanitize_response_text
from templates import get_filled_templates

# ---------------------------------------------------------------------------
# Bangla numerals → ASCII digits
# ---------------------------------------------------------------------------

_BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


def normalize_text(text: str) -> str:
    """Lowercase + translate Bangla digits to ASCII."""
    return text.translate(_BN_DIGITS).lower()


# ---------------------------------------------------------------------------
# Amount extraction
# ---------------------------------------------------------------------------

_AMOUNT_PATTERNS = [
    # "5000 taka", "tk 500", "500 BDT", "৫০০০ টাকা"
    re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(?:taka|tk|bdt|টাকা)", re.IGNORECASE),
    re.compile(r"(?:taka|tk|bdt|টাকা)\s*(\d[\d,]*(?:\.\d+)?)", re.IGNORECASE),
    # Plain number fallback (3–7 digits = plausible BDT amount)
    re.compile(r"\b(\d{2,7})\b"),
]


def extract_amounts(text: str) -> List[float]:
    """Return all plausible BDT amounts mentioned in text (deduplicated, sorted desc)."""
    norm = normalize_text(text).replace(",", "")
    seen: set = set()
    results: List[float] = []
    for pat in _AMOUNT_PATTERNS:
        for m in pat.finditer(norm):
            raw = m.group(1).replace(",", "")
            try:
                val = float(raw)
                if val not in seen:
                    seen.add(val)
                    results.append(val)
            except ValueError:
                pass
    return sorted(results, reverse=True)


# ---------------------------------------------------------------------------
# Timestamp parsing
# ---------------------------------------------------------------------------


def parse_ts(ts_str: str) -> datetime:
    """Parse ISO-8601 timestamp; return datetime.min on failure."""
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except Exception:
        logger.debug("Cannot parse timestamp '%s'", ts_str)
        return datetime.min.replace(tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Classification — ordered by priority (most-specific first)
# ---------------------------------------------------------------------------

# Each entry: (case_type, list_of_regex_patterns)
# Patterns are OR-ed together.  First matching group wins.
_CLASSIFY_RULES: List[Tuple[str, List[str]]] = [
    # 1. Phishing / social engineering — MUST be first (highest risk)
    ("phishing_or_social_engineering", [
        r"\bsomeone\s+(called|sms|messaged|texted)\b",
        r"\b(suspicious|fake|impersonat)\b",
        r"\b(asked?|ask(ing)?)\s+(me\s+)?for\s+(my\s+)?(otp|pin|password|card\s*number)",
        r"\b(otp|pin|password|card\s*number|cvv)\s+(was\s+)?(asked?|requested?|demand)",
        r"\b(scam|phish|hack(ed)?|social\s+engineer)\b",
        r"ওটিপি|পিন\s*নম্বর|পাসওয়ার্ড|কার্ড\s*নম্বর",
        # Someone asked for OTP even without "scam" keyword
        r"\b(otp|pin)\b.{0,50}\b(asked?|request|demand|share)\b",
        r"\b(asked?|request|demand|share)\b.{0,50}\b(otp|pin)\b",
    ]),
    # 2. Duplicate payment
    ("duplicate_payment", [
        r"\b(twice|double|two\s*times|duplicate\s*payment|charged\s*twice|deducted\s*twice)\b",
        r"দুইবার|দুই\s*বার|ডাবল\s*চার্জ",
    ]),
    # 3. Agent cash-in issue
    ("agent_cash_in_issue", [
        r"\bcash[\s\-]?in\b.{0,60}\b(agent|not\s+reflect|balance|পাইনি)\b",
        r"\bagent\b.{0,60}\bcash[\s\-]?in\b",
        r"\b(ক্যাশ\s*ইন|ক্যাশইন)\b",
        r"\bএজেন্ট\b.{0,60}\b(টাকা|ব্যালেন্স|আসেনি)\b",
    ]),
    # 4. Merchant settlement delay
    ("merchant_settlement_delay", [
        r"\b(settlement|settle)\b.{0,60}\b(delay|not\s+received|pending|missing)\b",
        r"\b(merchant)\b.{0,60}\b(settlement|settle|account)\b",
        r"সেটেলমেন্ট.{0,60}(পাইনি|আসেনি|দেরি)",
    ]),
    # 5. Wrong transfer
    ("wrong_transfer", [
        r"\bwrong\s+(number|recipient|person|account|transfer)\b",
        r"\b(sent?|send|transfer(red)?|পাঠিয়ে)\b.{0,60}\bwrong\b",
        r"\bwrong\b.{0,60}\b(sent?|send|transfer(red)?)\b",
        r"\b(mistake|accidental(ly)?)\b.{0,60}\b(send|sent|transfer|number)\b",
        r"ভুল\s*(নাম্বার|নম্বর|একাউন্ট|ব্যক্তি|জায়গায়|ট্রান্সফার)",
        # Implicit wrong transfer: sent to someone + they didn't receive
        r"\bsent?\b.{0,80}\b(didn'?t|did\s+not|hasn'?t|has\s+not)\s+(get|receive|got)\b",
        r"\b(he|she|they|brother|sister|friend|family)\b.{0,40}\b(didn'?t|did\s+not|hasn'?t|has\s+not)\s+(get|receive|got)\b",
    ]),
    # 6. Payment failed / balance deducted
    ("payment_failed", [
        r"\b(payment|transaction|recharge|bill\s*pay)\b.{0,60}\b(fail(ed)?|unsuccessful|stuck|declined)\b",
        r"\b(fail(ed)?|unsuccessful)\b.{0,60}\b(payment|transaction)\b",
        r"\b(balance|amount|money)\b.{0,40}\b(deducted?|cut|missing)\b",
        r"\bpayment\s+fail\b",
        r"\bпеімент|পেমেন্ট\b.{0,40}\bফেইল|ব্যর্থ\b",
        r"\bকেটে\s+(নেওয়া|গেছে|গেল)\b",
    ]),
    # 7. Refund request
    ("refund_request", [
        r"\b(refund|money\s*back|return\s*(my\s*)?money|chargeback|want\s+back)\b",
        r"রিফান্ড|টাকা\s+ফেরত",
    ]),
]

_COMPILED_RULES: List[Tuple[str, re.Pattern]] = [
    (ct, re.compile("|".join(patterns), re.IGNORECASE | re.DOTALL))
    for ct, patterns in _CLASSIFY_RULES
]

# Prompt-injection guard: if the complaint itself contains instruction overrides
_INJECTION_PATTERNS = re.compile(
    r"(ignore\s+(?:all\s+)?(?:previous|above)?\s*instructions?|"
    r"disregard\s+(?:all\s+)?(?:your|previous|above)?\s*instructions?|"
    r"you\s+are\s+now\s+|"
    r"new\s+instructions?\s*:|"
    r"system\s+prompt|"
    r"pretend\s+(?:you\s+are|to\s+be)|"
    r"act\s+as\s+(?:a\s+)?(?:different|new)|"
    r"override\s+(?:your\s+)?(?:rules?|instructions?))",
    re.IGNORECASE,
)


def classify_complaint(
    complaint: str,
    user_type: Optional[str] = None,
) -> Tuple[str, bool]:
    """
    Classify complaint into a case_type using prioritised regex rules.

    Returns:
        (case_type, injection_detected)

    When an injection attempt is detected, the caller MUST skip LLM enrichment
    and route directly to template-based response.
    """
    injection_detected = bool(_INJECTION_PATTERNS.search(complaint))
    if injection_detected:
        logger.warning("Possible prompt-injection detected — LLM enrichment will be skipped.")

    norm = normalize_text(complaint)

    # Merchant user_type strongly suggests settlement delay when no other signal fires
    merchant_hint = user_type == "merchant"

    for case_type, pattern in _COMPILED_RULES:
        if pattern.search(norm):
            return case_type, injection_detected

    if merchant_hint:
        return "merchant_settlement_delay", injection_detected

    return "other", injection_detected


# ---------------------------------------------------------------------------
# Transaction matching
# ---------------------------------------------------------------------------


def _amount_close(a: float, b: float, tolerance: float = 0.01) -> bool:
    return abs(a - b) <= tolerance


def _tx_type_keywords() -> Dict[str, List[str]]:
    return {
        "transfer": ["transfer", "sent", "send", "wrong", "ভুল", "পাঠিয়ে", "পাঠিয়েছি"],
        "payment": ["payment", "paid", "pay", "recharge", "bill", "merchant", "বিল", "পেমেন্ট"],
        "cash_in": ["cash in", "cash-in", "cashin", "deposit", "agent", "ক্যাশ ইন", "ক্যাশইন"],
        "cash_out": ["cash out", "cash-out", "cashout", "withdraw"],
        "settlement": ["settle", "settlement", "sales", "মার্চেন্ট", "সেটেলমেন্ট"],
        "refund": ["refund", "reversal", "রিফান্ড"],
    }


def _score_transaction(tx: Dict[str, Any], complaint_norm: str, amounts: List[float]) -> int:
    """Score a single transaction against the normalised complaint."""
    score = 0
    tx_amount: float = tx.get("amount", 0)
    tx_type: str = tx.get("type", "")
    tx_status: str = tx.get("status", "")

    # Amount match (+10), mismatch penalty (−3, not −5, to avoid wiping out type matches)
    if amounts:
        if any(_amount_close(a, tx_amount) for a in amounts):
            score += 10
        else:
            score -= 3

    # Transaction type keyword match
    type_kws = _tx_type_keywords()
    if any(kw in complaint_norm for kw in type_kws.get(tx_type, [])):
        score += 5

    # Status hint match
    status_hints: Dict[str, List[str]] = {
        "failed":   ["failed", "fail", "deducted", "cut", "ফেইল", "কেটে"],
        "pending":  ["pending", "delay", "waiting", "not received", "পেন্ডিং", "দেরি", "আসেনি", "পাইনি"],
        "reversed": ["reversed", "refunded", "রিভার্স"],
    }
    for status_key, kws in status_hints.items():
        if tx_status == status_key and any(kw in complaint_norm for kw in kws):
            score += 2
            break

    return score


def _detect_duplicate(
    transaction_history: List[Dict[str, Any]],
    amounts: List[float],
    is_dup_claim: bool,
    case_type: str,
) -> Optional[Tuple[Dict[str, Any], str]]:
    """
    Detect a duplicate payment pattern using multi-signal scoring.

    Requires ALL of:
      1. Complaint explicitly mentions duplication (is_dup_claim=True or case_type=duplicate_payment)
      2. Two completed transactions with identical (amount, type, counterparty)
      3. Amount in complaint matches the transaction amount
      4. Time gap is suspiciously tight (≤ 2 hours; recurring bills are often same-day but hours apart)

    Returns (second_tx, "consistent") if found, else None.
    """
    # Corroboration from complaint is REQUIRED — pure transaction shape is not enough.
    # Two rent payments on the same day are NOT duplicates unless the customer says so.
    if not (is_dup_claim or case_type == "duplicate_payment"):
        return None

    completed = [tx for tx in transaction_history if tx.get("status") == "completed"]
    if len(completed) < 2:
        return None

    # Group by (amount, type, counterparty) — all three must match
    groups: Dict[tuple, List[Dict[str, Any]]] = {}
    for tx in completed:
        key = (tx.get("amount"), tx.get("type"), tx.get("counterparty"))
        groups.setdefault(key, []).append(tx)

    for key, txs in groups.items():
        if len(txs) < 2:
            continue

        # Amount mentioned in complaint must plausibly match this group's amount
        if amounts and not any(_amount_close(a, key[0]) for a in amounts):
            continue

        txs_sorted = sorted(txs, key=lambda t: parse_ts(t.get("timestamp", "")))
        for i in range(len(txs_sorted) - 1):
            t1 = parse_ts(txs_sorted[i].get("timestamp", ""))
            t2 = parse_ts(txs_sorted[i + 1].get("timestamp", ""))
            delta_secs = (t2 - t1).total_seconds()
            # Tight time window (≤ 2 hours) strongly suggests duplicate vs. recurring payment
            if delta_secs <= 7200:
                return txs_sorted[i + 1], "consistent"
    return None


def _determine_verdict(
    tx: Dict[str, Any],
    complaint_norm: str,
    case_type: str,
    transaction_history: List[Dict[str, Any]],
) -> str:
    """Determine evidence verdict for a matched transaction."""
    tx_status = tx.get("status", "")
    tx_type = tx.get("type", "")
    tx_counterparty = tx.get("counterparty", "")
    tx_ts = parse_ts(tx.get("timestamp", ""))

    # --- Wrong transfer: established recipient pattern ---
    if case_type == "wrong_transfer":
        prior_same_cp = [
            other for other in transaction_history
            if other.get("transaction_id") != tx.get("transaction_id")
            and other.get("counterparty") == tx_counterparty
            and other.get("status") == "completed"
            and other.get("type") in ("transfer", "payment")
            and parse_ts(other.get("timestamp", "")) < tx_ts
        ]
        if len(prior_same_cp) >= 2:
            return "inconsistent"

    # --- Payment failed ---
    if case_type == "payment_failed":
        if tx_status == "failed":
            return "consistent"
        if tx_status == "completed":
            # Complaint says failed/deducted but tx is completed
            if re.search(r"\b(fail(ed)?|unsuccessful)\b", complaint_norm) and "deducted" not in complaint_norm:
                return "inconsistent"
            # Complaint says deducted — payment succeeded on our side; could still be a legit concern
            return "consistent"

    # --- Merchant settlement delay ---
    if case_type == "merchant_settlement_delay" and tx_type == "settlement":
        if tx_status == "pending":
            return "consistent"
        if tx_status == "completed":
            return "inconsistent"

    # --- Agent cash-in ---
    if case_type == "agent_cash_in_issue" and tx_type == "cash_in":
        if tx_status in ("pending", "failed"):
            return "consistent"
        if tx_status == "completed":
            return "inconsistent"

    # --- Default: derive verdict from transaction status vs. complaint expectation ---
    # A completed/reversed tx corroborates that something happened (claim is grounded)
    if tx_status in ("completed", "reversed"):
        return "consistent"
    # A failed/pending tx when the complaint mentions failure/pending → consistent
    # A failed/pending tx when the complaint does NOT mention failure (e.g. claims success) → inconsistent
    if tx_status in ("failed", "pending"):
        complaint_mentions_failure = bool(re.search(
            r"\b(fail(ed)?|unsuccessful|deducted?|cut|not\s+received|pending|stuck)\b"
            r"|ফেইল|কেটে|আসেনি|পাইনি|পেন্ডিং",
            complaint_norm,
        ))
        return "consistent" if complaint_mentions_failure else "inconsistent"

    return "insufficient_data"


def find_relevant_transaction(
    complaint: str,
    transaction_history: List[Dict[str, Any]],
    case_type: str,
) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Match complaint to the most relevant transaction and determine evidence verdict.

    Returns: (matched_tx_or_None, evidence_verdict)
    """
    if not transaction_history:
        return None, "insufficient_data"

    # "other" case type: vague complaint — never pin to a specific transaction
    if case_type == "other":
        return None, "insufficient_data"

    complaint_norm = normalize_text(complaint)
    amounts = extract_amounts(complaint_norm)

    # 1. Duplicate detection takes priority
    is_dup_claim = bool(re.search(
        r"\b(twice|double|two\s*times|duplicate|charged\s*twice)\b|দুইবার|দুই\s*বার|ডাবল",
        complaint_norm,
    ))
    dup_result = _detect_duplicate(transaction_history, amounts, is_dup_claim, case_type)
    if dup_result:
        return dup_result

    # 2. Score all transactions
    scored = [(
        _score_transaction(tx, complaint_norm, amounts),
        idx,   # stable tiebreak by index
        tx,
    ) for idx, tx in enumerate(transaction_history)]

    positives = [(s, i, tx) for s, i, tx in scored if s > 0]

    if not positives:
        return None, "insufficient_data"

    positives.sort(key=lambda x: (x[0], x[1]), reverse=True)
    top_score = positives[0][0]
    winners = [tx for s, _, tx in positives if s == top_score]

    if len(winners) == 1:
        best_tx = winners[0]
        verdict = _determine_verdict(best_tx, complaint_norm, case_type, transaction_history)
        return best_tx, verdict
    else:
        # Multiple equally-likely transactions → ambiguous
        return None, "insufficient_data"


# ---------------------------------------------------------------------------
# Severity / department / human-review mapping
# ---------------------------------------------------------------------------


# Case types where the high-value threshold does NOT automatically trigger human review
# (they have their own authoritative routing rules that override the amount heuristic)
_AMOUNT_THRESHOLD_EXEMPT = frozenset({
    "merchant_settlement_delay",  # High-value settlements are routine for merchants
    "phishing_or_social_engineering",  # Already always critical + human review
})


def _resolve_routing(
    case_type: str,
    verdict: str,
    amount: Optional[float],
) -> Tuple[str, str, bool]:
    """Return (severity, department, human_review_required)."""

    # Phishing ALWAYS forces critical + human_review regardless of verdict or amount.
    # This must be a hard rule, not an emergent property of the mapping.
    if case_type == "phishing_or_social_engineering":
        return "critical", "fraud_risk", True

    mapping: Dict[str, Dict[str, Any]] = {
        "wrong_transfer": {
            "severity": "high" if verdict == "consistent" else "medium",
            "department": "dispute_resolution",
            "human_review": verdict in ("consistent", "inconsistent"),
        },
        "payment_failed": {
            "severity": "high",
            "department": "payments_ops",
            # Inconsistent evidence (tx shows completed despite failure claim) needs human eyes
            "human_review": verdict == "inconsistent",
        },
        "refund_request": {
            "severity": "medium" if verdict == "inconsistent" else "low",
            "department": "dispute_resolution" if verdict == "inconsistent" else "customer_support",
            "human_review": verdict == "inconsistent",
        },
        "duplicate_payment": {
            "severity": "high",
            "department": "payments_ops",
            "human_review": True,
        },
        "merchant_settlement_delay": {
            "severity": "medium",
            "department": "merchant_operations",
            # Only needs review when data contradicts merchant claim
            "human_review": verdict == "inconsistent",
        },
        "agent_cash_in_issue": {
            "severity": "high",
            "department": "agent_operations",
            "human_review": True,
        },
        "other": {
            "severity": "low",
            "department": "customer_support",
            "human_review": False,
        },
    }

    row = mapping.get(case_type, mapping["other"])
    severity: str = row["severity"]
    department: str = row["department"]
    human_review: bool = row["human_review"]

    # High-value transactions (≥ 10 000 BDT) escalate to human review,
    # EXCEPT for case types with their own authoritative routing (settlement, phishing).
    if (
        amount is not None
        and amount >= 10_000
        and case_type not in _AMOUNT_THRESHOLD_EXEMPT
    ):
        human_review = True

    # Inconsistent evidence always warrants a second pair of eyes
    if verdict == "inconsistent":
        human_review = True

    return severity, department, human_review


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------


def _compute_confidence(verdict: str, case_type: str, tx_matched: bool) -> float:
    base = {
        "consistent": 0.90,
        "inconsistent": 0.80,
        "insufficient_data": 0.60,
    }.get(verdict, 0.70)

    # Phishing cases are high-confidence even without a matching tx
    if case_type == "phishing_or_social_engineering":
        base = max(base, 0.92)

    # Small bonus for having a matched transaction
    if tx_matched and verdict != "insufficient_data":
        base = min(1.0, base + 0.05)

    return round(base, 2)


# ---------------------------------------------------------------------------
# Reason codes
# ---------------------------------------------------------------------------


# Clean, human-readable reason code vocabulary (judged in Stage 2 manual review)
_REASON_CODE_MAP: Dict[str, str] = {
    "phishing_or_social_engineering": "social_engineering_detected",
    "wrong_transfer": "wrong_transfer_reported",
    "payment_failed": "payment_failure_reported",
    "duplicate_payment": "duplicate_payment_reported",
    "merchant_settlement_delay": "settlement_delay_reported",
    "agent_cash_in_issue": "cash_in_issue_reported",
    "refund_request": "refund_requested",
    "other": "unclassified_complaint",
}

_VERDICT_CODE_MAP: Dict[str, str] = {
    "consistent": "evidence_supports_claim",
    "inconsistent": "evidence_contradicts_claim",
    "insufficient_data": "insufficient_evidence",
}

_INCONSISTENT_DETAIL_MAP: Dict[str, str] = {
    "wrong_transfer": "established_recipient_pattern",
    "payment_failed": "transaction_shows_completed",
    "agent_cash_in_issue": "cash_in_shows_completed",
    "merchant_settlement_delay": "settlement_shows_completed",
}


def _build_reason_codes(
    case_type: str,
    verdict: str,
    tx_matched: bool,
    injection_detected: bool = False,
) -> List[str]:
    """Build clean, human-readable reason codes for Stage 2 review."""
    codes: List[str] = [_REASON_CODE_MAP.get(case_type, case_type)]

    if tx_matched:
        codes.append("transaction_match")
    else:
        codes.append("no_transaction_match")

    codes.append(_VERDICT_CODE_MAP.get(verdict, f"evidence_{verdict}"))

    if verdict == "inconsistent" and case_type in _INCONSISTENT_DETAIL_MAP:
        codes.append(_INCONSISTENT_DETAIL_MAP[case_type])

    if injection_detected:
        codes.append("injection_attempt_detected")

    return codes


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def analyze_ticket_logic(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Full pipeline: classify → match → verdict → route → generate responses.

    Args:
        request_data: Plain dict matching the API request schema.

    Returns:
        Plain dict matching the API response schema.
    """
    ticket_id: str = request_data.get("ticket_id", "UNKNOWN")
    complaint: str = request_data.get("complaint", "")
    language: Optional[str] = request_data.get("language")
    user_type: Optional[str] = request_data.get("user_type")
    history: List[Dict[str, Any]] = request_data.get("transaction_history") or []

    # 1. Language detection
    is_bn = language == "bn" or bool(re.search(r"[\u0980-\u09ff]", complaint))

    # 2. Classify — returns (case_type, injection_detected)
    case_type, injection_detected = classify_complaint(complaint, user_type)

    # 3. Transaction matching
    relevant_tx, verdict = find_relevant_transaction(complaint, history, case_type)

    # Refine case_type based on what we actually matched (without overriding a phishing call)
    relevant_tx_id: Optional[str] = None
    tx_amount: Optional[float] = None
    tx_counterparty: Optional[str] = None

    if relevant_tx:
        relevant_tx_id = relevant_tx.get("transaction_id")
        tx_amount = relevant_tx.get("amount")
        tx_counterparty = relevant_tx.get("counterparty")
        matched_type = relevant_tx.get("type")

        # Upgrade case_type based on matched transaction type when safe to do so
        if (
            case_type not in ("phishing_or_social_engineering",)
            and matched_type == "settlement"
            and case_type != "merchant_settlement_delay"
        ):
            case_type = "merchant_settlement_delay"

    # 4. Routing
    severity, department, human_review = _resolve_routing(case_type, verdict, tx_amount)

    # 5. Confidence & reason codes
    confidence = _compute_confidence(verdict, case_type, relevant_tx is not None)
    reason_codes = _build_reason_codes(
        case_type, verdict, relevant_tx is not None, injection_detected
    )

    # 6. Template-based response generation (always used as the base)
    filled = get_filled_templates(
        case_type=case_type,
        verdict=verdict,
        txn_id=relevant_tx_id,
        amount=f"{tx_amount:.0f}" if tx_amount is not None else None,
        counterparty=str(tx_counterparty) if tx_counterparty is not None else None,
        is_bangla=is_bn,
    )

    # 7. Optionally enrich with LLM — SKIPPED when injection is detected
    # The injection_detected flag prevents adversarial complaint text from
    # influencing LLM output; we stay with the deterministic template.
    agent_summary = filled["agent_summary"]
    customer_reply = filled["customer_reply"]

    if not injection_detected:
        try:
            from llm import enrich_with_llm
            agent_summary, customer_reply = enrich_with_llm(
                complaint=complaint,
                case_type=case_type,
                evidence_verdict=verdict,
                department=department,
                relevant_txn_id=relevant_tx_id,
                is_bangla=is_bn,
                fallback_summary=filled["agent_summary"],
                fallback_reply=filled["customer_reply"],
            )
        except ImportError:
            pass  # LLM module not available; template already set

    # 8. Final safety sanitisation — always applied, cannot be bypassed
    safe_reply = sanitize_response_text(customer_reply, is_bangla=is_bn)

    return {
        "ticket_id": ticket_id,
        "relevant_transaction_id": relevant_tx_id,
        "evidence_verdict": verdict,
        "case_type": case_type,
        "severity": severity,
        "department": department,
        "agent_summary": agent_summary,
        "recommended_next_action": filled["recommended_next_action"],
        "customer_reply": safe_reply,
        "human_review_required": human_review,
        "confidence": confidence,
        "reason_codes": reason_codes,
    }
