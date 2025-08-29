#!/usr/bin/env python3

import builtins
import json
import logging
import re
import time
from datetime import datetime
from handlers.utility_handler import UtilityHandler
from handlers.storage_handler import StorageHandler
from handlers.lifecycle_handler import LifecycleHandler
from handlers.cluster_handler import ClusterHandler
from handlers.allocation_handler import AllocationHandler
from handlers.index_handler import IndexHandler
from handlers.dangling_handler import DanglingHandler
from handlers.settings_handler import SettingsHandler
from handlers.snapshot_handler import SnapshotHandler
from handlers.help_handler import HelpHandler
import os

from configuration_manager import ConfigurationManager


class CommandHandler:

    def __init__(self, es_client, args, console, config_file, location_config, current_location=None):
        self.es_client = es_client
        self.args = args
        self.console = console
        self.config_file = config_file
        self.location_config = location_config
        self.current_location = current_location
        
        # Initialize handlers
        self.utility_handler = UtilityHandler(es_client, args, console, config_file, location_config, current_location)
        self.storage_handler = StorageHandler(es_client, args, console, config_file, location_config, current_location)
        self.snapshot_handler = SnapshotHandler(es_client, args, console, config_file, location_config, current_location)
        self.lifecycle_handler = LifecycleHandler(es_client, args, console, config_file, location_config, current_location)
        self.cluster_handler = ClusterHandler(es_client, args, console, config_file, location_config, current_location)
        self.allocation_handler = AllocationHandler(es_client, args, console, config_file, location_config, current_location)
        self.index_handler = IndexHandler(es_client, args, console, config_file, location_config, current_location)
        self.dangling_handler = DanglingHandler(es_client, args, console, config_file, location_config, current_location)
        self.settings_handler = SettingsHandler(es_client, args, console, config_file, location_config, current_location)
        self.help_handler = HelpHandler(es_client, args, console, config_file, location_config, current_location)

    def execute(self):
        command_handlers = {
            'ping': self.cluster_handler.handle_ping,  # Using handler
            'allocation': self.allocation_handler.handle_allocation,  # Using handler
            'current-master': self.cluster_handler.handle_current_master,  # Using handler
            'flush': self.index_handler.handle_flush,  # Using handler
            'freeze': self.index_handler.handle_freeze,  # Using handler
            'unfreeze': self.index_handler.handle_unfreeze,  # Using handler
            'nodes': self.cluster_handler.handle_nodes,  # Using handler
            'masters': self.cluster_handler.handle_masters,  # Using handler
            'health': self.cluster_handler.handle_health,  # Using handler
            'indice': self.index_handler.handle_indice,  # Using handler
            'indices': self.index_handler.handle_indices,  # Using handler
            'locations': self.utility_handler.handle_locations,  # Using handler
            'recovery': self.index_handler.handle_recovery,  # Using handler
            'rollover': self.lifecycle_handler.handle_rollover,  # Using handler
            'auto-rollover': self.lifecycle_handler.handle_auto_rollover,  # Using handler
            'exclude': self.allocation_handler.handle_exclude,  # Using handler
            'exclude-reset': self.allocation_handler.handle_exclude_reset,  # Using handler
            'settings': self.settings_handler.handle_settings,  # Using handler
            'dangling': self.dangling_handler.handle_dangling,  # Using handler
            'storage': self.storage_handler.handle_storage,  # Using handler
            'shards': self.storage_handler.handle_shards,  # Using handler
            'shard-colocation': self.storage_handler.handle_shard_colocation,  # Using handler
            'snapshots': self.snapshot_handler.handle_snapshots,  # Using handler
            'ilm': self.lifecycle_handler.handle_ilm,  # Using handler
            'datastreams': self.utility_handler.handle_datastreams,  # Using handler
            'cluster-check': self.utility_handler.handle_cluster_check,  # Using handler
            'set-replicas': self.utility_handler.handle_set_replicas,  # Using handler
            'help': self.help_handler.handle_help,  # Using handler
        }

        handler = command_handlers.get(self.args.command)
        if handler:
            handler()
        else:
            print(f"Unknown command: {self.args.command}")
