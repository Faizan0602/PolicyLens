"""Best-effort redaction of obvious personal identifiers in diagnostic messages."""

import re

_PATTERNS = (
    (re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I), "[REDACTED_EMAIL]"),
    (re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", re.I), "[REDACTED_PAN]"),
    (
        re.compile(
            r"(?<!\w)(?:\+[0-9](?:[ ()-]*[0-9]){7,14}"
            r"|[6-9][0-9]{4}[ -]?[0-9]{5}"
            r"|0[0-9]{2,4}[ -]?[0-9]{6,8})(?!\w)"
        ),
        "[REDACTED_PHONE]",
    ),
    (
        re.compile(r"(?<!\w)[2-9][0-9]{3}(?:[ -]?[0-9]{4}){2}(?!\w)"),
        "[REDACTED_AADHAAR]",
    ),
)


def redact_for_logging(message: str) -> str:
    """Mask common email, phone, PAN and Aadhaar formats; this is not ID validation."""
    for pattern, replacement in _PATTERNS:
        message = pattern.sub(replacement, message)
    return message
