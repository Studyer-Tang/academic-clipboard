from __future__ import annotations

import re

SENSITIVE_PATTERNS = (
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("authorization header", re.compile(r"(?i)\bauthorization\s*:\s*(?:bearer|basic)\s+\S+")),
    (
        "named secret",
        re.compile(
            r"(?i)\b(?:password|passwd|pwd|api[_-]?key|client[_-]?secret|access[_-]?token|refresh[_-]?token)"
            r"\s*[:=]\s*['\"]?\S{6,}"
        ),
    ),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("OpenAI-style key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("JSON Web Token", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("one-time code", re.compile(r"(?i)\b(?:otp|verification code|验证码|动态码)\D{0,12}\d{4,8}\b")),
)


def sensitive_reason(value: str) -> str:
    for reason, pattern in SENSITIVE_PATTERNS:
        if pattern.search(value):
            return reason
    return ""
