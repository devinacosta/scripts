#!/usr/bin/env python3

from .base_handler import BaseHandler


class SettingsHandler(BaseHandler):
    """Handler for Elasticsearch cluster settings operations."""

    def handle_settings(self):
        """Handle cluster settings display command."""
        if self.args.format == 'json':
            cluster_settings = self.es_client.get_settings()
            print(cluster_settings)
        else:
            self.es_client.print_enhanced_cluster_settings()
