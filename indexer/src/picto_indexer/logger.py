"""
Configures the logging for the Picto Indexer application.
"""
import logging
from rich.logging import RichHandler

def setup_logging():
    """
    Configures the root logger to use RichHandler for console output
    and a FileHandler for persistent logging.
    """
    # Set the format for the logs
    log_format = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    
    # Get the root logger
    log = logging.getLogger()
    log.setLevel(logging.INFO)

    # Prevent the root logger from propagating to the default handler
    log.propagate = False

    # Create a RichHandler for beautiful console output
    rich_handler = RichHandler(
        rich_tracebacks=True,
        show_path=False,
        log_time_format="[%X]"
    )
    rich_handler.setFormatter(logging.Formatter("%(message)s")) # Simple format for console

    # Create a FileHandler to save logs to a file
    file_handler = logging.FileHandler("indexer.log", mode='w', encoding='utf-8')
    file_handler.setFormatter(logging.Formatter(log_format))

    # Add handlers to the root logger only if they haven't been added before
    if not log.handlers:
        log.addHandler(rich_handler)
        log.addHandler(file_handler)
