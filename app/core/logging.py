import logging
import sys
from pathlib import Path

# 1. Setup Log Directory (Root/logs)
# This assumes you run the app from the root 'applify-backend' folder
LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

def _configure_logger(name: str, filename: str):
    """Helper to create a logger that writes to a specific file."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Prevent adding multiple handlers if file is re-imported
    if not logger.handlers:
        # File Handler
        file_handler = logging.FileHandler(LOG_DIR / filename, encoding="utf-8")
        file_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s', 
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        # Optional: Also print to console
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(file_formatter)
        logger.addHandler(stream_handler)
        
    return logger

# --- EXPORTED LOGGERS ---

# Logs HTTP requests, Logins, and User actions
traffic_logger = _configure_logger("traffic", "traffic.log")

# Logs Prompts, Context, and AI Responses
llm_logger = _configure_logger("llm", "llm.log")