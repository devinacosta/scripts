"""
CLI package for escmd - Command-line interface components.
"""

from .argument_parser import create_argument_parser
from .help_system import show_custom_help
from .special_commands import (
    handle_version,
    handle_locations,
    handle_get_default,
    handle_set_default,
    handle_show_settings
)

__all__ = [
    'create_argument_parser',
    'show_custom_help', 
    'handle_version',
    'handle_locations', 
    'handle_get_default',
    'handle_set_default',
    'handle_show_settings'
]
