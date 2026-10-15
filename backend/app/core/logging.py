"""
TruthGuard Structured & Privacy-Preserving Logger.

Redacts sensitive entities, tokens, and credentials.
Tracks execution latency, module stages, and structured request contexts.
"""

from __future__ import annotations
import logging
import re
import sys
import time
from typing import Any, Dict, Optional


SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|bearer|token|secret|password)[\"'\s:=]+([a-zA-Z0-9_\-\.]{8,})"),
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"tvly-[a-zA-Z0-9]{20,}"),
]


def redact_secrets(text: str) -> str:
    """Scrub sensitive credentials from logging outputs."""
    if not isinstance(text, str):
        return text
    sanitized = text
    for pattern in SECRET_PATTERNS:
        if pattern.groups >= 1:
            sanitized = pattern.sub(r"\1=***REDACTED***", sanitized)
        else:
            sanitized = pattern.sub("***REDACTED***", sanitized)
    return sanitized


class PrivacyFilter(logging.Filter):
    """Logging filter that cleanses records of sensitive patterns."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_secrets(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: redact_secrets(str(v)) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(redact_secrets(str(arg)) for arg in record.args)
        return True


def setup_logger(name: str = "truthguard") -> logging.Logger:
    """Initialize and configure a standard application logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        handler.addFilter(PrivacyFilter())
        logger.addHandler(handler)
        logger.propagate = False
    return logger


logger = setup_logger()


class ModuleTimer:
    """Context manager to measure module execution time cleanly."""

    def __init__(self, module_name: str, request_id: Optional[str] = None):
        self.module_name = module_name
        self.request_id = request_id or "local"
        self.start_time: float = 0.0
        self.elapsed_ms: float = 0.0

    def __enter__(self) -> "ModuleTimer":
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.elapsed_ms = (time.perf_counter() - self.start_time) * 1000.0
        status = "SUCCESS" if exc_type is None else f"FAILED: {exc_val}"
        logger.info(
            f"req_id={self.request_id} module={self.module_name} "
            f"latency_ms={self.elapsed_ms:.2f} status={status}"
        )
