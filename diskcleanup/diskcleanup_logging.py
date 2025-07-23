#!/usr/bin/python3
"""
Disk Cleanup Utility - Logging Infrastructure Module

This module contains all logging-related functionality including:
- Custom formatters and handlers for operation ID tracking
- Operation context management and metrics tracking
- Log sampling for high-volume operations
- Simplified log message formatting

Author: Devin Acosta
Version: 2.0.3
Date: 2025-07-23
"""

import datetime
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, Union

from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme

# Thread-local storage for current operation context
_local = threading.local()

def set_current_operation_id(operation_id: str) -> None:
    """Set the current operation ID for this thread."""
    _local.operation_id = operation_id

def get_current_operation_id() -> str:
    """Get the current operation ID for this thread."""
    return getattr(_local, 'operation_id', 'session')

class OperationIdFormatter(logging.Formatter):
    """Custom formatter that adds operation ID to the front of each log message."""
    
    def __init__(self, fmt=None, datefmt=None):
        # Store the original format without operation ID for fallback
        self.original_fmt = fmt
        super().__init__(fmt, datefmt)
    
    def format(self, record):
        # Get current operation ID
        op_id = get_current_operation_id()
        
        # Add operation ID to the message, not the entire format
        if op_id and op_id != 'session':
            # For non-session IDs, use compact format
            record.msg = f"[{op_id}] {record.msg}"
        else:
            # For session or missing IDs, use minimal format
            record.msg = f"[session] {record.msg}"
        
        # Use the original formatter normally
        return super().format(record)

class CleanRichHandler(RichHandler):
    """Clean RichHandler without operation ID duplication."""
    
    def emit(self, record):
        # Just emit cleanly without adding operation ID
        # (the LogHelper methods already include operation IDs)
        super().emit(record)

@dataclass
class OperationMetrics:
    """Tracks metrics for cleanup operations."""
    operation_id: str = ""
    files_processed: int = 0
    directories_processed: int = 0
    bytes_freed: int = 0
    errors_encountered: int = 0
    execution_time: float = 0.0
    
    def add_file(self, size: int = 0) -> None:
        """Add a processed file to metrics."""
        self.files_processed += 1
        self.bytes_freed += size
    
    def add_directory(self) -> None:
        """Add a processed directory to metrics."""
        self.directories_processed += 1
    
    def add_error(self) -> None:
        """Add an error to metrics."""
        self.errors_encountered += 1
    
    def to_dict(self) -> Dict[str, Union[int, float, str]]:
        """Convert metrics to dictionary for logging."""
        return {
            'id': self.operation_id,
            'files': self.files_processed,
            'dirs': self.directories_processed,
            'freed': f"{self.bytes_freed:,} bytes",
            'errors': self.errors_encountered,
            'duration': f"{self.execution_time:.2f}s"
        }

class LogSampler:
    """Log sampling for high-volume operations."""
    def __init__(self, sample_rate: int = 100):
        self.counter = 0
        self.sample_rate = sample_rate
    
    def should_log(self) -> bool:
        """Determine if this operation should be logged."""
        self.counter += 1
        return self.counter % self.sample_rate == 0

class OperationContext:
    """Context manager for tracking operations with descriptive correlation IDs."""
    def __init__(self, operation_name: str, component: str = "system", target: str = ""):
        self.operation_name = operation_name
        self.component = component
        self.target = target
        self.metrics = OperationMetrics()
        self.start_time = time.time()
        self.previous_operation_id = None
        
        # Generate simple operation ID
        timestamp = datetime.datetime.now().strftime("%H%M")
        random_suffix = str(uuid.uuid4())[:3]
        self.metrics.operation_id = f"{operation_name}_{timestamp}{random_suffix}"
    
    def __enter__(self):
        # Import here to avoid circular imports
        import logging
        log = logging.getLogger("diskcleanup")
        
        # Save previous operation ID and set current one
        self.previous_operation_id = get_current_operation_id()
        set_current_operation_id(self.metrics.operation_id)
        
        log.info(f"Starting {self.operation_name}")
        return self.metrics
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Import here to avoid circular imports
        import logging
        log = logging.getLogger("diskcleanup")
        
        self.metrics.execution_time = time.time() - self.start_time
        if exc_type is None:
            log.info(f"Completed - {self.metrics.to_dict()}")
        else:
            self.metrics.add_error()
            log.error(f"{self.operation_name} failed (error: {exc_type.__name__}: {exc_val}) {self.metrics.to_dict()}")
        
        # Restore previous operation ID
        if self.previous_operation_id:
            set_current_operation_id(self.previous_operation_id)
        else:
            set_current_operation_id('session')

class LogHelper:
    """Simplified logging helper - operation ID provides context, keep messages clean."""
    
    @staticmethod
    def action(details: str, **kwargs) -> str:
        """Format action log messages: Details (extra info)"""
        extra_info = " ".join(f"({k}: {v})" for k, v in kwargs.items() if v is not None)
        return f"{details} {extra_info}".strip()
    
    @staticmethod
    def dry_run(details: str, **kwargs) -> str:
        """Format dry-run log messages: Would details (extra info)"""
        extra_info = " ".join(f"({k}: {v})" for k, v in kwargs.items() if v is not None)
        return f"Would {details} {extra_info}".strip()
    
    @staticmethod
    def system(details: str, **kwargs) -> str:
        """Format system log messages: Details (extra info)"""
        extra_info = " ".join(f"({k}: {v})" for k, v in kwargs.items() if v is not None)
        return f"{details} {extra_info}".strip()
    
    @staticmethod
    def config(details: str, **kwargs) -> str:
        """Format configuration log messages: Details (extra info)"""
        extra_info = " ".join(f"({k}: {v})" for k, v in kwargs.items() if v is not None)
        return f"{details} {extra_info}".strip()
    
    @staticmethod
    def performance(**kwargs) -> str:
        """Format performance log messages: key: value pairs"""
        extra_info = " ".join(f"{k}: {v}" for k, v in kwargs.items() if v is not None)
        return f"Completed - {extra_info}"
    
    @staticmethod
    def error_with_context(path: str, error: Exception, **kwargs) -> str:
        """Format error messages with context."""
        extra_info = " ".join(f"({k}: {v})" for k, v in kwargs.items() if v is not None)
        return f"Failed to process {path}: {type(error).__name__}: {error} {extra_info}".strip()
    
    @staticmethod
    def progress(current: int, total: int, **kwargs) -> str:
        """Format progress messages."""
        percent = f"{(current/total)*100:.1f}%" if total > 0 else "0%"
        extra_info = " ".join(f"({k}: {v})" for k, v in kwargs.items() if v is not None)
        return f"Progress: {current}/{total} ({percent}) {extra_info}".strip()

def setup_logging(log_file_path: str, verbose: bool = False) -> tuple:
    """
    Set up logging with dual approach: Rich console + Standard file
    
    Returns:
        tuple: (console, logger_helper, global_metrics)
    """
    # Initialize console
    console = Console(
        theme=Theme({
            "info": "cyan",
            "warning": "yellow",
            "error": "bold red",
            "dry_run": "bold magenta"
        }),
        highlight=False  # Auto-detects terminal width for full console usage
    )
    
    # Initialize logger helper and global metrics
    logger_helper = LogHelper()
    global_metrics = OperationMetrics()
    global_metrics.operation_id = f"session_{datetime.datetime.now().strftime('%H%M')}{str(uuid.uuid4())[:3]}"
    
    # Rich console handler for beautiful interactive display
    console_handler = CleanRichHandler(
        console=console,
        rich_tracebacks=True,
        show_time=True,
        show_path=False,
        markup=False,  # Disable markup processing for log messages
        log_time_format="[%H:%M:%S]",
        omit_repeated_times=False,
        show_level=False,  # Don't show level to avoid duplication
        keywords=[]  # Don't highlight keywords 
    )
    # Set clean formatter without logger name
    console_handler.setFormatter(logging.Formatter('%(levelname)s %(message)s'))
    
    # File handler uses clean, standard format for tools/automation
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setFormatter(
        OperationIdFormatter(
            fmt='%(asctime)s %(levelname)-8s : %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    )
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        handlers=[file_handler, console_handler],
        force=True  # Ensure settings are applied
    )
    
    return console, logger_helper, global_metrics 