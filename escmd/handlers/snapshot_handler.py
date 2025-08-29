"""
Snapshot handler for escmd snapshot-related commands.

Handles commands like snapshots list and status.
"""

import json
import re
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from rich.table import Table

from .base_handler import BaseHandler


class SnapshotHandler(BaseHandler):
    """Handler for snapshot-related commands."""
    
    def handle_snapshots(self):
        """
        Handle snapshot-related commands.
        """
        if not hasattr(self.args, 'snapshots_action') or self.args.snapshots_action is None:
            self.es_client.show_message_box("Error", "No snapshots action specified. Use 'list' or 'status' to view snapshots.", message_style="bold white", panel_style="red")
            return

        if self.args.snapshots_action == 'list':
            self._handle_list_snapshots()
        elif self.args.snapshots_action == 'status':
            self._handle_snapshot_status()
        else:
            self.es_client.show_message_box("Error", f"Unknown snapshots action: {self.args.snapshots_action}", message_style="bold white", panel_style="red")

    def _handle_list_snapshots(self):
        """
        List all snapshots from the configured repository.
        """
        # Check if elastic_s3snapshot_repo is configured for this cluster
        elastic_s3snapshot_repo = self.location_config.get('elastic_s3snapshot_repo')

        if not elastic_s3snapshot_repo:
            self.es_client.show_message_box("Configuration Error",
                            f"No 'elastic_s3snapshot_repo' configured for cluster '{self.args.locations}'.\n"
                            f"Please add 'elastic_s3snapshot_repo: \"your-repo-name\"' to the cluster configuration in elastic_servers.yml",
                            message_style="bold white", panel_style="red")
            return

        try:
            # Get snapshots from the configured repository
            snapshots = self.es_client.list_snapshots(elastic_s3snapshot_repo)

            if not snapshots:
                self.es_client.show_message_box("No Snapshots",
                                f"No snapshots found in repository '{elastic_s3snapshot_repo}' or repository doesn't exist.")
                return

            # Apply regex filtering if pattern is provided
            original_count = len(snapshots)
            pattern = getattr(self.args, 'pattern', None)

            if pattern:
                try:
                    compiled_pattern = re.compile(pattern, re.IGNORECASE)
                    snapshots = [s for s in snapshots if compiled_pattern.search(s['snapshot'])]
                except re.error as e:
                    self.es_client.show_message_box("Invalid Pattern", f"Invalid regex pattern '{pattern}': {str(e)}")
                    return

                if not snapshots:
                    self.es_client.show_message_box("No Matches",
                                    f"No snapshots found matching pattern '{pattern}' in repository '{elastic_s3snapshot_repo}'.\n"
                                    f"Total snapshots in repository: {original_count}")
                    return

            # Display snapshots based on format
            format_type = getattr(self.args, 'format', 'table')
            if format_type == 'json':
                self._display_snapshots_json(snapshots, elastic_s3snapshot_repo, pattern, original_count)
            else:
                use_pager = getattr(self.args, 'pager', False)
                self._display_snapshots_table(snapshots, elastic_s3snapshot_repo, pattern, original_count, use_pager=use_pager)

        except Exception as e:
            self.es_client.show_message_box("Error", f"Error listing snapshots: {str(e)}", message_style="bold white", panel_style="red")

    def _display_snapshots_table(self, snapshots, repository_name, pattern=None, original_count=None, use_pager=False):
        """
        Display snapshots in enhanced multi-panel format following the 2.0+ style.
        """
        console = self.console

        # Calculate statistics
        total_snapshots = len(snapshots)
        state_counts = {'SUCCESS': 0, 'FAILED': 0, 'IN_PROGRESS': 0, 'PARTIAL': 0}
        total_indices = 0
        total_failures = 0

        # Analyze snapshots for statistics
        for snapshot in snapshots:
            state = snapshot.get('state', 'UNKNOWN')
            state_counts[state] = state_counts.get(state, 0) + 1
            total_indices += snapshot.get('indices_count', 0)
            total_failures += len(snapshot.get('failures', []))

        # Create title panel with statistics
        if pattern:
            title_text = f"📦 Elasticsearch Snapshots Overview (Repository: {repository_name}, Pattern: {pattern})"
            subtitle_text = f"Total: {total_snapshots} | Success: {state_counts.get('SUCCESS', 0)} | Failed: {state_counts.get('FAILED', 0)} | In Progress: {state_counts.get('IN_PROGRESS', 0)} | Showing {total_snapshots} of {original_count if original_count else total_snapshots}"
        else:
            title_text = f"📦 Elasticsearch Snapshots Overview (Repository: {repository_name})"
            subtitle_text = f"Total: {total_snapshots} | Success: {state_counts.get('SUCCESS', 0)} | Failed: {state_counts.get('FAILED', 0)} | In Progress: {state_counts.get('IN_PROGRESS', 0)} | Total Indices: {total_indices:,}"

        title_panel = Panel(
            Text(title_text, style="bold cyan", justify="center"),
            subtitle=subtitle_text,
            border_style="cyan",
            padding=(1, 2)
        )

        # Create enhanced snapshots table with emoji headers
        table = Table(show_header=True, header_style="bold white", title="📦 Elasticsearch Snapshots", expand=True)
        table.add_column("📸 Snapshot Name", style="cyan", no_wrap=True, overflow="ellipsis")
        table.add_column("🎯 State", justify="center", width=12, no_wrap=True)
        table.add_column("📅 Start Time", style="yellow", width=16, no_wrap=True)
        table.add_column("⏱️ Duration", style="blue", width=8, justify="center", no_wrap=True)
        table.add_column("📊 Indices", style="magenta", width=8, justify="right", no_wrap=True)
        table.add_column("❌ Failures", style="red", width=8, justify="right", no_wrap=True)

        for snapshot in snapshots:
            # Enhanced state formatting with icons
            state = snapshot.get('state', 'UNKNOWN')
            if state == 'SUCCESS':
                state_display = "✅ Success"
                row_style = "green"
            elif state == 'IN_PROGRESS':
                state_display = "⏳ Progress"
                row_style = "yellow"
            elif state == 'FAILED':
                state_display = "❌ Failed"
                row_style = "red"
            elif state == 'PARTIAL':
                state_display = "⚠️ Partial"
                row_style = "yellow"
            else:
                state_display = f"❓ {state}"
                row_style = "white"

            # Format failures count
            failures_count = len(snapshot.get('failures', []))
            failures_text = str(failures_count) if failures_count > 0 else "-"

            # Get values with fallbacks
            snapshot_name = snapshot.get('snapshot', 'N/A')
            start_time = snapshot.get('start_time_formatted', 'N/A')
            duration = snapshot.get('duration', 'N/A')
            indices_count = f"{snapshot.get('indices_count', 0):,}"

            table.add_row(
                snapshot_name,
                state_display,
                start_time,
                duration,
                indices_count,
                failures_text,
                style=row_style
            )

        # Create bottom panels for legend and actions
        # Legend table
        legend_table = Table.grid(padding=(0, 3))
        legend_table.add_column(style="white", no_wrap=True)
        legend_table.add_column(style="white")
        legend_table.add_row("✅ Success:", "Snapshot completed successfully")
        legend_table.add_row("⏳ In Progress:", "Snapshot currently running")
        legend_table.add_row("❌ Failed:", "Snapshot failed to complete")
        legend_table.add_row("⚠️ Partial:", "Snapshot completed with warnings")

        legend_panel = Panel(
            legend_table,
            title="[bold white]🔍 Legend[/bold white]",
            border_style="cyan",
            padding=(1, 1),
            width=50
        )

        # Quick actions panel
        actions_table = Table.grid(padding=(0, 3))
        actions_table.add_column(style="bold magenta", no_wrap=True)
        actions_table.add_column(style="dim white")
        actions_table.add_row("Filter by pattern:", "./escmd.py snapshots list <pattern>")
        actions_table.add_row("Use pager:", "./escmd.py snapshots list --pager")
        actions_table.add_row("JSON output:", "./escmd.py snapshots list --format json")
        actions_table.add_row("Pattern example:", "./escmd.py snapshots list 'logs-app.*'")

        actions_panel = Panel(
            actions_table,
            title="[bold white]🚀 Quick Actions[/bold white]",
            border_style="magenta",
            padding=(1, 1),
            width=45
        )

        # Check if we should use pager for large datasets
        from configuration_manager import ConfigurationManager
        import os

        try:
            config_file = os.path.join(os.path.dirname(__file__), 'elastic_servers.yml')
            config_manager = ConfigurationManager(config_file, os.path.join(os.path.dirname(config_file), 'escmd.json'))

            # Try to get paging settings with fallback to defaults
            paging_enabled = getattr(config_manager, 'get_paging_enabled', lambda: False)()
            paging_threshold = getattr(config_manager, 'get_paging_threshold', lambda: 50)()
        except Exception:
            # Fallback to safe defaults if configuration fails
            paging_enabled = False
            paging_threshold = 50

        should_use_pager = use_pager or (paging_enabled and len(snapshots) > paging_threshold)

        if should_use_pager:
            # Capture all output to pager
            with console.pager():
                console.print()
                console.print(title_panel)
                console.print()
                console.print(table)
                console.print()
                console.print(Columns([legend_panel, actions_panel], expand=False))
                console.print()
        else:
            # Normal display with enhanced layout
            print()
            console.print(title_panel)
            print()
            console.print(table)
            print()
            console.print(Columns([legend_panel, actions_panel], expand=False))
            print()

    def _display_snapshots_json(self, snapshots, repository_name, pattern=None, original_count=None):
        """
        Display snapshots in JSON format.
        """
        # Create output structure
        output = {
            "repository": repository_name,
            "total_snapshots": len(snapshots),
            "snapshots": snapshots
        }

        # Add filtering information if pattern was used
        if pattern and original_count:
            output["filter_pattern"] = pattern
            output["original_total"] = original_count
            output["filtered"] = True
        else:
            output["filtered"] = False

        # Output JSON
        self.es_client.pretty_print_json(output)

    def _handle_snapshot_status(self):
        """
        Handle snapshot status command to show detailed status of a specific snapshot.
        """        
        # Get snapshot name from arguments
        snapshot_name = self.args.snapshot_name
        
        # Determine repository to use
        repository_name = getattr(self.args, 'repository', None)
        if not repository_name:
            # Use configured repository for this cluster
            repository_name = self.location_config.get('elastic_s3snapshot_repo')
            
        if not repository_name:
            self.es_client.show_message_box("Configuration Error",
                            f"No snapshot repository specified.\n"
                            f"Either use --repository option or configure 'elastic_s3snapshot_repo' for cluster '{self.current_location}'.\n"
                            f"Please add 'elastic_s3snapshot_repo: \"your-repo-name\"' to the cluster configuration in elastic_servers.yml",
                            message_style="bold white", panel_style="red")
            return

        try:
            # Get snapshot status from Elasticsearch
            snapshot_status = self.es_client.get_snapshot_status(repository_name, snapshot_name)
            
            if not snapshot_status:
                self.es_client.show_message_box("Snapshot Not Found",
                                f"Snapshot '{snapshot_name}' not found in repository '{repository_name}'.\n"
                                f"Use './escmd.py snapshots list' to see available snapshots.",
                                message_style="bold white", panel_style="red")
                return

            # Display the status based on format
            if self.args.format == 'json':
                self.es_client.pretty_print_json(snapshot_status)
            else:
                self.es_client.display_snapshot_status(snapshot_status, repository_name)

        except Exception as e:
            self.es_client.show_message_box("Error", f"Error getting snapshot status: {str(e)}", message_style="bold white", panel_style="red")
