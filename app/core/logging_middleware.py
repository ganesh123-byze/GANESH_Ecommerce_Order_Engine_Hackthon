from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import logging
import time

logger = logging.getLogger("app")
handler = logging.StreamHandler()
formatter = logging.Formatter("[%(asctime)s] %(levelname)s %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        logger.info(f"start request path={request.url.path} method={request.method}")
        response = await call_next(request)
        elapsed = (time.time() - start) * 1000
        logger.info(f"end request path={request.url.path} status={response.status_code} duration_ms={elapsed:.2f}")
        return response
