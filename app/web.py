"""Shared HTTP policies and request-scoped application dependencies."""

import hmac
from typing import Any

from flask import Response, current_app, jsonify, make_response, request
from flask.json.provider import DefaultJSONProvider
from werkzeug.exceptions import HTTPException
from werkzeug.local import LocalProxy

from app.serialization import convert_to_serializable

config = LocalProxy(lambda: current_app.extensions["fortune_config"])
progress_tracker = LocalProxy(lambda: current_app.extensions["progress_tracker"])
scrape_semaphore = LocalProxy(lambda: current_app.extensions["scrape_semaphore"])
ai_semaphore = LocalProxy(lambda: current_app.extensions["ai_semaphore"])
HTTPResponse = str | Response | tuple[str | Response, int]


class ScientificJSONProvider(DefaultJSONProvider):
    """Normalize NumPy values for all Flask JSON responses."""

    def dumps(self, obj: Any, **kwargs: Any) -> str:
        """Serialize a normalized document."""
        return super().dumps(convert_to_serializable(obj), **kwargs)


def build_error_response(
    exception: Exception, default_status: int = 400
) -> tuple[Response, int]:
    """Return a consistent error without disclosing internal exception details."""
    status = getattr(exception, "status_code", default_status)
    payload = {"success": False, "error": str(exception)}
    details = getattr(exception, "details", None)
    if status >= 500 and status != 503:
        payload["error"] = (
            "An unexpected error occurred. Check server logs for details."
        )
    elif details and status < 500:
        payload["details"] = details
    return jsonify(payload), status


def require_network_authentication() -> Response | None:
    """Challenge requests when credentials have been configured."""
    if not config.BASIC_AUTH_USERNAME:
        return None
    authorization = request.authorization
    username = authorization.username if authorization else ""
    password = authorization.password if authorization else ""
    username_matches = hmac.compare_digest(
        (username or "").encode(), config.BASIC_AUTH_USERNAME.encode()
    )
    password_matches = hmac.compare_digest(
        (password or "").encode(), config.BASIC_AUTH_PASSWORD.encode()
    )
    if (
        authorization
        and authorization.type.lower() == "basic"
        and username_matches
        and password_matches
    ):
        return None
    response = make_response(
        jsonify({"success": False, "error": "Authentication required"}), 401
    )
    response.headers["WWW-Authenticate"] = 'Basic realm="Fortune Lab"'
    return response


def set_security_headers(response: Response) -> Response:
    """Apply response headers, including HSTS only over HTTPS."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if request.is_secure and not config.DEBUG:
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
    return response


def handle_http_error(error: HTTPException) -> Response | HTTPException:
    """Keep API HTTP errors, including rate limits, in the JSON contract."""
    if request.path.startswith("/api/") or request.path == "/scrape":
        response = make_response(error.get_response())
        response.data = current_app.json.dumps(
            {"success": False, "error": error.description}
        )
        response.content_type = "application/json"
        return response
    return error
