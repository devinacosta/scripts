"""
Configuration-related command handlers for escmd.

This module contains handlers for configuration and utility operations.
"""

from .base_handler import BaseHandler


class ConfigurationHandler(BaseHandler):
    """Handler for configuration and utility operations."""

    def handle_locations(self):
        """Handle locations command - display all configured Elasticsearch locations"""
        # Use the configuration manager's show_locations method instead of utils
        from configuration_manager import ConfigurationManager
        config_manager = ConfigurationManager(self.config_file, "escmd.json")
        config_manager.show_locations()
