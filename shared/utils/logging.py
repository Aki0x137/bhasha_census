"""Structured logging helper for session/job/challenge events."""
from __future__ import annotations

import logging
import structlog


def configure_logging(level: str = "INFO") -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )


def get_logger(name: str) -> structlog.BoundLogger:
    return structlog.get_logger(name)


def log_session_event(logger: structlog.BoundLogger, session_id: str, event: str, **kw) -> None:
    logger.info(event, session_id=session_id, **kw)


def log_challenge_event(
    logger: structlog.BoundLogger, session_id: str, challenge_id: str, event: str, **kw
) -> None:
    logger.info(event, session_id=session_id, challenge_id=challenge_id, **kw)


def log_job_event(
    logger: structlog.BoundLogger, session_id: str, job_id: str, event: str, **kw
) -> None:
    logger.info(event, session_id=session_id, job_id=job_id, **kw)
