"""
Node management command handlers for escmd.

This module contains handlers for node information and master node operations.
"""

from .base_handler import BaseHandler


class NodeHandler(BaseHandler):
    """Handler for node management commands."""

    def handle_nodes(self):
        """Handle nodes listing command."""
        nodes = self.es_client.get_nodes()
        if self.args.format == 'json':
            import json
            print(json.dumps(nodes))
        elif self.args.format == 'data':
            data_nodes = self.es_client.filter_nodes_by_role(nodes, 'data')
            self.es_client.print_enhanced_nodes_table(data_nodes, show_data_only=True)
        else:
            self.es_client.print_enhanced_nodes_table(nodes)

    def handle_masters(self):
        """Handle masters listing command."""
        nodes = self.es_client.get_nodes()
        master_nodes = self.es_client.filter_nodes_by_role(nodes, 'master')
        if self.args.format == 'json':
            import json
            print(json.dumps(master_nodes))
        else:
            self.es_client.print_enhanced_masters_info(master_nodes)

    def handle_current_master(self):
        """Handle current master node identification command."""
        try:
            master_info = self.es_client.get_current_master_info()
            if self.args.format == 'json':
                import json
                print(json.dumps(master_info))
            else:
                self.es_client.print_current_master_info(master_info)
        except Exception as e:
            if self.args.format == 'json':
                import json
                print(json.dumps({"error": str(e)}))
            else:
                self.console.print(f"[red]Error getting master info: {str(e)}[/red]")
