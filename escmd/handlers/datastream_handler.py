"""
Datastream-related command handlers for escmd.

This module contains handlers for datastream operations and management commands.
"""

import json
from rich.table import Table
from rich.console import Console
from rich.panel import Panel

from .base_handler import BaseHandler


class DatastreamHandler(BaseHandler):
    """Handler for datastream operations and management commands."""

    def handle_datastreams(self):
        """Handle datastreams command - list all datastreams, show details, or delete a specific one"""
        try:
            if hasattr(self.args, 'name') and self.args.name and hasattr(self.args, 'delete') and self.args.delete:
                # Delete the specified datastream with confirmation
                self._handle_datastream_delete()
            elif hasattr(self.args, 'name') and self.args.name:
                # Show details for specific datastream
                datastream_details = self.es_client.get_datastream_details(self.args.name)
                if self.args.format == 'json':
                    print(json.dumps(datastream_details, indent=2))
                else:
                    self._print_datastream_details_table(datastream_details)
            elif hasattr(self.args, 'delete') and self.args.delete:
                # Delete option requires a datastream name
                print("❌ Error: Datastream name is required when using --delete option")
                print("Usage: ./escmd.py datastreams <datastream_name> --delete")
            else:
                # List all datastreams
                datastreams_data = self.es_client.list_datastreams()

                if self.args.format == 'json':
                    print(json.dumps(datastreams_data, indent=2))
                else:
                    self._print_datastreams_table(datastreams_data)

        except Exception as e:
            print(f"Error with datastreams operation: {e}")

    def _print_datastreams_table(self, datastreams_data):
        """Print datastreams list in table format"""
        console = Console(width=120)
        
        # Check if there are any datastreams
        datastreams_list = datastreams_data.get('data_streams', [])
        if not datastreams_list:
            # Create a nice panel showing no datastreams found
            from rich.text import Text
            
            content_text = "🔍 No datastreams found in this cluster\n\n💡 Datastreams store time-series data (logs, metrics).\n   Create using index templates with 'data_stream' config."
            
            panel = Panel(
                content_text,
                title="📊 Datastreams",
                border_style="cyan",
                padding=(1, 2)
            )
            
            print()
            console.print(panel)
            print()
            return
        
        table = Table(show_header=True, header_style="bold magenta", title="📊 Datastreams")
        
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Status", style="green")
        table.add_column("Template", style="yellow")
        table.add_column("ILM Policy", style="blue")
        table.add_column("Generation", style="white", justify="right")
        table.add_column("Indices Count", style="white", justify="right")

        for datastream in datastreams_list:
            name = datastream.get('name', 'N/A')
            status = datastream.get('status', 'N/A')
            template = datastream.get('template', 'N/A')
            ilm_policy = datastream.get('ilm_policy', 'N/A')
            generation = str(datastream.get('generation', 0))
            indices_count = str(len(datastream.get('indices', [])))
            
            table.add_row(name, status, template, ilm_policy, generation, indices_count)

        print()
        console.print(table)
        print()

    def _print_datastream_details_table(self, datastream_details):
        """Print detailed datastream information in table format"""
        console = Console()
        
        # Create main details table
        table = Table.grid(padding=(0, 1))
        table.add_column(style="bold white", no_wrap=True)
        table.add_column(style="cyan")

        table.add_row("🏷️  Name:", datastream_details.get('name', 'N/A'))
        table.add_row("📊 Status:", datastream_details.get('status', 'N/A'))
        table.add_row("📋 Template:", datastream_details.get('template', 'N/A'))
        table.add_row("🔄 Generation:", str(datastream_details.get('generation', 0)))
        table.add_row("📁 Indices Count:", str(len(datastream_details.get('indices', []))))

        panel = Panel(
            table,
            title=f"[bold cyan]📊 Datastream Details[/bold cyan]",
            border_style="cyan",
            padding=(1, 2)
        )

        print()
        console.print(panel)
        print()

    def _handle_datastream_delete(self):
        """Handle datastream deletion with confirmation"""
        print(f"❌ Error: Datastream deletion functionality not yet implemented")
        print("This is a destructive operation that requires careful implementation")
