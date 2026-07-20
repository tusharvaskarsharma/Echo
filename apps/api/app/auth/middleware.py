from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response
import logging

logger = logging.getLogger(__name__)

class AuthMiddleware(BaseHTTPMiddleware):
    """
    Optional global auth middleware. 
    In FastAPI, route protection is usually done via Dependencies (see dependencies.py),
    but this middleware can be used to log auth headers or block specific global paths.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        # CORS preflight must never require authentication.  CORSMiddleware is
        # deliberately the outer ASGI wrapper, so browser preflights are handled
        # there first; this guard also makes bare OPTIONS requests safe if they
        # reach this middleware directly.
        if request.method == "OPTIONS":
            return Response(status_code=200)

        # Example: Log if a request to a protected route has an auth header
        if request.url.path.startswith("/api/protected"):
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                logger.warning(f"Unauthenticated access attempt to {request.url.path}")
                
        response = await call_next(request)
        return response
