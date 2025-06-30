import logging
import sys
import os
from py2c.utils import constants


def setup_logger(name: str = "py2cpp", level: int = None) -> logging.Logger:
    """
    Setup logger for the py2cpp project
    
    Args:
        name: Logger name
        level: Logging level (defaults to DEBUG in dev, INFO in prod)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    if logger.handlers:
        return logger
    
    debug_mode = os.getenv('PY2CPP_DEBUG', 'false').lower() in ('true', '1', 'yes')
    
    if level is None:
        level = logging.DEBUG if debug_mode or not constants.PROD else logging.INFO
    
    logger.setLevel(level)
    
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(level)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    # Create file handler for debug output
    # Can be controlled by PY2CPP_DEBUG environment variable or PROD setting
    if debug_mode or not constants.PROD:
        debug_file = "debug.log"
        file_handler = logging.FileHandler(debug_file, mode='w')
        file_handler.setLevel(logging.DEBUG)
        
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger

logger = setup_logger()
