import logging
import sys
import os


def configure_logging():
    lvl = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        stream=sys.stderr, level=lvl, format="%(levelname)s %(name)s: %(message)s"
    )
    if lvl != "DEBUG":
        logging.getLogger("httpx").setLevel(logging.WARNING)
