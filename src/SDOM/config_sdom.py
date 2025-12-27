import logging
from .constants import LOG_COLORS

class ColorFormatter(logging.Formatter):
    """
    Custom logging formatter that adds ANSI color codes to log level names.
    
    This formatter enhances console output readability by colorizing log messages
    based on their severity level:
    - INFO: Green
    - WARNING: Yellow  
    - ERROR/CRITICAL: Red
    - DEBUG: Blue
    
    Attributes:
        COLORS (dict): Mapping from log level names to ANSI escape codes.
        RESET (str): ANSI escape code to reset color formatting.
    
    Examples:
        >>> handler = logging.StreamHandler()
        >>> handler.setFormatter(ColorFormatter('%(levelname)s - %(message)s'))
        >>> logging.getLogger().addHandler(handler)
    """
    COLORS = LOG_COLORS
        
    RESET = '\033[0m'

    def format(self, record):
        """
        Formats a log record by adding color codes to the level name.
        
        Args:
            record (logging.LogRecord): The log record to format.
        
        Returns:
            str: The formatted log message with colorized level name.
        """
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
        return super().format(record)

def configure_logging(level=logging.INFO, log_file=None):
    """
    Configures the logging system for the SDOM module with color-coded output.
    
    This function sets up logging handlers with custom color formatting for both
    console and optional file output. It should be called once at the start of
    a script before any SDOM functions that generate log messages.
    
    Args:
        level (int, optional): Logging level from the logging module. Controls which
            messages are displayed. Options:
            - logging.DEBUG (10): All messages including detailed diagnostics
            - logging.INFO (20): Informational messages and above (default)
            - logging.WARNING (30): Warnings and errors only
            - logging.ERROR (40): Errors and critical messages only
            Defaults to logging.INFO.
        log_file (str, optional): Path to a file where logs should also be written.
            If None, logs only to console. Defaults to None.
    
    Side Effects:
        Configures the root logger with handlers and formatters.
    
    Examples:
        >>> import logging
        >>> from sdom import configure_logging
        >>> configure_logging(level=logging.DEBUG, log_file='sdom_run.log')
        >>> logging.info("Starting optimization")  # Will be colored green in console
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
