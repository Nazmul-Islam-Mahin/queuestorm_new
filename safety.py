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

# Safe negation phrases — text that WARNS customers NOT to share credentials
# (these are always allowed and expected in our templates)
_SAFE_NEGATIONS = re.compile(
    r"\b(do\s+not|don'?t|never|please\s+do\s+not)\s+(share|give|send|provide|enter|tell)\b"
    r"|করবেন\s+না|শেয়ার\s+করবেন\s+না|বলবেন\s+না|দেবেন\s+না",
    re.IGNORECASE,
)

# Asking / requesting credential patterns — dangerous requests (without a "don't" prefix)
_CREDENTIAL_REQUESTS = re.compile(
    r"\b(please\s+)?(share|send|give|provide|enter|tell|type|write)\s+(your|me\s+your|us\s+your)\s+"
    r"(otp|pin|password|card\s*number|cvv)\b"
    r"|\b(otp|pin|password)\s+(se|ko)\s+(share|bhejo|batao)\b",  # Hinglish variants
    re.IGNORECASE,
)

# Unauthorized refund / reversal promises
_REFUND_PROMISES = re.compile(
    r"\b(we\s+will|we'll|i\s+will|i'll)\s+(refund|reverse|credit|unblock|recover\s+your)\b"
    r"|\b(refund|reversal|unblock)\s+(is|has\s+been|was)\s+(initiated|processed|completed|done|guaranteed|approved)\b"
    r"|\bwe\s+will\s+return\s+your\s+money\b"
    r"|\bআমরা\s+(টাকা|অর্থ)\s+ফেরত\s+দেব\b"
    r"|\bটাকা\s+ফেরত\s+দেওয়া\s+হবে\b",
    re.IGNORECASE,
)

# Suspicious third-party redirects
_THIRD_PARTY = re.compile(
    r"\bcontact\s+(via\s+)?(whatsapp|telegram|facebook|imo|viber|messenger)\b"
    r"|\bcall\s+this\s+number\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def is_reply_safe(text: str) -> bool:
    """
    Return True if `text` does not violate any safety rules.

    Logic for credentials:
      - If a credential TERM is present AND there is a safe negation near it → OK (warning style)
      - If a credential TERM is present AND an active REQUEST pattern is found → UNSAFE
    """
    # Rule 1: Credential requests
    if _CREDENTIAL_TERMS.search(text):
        # Check whether this is a "do not share…" style warning (safe)
        has_safe_negation = bool(_SAFE_NEGATIONS.search(text))
        has_active_request = bool(_CREDENTIAL_REQUESTS.search(text))

        # If there IS an active credential request in addition to (or instead of) a warning → unsafe
        if has_active_request:
            return False
        # If credentials are mentioned but only in a negation context → safe (our templates do this)
        if not has_safe_negation:
            # Credential term present with neither negation nor request — borderline; be conservative
            return False

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
