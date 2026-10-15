"""
TruthGuard Security & Input Sanitization.

Provides protections against:
1. Server-Side Request Forgery (SSRF) when fetching external URLs.
2. Prompt injection and jailbreak attempts within inputs or retrieved evidence.
3. Excessive input payloads.
"""

from __future__ import annotations
import ipaddress
import re
from urllib.parse import urlparse
from typing import Optional
from fastapi import HTTPException


# Reserved, local, loopback, and cloud metadata IP ranges to block
BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),      # Loopback
    ipaddress.ip_network("10.0.0.0/8"),       # Private RFC1918
    ipaddress.ip_network("172.16.0.0/12"),    # Private RFC1918
    ipaddress.ip_network("192.168.0.0/16"),   # Private RFC1918
    ipaddress.ip_network("169.254.0.0/16"),   # Link-Local / AWS/GCP/Azure Metadata
    ipaddress.ip_network("0.0.0.0/8"),        # Current network
    ipaddress.ip_network("::1/128"),          # IPv6 Loopback
    ipaddress.ip_network("fc00::/7"),         # IPv6 Private
    ipaddress.ip_network("fe80::/10"),        # IPv6 Link-Local
]

# Common injection tokens attempting to override system behavior
PROMPT_INJECTION_PATTERNS = [
    re.compile(r"(?i)ignore\s+(all\s+)?(previous|prior)\s+(instructions|directives|prompts)"),
    re.compile(r"(?i)system\s*:\s*you\s+are\s+now"),
    re.compile(r"(?i)disregard\s+(the\s+above|all\s+rules)"),
    re.compile(r"(?i)<\s*\|\s*im_start\s*\|\s*>"),
    re.compile(r"(?i)\[\s*INST\s*\]"),
]


def validate_url_safe_for_ssrf(url: str) -> bool:
    """
    Validate that an external URL does not point to internal,
    private, loopback, or cloud-provider metadata endpoints.
    """
    if not url or not isinstance(url, str):
        return False

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False

    hostname = parsed.hostname
    if not hostname:
        return False

    # Check for direct IP access
    try:
        ip = ipaddress.ip_address(hostname)
        for blocked_net in BLOCKED_IP_NETWORKS:
            if ip in blocked_net:
                return False
    except ValueError:
        # Hostname is a domain name, not a raw IP
        if hostname.lower() in ("localhost", "metadata.google.internal", "instance-data"):
            return False

    return True


def sanitize_external_evidence_text(text: str) -> str:
    """
    Sanitize retrieved evidence to prevent prompt-injection or delimiter attacks
    when passing external evidence into inference engines.
    """
    if not text:
        return ""
    # Strip dangerous LLM special control tags
    sanitized = re.sub(r"(<\|.*?\|>|\[INST\]|\[/INST\])", "", text)
    # Neutralize instruction override phrases
    for pattern in PROMPT_INJECTION_PATTERNS:
        sanitized = pattern.sub("[FILTERED_INSTRUCTION_OVERRIDE]", sanitized)
    return sanitized.strip()


def validate_input_size(text: str, max_chars: int = 20000) -> str:
    """Ensure input size remains within bounds."""
    if len(text) > max_chars:
        raise HTTPException(
            status_code=413,
            detail=f"Input payload exceeds maximum allowed size of {max_chars} characters."
        )
    return text
