import json
import re
from rich import print
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from utils import show_message_box, find_matching_index, find_matching_node, show_locations, print_json_as_table
from configuration_manager import ConfigurationManager
import os

class CommandHandler:

    def handle_dangling(self):
        """Handle dangling indices command - list or delete based on arguments."""
        from rich.panel import Panel
        from rich.text import Text
        from rich.columns import Columns
        from rich.table import Table, Table as InnerTable
        import json

        console = self.console

        try:
            # Check if deletion is requested
            if hasattr(self.args, 'delete') and self.args.delete:
                if hasattr(self.args, 'uuid') and self.args.uuid:
                    self._handle_dangling_delete()
                    return
                else:
                    error_panel = Panel(
                        Text(f"❌ UUID is required for deletion.\nUsage: ./escmd.py dangling <uuid> --delete", 
                             style="bold red", justify="center"),
                        title="Missing UUID Parameter",
                        border_style="red",
                        padding=(1, 2)
                    )
                    print()
                    console.print(error_panel)
                    print()
                    return

            # Regular listing functionality (existing code)
            # Get dangling indices data first
            dangling = self.es_client.list_dangling_indices()

            # Handle JSON format - return immediately with pure JSON output
            if getattr(self.args, 'format', 'table') == 'json':
                print(json.dumps(dangling, indent=2))
                return

            # Get cluster information for context (only for table format)
            try:
                health_data = self.es_client.get_cluster_health()
                cluster_name = health_data.get('cluster_name', 'Unknown')
                total_nodes = health_data.get('number_of_nodes', 0)
            except:
                cluster_name = 'Unknown'
                total_nodes = 0

            # Create title panel
            title_panel = Panel(
                Text(f"🔍 Dangling Indices Analysis", style="bold orange1", justify="center"),
                subtitle=f"Cluster: {cluster_name} | Nodes: {total_nodes}",
                border_style="orange1",
                padding=(1, 2)
            )

            print()
            console.print(title_panel)
            print()

            # Check if there are dangling indices
            dangling_indices = dangling.get('dangling_indices', [])
            
            if not dangling_indices:
                # No dangling indices found - success case
                success_panel = Panel(
                    Text("🎉 No dangling indices found in the cluster!\n\n"
                         "This indicates that:\n"
                         "• All indices are properly assigned to nodes\n"
                         "• No orphaned index metadata exists\n"
                         "• Cluster index management is healthy",
                         style="green", justify="center"),
                    title="✅ Cluster Index Status: Clean",
                    border_style="green",
                    padding=(1, 2)
                )
                console.print(success_panel)
                
                # Create quick actions panel
                actions_table = InnerTable(show_header=False, box=None, padding=(0, 1))
                actions_table.add_column("Action", style="bold cyan", no_wrap=True)
                actions_table.add_column("Command", style="dim white")
                
                actions_table.add_row("Check cluster health:", "./escmd.py health")
                actions_table.add_row("List all indices:", "./escmd.py indices")
                actions_table.add_row("View cluster nodes:", "./escmd.py nodes")
                actions_table.add_row("Monitor recovery:", "./escmd.py recovery")

                actions_panel = Panel(
                    actions_table,
                    title="🚀 Related Commands",
                    border_style="cyan",
                    padding=(1, 2)
                )
                
                print()
                console.print(actions_panel)
                print()
                return

            # Calculate statistics
            total_dangling = len(dangling_indices)
            unique_nodes = set()
            creation_dates = []
            
            for idx in dangling_indices:
                node_ids = idx.get('node_ids', [])
                unique_nodes.update(node_ids)
                creation_date = idx.get('creation_date', 'Unknown')
                if creation_date != 'Unknown':
                    creation_dates.append(creation_date)

            # Create statistics panel
            stats_table = InnerTable(show_header=False, box=None, padding=(0, 1))
            stats_table.add_column("Label", style="bold", no_wrap=True)
            stats_table.add_column("Icon", justify="left", width=3)
            stats_table.add_column("Value", no_wrap=True)

            stats_table.add_row("Total Dangling:", "⚠️", f"{total_dangling:,}")
            stats_table.add_row("Affected Nodes:", "🖥️", f"{len(unique_nodes):,}")
            stats_table.add_row("Cluster Nodes:", "📊", f"{total_nodes:,}")
            
            if creation_dates:
                # Find oldest creation date
                oldest_date = min(creation_dates)
                stats_table.add_row("Oldest Found:", "📅", oldest_date)

            stats_panel = Panel(
                stats_table,
                title="📊 Dangling Indices Summary",
                border_style="yellow",
                padding=(1, 2)
            )

            # Create information panel about dangling indices
            info_text = ("🔍 About Dangling Indices:\n\n"
                        "• Indices that exist on disk but are not part of cluster metadata\n"
                        "• Often caused by node failures or split-brain scenarios\n"
                        "• Can be imported back to cluster or deleted manually\n"
                        "• May contain important data that needs recovery")

            info_panel = Panel(
                info_text,
                title="ℹ️ Information",
                border_style="blue",
                padding=(1, 2)
            )

            # Display summary panels
            console.print(Columns([stats_panel, info_panel], expand=True))
            print()

            # Get node mapping once for efficient hostname resolution
            node_id_to_hostname_map = self.es_client.get_node_id_to_hostname_map()

            # Create detailed dangling indices table
            table = Table(show_header=True, header_style="bold white", expand=True)
            table.add_column("🆔 Index UUID", style="cyan", no_wrap=True, width=38)
            table.add_column("📅 Creation Date", style="yellow", width=20, no_wrap=True)
            table.add_column("🖥️ Hostnames", style="magenta", no_wrap=False)
            table.add_column("📊 Node Count", style="white", width=12, justify="center")

            # Add rows to the table
            for idx in dangling_indices:
                index_uuid = idx.get('index_uuid', 'N/A')
                creation_date = idx.get('creation_date', 'N/A')
                node_ids = idx.get('node_ids', [])
                node_count = len(node_ids)
                
                # Resolve node IDs to hostnames using pre-built mapping
                if node_ids:
                    hostnames = self.es_client.resolve_node_ids_to_hostnames(node_ids, node_id_to_hostname_map)
                    # Format hostnames - truncate if too many
                    if len(hostnames) > 3:
                        node_display = ', '.join(hostnames[:3]) + f' (+{len(hostnames)-3} more)'
                    else:
                        node_display = ', '.join(hostnames)
                else:
                    node_display = 'N/A'

                # Color coding based on node count
                if node_count > 1:
                    row_style = "yellow"  # Multiple nodes have this dangling index
                elif node_count == 1:
                    row_style = "red"     # Only one node has this index
                else:
                    row_style = "dim"     # No nodes specified

                table.add_row(
                    index_uuid,
                    creation_date,
                    node_display,
                    str(node_count),
                    style=row_style
                )

            # Create table panel
            table_panel = Panel(
                table,
                title="⚠️ Dangling Indices Details",
                border_style="orange1",
                padding=(1, 2)
            )

            console.print(table_panel)
            print()

            # Create warning and actions panel
            warning_text = ("⚠️ WARNING: Dangling indices detected!\n\n"
                           f"Found {total_dangling} dangling indices across {len(unique_nodes)} nodes.\n"
                           "These indices contain data that is not accessible through normal cluster operations.\n\n"
                           "🚨 IMPORTANT: Review these indices carefully before taking action.\n"
                           "Consider consulting Elasticsearch documentation for recovery procedures.")

            warning_panel = Panel(
                warning_text,
                title="🚨 Action Required",
                border_style="red",
                padding=(1, 2)
            )

            # Create recovery actions panel
            recovery_table = InnerTable(show_header=False, box=None, padding=(0, 1))
            recovery_table.add_column("Action", style="bold red", no_wrap=True)
            recovery_table.add_column("Description", style="dim white")

            recovery_table.add_row("Delete Index:", f"./escmd.py dangling <uuid> --delete")
            recovery_table.add_row("Import Index:", "Use ES API to import dangling index back to cluster")
            recovery_table.add_row("Backup Data:", "Create backup before any recovery actions")
            recovery_table.add_row("Check Logs:", "Review Elasticsearch logs for root cause")

            recovery_panel = Panel(
                recovery_table,
                title="🔧 Recovery Options",
                border_style="magenta",
                padding=(1, 2)
            )

            console.print(Columns([warning_panel, recovery_panel], expand=True))
            print()

        except Exception as e:
            error_panel = Panel(
                Text(f"❌ Error retrieving dangling indices: {str(e)}", style="bold red", justify="center"),
                subtitle="Check cluster connectivity and permissions",
                border_style="red",
                padding=(1, 2)
            )
            print()
            console.print(error_panel)
            print()

    def _handle_dangling_delete(self):
        """Handle deletion of a specific dangling index by UUID."""
        console = self.console
        from rich.panel import Panel
        from rich.text import Text
        from rich.table import Table as InnerTable
        from rich.columns import Columns
        import json

        uuid = self.args.uuid

        try:
            # First, verify the dangling index exists and get its details
            with console.status(f"Verifying dangling index {uuid}...") as status:
                dangling = self.es_client.list_dangling_indices()

            dangling_indices = dangling.get('dangling_indices', [])
            target_index = None

            # Find the specific dangling index by UUID
            for idx in dangling_indices:
                if idx.get('index_uuid') == uuid:
                    target_index = idx
                    break

            if not target_index:
                error_panel = Panel(
                    Text(f"❌ Dangling index with UUID '{uuid}' not found.\n\n"
                         f"Use './escmd.py dangling' to list available dangling indices.",
                         style="bold red", justify="center"),
                    title="UUID Not Found",
                    border_style="red",
                    padding=(1, 2)
                )
                print()
                console.print(error_panel)
                print()
                return

            # Get cluster information for context
            try:
                health_data = self.es_client.get_cluster_health()
                cluster_name = health_data.get('cluster_name', 'Unknown')
            except:
                cluster_name = 'Unknown'

            # Get node mapping once for efficient hostname resolution
            node_id_to_hostname_map = self.es_client.get_node_id_to_hostname_map()

            # Show details of the index to be deleted
            details_table = InnerTable(show_header=False, box=None, padding=(0, 1))
            details_table.add_column("Label", style="bold white", no_wrap=True)
            details_table.add_column("Value", style="yellow")

            details_table.add_row("🆔 Index UUID:", target_index.get('index_uuid', 'N/A'))
            details_table.add_row("📅 Creation Date:", target_index.get('creation_date', 'N/A'))
            
            node_ids = target_index.get('node_ids', [])
            node_count = len(node_ids)
            details_table.add_row("🖥️ Affected Nodes:", str(node_count))
            
            # Show hostnames if there are any node IDs
            if node_ids:
                hostnames = self.es_client.resolve_node_ids_to_hostnames(node_ids, node_id_to_hostname_map)
                if len(hostnames) <= 3:
                    details_table.add_row("🏠 Hostnames:", ', '.join(hostnames))
                else:
                    details_table.add_row("🏠 Hostnames:", ', '.join(hostnames[:3]) + f' (+{len(hostnames)-3} more)')

            details_panel = Panel(
                details_table,
                title=f"🗑️ Dangling Index to be Deleted",
                border_style="yellow",
                padding=(1, 2)
            )

            # Create warning panel
            warning_text = (f"⚠️ You are about to permanently delete the dangling index:\n"
                           f"UUID: {uuid}\n\n"
                           f"This operation will:\n"
                           f"• Remove the dangling index from all affected nodes ({node_count} nodes)\n"
                           f"• Permanently delete any data contained in this index\n"
                           f"• Cannot be undone\n\n"
                           f"🚨 Make sure you have backed up any important data!")

            warning_panel = Panel(
                warning_text,
                title="⚠️ DANGER: Destructive Operation",
                border_style="red",
                padding=(1, 2)
            )

            # Display information
            print()
            console.print(details_panel)
            print()
            console.print(warning_panel)

            # Check for automatic confirmation flag
            if hasattr(self.args, 'yes_i_really_mean_it') and self.args.yes_i_really_mean_it:
                console.print(f"\n🤖 [bold yellow]Automatic confirmation enabled with --yes-i-really-mean-it flag[/bold yellow]")
                console.print(f"🗑️ [bold red]Proceeding with deletion of dangling index {uuid}...[/bold red]")
            else:
                # Confirmation prompt
                print(f"🚨 [bold red]DANGER: This action cannot be undone![/bold red]")
                print(f"You are about to permanently delete dangling index '[bold yellow]{uuid}[/bold yellow]'.")

                try:
                    # Show short UUID for confirmation to make it more user-friendly
                    short_uuid = uuid[:8] if len(uuid) > 8 else uuid
                    confirmation = input(f"\nType 'DELETE {short_uuid}' to confirm deletion: ").strip()

                    if confirmation != f"DELETE {short_uuid}":
                        console.print(f"\n❌ [bold yellow]Deletion cancelled - confirmation text did not match[/bold yellow]")
                        console.print(f"Expected: 'DELETE {short_uuid}'")
                        console.print(f"Got: '{confirmation}'")
                        return

                except KeyboardInterrupt:
                    console.print(f"\n❌ [bold yellow]Deletion cancelled by user[/bold yellow]")
                    return

            # Perform deletion
            console.print(f"\n🗑️ [bold red]Deleting dangling index {uuid}...[/bold red]")

            with console.status("Performing deletion...") as status:
                delete_result = self.es_client.delete_dangling_index(uuid)

                # Check for errors in the result
                if 'error' in delete_result:
                    error_panel = Panel(
                        Text(f"❌ Failed to delete dangling index:\n{delete_result['error']}",
                             style="bold red", justify="center"),
                        title="Deletion Failed",
                        border_style="red",
                        padding=(1, 2)
                    )
                    print()
                    console.print(error_panel)
                    print()
                    return

                # Success confirmation
                success_text = (f"✅ Dangling index has been successfully deleted!\n\n"
                               f"• UUID: {uuid}\n"
                               f"• Affected nodes: {node_count}\n"
                               f"• Operation completed successfully\n\n"
                               f"The dangling index has been permanently removed from the cluster.")

                success_panel = Panel(
                    Text(success_text, style="green"),
                    title="🎉 Deletion Successful",
                    border_style="green",
                    padding=(1, 2)
                )

                print()
                console.print(success_panel)

                # Show next steps
                actions_table = InnerTable(show_header=False, box=None, padding=(0, 1))
                actions_table.add_column("Action", style="bold cyan", no_wrap=True)
                actions_table.add_column("Command", style="dim white")

                actions_table.add_row("Check remaining:", "./escmd.py dangling")
                actions_table.add_row("Verify cluster health:", "./escmd.py health")
                actions_table.add_row("List all indices:", "./escmd.py indices")
                actions_table.add_row("View nodes:", "./escmd.py nodes")

                actions_panel = Panel(
                    actions_table,
                    title="🚀 Next Steps",
                    border_style="cyan",
                    padding=(1, 2)
                )

                print()
                console.print(actions_panel)
                print()

        except KeyboardInterrupt:
            console.print(f"\n❌ [bold yellow]Deletion cancelled by user[/bold yellow]")
            return

        except Exception as e:
            error_panel = Panel(
                Text(f"❌ Error during deletion: {str(e)}", style="bold red", justify="center"),
                subtitle="Check cluster connectivity and permissions",
                border_style="red",
                padding=(1, 2)
            )
            print()
            console.print(error_panel)
            print()
    def __init__(self, es_client, args, console, config_file, location_config, current_location=None):
        self.es_client = es_client
        self.args = args
        self.console = console
        self.config_file = config_file
        self.location_config = location_config
        self.current_location = current_location

    def handle_ping(self):
        """Enhanced ping command with Rich formatting and detailed connection information."""
        import json
        from rich.panel import Panel
        from rich.text import Text
        from rich.columns import Columns
        from rich.table import Table as InnerTable

        console = self.console

        try:
            # Test the connection
            if self.es_client.ping():
                # Get comprehensive cluster information
                cluster_connection_info = self._get_cluster_connection_info()

                # Get cluster health for additional context
                try:
                    health_data = self.es_client.get_cluster_health()
                    cluster_name = health_data.get('cluster_name', 'Unknown')
                    cluster_status = health_data.get('cluster_status', 'unknown')
                    total_nodes = health_data.get('number_of_nodes', 0)
                    data_nodes = health_data.get('number_of_data_nodes', 0)
                except:
                    cluster_name = 'Unknown'
                    cluster_status = 'unknown'
                    total_nodes = 0
                    data_nodes = 0

                # Handle JSON format
                if getattr(self.args, 'format', 'table') == 'json':
                    ping_data = {
                        'connection_successful': True,
                        'cluster_name': cluster_name,
                        'cluster_status': cluster_status,
                        'connection_details': {
                            'host': self.es_client.host1,
                            'port': self.es_client.port,
                            'ssl_enabled': self.es_client.use_ssl,
                            'verify_certs': self.es_client.verify_certs,
                            'username': self.es_client.elastic_username if self.es_client.elastic_username else None
                        },
                        'cluster_overview': {
                            'total_nodes': total_nodes,
                            'data_nodes': data_nodes
                        }
                    }
                    print(json.dumps(ping_data, indent=2))
                    return True

                # Create title panel
                title_panel = Panel(
                    Text(f"🏓 Elasticsearch Connection Test", style="bold green", justify="center"),
                    subtitle=f"✅ Connection Successful | Cluster: {cluster_name} | Status: {cluster_status.title()}",
                    border_style="green",
                    padding=(1, 2)
                )

                # Create connection details panel
                connection_table = InnerTable(show_header=False, box=None, padding=(0, 1))
                connection_table.add_column("Label", style="bold", no_wrap=True)
                connection_table.add_column("Icon", justify="left", width=3)
                connection_table.add_column("Value", no_wrap=True)

                connection_table.add_row("Host:", "🌐", self.es_client.host1)
                connection_table.add_row("Port:", "🔌", str(self.es_client.port))
                connection_table.add_row("SSL Enabled:", "🔒", "Yes" if self.es_client.use_ssl else "No")
                connection_table.add_row("Verify Certs:", "📜", "Yes" if self.es_client.verify_certs else "No")

                if self.es_client.elastic_username:
                    connection_table.add_row("Username:", "👤", self.es_client.elastic_username)
                    connection_table.add_row("Password:", "🔐", "***" + self.es_client.elastic_password[-2:] if len(self.es_client.elastic_password) > 2 else "***")
                else:
                    connection_table.add_row("Authentication:", "🔓", "None")

                connection_panel = Panel(
                    connection_table,
                    title="🔗 Connection Details",
                    border_style="blue",
                    padding=(1, 2)
                )

                # Create cluster overview panel
                overview_table = InnerTable(show_header=False, box=None, padding=(0, 1))
                overview_table.add_column("Label", style="bold", no_wrap=True)
                overview_table.add_column("Icon", justify="left", width=3)
                overview_table.add_column("Value", no_wrap=True)

                status_icon = "🟢" if cluster_status == 'green' else "🟡" if cluster_status == 'yellow' else "🔴"
                overview_table.add_row("Cluster Name:", "🏢", cluster_name)
                overview_table.add_row("Status:", status_icon, cluster_status.title())
                overview_table.add_row("Total Nodes:", "🖥️", str(total_nodes))
                overview_table.add_row("Data Nodes:", "💾", str(data_nodes))

                overview_panel = Panel(
                    overview_table,
                    title="📊 Cluster Overview",
                    border_style="cyan",
                    padding=(1, 2)
                )

                # Create quick actions panel
                actions_table = InnerTable(show_header=False, box=None, padding=(0, 1))
                actions_table.add_column("Action", style="bold magenta", no_wrap=True)
                actions_table.add_column("Command", style="dim white")

                actions_table.add_row("Check health:", "./escmd.py health")
                actions_table.add_row("View nodes:", "./escmd.py nodes")
                actions_table.add_row("List indices:", "./escmd.py indices")
                actions_table.add_row("View settings:", "./escmd.py settings")
                actions_table.add_row("JSON output:", "./escmd.py ping --format json")

                actions_panel = Panel(
                    actions_table,
                    title="🚀 Next Steps",
                    border_style="magenta",
                    padding=(1, 2)
                )

                # Display everything
                print()
                console.print(title_panel)
                print()
                console.print(Columns([connection_panel, overview_panel], expand=True))
                print()
                console.print(actions_panel)
                print()

                return True
            else:
                # Connection failed
                if getattr(self.args, 'format', 'table') == 'json':
                    error_data = {
                        'connection_successful': False,
                        'error': 'Connection failed',
                        'host': self.es_client.host1,
                        'port': self.es_client.port
                    }
                    print(json.dumps(error_data, indent=2))
                    return False

                error_panel = Panel(
                    Text(f"❌ Connection Failed", style="bold red", justify="center"),
                    subtitle=f"Unable to connect to {self.es_client.host1}:{self.es_client.port}",
                    border_style="red",
                    padding=(1, 2)
                )
                print()
                console.print(error_panel)
                print()
                return False

        except Exception as e:
            # Handle connection errors
            if getattr(self.args, 'format', 'table') == 'json':
                error_data = {
                    'connection_successful': False,
                    'error': str(e),
                    'host': self.es_client.host1,
                    'port': self.es_client.port
                }
                print(json.dumps(error_data, indent=2))
                return False

            from utils import show_message_box
            show_message_box("Connection Error", f"❌ Connection Error: {str(e)}\nFailed to ping {self.es_client.host1}:{self.es_client.port}", message_style="bold white", panel_style="red")
            return False

    def _get_current_exclusions(self):
        """Get list of currently excluded hosts."""
        try:
            settings = self.es_client.es.cluster.get_settings()
            exclusions_setting = settings.get('transient', {}).get('cluster', {}).get('routing', {}).get('allocation', {}).get('exclude', {}).get('_name', '')

            if exclusions_setting:
                return [host.strip() for host in exclusions_setting.split(',') if host.strip()]
            return []
        except Exception as e:
            print(f"Error getting current exclusions: {str(e)}")
            return []

    def _set_exclusions(self, hostnames):
        """Set exclusions to specific list of hostnames."""
        try:
            exclusion_string = ','.join(hostnames)
            settings = {
                "transient": {
                    "cluster.routing.allocation.exclude._name": exclusion_string
                }
            }
            self.es_client.es.cluster.put_settings(body=settings)
            return True
        except Exception as e:
            print(f"Error setting exclusions: {str(e)}")
            return False

    def _reset_all_exclusions(self):
        """Reset all exclusions (same as existing reset functionality)."""
        try:
            settings = {
                "transient": {
                    "cluster.routing.allocation.exclude._name": None
                }
            }
            self.es_client.es.cluster.put_settings(body=settings)
            return True
        except Exception as e:
            print(f"Error resetting exclusions: {str(e)}")
            return False

    def handle_allocation(self):
        # Handle main allocation actions
        if not hasattr(self.args, 'allocation_action') or self.args.allocation_action is None:
            # Default to display if no action specified
            format_type = getattr(self.args, 'format', 'table')
            if format_type == 'json':
                settings_json = self.es_client.show_cluster_settings()
                print(settings_json)
            else:
                self.es_client.print_enhanced_allocation_settings()
            return

        if self.args.allocation_action == "display":
            format_type = getattr(self.args, 'format', 'table')
            if format_type == 'json':
                settings_json = self.es_client.show_cluster_settings()
                print(settings_json)
            else:
                self.es_client.print_enhanced_allocation_settings()
            return

        elif self.args.allocation_action == "enable":
            success = self.es_client.change_shard_allocation('all')
            if success:
                show_message_box("Success", "✅ Successfully enabled shard allocation (all shards).", message_style="bold white", panel_style="green")
                # Show updated settings
                format_type = getattr(self.args, 'format', 'table')
                if format_type == 'json':
                    settings_json = self.es_client.show_cluster_settings()
                    print(settings_json)
                else:
                    self.es_client.print_enhanced_allocation_settings()
            else:
                show_message_box("Error", "❌ An ERROR occurred trying to enable allocation", message_style="bold white", panel_style="red")
                exit(1)
            return

        elif self.args.allocation_action == "disable":
            success = self.es_client.change_shard_allocation('primary')
            if success:
                show_message_box("Success", "⚠️ Successfully disabled shard allocation (primaries only).\nReplica shards will not be allocated or moved.", message_style="bold white", panel_style="yellow")
                # Show updated settings
                format_type = getattr(self.args, 'format', 'table')
                if format_type == 'json':
                    settings_json = self.es_client.show_cluster_settings()
                    print(settings_json)
                else:
                    self.es_client.print_enhanced_allocation_settings()
            else:
                show_message_box("Error", "❌ An ERROR occurred trying to disable allocation", message_style="bold white", panel_style="red")
                exit(1)
            return

        elif self.args.allocation_action == "exclude":
            # Handle exclude subcommands
            if not hasattr(self.args, 'exclude_action') or self.args.exclude_action is None:
                show_message_box("Error", "No exclude action specified. Use 'add', 'remove', or 'reset'.", message_style="bold white", panel_style="red")
                return

            if self.args.exclude_action == "add":
                if not hasattr(self.args, 'hostname') or not self.args.hostname:
                    show_message_box("Error", "Hostname is required for exclude add operation", message_style="bold white", panel_style="red")
                    return

                success = self.es_client.exclude_node_from_allocation(self.args.hostname)
                if success:
                    show_message_box("Success", f"✅ Successfully excluded node '{self.args.hostname}' from allocation.\nShards will be moved away from this node.", message_style="bold white", panel_style="green")
                    # Show updated settings
                    format_type = getattr(self.args, 'format', 'table')
                    if format_type == 'json':
                        settings_json = self.es_client.show_cluster_settings()
                        print(settings_json)
                    else:
                        self.es_client.print_enhanced_allocation_settings()
                else:
                    show_message_box("Error", "❌ An ERROR occurred trying to exclude node from allocation", message_style="bold white", panel_style="red")
                    exit(1)
                return

            elif self.args.exclude_action == "remove":
                if not hasattr(self.args, 'hostname') or not self.args.hostname:
                    show_message_box("Error", "Hostname is required for exclude remove operation", message_style="bold white", panel_style="red")
                    return
                self.handle_allocation_remove()
                return

            elif self.args.exclude_action == "reset":
                success = self.es_client.reset_node_allocation_exclusion()
                if success:
                    show_message_box("Success", "✅ Successfully reset node allocation exclusions.\nAll nodes are now available for allocation.", message_style="bold white", panel_style="green")
                    # Show updated settings
                    format_type = getattr(self.args, 'format', 'table')
                    if format_type == 'json':
                        settings_json = self.es_client.show_cluster_settings()
                        print(settings_json)
                    else:
                        self.es_client.print_enhanced_allocation_settings()
                else:
                    show_message_box("Error", "❌ An ERROR occurred trying to reset node allocation exclusion", message_style="bold white", panel_style="red")
                    exit(1)
                return

        elif self.args.allocation_action == "explain":
            self.handle_allocation_explain()
            return
        else:
            show_message_box("Error", f"Unknown allocation action: {self.args.allocation_action}", message_style="bold white", panel_style="red")

    def handle_allocation_remove(self):
        """Remove a specific host from the exclusion list."""
        hostname = self.args.hostname

        # Get current exclusions
        current_exclusions = self._get_current_exclusions()

        if not current_exclusions:
            show_message_box("Info", "ℹ️ No hosts are currently excluded from allocation", message_style="bold white", panel_style="blue")
            return

        # Check if hostname is in exclusion list
        if hostname not in current_exclusions:
            show_message_box("Info", f"ℹ️ Host '{hostname}' is not in the exclusion list.\n\nCurrently excluded hosts:\n• {chr(10).join(['• ' + host for host in current_exclusions])}", message_style="bold white", panel_style="blue")
            return

        # Remove hostname from list
        updated_exclusions = [host for host in current_exclusions if host != hostname]

        # Apply updated exclusions
        if updated_exclusions:
            # Set exclusions with remaining hosts
            success = self._set_exclusions(updated_exclusions)
            if success:
                show_message_box("Success", f"✅ Successfully removed '{hostname}' from exclusion list.\n\nRemaining excluded hosts:\n• {chr(10).join(['• ' + host for host in updated_exclusions])}", message_style="bold white", panel_style="green")
                # Show updated settings
                format_type = getattr(self.args, 'format', 'table')
                if format_type == 'json':
                    settings_json = self.es_client.show_cluster_settings()
                    print(settings_json)
                else:
                    self.es_client.print_enhanced_allocation_settings()
            else:
                show_message_box("Error", f"❌ Failed to remove '{hostname}' from exclusion list", message_style="bold white", panel_style="red")
        else:
            # Reset if no hosts remain
            success = self._reset_all_exclusions()
            if success:
                show_message_box("Success", f"✅ Successfully removed '{hostname}' from exclusion list.\n\nNo hosts remain excluded - all nodes are available for allocation.", message_style="bold white", panel_style="green")
                # Show updated settings
                format_type = getattr(self.args, 'format', 'table')
                if format_type == 'json':
                    settings_json = self.es_client.show_cluster_settings()
                    print(settings_json)
                else:
                    self.es_client.print_enhanced_allocation_settings()
            else:
                show_message_box("Error", f"❌ Failed to remove '{hostname}' from exclusion list", message_style="bold white", panel_style="red")

    def handle_allocation_explain(self):
        """
        Handle allocation explain command.
        Provides detailed allocation information for a specific index/shard.
        """
        try:
            index_name = self.args.index
            shard_number = getattr(self.args, 'shard', 0)

            # Auto-detect primary vs replica if not specified
            if hasattr(self.args, 'primary') and self.args.primary:
                is_primary = True
            else:
                # Auto-detect by checking shard status
                try:
                    shards_data = self.es_client.get_shards_as_dict()
                    index_shards = [s for s in shards_data if s['index'] == index_name and s['shard'] == str(shard_number)]

                    if index_shards:
                        # If we have both primary and replica, prefer primary for explanation
                        primary_shard = next((s for s in index_shards if s['prirep'] == 'p'), index_shards[0])
                        is_primary = primary_shard['prirep'] == 'p'
                    else:
                        # Default to primary if we can't find the shard
                        is_primary = True
                except:
                    # Fallback to primary if detection fails
                    is_primary = True

            # Get allocation explanation
            explain_result = self.es_client.get_enhanced_allocation_explain(index_name, shard_number, is_primary)

            if self.args.format == 'json':
                print(json.dumps(explain_result, indent=2))
            else:
                self.es_client.print_allocation_explain_results(explain_result)

        except Exception as e:
            from utils import show_message_box
            show_message_box("Error", f"Failed to explain allocation for {self.args.index}: {str(e)}", message_style="bold white", panel_style="red")

    def handle_current_master(self):
        import json
        master_node_id = self.es_client.get_master_node()
        if self.args.format == 'json':
            # Get comprehensive master node information for JSON output
            try:
                nodes = self.es_client.get_nodes()
                health_data = self.es_client.get_cluster_health()

                # Find the master node details
                master_node = None
                for node in nodes:
                    if node.get('name') == master_node_id:
                        master_node = node
                        break

                if master_node:
                    # Try to get more detailed node information
                    try:
                        # Get additional node details from nodes.info() API
                        node_info_response = self.es_client.es.nodes.info(node_id=master_node.get('nodeid', '*'))
                        node_details = None

                        # Find the specific node in the response
                        if 'nodes' in node_info_response:
                            for node_id, node_data in node_info_response['nodes'].items():
                                if node_data.get('name') == master_node_id:
                                    node_details = node_data
                                    break

                        # Build master data with available information
                        roles = master_node.get('roles', [])
                        master_node_info = {
                            'name': master_node.get('name'),
                            'hostname': master_node.get('hostname'),
                            'node_id': master_node.get('nodeid'),
                            'roles': roles,
                            'is_dedicated_master': len(roles) == 1 and 'master' in roles,
                            'is_data_node': any(role.startswith('data') for role in roles)
                        }

                        # Only include per-node stats for data nodes (where they're meaningful)
                        if any(role.startswith('data') for role in roles):
                            master_node_info.update({
                                'documents_on_node': master_node.get('indices', 0),
                                'shards_on_node': master_node.get('shards', 0)
                            })

                        # Add detailed info if available
                        if node_details:
                            master_node_info.update({
                                'transport_address': node_details.get('transport_address'),
                                'ip': node_details.get('ip'),
                                'version': node_details.get('version'),
                                'jvm_version': node_details.get('jvm', {}).get('version'),
                                'os_name': node_details.get('os', {}).get('name'),
                                'os_version': node_details.get('os', {}).get('version')
                            })

                        # Extract available master node data
                        master_data = {
                            'master_node_name': master_node_id,
                            'master_node_details': master_node_info,
                            'cluster_overview': {
                                'cluster_name': health_data.get('cluster_name', 'Unknown'),
                                'cluster_status': health_data.get('cluster_status', 'unknown'),
                                'total_nodes': health_data.get('number_of_nodes', 0),
                                'data_nodes': health_data.get('number_of_data_nodes', 0),
                                'active_primary_shards': health_data.get('active_primary_shards', 0),
                                'active_shards': health_data.get('active_shards', 0)
                            }
                        }

                    except Exception:
                        # Fallback if nodes.info() API fails
                        roles = master_node.get('roles', [])
                        fallback_node_info = {
                            'name': master_node.get('name'),
                            'hostname': master_node.get('hostname'),
                            'node_id': master_node.get('nodeid'),
                            'roles': roles,
                            'is_dedicated_master': len(roles) == 1 and 'master' in roles,
                            'is_data_node': any(role.startswith('data') for role in roles)
                        }

                        # Only include per-node stats for data nodes
                        if any(role.startswith('data') for role in roles):
                            fallback_node_info.update({
                                'documents_on_node': master_node.get('indices', 0),
                                'shards_on_node': master_node.get('shards', 0)
                            })

                        master_data = {
                            'master_node_name': master_node_id,
                            'master_node_details': fallback_node_info,
                            'cluster_overview': {
                                'cluster_name': health_data.get('cluster_name', 'Unknown'),
                                'cluster_status': health_data.get('cluster_status', 'unknown'),
                                'total_nodes': health_data.get('number_of_nodes', 0),
                                'data_nodes': health_data.get('number_of_data_nodes', 0),
                                'active_primary_shards': health_data.get('active_primary_shards', 0),
                                'active_shards': health_data.get('active_shards', 0)
                            }
                        }
                else:
                    # Fallback if detailed node info not found
                    master_data = {
                        'master_node_name': master_node_id,
                        'master_node_details': None,
                        'cluster_overview': {
                            'cluster_name': health_data.get('cluster_name', 'Unknown'),
                            'cluster_status': health_data.get('cluster_status', 'unknown'),
                            'total_nodes': health_data.get('number_of_nodes', 0),
                            'data_nodes': health_data.get('number_of_data_nodes', 0),
                            'active_primary_shards': health_data.get('active_primary_shards', 0),
                            'active_shards': health_data.get('active_shards', 0)
                        }
                    }

                print(json.dumps(master_data, indent=2))

            except Exception as e:
                # Fallback to simple output if there's an error
                master_data = {
                    'master_node_name': master_node_id,
                    'error': f"Error retrieving detailed information: {str(e)}"
                }
                print(json.dumps(master_data, indent=2))
        else:
            self.es_client.print_enhanced_current_master(master_node_id)

    def handle_flush(self):
        """Enhanced flush command with Rich formatting and operation details."""
        from rich.panel import Panel
        from rich.text import Text
        from rich.columns import Columns
        from rich.table import Table as InnerTable

        console = self.console

        try:
            # Get cluster information for context
            try:
                health_data = self.es_client.get_cluster_health()
                cluster_name = health_data.get('cluster_name', 'Unknown')
                total_nodes = health_data.get('number_of_nodes', 0)
            except:
                cluster_name = 'Unknown'
                total_nodes = 0

            # Create title panel
            title_panel = Panel(
                Text(f"🔄 Elasticsearch Flush Operation", style="bold cyan", justify="center"),
                subtitle=f"Synced flush across cluster: {cluster_name} | Nodes: {total_nodes}",
                border_style="cyan",
                padding=(1, 2)
            )

            # Show operation in progress
            print()
            console.print(title_panel)
            print()

            # Enhanced flush with retry logic
            max_retries = 10  # Maximum number of retry attempts
            retry_count = 0
            failed_shards = 1  # Initialize to enter the loop

            while failed_shards > 0 and retry_count <= max_retries:
                retry_count += 1

                # Show current attempt status
                if retry_count == 1:
                    status_message = "Performing synced flush operation..."
                else:
                    status_message = f"Retrying flush operation (attempt {retry_count}/{max_retries + 1})..."

                with console.status(status_message):
                    flushsync = self.es_client.flush_synced_elasticsearch(
                        host=self.es_client.host1,
                        port=self.es_client.port,
                        use_ssl=self.es_client.use_ssl,
                        authentication=self.es_client.elastic_authentication,
                        username=self.es_client.elastic_username,
                        password=self.es_client.elastic_password
                    )

                # Check results
                if isinstance(flushsync, dict):
                    failed_shards = flushsync.get('_shards', {}).get('failed', 0)
                    total_shards = flushsync.get('_shards', {}).get('total', 0)
                    successful_shards = flushsync.get('_shards', {}).get('successful', 0)

                    if failed_shards > 0 and retry_count <= max_retries:
                        # Show retry information
                        retry_panel = Panel(
                            Text(f"⚠️ Flush attempt {retry_count} completed with {failed_shards}/{total_shards} failed shards.\n"
                                f"💤 Waiting 10 seconds before retry {retry_count + 1}...",
                                style="yellow", justify="center"),
                            title=f"🔄 Retry {retry_count}/{max_retries + 1}",
                            border_style="yellow",
                            padding=(1, 2)
                        )
                        console.print(retry_panel)

                        # Wait 10 seconds before retry
                        import time
                        time.sleep(10)
                    elif failed_shards == 0:
                        # Success - show completion message if retries were needed
                        if retry_count > 1:
                            success_panel = Panel(
                                Text(f"🎉 Flush operation successful after {retry_count} attempts!\n"
                                    f"All {total_shards} shards successfully flushed.",
                                    style="green", justify="center"),
                                title="✅ Operation Complete",
                                border_style="green",
                                padding=(1, 2)
                            )
                            console.print(success_panel)
                        break
                else:
                    # Non-dict response, exit retry loop
                    break

            # Check if we hit max retries
            if failed_shards > 0 and retry_count > max_retries:
                max_retry_panel = Panel(
                    Text(f"⚠️ Maximum retry attempts ({max_retries + 1}) exceeded.\n"
                        f"Final result: {failed_shards}/{total_shards} shards still failed.",
                        style="red", justify="center"),
                    title="❌ Max Retries Exceeded",
                    border_style="red",
                    padding=(1, 2)
                )
                console.print(max_retry_panel)
                print()

            # Process and display results
            if isinstance(flushsync, dict):
                # Extract statistics from flush response
                total_shards = flushsync.get('_shards', {}).get('total', 0)
                successful_shards = flushsync.get('_shards', {}).get('successful', 0)
                failed_shards = flushsync.get('_shards', {}).get('failed', 0)
                skipped_shards = flushsync.get('_shards', {}).get('skipped', 0)

                # Calculate success rate
                success_rate = (successful_shards / total_shards * 100) if total_shards > 0 else 0

                # Create operation summary panel
                summary_table = InnerTable(show_header=False, box=None, padding=(0, 1))
                summary_table.add_column("Label", style="bold", no_wrap=True)
                summary_table.add_column("Icon", justify="left", width=3)
                summary_table.add_column("Value", no_wrap=True)

                summary_table.add_row("Total Shards:", "📊", f"{total_shards:,}")
                summary_table.add_row("Successful:", "✅", f"{successful_shards:,}")
                summary_table.add_row("Failed:", "❌", f"{failed_shards:,}")
                summary_table.add_row("Skipped:", "⏭️", f"{skipped_shards:,}")
                summary_table.add_row("Success Rate:", "📈", f"{success_rate:.1f}%")

                # Add retry information if retries were performed
                if retry_count > 1:
                    summary_table.add_row("Retry Attempts:", "🔄", f"{retry_count}")
                    if failed_shards == 0:
                        summary_table.add_row("Final Status:", "🎉", "Success after retries")
                    elif retry_count > max_retries:
                        summary_table.add_row("Final Status:", "⚠️", "Max retries exceeded")

                summary_panel = Panel(
                    summary_table,
                    title="📊 Flush Summary",
                    border_style="green" if failed_shards == 0 else "yellow",
                    padding=(1, 2)
                )

                # Create operation details panel
                details_table = InnerTable(show_header=False, box=None, padding=(0, 1))
                details_table.add_column("Label", style="bold", no_wrap=True)
                details_table.add_column("Icon", justify="left", width=3)
                details_table.add_column("Value", no_wrap=True)

                # Determine operation type and status based on retry attempts
                operation_type = "Synced Flush with Auto-Retry" if retry_count > 1 else "Synced Flush"
                if failed_shards == 0:
                    if retry_count > 1:
                        status_text = f"Success (after {retry_count} attempts)"
                        status_icon = "🎉"
                    else:
                        status_text = "Success"
                        status_icon = "✅"
                elif retry_count > max_retries:
                    status_text = "Failed (max retries exceeded)"
                    status_icon = "❌"
                else:
                    status_text = "Partial Success"
                    status_icon = "⚠️"

                details_table.add_row("Operation:", "🔄", operation_type)
                details_table.add_row("Cluster:", "🏢", cluster_name)
                details_table.add_row("Target:", "🎯", "All Indices")
                details_table.add_row("Status:", status_icon, status_text)

                details_panel = Panel(
                    details_table,
                    title="⚙️ Operation Details",
                    border_style="blue",
                    padding=(1, 2)
                )

                # Show detailed results if there are failures
                if failed_shards > 0 or 'failures' in flushsync:
                    if retry_count > max_retries:
                        failures_content = f"❌ Flush operation failed after {retry_count} attempts (including {retry_count - 1} retries).\n\n"
                        failures_content += f"⚠️ {failed_shards}/{total_shards} shards still failed after maximum retry attempts:\n\n"
                    else:
                        failures_content = "⚠️ Some shards failed to flush:\n\n"

                    failures = flushsync.get('failures', [])
                    for i, failure in enumerate(failures[:5]):  # Show first 5 failures
                        index = failure.get('index', 'Unknown')
                        shard = failure.get('shard', 'Unknown')
                        reason = failure.get('reason', {}).get('reason', 'Unknown error')
                        failures_content += f"• {index}[{shard}]: {reason}\n"

                    if len(failures) > 5:
                        failures_content += f"... and {len(failures) - 5} more failures"

                    # Add retry recommendation if max retries exceeded
                    if retry_count > max_retries:
                        failures_content += f"\n\n💡 Consider investigating cluster health or specific index issues."

                    failures_panel = Panel(
                        failures_content.rstrip(),
                        title="❌ Persistent Flush Failures" if retry_count > max_retries else "⚠️ Flush Failures",
                        border_style="red",
                        padding=(1, 2)
                    )
                else:
                    # Success message
                    if retry_count > 1:
                        success_text = Text(f"🎉 All shards flushed successfully after {retry_count} attempts!\n\nThe synced flush operation completed successfully with automatic retry recovery.", style="green")
                        title = "🎉 Success with Auto-Retry"
                    else:
                        success_text = Text("🎉 All shards flushed successfully!\n\nThe synced flush operation completed without errors.", style="green")
                        title = "✅ Success"

                    failures_panel = Panel(
                        success_text,
                        title=title,
                        border_style="green",
                        padding=(1, 2)
                    )

                # Create quick actions panel
                actions_table = InnerTable(show_header=False, box=None, padding=(0, 1))
                actions_table.add_column("Action", style="bold cyan", no_wrap=True)
                actions_table.add_column("Command", style="dim white")

                actions_table.add_row("Check health:", "./escmd.py health")
                actions_table.add_row("View shards:", "./escmd.py shards")
                actions_table.add_row("Monitor recovery:", "./escmd.py recovery")
                actions_table.add_row("View indices:", "./escmd.py indices")

                actions_panel = Panel(
                    actions_table,
                    title="🚀 Related Commands",
                    border_style="magenta",
                    padding=(1, 2)
                )

                # Display results
                print()
                console.print(Columns([summary_panel, details_panel], expand=True))
                print()
                console.print(failures_panel)
                print()
                console.print(actions_panel)
                print()

            else:
                # Simple response display
                simple_panel = Panel(
                    Text(f"🔄 Flush completed: {flushsync}", style="green", justify="center"),
                    title="✅ Flush Operation Complete",
                    border_style="green",
                    padding=(1, 2)
                )
                print()
                console.print(simple_panel)
                print()

        except Exception as e:
            error_panel = Panel(
                Text(f"❌ Flush operation failed: {str(e)}", style="bold red", justify="center"),
                subtitle="Check cluster connectivity and permissions",
                border_style="red",
                padding=(1, 2)
            )
            print()
            console.print(error_panel)
            print()

    def handle_freeze(self):
        """Enhanced freeze command with Rich formatting and validation details."""
        from rich.panel import Panel
        from rich.text import Text
        from rich.columns import Columns
        from rich.table import Table as InnerTable

        console = self.console

        try:
            # Get cluster information for context
            try:
                health_data = self.es_client.get_cluster_health()
                cluster_name = health_data.get('cluster_name', 'Unknown')
            except:
                cluster_name = 'Unknown'

            # Create title panel
            title_panel = Panel(
                Text(f"🧊 Elasticsearch Index Freeze Operation", style="bold cyan", justify="center"),
                subtitle=f"Target Index: {self.args.indice} | Cluster: {cluster_name}",
                border_style="cyan",
                padding=(1, 2)
            )

            print()
            console.print(title_panel)
            print()

            # Validate index exists
            with console.status(f"Validating index '{self.args.indice}'..."):
                cluster_active_indices = self.es_client.get_indices_stats(pattern=None, status=None)

            if not cluster_active_indices:
                error_panel = Panel(
                    Text(f"❌ No active indices found in cluster", style="bold red", justify="center"),
                    subtitle="Unable to retrieve cluster indices",
                    border_style="red",
                    padding=(1, 2)
                )
                console.print(error_panel)
                return

            # Find matching index
            from utils import find_matching_index
            if not find_matching_index(cluster_active_indices, self.args.indice):
                # Show available indices for reference
                available_indices = [idx.get('index', 'Unknown') for idx in cluster_active_indices[:10]]

                error_content = f"Index '{self.args.indice}' not found in the cluster.\n\n"
                error_content += "Available indices (showing first 10):\n"
                for idx in available_indices:
                    error_content += f"• {idx}\n"

                error_panel = Panel(
                    error_content.rstrip(),
                    title="❌ Index Not Found",
                    border_style="red",
                    padding=(1, 2)
                )
                console.print(error_panel)
                return

            # Get index details before freezing
            try:
                index_info = next((idx for idx in cluster_active_indices if idx.get('index') == self.args.indice), {})
                health = index_info.get('health', 'unknown')
                status = index_info.get('status', 'unknown')
                docs_count = index_info.get('docs.count', '0')
                size = index_info.get('store.size', '0')
            except:
                health = 'unknown'
                status = 'unknown'
                docs_count = '0'
                size = '0'

            # Create validation summary panel
            validation_table = InnerTable(show_header=False, box=None, padding=(0, 1))
            validation_table.add_column("Label", style="bold", no_wrap=True)
            validation_table.add_column("Icon", justify="left", width=3)
            validation_table.add_column("Value", no_wrap=True)

            health_icon = "🟢" if health == 'green' else "🟡" if health == 'yellow' else "🔴"
            status_icon = "📂" if status == 'open' else "🔒"

            validation_table.add_row("Index Name:", "📋", self.args.indice)
            validation_table.add_row("Health:", health_icon, health.title())
            validation_table.add_row("Status:", status_icon, status.title())
            validation_table.add_row("Documents:", "📊", f"{docs_count:,}" if docs_count.isdigit() else docs_count)
            validation_table.add_row("Size:", "💾", size)

            validation_panel = Panel(
                validation_table,
                title="✅ Index Validation",
                border_style="green",
                padding=(1, 2)
            )

            # Create freeze operation details panel
            operation_table = InnerTable(show_header=False, box=None, padding=(0, 1))
            operation_table.add_column("Label", style="bold", no_wrap=True)
            operation_table.add_column("Icon", justify="left", width=3)
            operation_table.add_column("Value", no_wrap=True)

            operation_table.add_row("Operation:", "🧊", "Freeze Index")
            operation_table.add_row("Effect:", "🔒", "Read-Only Mode")
            operation_table.add_row("Storage:", "💾", "Optimized")
            operation_table.add_row("Searchable:", "🔍", "Yes")
            operation_table.add_row("Writable:", "✏️", "No")

            operation_panel = Panel(
                operation_table,
                title="⚙️ Freeze Operation",
                border_style="blue",
                padding=(1, 2)
            )

            # Display validation
            console.print(Columns([validation_panel, operation_panel], expand=True))
            print()

            # Perform freeze operation
            with console.status(f"Freezing index '{self.args.indice}'..."):
                freeze_result = self.es_client.freeze_index(self.args.indice)

            if freeze_result:
                # Success panel
                success_text = f"🎉 Index '{self.args.indice}' has been successfully frozen!\n\n"
                success_text += "The index is now:\n"
                success_text += "• ✅ Read-only (no new writes allowed)\n"
                success_text += "• 💾 Storage optimized for reduced memory usage\n"
                success_text += "• 🔍 Still searchable but with potential latency\n"
                success_text += "• 🧊 Frozen state persists until manually unfrozen"

                success_panel = Panel(
                    success_text,
                    title="✅ Freeze Operation Successful",
                    border_style="green",
                    padding=(1, 2)
                )

                # Create quick actions panel
                actions_table = InnerTable(show_header=False, box=None, padding=(0, 1))
                actions_table.add_column("Action", style="bold cyan", no_wrap=True)
                actions_table.add_column("Command", style="dim white")

                actions_table.add_row("Verify status:", f"./escmd.py indice {self.args.indice}")
                actions_table.add_row("List indices:", "./escmd.py indices")
                actions_table.add_row("Unfreeze index:", f"# No direct command available")
                actions_table.add_row("Check settings:", "./escmd.py settings")

                actions_panel = Panel(
                    actions_table,
                    title="🚀 Next Steps",
                    border_style="magenta",
                    padding=(1, 2)
                )

                console.print(success_panel)
                print()
                console.print(actions_panel)
                print()

            else:
                # Failure panel
                error_panel = Panel(
                    Text(f"❌ Failed to freeze index '{self.args.indice}'", style="bold red", justify="center"),
                    subtitle="Check index permissions and cluster status",
                    border_style="red",
                    padding=(1, 2)
                )
                console.print(error_panel)
                print()

        except Exception as e:
            error_panel = Panel(
                Text(f"❌ Freeze operation error: {str(e)}", style="bold red", justify="center"),
                subtitle=f"Failed to freeze index: {self.args.indice}",
                border_style="red",
                padding=(1, 2)
            )
            print()
            console.print(error_panel)
            print()

    def handle_nodes(self):
        nodes = self.es_client.get_nodes()
        if self.args.format == 'json':
            print(json.dumps(nodes))
        elif self.args.format == 'data':
            data_nodes = self.es_client.filter_nodes_by_role(nodes, 'data')
            self.es_client.print_enhanced_nodes_table(data_nodes, show_data_only=True)
        else:
            self.es_client.print_enhanced_nodes_table(nodes)

    def handle_masters(self):
        nodes = self.es_client.get_nodes()
        master_nodes = self.es_client.filter_nodes_by_role(nodes, 'master')
        if self.args.format == 'json':
            print(json.dumps(master_nodes))
        else:
            self.es_client.print_enhanced_masters_info(master_nodes)

    def handle_health(self):
        # Check if group health is requested
        if hasattr(self.args, 'group') and self.args.group:
            self._handle_health_group()
            return

        # Check if comparison is requested
        if hasattr(self.args, 'compare') and self.args.compare:
            self._handle_health_compare()
            return

        # Check if quick mode is requested
        if hasattr(self.args, 'quick') and self.args.quick:
            self._handle_health_quick()
            return

        # For JSON output, gather data quickly without progress
        if self.args.format == 'json':
            health_data = self.es_client.get_cluster_health()
            print(json.dumps(health_data))
        else:
            # Choose display style: command-line argument overrides config file
            if hasattr(self.args, 'style') and self.args.style:
                style = self.args.style
            else:
                # Use configured style from elastic_servers.yml
                style = self.location_config.get('health_style', 'dashboard')

            if style == 'classic':
                # For classic mode, show simple progress
                with self.console.status("[bold blue]Gathering cluster health data...") as status:
                    health_data = self.es_client.get_cluster_health()
                    status.update("[bold green]Processing health data...")

                # Determine classic format: command-line override or config file
                if hasattr(self.args, 'classic_style') and self.args.classic_style:
                    classic_format = self.args.classic_style
                else:
                    classic_format = self.location_config.get('classic_style', 'panel')

                print("")
                if classic_format == 'table':
                    # Original key-value table format
                    self.es_client.print_table_from_dict('Elastic Health Status', health_data)
                else:
                    # New styled panel format (same as comparison)
                    status_icon = "✅" if health_data.get('cluster_status', '').upper() == 'GREEN' else "⚠️" if health_data.get('cluster_status', '').upper() == 'YELLOW' else "❌"
                    health_table = self.es_client._create_health_table(
                        self.current_location,
                        health_data,
                        status_icon
                    )
                    from rich.console import Console
                    console = Console()
                    console.print(health_table)
            else:
                # Dashboard mode with detailed progress tracking
                self._handle_health_dashboard()

    def _handle_health_dashboard(self):
        """Handle dashboard health display with progress tracking."""
        from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
        import time

        # Set snapshot repository for dashboard
        snapshot_repo = self.location_config.get('elastic_s3snapshot_repo')
        self.es_client.snapshot_repo = snapshot_repo

        # Create progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console,
            transient=True
        ) as progress:

            # Create main task
            main_task = progress.add_task("[bold cyan]Gathering cluster diagnostics...", total=6)

            # Step 1: Basic cluster health
            progress.update(main_task, description="[bold cyan]📊 Getting cluster health...")
            health_data = self.es_client.get_cluster_health()
            progress.advance(main_task)
            time.sleep(0.1)  # Brief pause to show progress

            # Step 2: Recovery status
            progress.update(main_task, description="[bold yellow]🔄 Checking recovery status...")
            recovery_status = self.es_client.get_recovery_status()
            progress.advance(main_task)
            time.sleep(0.1)

            # Step 3: Allocation issues
            progress.update(main_task, description="[bold orange1]⚠️  Analyzing allocation issues...")
            allocation_issues = self.es_client.check_allocation_issues()
            progress.advance(main_task)
            time.sleep(0.1)

            # Step 4: Node information
            progress.update(main_task, description="[bold green]🖥️  Getting node details...")
            try:
                nodes = self.es_client.get_nodes()
                progress.advance(main_task)
            except:
                nodes = []
                progress.advance(main_task)
            time.sleep(0.1)

            # Step 5: Master node identification
            progress.update(main_task, description="[bold magenta]👑 Identifying master node...")
            try:
                master_node = self.es_client.get_master_node()
                progress.advance(main_task)
            except:
                master_node = "Unknown"
                progress.advance(main_task)
            time.sleep(0.1)

            # Step 6: Snapshot information (if configured)
            if snapshot_repo:
                progress.update(main_task, description="[bold blue]📦 Checking snapshot status...")
                try:
                    snapshots = self.es_client.list_snapshots(snapshot_repo)
                    progress.advance(main_task)
                except:
                    snapshots = []
                    progress.advance(main_task)
            else:
                progress.update(main_task, description="[bold blue]📦 Finalizing dashboard...")
                snapshots = []
                progress.advance(main_task)
            time.sleep(0.1)

            # Final update
            progress.update(main_task, description="[bold green]✅ Dashboard ready!")
            time.sleep(0.2)  # Brief pause to show completion

        # Store additional data in health_data for dashboard
        health_data['_recovery_status'] = recovery_status
        health_data['_allocation_issues'] = allocation_issues
        health_data['_nodes'] = nodes
        health_data['_master_node'] = master_node
        health_data['_snapshots'] = snapshots

        # Display the dashboard
        self.es_client.print_stylish_health_dashboard(health_data)

    def _handle_health_quick(self):
        """Handle quick health check - only basic cluster health without additional diagnostics."""
        import json

        # Get only the basic cluster health data
        health_data = self.es_client.get_cluster_health()

        if self.args.format == 'json':
            print(json.dumps(health_data))
        else:
            # Simple, fast display of core health metrics
            try:
                from rich.table import Table
                from rich.panel import Panel
                from rich.console import Console
                from rich.text import Text

                console = self.console if hasattr(self.console, 'print') else Console()

                # Get cluster status and set colors
                status = health_data.get('cluster_status', 'unknown').upper()
                if status == 'GREEN':
                    status_color = "bright_green"
                    status_icon = "🟢"
                elif status == 'YELLOW':
                    status_color = "bright_yellow"
                    status_icon = "🟡"
                elif status == 'RED':
                    status_color = "bright_red"
                    status_icon = "🔴"
                else:
                    status_color = "dim"
                    status_icon = "⚪"

                # Create quick health table
                table = Table.grid(padding=(0, 1))
                table.add_column(style="bold white", no_wrap=True)
                table.add_column(style="bold cyan")

                # Core health metrics only
                table.add_row("🏢 Cluster:", health_data.get('cluster_name', 'Unknown'))
                table.add_row(f"{status_icon} Status:", f"[bold {status_color}]{status}[/bold {status_color}]")
                table.add_row("🖥️  Nodes:", str(health_data.get('number_of_nodes', 0)))
                table.add_row("💾 Data Nodes:", str(health_data.get('number_of_data_nodes', 0)))
                table.add_row("🟢 Primary Shards:", f"{health_data.get('active_primary_shards', 0):,}")
                table.add_row("🔵 Total Shards:", f"{health_data.get('active_shards', 0):,}")

                unassigned = health_data.get('unassigned_shards', 0)
                if unassigned > 0:
                    table.add_row("🔴 Unassigned:", f"[bold red]{unassigned:,}[/bold red]")
                else:
                    table.add_row("✅ Assignment:", "[bold green]Complete[/bold green]")

                active_percent = health_data.get('active_shards_percent', 0)
                table.add_row("📊 Shard Health:", f"{active_percent:.1f}%")

                # Create panel
                panel = Panel(
                    table,
                    title=f"[bold cyan]⚡ Quick Cluster Health[/bold cyan]",
                    border_style=status_color.replace('bright_', ''),
                    padding=(1, 2)
                )

                import builtins
                builtins.print()
                console.print(panel)
                builtins.print()

            except Exception as e:
                # Fallback to simple text output if rich formatting fails
                import builtins
                builtins.print(f"\n⚡ Quick Cluster Health:")
                builtins.print(f"🏢 Cluster: {health_data.get('cluster_name', 'Unknown')}")
                status = health_data.get('cluster_status', 'unknown').upper()
                status_icon = "🟢" if status == 'GREEN' else "🟡" if status == 'YELLOW' else "🔴" if status == 'RED' else "⚪"
                builtins.print(f"{status_icon} Status: {status}")
                builtins.print(f"🖥️  Nodes: {health_data.get('number_of_nodes', 0)}")
                builtins.print(f"💾 Data Nodes: {health_data.get('number_of_data_nodes', 0)}")
                builtins.print(f"🟢 Primary Shards: {health_data.get('active_primary_shards', 0):,}")
                builtins.print(f"🔵 Total Shards: {health_data.get('active_shards', 0):,}")
                unassigned = health_data.get('unassigned_shards', 0)
                if unassigned > 0:
                    builtins.print(f"🔴 Unassigned: {unassigned:,}")
                else:
                    builtins.print(f"✅ Assignment: Complete")
                active_percent = health_data.get('active_shards_percent', 0)
                builtins.print(f"📊 Shard Health: {active_percent:.1f}%")
                builtins.print()

    def _handle_health_compare(self):
        """Handle health comparison between two clusters."""
        from esclient import ElasticsearchClient
        from configuration_manager import ConfigurationManager

        current_cluster = self.current_location
        compare_cluster = self.args.compare

        # Get health data from current cluster
        try:
            current_health = self.es_client.get_cluster_health()
            current_status = "✅"
        except Exception as e:
            current_health = {"error": str(e)}
            current_status = "❌"

        # Get configuration for comparison cluster
        config_manager = ConfigurationManager(self.config_file, "default.state")
        try:
            compare_config = config_manager.get_server_config_by_location(compare_cluster)
            if not compare_config:
                print(f"❌ Error: Cluster '{compare_cluster}' not found in configuration")
                return

            # Map configuration keys to ElasticsearchClient format
            hostname = compare_config.get('elastic_host')
            hostname2 = compare_config.get('elastic_host2')
            port = compare_config.get('elastic_port', 9200)

            # Validate required configuration
            if not hostname:
                print(f"❌ Error: No hostname configured for cluster '{compare_cluster}'")
                return

            # Create client for comparison cluster with proper authentication handling
            username = compare_config.get('elastic_username')
            password = compare_config.get('elastic_password')

            # Handle None values that might cause issues
            if username is None:
                username = ""
            if password is None:
                password = ""
            if hostname2 is None:
                hostname2 = ""

            compare_es_client = ElasticsearchClient(
                hostname,           # host1
                hostname2,          # host2
                port,               # port
                compare_config.get('use_ssl', False),                  # use_ssl
                compare_config.get('verify_certs', False),             # verify_certs
                60,                 # timeout (default)
                compare_config.get('elastic_authentication', False),   # elastic_authentication
                username,           # elastic_username
                password            # elastic_password
            )

            # Get health data from comparison cluster
            try:
                compare_health = compare_es_client.get_cluster_health()
                compare_status = "✅"
            except Exception as e:
                compare_health = {"error": str(e)}
                compare_status = "❌"

        except Exception as e:
            print(f"❌ Error connecting to cluster '{compare_cluster}': {str(e)}")
            return

        # Display side-by-side comparison
        if self.args.format == 'json':
            comparison_data = {
                current_cluster: current_health,
                compare_cluster: compare_health
            }
            print(json.dumps(comparison_data))
        else:
            self.es_client.print_side_by_side_health(
                current_cluster, current_health, current_status,
                compare_cluster, compare_health, compare_status
            )

    def _handle_health_group(self):
        """Handle health display for all clusters in a group."""
        from esclient import ElasticsearchClient
        from configuration_manager import ConfigurationManager

        group_name = self.args.group

        # Get configuration manager and check if group exists
        config_manager = ConfigurationManager(self.config_file, "default.state")

        if not config_manager.is_cluster_group(group_name):
            print(f"❌ Error: Cluster group '{group_name}' not found in configuration")
            available_groups = list(config_manager.get_cluster_groups().keys())
            if available_groups:
                print(f"Available groups: {', '.join(available_groups)}")
            return

        cluster_list = config_manager.get_cluster_group_members(group_name)
        if not cluster_list:
            print(f"❌ Error: No clusters found in group '{group_name}'")
            return

        print(f"\n🔍 Health Status for Cluster Group: {group_name.upper()}")
        print(f"📋 Clusters: {', '.join(cluster_list)}")
        print()

        # Collect health data for all clusters in the group
        cluster_health_data = []

        for cluster_name in cluster_list:
            try:
                # Get configuration for this cluster
                cluster_config = config_manager.get_server_config_by_location(cluster_name)
                if not cluster_config:
                    print(f"❌ Warning: Configuration not found for cluster '{cluster_name}', skipping...")
                    continue

                # Create client for this cluster
                hostname = cluster_config.get('elastic_host')
                hostname2 = cluster_config.get('elastic_host2')
                port = cluster_config.get('elastic_port', 9200)
                username = cluster_config.get('elastic_username')
                password = cluster_config.get('elastic_password')

                # Handle None values
                if username is None:
                    username = ""
                if password is None:
                    password = ""
                if hostname2 is None:
                    hostname2 = ""

                cluster_es_client = ElasticsearchClient(
                    hostname,           # host1
                    hostname2,          # host2
                    port,               # port
                    cluster_config.get('use_ssl', False),                  # use_ssl
                    cluster_config.get('verify_certs', False),             # verify_certs
                    60,                 # timeout (default)
                    cluster_config.get('elastic_authentication', False),   # elastic_authentication
                    username,           # elastic_username
                    password            # elastic_password
                )

                # Get health data
                health_data = cluster_es_client.get_cluster_health()
                status_icon = "✅" if health_data.get('cluster_status', '').upper() == 'GREEN' else "⚠️" if health_data.get('cluster_status', '').upper() == 'YELLOW' else "❌"

                cluster_health_data.append({
                    'name': cluster_name,
                    'data': health_data,
                    'status': status_icon,
                    'client': cluster_es_client
                })

            except Exception as e:
                print(f"❌ Error connecting to cluster '{cluster_name}': {str(e)}")
                # Add error entry
                cluster_health_data.append({
                    'name': cluster_name,
                    'data': {"error": str(e)},
                    'status': "❌",
                    'client': None
                })

        # Display results
        if self.args.format == 'json':
            # JSON output for all clusters
            json_output = {}
            for cluster_info in cluster_health_data:
                json_output[cluster_info['name']] = cluster_info['data']
            print(json.dumps(json_output))
        else:
            # Display all clusters using panel format
            self.es_client.print_group_health(group_name, cluster_health_data)

    def handle_indice(self):
        indice = self.args.indice
        self.es_client.print_detailed_indice_info(indice)

    def handle_indices(self):
        if self.args.cold:
            self._handle_cold_indices()
            return

        if self.args.regex:
            self._handle_regex_indices()
            return

        if self.args.format == 'json':
            print(self.es_client.filter_indices(pattern=None, status=self.args.status))
        else:
            indices = self.es_client.filter_indices(pattern=None, status=self.args.status)
            # Check if pager argument exists and use it
            use_pager = getattr(self.args, 'pager', False)
            self.es_client.print_table_indices(indices, use_pager=use_pager)

    def handle_locations(self):
        """
        Display all configured Elasticsearch locations.
        """
        config_manager = ConfigurationManager(self.config_file, os.path.join(os.path.dirname(self.config_file), 'escmd.json'))
        config_manager.show_locations()

    def handle_recovery(self):
        if self.args.format == "json":
            es_recovery = self.es_client.get_recovery_status()
            print(json.dumps(es_recovery))
        else:
            with self.console.status("Retrieving recovery data..."):
                es_recovery = self.es_client.get_recovery_status()
                self.es_client.print_enhanced_recovery_status(es_recovery)

    def handle_rollover(self):
        if not self.args.datastream:
            print("ERROR: No Datastream passed.")
            exit(1)
        rollover_stats = self.es_client.rollover_datastream(self.args.datastream)
        print_json_as_table(rollover_stats)

    def handle_datastreams(self):
        """Handle datastreams command - list all datastreams, show details, or delete a specific one"""
        try:
            if self.args.name and self.args.delete:
                # Delete the specified datastream with confirmation
                self._handle_datastream_delete()
            elif self.args.name:
                # Show details for a specific datastream
                datastream_details = self.es_client.get_datastream_details(self.args.name)

                if self.args.format == 'json':
                    print(json.dumps(datastream_details, indent=2))
                else:
                    self._print_datastream_details_table(datastream_details)
            elif self.args.delete:
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
        from rich.table import Table
        from rich.console import Console

        console = Console()
        table = Table(show_header=True, header_style="bold magenta", title="📊 Datastreams")

        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Status", style="green")
        table.add_column("Template", style="yellow")
        table.add_column("ILM Policy", style="blue")
        table.add_column("Generation", style="white", justify="right")
        table.add_column("Indices Count", style="white", justify="right")

        for datastream in datastreams_data.get('data_streams', []):
            name = datastream.get('name', 'N/A')
            status = datastream.get('status', 'N/A')
            template = datastream.get('template', 'N/A')
            ilm_policy = datastream.get('ilm_policy', 'N/A')
            generation = str(datastream.get('generation', 0))
            indices_count = str(len(datastream.get('indices', [])))

            table.add_row(name, status, template, ilm_policy, generation, indices_count)

        console.print(table)

    def _print_datastream_details_table(self, datastream_data):
        """Print detailed datastream information in table format"""
        from rich.table import Table
        from rich.console import Console
        from rich.panel import Panel

        console = Console()

        if 'data_streams' not in datastream_data or not datastream_data['data_streams']:
            console.print("[red]No datastream found or datastream data is empty[/red]")
            return

        datastream = datastream_data['data_streams'][0]

        # Main datastream info panel
        info_table = Table.grid(padding=(0, 1))
        info_table.add_column(style="bold white", no_wrap=True)
        info_table.add_column(style="cyan")

        info_table.add_row("📛 Name:", datastream.get('name', 'N/A'))
        info_table.add_row("📊 Status:", datastream.get('status', 'N/A'))
        info_table.add_row("📋 Template:", datastream.get('template', 'N/A'))
        info_table.add_row("🔄 ILM Policy:", datastream.get('ilm_policy', 'N/A'))
        info_table.add_row("🔢 Generation:", str(datastream.get('generation', 0)))

        panel = Panel(info_table, title="🗂️ Datastream Details", border_style="cyan")
        console.print(panel)

        # Indices table
        indices = datastream.get('indices', [])
        if indices:
            indices_table = Table(show_header=True, header_style="bold magenta", title="📚 Backing Indices")
            indices_table.add_column("Index Name", style="cyan")
            indices_table.add_column("UUID", style="yellow")

            for index in indices:
                indices_table.add_row(
                    index.get('index_name', 'N/A'),
                    index.get('index_uuid', 'N/A')
                )

            console.print(indices_table)

    def _handle_datastream_delete(self):
        """Handle datastream deletion with confirmation and validation"""
        from rich.panel import Panel
        from rich.text import Text
        from rich.console import Console
        from rich.table import Table as InnerTable

        console = Console()
        datastream_name = self.args.name

        try:
            # First, verify the datastream exists by getting its details
            console.print(f"\n🔍 Verifying datastream '{datastream_name}'...")

            try:
                datastream_details = self.es_client.get_datastream_details(datastream_name)
                if not datastream_details.get('data_streams'):
                    console.print(f"❌ [bold red]Datastream '{datastream_name}' not found[/bold red]")
                    return

                datastream = datastream_details['data_streams'][0]
            except Exception as e:
                console.print(f"❌ [bold red]Error: Datastream '{datastream_name}' not found or inaccessible[/bold red]")
                console.print(f"Details: {str(e)}")
                return

            # Show datastream information before deletion
            info_table = InnerTable(show_header=False, box=None, padding=(0, 1))
            info_table.add_column(style="bold white", no_wrap=True)
            info_table.add_column(style="cyan")

            info_table.add_row("📛 Name:", datastream.get('name', 'N/A'))
            info_table.add_row("📊 Status:", datastream.get('status', 'N/A'))
            info_table.add_row("📋 Template:", datastream.get('template', 'N/A'))
            info_table.add_row("🔄 ILM Policy:", datastream.get('ilm_policy', 'N/A'))
            info_table.add_row("🔢 Generation:", str(datastream.get('generation', 0)))

            indices_count = len(datastream.get('indices', []))
            info_table.add_row("📚 Backing Indices:", str(indices_count))

            warning_panel = Panel(
                info_table,
                title="⚠️  [bold yellow]Datastream to be Deleted[/bold yellow]",
                border_style="yellow",
                padding=(1, 2)
            )

            console.print()
            console.print(warning_panel)

            # Show backing indices that will be deleted
            indices = datastream.get('indices', [])
            if indices:
                console.print(f"\n💥 [bold red]WARNING: This will also delete {len(indices)} backing indices:[/bold red]")
                for i, index in enumerate(indices[:5]):  # Show first 5 indices
                    console.print(f"   • {index.get('index_name', 'N/A')}")

                if len(indices) > 5:
                    console.print(f"   ... and {len(indices) - 5} more indices")

            # Confirmation prompt
            console.print(f"\n🚨 [bold red]DANGER: This action cannot be undone![/bold red]")
            console.print(f"You are about to permanently delete datastream '[bold cyan]{datastream_name}[/bold cyan]' and all its backing indices.")

            # Interactive confirmation
            try:
                confirmation = input(f"\nType 'DELETE {datastream_name}' to confirm deletion: ").strip()

                if confirmation != f"DELETE {datastream_name}":
                    console.print(f"\n❌ [bold yellow]Deletion cancelled - confirmation text did not match[/bold yellow]")
                    console.print(f"Expected: 'DELETE {datastream_name}'")
                    console.print(f"Got: '{confirmation}'")
                    return

                # Perform deletion
                console.print(f"\n🗑️  [bold red]Deleting datastream '{datastream_name}'...[/bold red]")

                delete_result = self.es_client.delete_datastream(datastream_name)

                # Success confirmation
                success_panel = Panel(
                    Text(f"✅ Datastream '{datastream_name}' has been successfully deleted!\n\n"
                         f"• Datastream and all backing indices have been removed\n"
                         f"• {indices_count} indices were deleted\n"
                         f"• Operation completed successfully",
                         style="green"),
                    title="🎉 Deletion Successful",
                    border_style="green",
                    padding=(1, 2)
                )

                console.print()
                console.print(success_panel)
                console.print()

                # Show next steps
                actions_table = InnerTable(show_header=False, box=None, padding=(0, 1))
                actions_table.add_column("Action", style="bold cyan", no_wrap=True)
                actions_table.add_column("Command", style="dim white")

                actions_table.add_row("List datastreams:", "./escmd.py datastreams")
                actions_table.add_row("Check indices:", "./escmd.py indices")
                actions_table.add_row("View cluster health:", "./escmd.py health")

                actions_panel = Panel(
                    actions_table,
                    title="🚀 Next Steps",
                    border_style="cyan",
                    padding=(1, 2)
                )

                console.print(actions_panel)
                console.print()

            except KeyboardInterrupt:
                console.print(f"\n❌ [bold yellow]Deletion cancelled by user[/bold yellow]")
                return

        except Exception as e:
            error_panel = Panel(
                Text(f"❌ Failed to delete datastream '{datastream_name}': {str(e)}",
                     style="bold red"),
                title="💥 Deletion Failed",
                border_style="red",
                padding=(1, 2)
            )
            console.print()
            console.print(error_panel)
            console.print()

    def handle_auto_rollover(self):
        if not self.args.host:
            print("ERROR: No hostname passed.")
            exit(1)
        self._process_auto_rollover()

    def handle_exclude(self):
        if not self.args.indice or not self.args.server:
            self._show_exclude_error()
            return
        self._process_exclude()

    def handle_exclude_reset(self):
        if not self.args.indice:
            show_message_box("ERROR", "You must pass indice name \n(i.e.: .ds-aex10-c01-logs-ueb-main-2025.04.03-000732)", message_style="bold white", panel_style="red")
            exit(1)
        self._process_exclude_reset()

    def handle_settings(self):
        if self.args.format == 'json':
            cluster_settings = self.es_client.get_settings()
            print(cluster_settings)
        else:
            self.es_client.print_enhanced_cluster_settings()

    def handle_storage(self):
        allocation_data = self.es_client.get_allocation_as_dict()
        self.es_client.print_enhanced_storage_table(allocation_data)

    def handle_shards(self):
        if self.args.regex:
            self._handle_regex_shards()
            return
        self._handle_default_shards()

    def handle_shard_colocation(self):
        """
        Handle shard colocation detection command.
        Finds indices where primary and replica shards are on the same host.
        """
        try:
            # Get shard colocation analysis
            colocation_results = self.es_client.analyze_shard_colocation(pattern=self.args.regex)

            if self.args.format == 'json':
                print(json.dumps(colocation_results, indent=2))
            else:
                use_pager = getattr(self.args, 'pager', False)
                self.es_client.print_shard_colocation_results(colocation_results, use_pager=use_pager)

        except Exception as e:
            from utils import show_message_box
            show_message_box("Error", f"Failed to analyze shard colocation: {str(e)}", message_style="bold white", panel_style="red")

    def handle_snapshots(self):
        """
        Handle snapshot-related commands.
        """
        if not hasattr(self.args, 'snapshots_action') or self.args.snapshots_action is None:
            show_message_box("Error", "No snapshots action specified. Use 'list' to view snapshots.", message_style="bold white", panel_style="red")
            return

        if self.args.snapshots_action == 'list':
            self._handle_list_snapshots()
        else:
            show_message_box("Error", f"Unknown snapshots action: {self.args.snapshots_action}", message_style="bold white", panel_style="red")

    def handle_ilm(self):
        """
        Handle ILM (Index Lifecycle Management) related commands.
        """
        if not hasattr(self.args, 'ilm_action') or self.args.ilm_action is None:
            show_message_box("Error", "No ILM action specified. Use 'status', 'policies', 'policy', 'explain', or 'errors'.", message_style="bold white", panel_style="red")
            return

        if self.args.ilm_action == 'status':
            self._handle_ilm_status()
        elif self.args.ilm_action == 'policies':
            self._handle_ilm_policies()
        elif self.args.ilm_action == 'policy':
            self._handle_ilm_policy()
        elif self.args.ilm_action == 'explain':
            self._handle_ilm_explain()
        elif self.args.ilm_action == 'errors':
            self._handle_ilm_errors()
        else:
            show_message_box("Error", f"Unknown ILM action: {self.args.ilm_action}", message_style="bold white", panel_style="red")

    def _handle_list_snapshots(self):
        """
        List all snapshots from the configured repository.
        """
        # Check if elastic_s3snapshot_repo is configured for this cluster
        elastic_s3snapshot_repo = self.location_config.get('elastic_s3snapshot_repo')

        if not elastic_s3snapshot_repo:
            show_message_box("Configuration Error",
                            f"No 'elastic_s3snapshot_repo' configured for cluster '{self.args.locations}'.\n"
                            f"Please add 'elastic_s3snapshot_repo: \"your-repo-name\"' to the cluster configuration in elastic_servers.yml",
                            message_style="bold white", panel_style="red")
            return

        try:
            # Get snapshots from the configured repository
            snapshots = self.es_client.list_snapshots(elastic_s3snapshot_repo)

            if not snapshots:
                show_message_box("No Snapshots",
                                f"No snapshots found in repository '{elastic_s3snapshot_repo}' or repository doesn't exist.")
                return

            # Apply regex filtering if pattern is provided
            original_count = len(snapshots)
            pattern = getattr(self.args, 'pattern', None)

            if pattern:
                import re
                try:
                    compiled_pattern = re.compile(pattern, re.IGNORECASE)
                    snapshots = [s for s in snapshots if compiled_pattern.search(s['snapshot'])]
                except re.error as e:
                    show_message_box("Invalid Pattern", f"Invalid regex pattern '{pattern}': {str(e)}")
                    return

                if not snapshots:
                    show_message_box("No Matches",
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
            show_message_box("Error", f"Error listing snapshots: {str(e)}", message_style="bold white", panel_style="red")

    def _display_snapshots_table(self, snapshots, repository_name, pattern=None, original_count=None, use_pager=False):
        """
        Display snapshots in enhanced multi-panel format following the 2.0+ style.
        """
        from rich.panel import Panel
        from rich.text import Text
        from rich.columns import Columns

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
        legend_table = Table.grid(padding=(0, 2))
        legend_table.add_column(style="bold white", no_wrap=True)
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
        actions_table = Table.grid(padding=(0, 1))
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
        import json

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
        print(json.dumps(output, indent=2))

    def _handle_ilm_status(self):
        """Handle ILM status command with comprehensive multi-panel display."""
        if self.args.format == 'json':
            ilm_data = self.es_client._get_ilm_status()
            print(json.dumps(ilm_data, indent=2))
        else:
            self.es_client.print_enhanced_ilm_status()

    def _handle_ilm_policies(self):
        """Handle ILM policies list command."""
        if self.args.format == 'json':
            policies = self.es_client.get_ilm_policies()
            print(json.dumps(policies, indent=2))
        else:
            self.es_client.print_enhanced_ilm_policies()

    def _handle_ilm_policy(self):
        """Handle ILM policy detail command."""
        if self.args.format == 'json':
            policy_data = self.es_client.get_ilm_policy_detail(self.args.policy_name)
            print(json.dumps(policy_data, indent=2))
        else:
            show_all = getattr(self.args, 'show_all', False)
            self.es_client.print_enhanced_ilm_policy_detail(self.args.policy_name, show_all_indices=show_all)

    def _handle_ilm_explain(self):
        """Handle ILM explain command for specific index."""
        if self.args.format == 'json':
            explain_data = self.es_client.get_ilm_explain(self.args.index)
            print(json.dumps(explain_data, indent=2))
        else:
            self.es_client.print_enhanced_ilm_explain(self.args.index)

    def _handle_ilm_errors(self):
        """Handle ILM errors command."""
        if self.args.format == 'json':
            errors_data = self.es_client.get_ilm_errors()
            print(json.dumps(errors_data, indent=2))
        else:
            self.es_client.print_enhanced_ilm_errors()

    def execute(self):
        command_handlers = {
            'ping': self.handle_ping,
            'allocation': self.handle_allocation,
            'current-master': self.handle_current_master,
            'flush': self.handle_flush,
            'freeze': self.handle_freeze,
            'nodes': self.handle_nodes,
            'masters': self.handle_masters,
            'health': self.handle_health,
            'indice': self.handle_indice,
            'indices': self.handle_indices,
            'locations': self.handle_locations,
            'recovery': self.handle_recovery,
            'rollover': self.handle_rollover,
            'auto-rollover': self.handle_auto_rollover,
            'exclude': self.handle_exclude,
            'exclude-reset': self.handle_exclude_reset,
            'settings': self.handle_settings,
            'storage': self.handle_storage,
            'shards': self.handle_shards,
            'shard-colocation': self.handle_shard_colocation,
            'snapshots': self.handle_snapshots,
            'ilm': self.handle_ilm,
            'datastreams': self.handle_datastreams
        }

        handler = command_handlers.get(self.args.command)
        if handler:
            handler()
        else:
            print(f"Unknown command: {self.args.command}")

    def _get_cluster_connection_info(self):
        if self.es_client.elastic_username and self.es_client.elastic_password:
            return f"Cluster: {self.args.locations}\nhost: {self.es_client.host1}\nport: {self.es_client.port}\nssl: {self.es_client.use_ssl}\nverify_certs: {self.es_client.verify_certs}\nelastic_username: {self.es_client.elastic_username}\nelastic_password: XXXXXXXXXXX\n"
        return f"Cluster: {self.args.locations}\nhost: {self.es_client.host1}\nport: {self.es_client.port}\nssl: {self.es_client.use_ssl}\nverify_certs: {self.es_client.verify_certs}\n"

    def _find_shard_matches(self, shards_data, indice):
        pattern = rf'.*{indice}.*'
        matches = [shard for shard in shards_data if re.findall(pattern, shard['index'])]
        return sorted(matches, key=lambda x: (x['prirep'], int(x['shard'])))

    def _print_shard_info(self, matches):
        for shard in matches:
            shard_info = self._get_shard_info(shard)
            print(shard_info)

    def _get_shard_info(self, shard):
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

    def _handle_cold_indices(self):
        _data = self.es_client.get_indices_stats(pattern=self.args.regex, status=self.args.status)
        print(_data)
        index_ilms = self.es_client.get_index_ilms(short=True)
        cold_indices = [index for index, info in index_ilms.items() if info.get('phase') == 'cold']
        print(f"Cold Indices: {cold_indices}")

    def _handle_regex_indices(self):
        if self.args.format == 'json':
            print(self.es_client.get_indices_stats(pattern=self.args.regex, status=self.args.status))
            return

        indices = self.es_client.filter_indices(pattern=self.args.regex, status=self.args.status)
        if not indices:
            self.es_client.show_message_box("Indices", f"Pattern: {self.args.regex}\nThere were no matching indices found", message_style="white", panel_style="bold white")
            return

        use_pager = getattr(self.args, 'pager', False)
        self.es_client.print_table_indices(indices, use_pager=use_pager)

        if self.args.delete:
            self._handle_indices_deletion(indices)

    def _handle_indices_deletion(self, indices):
        while True:
            confirm_delete = input("Are you sure you want to delete these indices? (y/n): ")
            if confirm_delete.lower() in ('yes', 'y', 'no', 'n'):
                break
            print("Invalid input. Please enter 'y', 'n', 'yes', 'no'.")

        if confirm_delete.lower() in ('y', 'yes'):
            self.es_client.delete_indices(indices)
        else:
            print("Aborted process... script exiting.")

    def _process_auto_rollover(self):
        shards_data_dict = sorted(self.es_client.get_shards_as_dict(), key=lambda x: x['size'], reverse=True)
        pattern = f".*{self.args.host}.*"
        filtered_data = [item for item in shards_data_dict if re.search(pattern, item['node'], re.IGNORECASE)]
        largest_primary_shard = next((item for item in filtered_data if item["prirep"] == "p"), None)

        if not largest_primary_shard:
            print("No matching shards found")
            return

        largest_indice_short = self.es_client.clean_index_name(largest_primary_shard['index'])
        msg = f"Indice: {largest_indice_short} [{largest_primary_shard['prirep']}] ({largest_primary_shard['store']})\nNode: {largest_primary_shard['node']}"
        show_message_box("Confirmation", msg, message_style="bold white", panel_style="black")

        answer = input("Are you sure you want to rollover? [y/n]: ")
        if answer.lower() in ('yes', 'y'):
            rollover_response = self.es_client.rollover_index(largest_indice_short)
            print(rollover_response)

    def _show_exclude_error(self):
        if not self.args.indice:
            print("Error, You must pass indice name (i.e.: .ds-aex10-c01-logs-ueb-main-2025.04.03-000732)")
        if not self.args.server:
            print("Error, -s {server} (ie: aex10-c01-ess01-1) is required for this parameter.")
        exit(1)

    def _process_exclude(self):
        args_server = self.args.server[0]
        cluster_active_indices = self.es_client.get_indices_stats(pattern=None, status=None)

        if not find_matching_index(cluster_active_indices, self.args.indice):
            show_message_box('ERROR', f"No such indice found: {self.args.indice}", message_style="white", panel_style="white")
            exit(1)

        cluster_shards = self.es_client.get_shards_stats(pattern='*')
        indice_server_fullname = find_matching_node(cluster_shards, self.args.indice, args_server)

        if not indice_server_fullname:
            show_message_box('ERROR', f"ERROR: No matching Shard for {self.args.indice} on Server {args_server}", message_style="white", panel_style="white")
            exit(1)

        response = self.es_client.exclude_index_from_host(self.args.indice, indice_server_fullname)
        if response:
            show_message_box('SUCCESS', f"Indice: {self.args.indice}\nHost: {indice_server_fullname}")
        else:
            show_message_box('ERROR', "An error has occured trying to exclude indice from host.")
            exit(1)

    def _process_exclude_reset(self):
        response, message = self.es_client.exclude_index_reset(self.args.indice)
        if response:
            show_message_box("SUCCESS", f"Succesfully removed exclude settings from indice {self.args.indice}")
        else:
            show_message_box("ERROR", message)
            exit(1)

    def _handle_regex_shards(self):
        if self.args.regex == 'unassigned':
            self._handle_unassigned_shards()
            return

        if self.args.format == 'json':
            print(json.dumps(self.es_client.get_shards_stats(pattern=self.args.regex)))
            return

        shards_data = self.es_client.get_shards_stats(pattern=self.args.regex)
        use_pager = getattr(self.args, 'pager', False)
        self.es_client.print_table_shards(shards_data, use_pager=use_pager)

    def _handle_unassigned_shards(self):
        if self.args.format == 'json':
            shards_data = self.es_client.get_shards_stats(pattern='*')
            filtered_data = [item for item in shards_data if item['state'] == 'UNASSIGNED']
            print(json.dumps(filtered_data))
            return

        shards_data = self.es_client.get_shards_stats(pattern='*')
        filtered_data = [item for item in shards_data if item['state'] == 'UNASSIGNED']
        if not filtered_data:
            self.es_client.show_message_box(f'Results: Shards [ {self.args.locations} ]', 'There was no unassigned shards found in cluster.', 'white on blue', 'bold white')
        else:
            use_pager = getattr(self.args, 'pager', False)
            self.es_client.print_table_shards(filtered_data, use_pager=use_pager)

    def _handle_default_shards(self):
        shards_data_dict = self.es_client.get_shards_as_dict()

        if self.args.size:
            shards_data_dict = sorted(shards_data_dict, key=lambda x: x['size'], reverse=True)

        if self.args.server:
            search_location = self.args.server[0]
            pattern = f".*{search_location}.*"
            shards_data_dict = [item for item in shards_data_dict if re.search(pattern, item['node'], re.IGNORECASE)]

        if self.args.limit != 0:
            shards_data_dict = shards_data_dict[:int(self.args.limit)]

        if self.args.format == 'json':
            print(json.dumps(shards_data_dict))
        else:
            use_pager = getattr(self.args, 'pager', False)
            self.es_client.print_table_shards(shards_data_dict, use_pager=use_pager)
