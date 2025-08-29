"""
Shard management command handlers for escmd.

This module contains handlers for shard operations, colocation analysis, and rollover operations.
"""

from .base_handler import BaseHandler


class ShardHandler(BaseHandler):
    """Handler for shard management commands."""

    def handle_shards(self):
        """Handle shards listing and analysis."""
        if hasattr(self.args, 'regex') and self.args.regex:
            self._handle_regex_shards()
        else:
            # Regular shards listing - replicate original logic
            shards_data_dict = self.es_client.get_shards_as_dict()

            if hasattr(self.args, 'size') and self.args.size:
                shards_data_dict = sorted(shards_data_dict, key=lambda x: x['size'], reverse=True)

            if hasattr(self.args, 'server') and self.args.server:
                import re
                search_location = self.args.server[0]
                pattern = f".*{search_location}.*"
                shards_data_dict = [item for item in shards_data_dict if re.search(pattern, item['node'], re.IGNORECASE)]

            if hasattr(self.args, 'limit') and self.args.limit != 0:
                shards_data_dict = shards_data_dict[:int(self.args.limit)]

            if self.args.format == 'json':
                import json
                print(json.dumps(shards_data_dict))
            else:
                use_pager = getattr(self.args, 'pager', False)
                self.es_client.print_table_shards(shards_data_dict, use_pager=use_pager)

    def _handle_regex_shards(self):
        """Handle regex-based shard filtering."""
        if self.args.regex == 'unassigned':
            self._handle_unassigned_shards()
            return

        if self.args.format == 'json':
            import json
            print(json.dumps(self.es_client.get_shards_stats(pattern=self.args.regex)))
            return

        shards_data = self.es_client.get_shards_stats(pattern=self.args.regex)
        use_pager = getattr(self.args, 'pager', False)
        self.es_client.print_table_shards(shards_data, use_pager=use_pager)

    def _handle_unassigned_shards(self):
        """Handle unassigned shards analysis."""
        if self.args.format == 'json':
            import json
            shards_data = self.es_client.get_shards_stats(pattern='*')
            filtered_data = [item for item in shards_data if item['state'] == 'UNASSIGNED']
            print(json.dumps(filtered_data))
            return

        shards_data = self.es_client.get_shards_stats(pattern='*')
        filtered_data = [item for item in shards_data if item['state'] == 'UNASSIGNED']
        if not filtered_data:
            # from utils import show_message_box
            self.es_client.show_message_box(f'Results: Shards [ {self.args.locations} ]', 'There was no unassigned shards found in cluster.', 'white on blue', 'bold white')
        else:
            use_pager = getattr(self.args, 'pager', False)
            self.es_client.print_table_shards(filtered_data, use_pager=use_pager)

    def handle_shard_colocation(self):
        """Handle shard colocation analysis."""
        if hasattr(self.args, 'regex') and self.args.regex:
            pattern = self.args.regex
        else:
            pattern = None
            
        if self.args.format == 'json':
            import json
            colocation_data = self.es_client.analyze_shard_colocation(pattern)
            print(json.dumps(colocation_data))
        else:
            use_pager = getattr(self.args, 'pager', False)
            self.es_client.print_shard_colocation_analysis(pattern, use_pager=use_pager)

    def handle_rollover(self):
        """Handle index rollover operations."""
        alias = getattr(self.args, 'alias', None)
        
        if not alias:
            self.console.print("[red]Alias is required for rollover operation[/red]")
            return
            
        dry_run = getattr(self.args, 'dry_run', False)
        
        if self.args.format == 'json':
            import json
            result = self.es_client.perform_rollover(alias, dry_run)
            print(json.dumps(result))
        else:
            self.es_client.perform_rollover_with_output(alias, dry_run)

    def handle_auto_rollover(self):
        """Handle auto rollover command."""
        # from utils import show_message_box
        self.es_client.show_message_box("Auto Rollover", "This feature is not yet implemented", message_style="bold white", panel_style="yellow")
