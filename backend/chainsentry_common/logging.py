"""ChainSentry Structured Logging Module.
Formats log messages with correlation IDs and redacts credentials/passwords.
"""
import logging
import re
import sys
from typing import Any, Dict

SENSITIVE_PATTERNS = [
    re.compile(r'("?(?:password|secret|token|api_key|authorization)"?\s*[:=]\s*)"?([^",\s]+)"?', re.IGNORECASE),
    re.compile(r'(Bearer\s+)([A-Za-z0-9\-._~+/]+=*)', re.IGNORECASE),
]

class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        for pattern in SENSITIVE_PATTERNS:
            msg = pattern.sub(r'\1[REDACTED]', msg)
        return msg

def setup_logger(name: str = "chainsentry") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        formatter = RedactingFormatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False
    return logger

logger = setup_logger()
