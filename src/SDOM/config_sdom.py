import logging
from .constants import LOG_COLORS

class ColorFormatter(logging.Formatter):
    COLORS = LOG_COLORS
        
    RESET = '\033[0m'

    def format(self, record):
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
        return super().format(record)

def configure_logging(level=logging.INFO, log_file=None):
    """
    Configures logging for the module.
    Args:
        level: Logging level (default: logging.INFO)
        log_file: Optional file path to log to a file
    """
    handlers = [logging.StreamHandler()]
    formatter = ColorFormatter('%(asctime)s - %(levelname)s - %(message)s')

    if log_file:
        handlers.append(logging.FileHandler(log_file))

    for handler in handlers:
        handler.setFormatter(formatter)

    logging.basicConfig(
        level=level,
        handlers=handlers
    )
