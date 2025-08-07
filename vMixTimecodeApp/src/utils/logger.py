import logging
import os
from datetime import datetime

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, f"app_{datetime.now().strftime('%Y%m%d')}.log")

# Ensure log directory exists
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logging():
    logger = logging.getLogger('vMixTimecodeApp')
    logger.setLevel(logging.INFO)

    # Create handlers
    c_handler = logging.StreamHandler() # Console handler
    f_handler = logging.FileHandler(LOG_FILE, encoding='utf-8') # File handler

    # Set levels
    c_handler.setLevel(logging.INFO)
    f_handler.setLevel(logging.INFO)

    # Create formatters and add it to handlers
    c_format = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    c_handler.setFormatter(c_format)
    f_handler.setFormatter(f_format)

    # Add handlers to the logger
    logger.addHandler(c_handler)
    logger.addHandler(f_handler)

    return logger

app_logger = setup_logging()
