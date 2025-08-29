"""
Base handler class providing common functionality for all command handlers.
"""

from abc import ABC
import json
import re
import time
import logging
import logging.handlers
from datetime import datetime
from rich import print
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box


class BaseHandler(ABC):
    """Abstract base class for all command handlers."""
    
    def __init__(self, es_client, args, console, config_file, location_config, current_location=None):
        """
        Initialize the base handler with common dependencies.
        
        Args:
            es_client: Elasticsearch client instance
            args: Parsed command line arguments
            console: Rich console instance for output formatting
            config_file: Configuration file path
            location_config: Location-specific configuration
            current_location: Current location identifier
        """
        self.es_client = es_client
        self.args = args
        self.console = console
        self.config_file = config_file
        self.location_config = location_config
        self.current_location = current_location

    def _get_cluster_connection_info(self):
        """Get cluster connection information for display."""
        if self.es_client.elastic_username and self.es_client.elastic_password:
            return f"Cluster: {self.args.locations}\nhost: {self.es_client.host1}\nport: {self.es_client.port}\nssl: {self.es_client.use_ssl}\nverify_certs: {self.es_client.verify_certs}\nelastic_username: {self.es_client.elastic_username}\nelastic_password: XXXXXXXXXXX\n"
        return f"Cluster: {self.args.locations}\nhost: {self.es_client.host1}\nport: {self.es_client.port}\nssl: {self.es_client.use_ssl}\nverify_certs: {self.es_client.verify_certs}\n"

    def _find_shard_matches(self, shards_data, indice):
        """Find shards matching a given index pattern."""
        pattern = rf'.*{indice}.*'
        matches = [shard for shard in shards_data if re.findall(pattern, shard['index'])]
        return sorted(matches, key=lambda x: (x['prirep'], int(x['shard'])))

    def _print_shard_info(self, matches):
        """Print information about matching shards."""
        for shard in matches:
            shard_info = self._get_shard_info(shard)
            print(shard_info)

    def _get_shard_info(self, shard):
        """Get formatted shard information string."""
        shard_name = shard['index']
        shard_state = shard['state']
        shard_shard = shard['shard']
        shard_prirep = shard['prirep']
        shard_primary_ornot = 'true' if shard_prirep == "p" else 'false'

        if shard_state == "UNASSIGNED":
            shard_reason = self.es_client.get_index_allocation_explain(shard_name, shard_shard, shard_primary_ornot)
            unassigned_info = shard_reason['unassigned_info']
            return f"{shard_name} {shard_prirep} {shard_shard} {shard_state} Reason: {unassigned_info['reason']} Last Status: {unassigned_info['last_allocation_status']}"
        return f"{shard_name} {shard_prirep} {shard_shard} {shard_state}"
