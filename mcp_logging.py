#!/usr/bin/env python3
"""
MCP Logging Module

A reusable logging configuration module for Model Context Protocol (MCP) servers.
This provides standardized logging setup that works across different MCP server
implementations.
"""
import os
import sys
import logging
from typing import Optional, Union, List
import logging.config


def configure_logging(
    app_name: str,
    level: Optional[str] = None,
    log_file: Optional[str] = None,
    log_format: Optional[str] = None
) -> logging.Logger:
    """
    Configure logging for an MCP server application.
    
    Args:
        app_name (str): Name of the application (used for logger naming)
        level (Optional[str]): Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
                               Defaults to environment variable MCP_LOG_LEVEL or INFO
        log_file (Optional[str]): Path to log file. 
                                  Defaults to environment variable MCP_LOG_FILE
        log_format (Optional[str]): Log format string. Defaults to standard format.
                                   
    Returns:
        logging.Logger: Configured logger instance
    """
    # Check environment for development mode - standard Python practice
    # https://docs.python.org/3/library/os.html#os.environ 
    # https://docs.python.org/3/using/cmdline.html#environment-variables
    is_dev = os.environ.get('PYTHONDEBUG') or os.environ.get('MCP_DEV_MODE', '').lower() == 'true'
    
    # Default log level
    if level is None:
        level = os.environ.get('MCP_LOG_LEVEL', 'INFO').upper()
    
    # Convert string level to logging level constant
    numeric_level = getattr(logging, level, logging.INFO)
    
    # Default log format
    if log_format is None:
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Build handlers list based on configuration
    handlers = []
    
    # Add stderr handler for development
    if is_dev:
        console = logging.StreamHandler(sys.stderr)
        console.setLevel(numeric_level)
        console.setFormatter(logging.Formatter(log_format))
        handlers.append(console)
    
    # Add file handler if file path provided
    if log_file is None:
        log_file = os.environ.get('MCP_LOG_FILE', '')
    
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(logging.Formatter(log_format))
        handlers.append(file_handler)
    
    # Use a more comprehensive configuration when no handlers were specified
    if not handlers:
        if is_dev:
            # In dev mode with no explicit handlers, use a NullHandler to avoid warnings
            handlers.append(logging.NullHandler())
        else:
            # In production with no handlers, use the last resort logging
            # configuration that sends to stderr if critical errors occur
            root_logger = logging.getLogger()
            if not root_logger.handlers:
                logging.basicConfig(
                    level=logging.CRITICAL,
                    format=log_format
                )
    
    # Get logger for this app and configure it
    logger = logging.getLogger(f"mcp.{app_name}")
    logger.setLevel(numeric_level)
    
    # Clear any existing handlers to avoid duplicates if reconfigured
    if logger.handlers:
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
    
    # Add all configured handlers
    for handler in handlers:
        logger.addHandler(handler)
    
    return logger


def get_dict_config(app_name: str) -> dict:
    """
    Get a dictionary configuration for logging.config.dictConfig.
    More advanced configuration for when you need finer control.
    
    Args:
        app_name (str): Name of the application for logger naming
        
    Returns:
        dict: Configuration dictionary for logging.config.dictConfig
    """
    is_dev = os.environ.get('PYTHONDEBUG') or os.environ.get('MCP_DEV_MODE', '').lower() == 'true'
    log_file = os.environ.get('MCP_LOG_FILE', '')
    log_level = os.environ.get('MCP_LOG_LEVEL', 'INFO').upper()
    
    handlers = {
        'null': {
            'class': 'logging.NullHandler',
        }
    }
    
    # Add console logger in dev mode
    if is_dev:
        handlers['console'] = {
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
            'level': log_level,
            'stream': 'ext://sys.stderr',
        }
    
    # Add file logger if configured
    if log_file:
        handlers['file'] = {
            'class': 'logging.FileHandler',
            'formatter': 'standard',
            'level': log_level,
            'filename': log_file,
        }
    
    # Default handler list
    handler_list = []
    if is_dev:
        handler_list.append('console')
    if log_file:
        handler_list.append('file')
    if not handler_list:
        handler_list.append('null')
    
    return {
        'version': 1,
        'formatters': {
            'standard': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            },
            'simple': {
                'format': '%(levelname)s - %(message)s'
            }
        },
        'handlers': handlers,
        'loggers': {
            f'mcp.{app_name}': {
                'handlers': handler_list,
                'level': log_level,
                'propagate': False
            }
        }
    }