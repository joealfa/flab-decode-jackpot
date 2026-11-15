"""Standalone development entry point for Fortune Lab."""

import logging
import os

from dotenv import load_dotenv

from app import create_app


def main() -> None:
    """Run one application process with explicitly managed background jobs."""
    load_dotenv()
    from app.config import Config

    settings = Config()
    logging.basicConfig(
        level=settings.LOG_LEVEL.upper(),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    start_scheduler = (
        not settings.DEBUG or os.environ.get("WERKZEUG_RUN_MAIN") == "true"
    )
    application = create_app(settings, start_scheduler=start_scheduler)
    ssl_context = (
        (settings.SSL_CERTFILE, settings.SSL_KEYFILE) if settings.SSL_CERTFILE else None
    )
    application.run(
        host=settings.HOST,
        port=settings.PORT,
        debug=settings.DEBUG,
        ssl_context=ssl_context,
    )


if __name__ == "__main__":
    main()
