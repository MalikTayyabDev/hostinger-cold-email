import logging
import os
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent / "logs"


def setup_logging(name="cold_email"):
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    # Vercel serverless has a read-only filesystem — skip file logging there.
    if not os.getenv("VERCEL"):
        try:
            LOG_DIR.mkdir(exist_ok=True)
            file_handler = logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except OSError:
            pass

    return logger
