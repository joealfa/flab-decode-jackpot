"""Fortune Lab application factory."""

import atexit
import logging
import threading
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Callable, cast

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from flask import Flask
from flask.typing import ResponseReturnValue
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.exceptions import HTTPException


def isolate_view(view):
    """Prevent limiter decoration from mutating shared blueprint functions."""

    @wraps(view, updated=())
    def bound(*args, **kwargs):
        """Call the underlying view through an app-owned wrapper."""
        return view(*args, **kwargs)

    return bound


def create_app(settings=None, *, start_scheduler: bool = False) -> Flask:
    """Build an isolated app, starting background jobs only when requested.

    Args:
            settings: Optional Config instance for a deployment or test.
            start_scheduler: Start periodic cleanup in this process.

    Returns:
            Configured Flask application.
    """
    load_dotenv()
    from app.config import Config
    from app.modules.progress_tracker import ProgressTracker
    from app.routes import blueprints
    from app.web import (
        ScientificJSONProvider,
        handle_http_error,
        require_network_authentication,
        set_security_headers,
    )

    settings = settings or Config()
    application = Flask(__name__, instance_relative_config=True)
    application.config.update(settings.flask_config)
    application.json = ScientificJSONProvider(application)
    application.extensions["fortune_config"] = settings
    for directory in (
        settings.DATA_PATH,
        settings.ANALYSIS_PATH,
        settings.AI_ANALYSIS_PATH,
        settings.PROGRESS_PATH,
        settings.ACCURACY_PATH,
    ):
        Path(directory).mkdir(parents=True, exist_ok=True)
    tracker = ProgressTracker(settings.PROGRESS_PATH, settings.PROGRESS_CLEANUP_AGE)
    application.extensions["progress_tracker"] = tracker
    application.extensions["scrape_semaphore"] = threading.BoundedSemaphore(
        settings.MAX_CONCURRENT_SCRAPES
    )
    # One local model run at a time; additional AI requests wait in their threads.
    application.extensions["ai_semaphore"] = threading.BoundedSemaphore(1)
    application.before_request(require_network_authentication)
    application.after_request(set_security_headers)
    application.register_error_handler(HTTPException, handle_http_error)
    limiter = Limiter(key_func=get_remote_address, app=application)
    application.extensions["fortune_limiter"] = limiter
    for blueprint in blueprints:
        application.register_blueprint(blueprint)
    route_limits = {
        "scraping.scrape_data": settings.RATE_LIMIT_SCRAPE,
        "scraping.get_progress": "600 per minute",
        "analysis.analyze": settings.RATE_LIMIT_ANALYZE,
        "analysis.api_analyze": settings.RATE_LIMIT_ANALYZE,
        "analysis.api_ai_analyze": settings.RATE_LIMIT_ANALYZE,
    }
    for endpoint, limit in route_limits.items():
        view = cast(
            Callable[..., ResponseReturnValue],
            application.view_functions[endpoint],
        )
        application.view_functions[endpoint] = limiter.limit(limit)(isolate_view(view))
    for rule in list(application.url_map.iter_rules()):
        if "." in rule.endpoint and rule.endpoint != "static":
            application.add_url_rule(
                rule.rule,
                endpoint=rule.endpoint.split(".", 1)[1],
                methods=rule.methods,
                build_only=True,
            )
    scheduler = BackgroundScheduler()
    # Run immediately so files left by a previous process are removed at startup.
    scheduler.add_job(
        tracker.cleanup_all,
        "interval",
        minutes=1,
        id="progress_cleanup",
        next_run_time=datetime.now(),
        coalesce=True,
        max_instances=1,
    )
    application.extensions["scheduler"] = scheduler
    if start_scheduler and not settings.TESTING:
        from app.services.ai_history import fail_interrupted_ai_analyses

        # Background AI threads do not survive a restart of the serving process.
        recovered = fail_interrupted_ai_analyses(settings.AI_ANALYSIS_PATH)
        if recovered:
            logging.getLogger(__name__).info(
                "Marked %d interrupted AI analyses as failed", recovered
            )
        interrupted = tracker.fail_interrupted_tasks()
        if interrupted:
            logging.getLogger(__name__).info(
                "Marked %d interrupted scraping tasks as failed", interrupted
            )
        scheduler.start()
        atexit.register(lambda: scheduler.shutdown() if scheduler.running else None)
    logging.getLogger(__name__).info("Fortune Lab application initialized")
    return application
