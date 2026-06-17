"""Centralised logging setup with a redaction filter so API keys never hit logs."""
import logging
import re

from app.config import settings

# Patterns that look like secrets we must never log.
_REDACT_PATTERNS = [
    re.compile(r"sk-ant-[A-Za-z0-9-_]{6,}"),
    re.compile(r"tvly-[A-Za-z0-9-_]{6,}"),
    re.compile(r"sk-[A-Za-z0-9-_]{12,}"),
]


class RedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        redacted = msg
        for pat in _REDACT_PATTERNS:
            redacted = pat.sub("***REDACTED***", redacted)
        if redacted != msg:
            record.msg = redacted
            record.args = ()
        return True


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
    )
    handler.addFilter(RedactionFilter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.log_level.upper())


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
