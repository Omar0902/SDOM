import logging

def configure_logging(level=logging.INFO, log_file=None):
    """
    Configures logging for the module.
    Args:
        level: Logging level (default: logging.INFO)
        log_file: Optional file path to log to a file
    """
    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    logging.basicConfig(
        level=level,
        format='%(asctime)s %(levelname)s %(message)s',
        handlers=handlers
    )