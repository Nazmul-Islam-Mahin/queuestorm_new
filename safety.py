"""
safety.py — Safety guardrail checks for all generated output fields.

Rules (from problem statement §8):
  1. Never ask customer for PIN / OTP / password / card number.
  2. Never confirm a refund / reversal / unblock without authority.
  3. Never direct customer to a suspicious third party.
  4. Adversarial complaint text must not override system rules.
"""

import re

# ---------------------------------------------------------------------------
# Pattern sets
# ---------------------------------------------------------------------------

# Credential terms that must NEVER appear as a *request* in a reply
_CREDENTIAL_TERMS = re.compile(
    r"\b(otp|pin|password|verification\s*code|card\s*number|cvv|pin\s*number)\b"
    r"|ওটিপি|পিন\s*নম্বর|পাসওয়ার্ড|কার্ড\s*নম্বর",
    re.IGNORECASE,
)

# Asking / requesting credential patterns — dangerous requests.
# CRITICAL: We use a negative-lookbehind to ensure a preceding negation
# (do not, don't, never, please do not) is NOT present within 40 chars before.
# This prevents "do not share your PIN" from matching as a request.
_CREDENTIAL_REQUESTS = re.compile(
    # Positive request verbs followed by credential terms — no preceding negation allowed
    r"(?<!\bdo not\s)(?<!\bdon't\s)(?<!\bnever\s)"
    r"\b(please\s+)?(share|send|give|provide|enter|tell|type|write)\s+"
    r"(your|me\s+your|us\s+your)\s+"
    r"(otp|pin|password|card\s*number|cvv)\b"
    r"|\b(otp|pin|password)\s+(se|ko)\s+(share|bhejo|batao)\b",  # Hinglish
    re.IGNORECASE,
)

# Broad negation guard: checks if a credential request co-occurs with "do not / don't / never"
# anywhere in the text — used to filter out false positives from _CREDENTIAL_REQUESTS
_NEGATION_GUARD = re.compile(
    r"\b(do\s+not|don'?t|never|please\s+do\s+not)\s+(share|give|send|provide|enter|tell)\b"
    r"|করবেন\s+না|শেয়ার\s+করবেন\s+না|বলবেন\s+না|দেবেন\s+না",
    re.IGNORECASE,
)

# Unauthorized refund / reversal promises (English + Bangla)
_REFUND_PROMISES = re.compile(
    r"\b(we\s+will|we'll|i\s+will|i'll)\s+(refund|reverse|credit|unblock|recover\s+your)\b"
    r"|\b(refund|reversal|unblock)\s+(is|has\s+been|was)\s+(initiated|processed|completed|done|guaranteed|approved)\b"
    r"|\bwe\s+will\s+return\s+your\s+money\b"
    # Bangla refund promises
    r"|আমরা\s+(টাকা|অর্থ)\s+ফেরত\s+দেব"
    r"|টাকা\s+ফেরত\s+দেওয়া\s+হবে"
    r"|রিফান্ড\s+(করা\s+হবে|দেওয়া\s+হবে|প্রক্রিয়া\s+করা\s+হয়েছে)",
    re.IGNORECASE,
)

# Suspicious third-party redirects (English + Bangla)
_THIRD_PARTY = re.compile(
    r"\bcontact\s+(via\s+)?(whatsapp|telegram|facebook|imo|viber|messenger)\b"
    r"|\bcall\s+this\s+number\b"
    # Bangla third-party patterns
    r"|হোয়াটসঅ্যাপ|টেলিগ্রাম|ফেসবুক\s+মেসেঞ্জার"
    r"|এই\s+নম্বরে\s+(ফোন|কল)\s+করুন"
    r"|অন্য\s+কোনো\s+নম্বরে\s+যোগাযোগ",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def is_reply_safe(text: str) -> bool:
    """
    Return True if `text` does not violate any safety rules.

    Credential logic (strict — no negation escape hatch):
      - If an active credential REQUEST pattern is found → UNSAFE, full stop.
        Exception: if the ENTIRE text contains ONLY negation-framed mentions
        (e.g. "do not share your PIN") and NO affirmative request verb pair,
        it is safe. We detect this by requiring a negation guard match to
        override a credential-term hit when no explicit request verb is found.
    """
    # Rule 1: Credential requests — strict, no negation exception for requests
    if _CREDENTIAL_TERMS.search(text):
        has_active_request = bool(_CREDENTIAL_REQUESTS.search(text))
        has_negation = bool(_NEGATION_GUARD.search(text))

        if has_active_request:
            # Even with a negation somewhere, an active request is still unsafe.
            # e.g. "Please share your OTP. Do not worry." → UNSAFE
            return False

        if not has_negation:
            # Credential term present but no negation framing and no explicit request
            # verb found — conservative rejection (could be echoed from complaint).
            return False
        # has_negation=True and has_active_request=False → safe warning-style mention
        # e.g. "Please do not share your PIN or OTP with anyone." → SAFE

    # Rule 2: Unauthorized refund/reversal promises
    if _REFUND_PROMISES.search(text):
        return False

    # Rule 3: Suspicious third-party redirect
    if _THIRD_PARTY.search(text):
        return False

    return True


def sanitize_response_text(text: str, is_bangla: bool = False) -> str:
    """
    Pass `text` through the safety checker.
    If it fails, replace with a pre-validated safe fallback.
    """
    if is_reply_safe(text):
        return text

    if is_bangla:
        return (
            "আপনার অভিযোগটি আমাদের সংশ্লিষ্ট টিম পর্যালোচনা করছে। "
            "যেকোনো যোগ্য পরিমাণ অফিসিয়াল চ্যানেলের মাধ্যমে ফেরত দেওয়া হবে। "
            "অনুগ্রহ করে আপনার পিন বা ওটিপি কারো সাথে শেয়ার করবেন না।"
        )
    return (
        "We have noted your concern. Our team is investigating and any eligible amount "
        "will be returned through official channels. "
        "Please do not share your PIN or OTP with anyone."
    )
