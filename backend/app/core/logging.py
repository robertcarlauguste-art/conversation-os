"""
Structured logging setup.

Every request gets logged like an entry in a building's visitor log:
who came in (request id), when (timestamp), how long they stayed
(duration), and how it went (status). The "authenticated_user" field
is a placeholder for now — Sprint 0 has no auth yet, so it stays empty
until Clerk/JWT are wired in.
"""

import logging
import sys
import time
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | request_id=%(request_id)s | %(message)s",
        stream=sys.stdout,
    )
    old_factory = logging.getLogRecordFactory()

    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        record.request_id = request_id_ctx.get()
        return record

    logging.setLogRecordFactory(record_factory)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs request id, timestamp, duration, and status for every request."""

    async def dispatch(self, request: Request, call_next) -> Response:
        req_id = str(uuid.uuid4())
        token = request_id_ctx.set(req_id)
        start = time.perf_counter()
        logger = logging.getLogger("conversation_os.request")
        response: Response | None = None
        try:
            response = await call_next(request)
            return response
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            # Placeholder for authenticated user info — populated once auth exists.
            authenticated_user = getattr(request.state, "user_id", None)
            status_code = response.status_code if response is not None else 500
            logger.info(
                "method=%s path=%s status=%s duration_ms=%.2f authenticated_user=%s",
                request.method,
                request.url.path,
                status_code,
                duration_ms,
                authenticated_user,
            )
            if response is not None:
                response.headers["X-Request-ID"] = req_id
            request_id_ctx.reset(token)
