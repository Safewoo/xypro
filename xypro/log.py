import sys

from loguru import logger


def configure_logging(level="INFO"):
    "Configure logging."
    logger.remove()
    logger.add(sys.stderr, level=level)
