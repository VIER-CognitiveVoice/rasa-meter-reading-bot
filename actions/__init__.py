import logging
from colorlog import ColoredFormatter

LOG_FORMAT = (
    " %(log_color)s%(asctime)s,%(msecs)d |"
    " %(levelname)-8s%(reset)s |"
    " %(log_color)s[%(filename)s:%(lineno)3d] |"
    " %(message)s%(reset)s"
)
LOG_DATE_FORMAT = "%Y-%m-%d:%H:%M:%S"


def create_logger(
        logger_name: str,
        log_level: int = logging.INFO
        ) -> logging.Logger:
    """Creates a logger with the given name and level."""

    logger_name = logger_name.replace(".py", "")

    formatter = ColoredFormatter(LOG_FORMAT, LOG_DATE_FORMAT)
    stream = logging.StreamHandler()
    stream.setLevel(log_level)
    stream.setFormatter(formatter)
    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level)
    logger.handlers = [stream]
    logger.propagate = False

    return logger
