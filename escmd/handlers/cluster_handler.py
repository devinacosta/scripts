"""
ClusterHandler - Handles cluster-related operations

This module contains handlers for:
- ping: Test Elasticsearch connection with detailed information
- current-master: Display current cluster master node information
- nodes: Show cluster node information
- masters: Display master node information
- health: Comprehensive cluster health monitoring
"""

from .base_handler import BaseHandler
import json
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from rich.table import Table as InnerTable


class ClusterHandler(BaseHandler):
    """Handler for cluster-related operations."""

    def handle_ping(self):
        """Enhanced ping command with Rich formatting and detailed connection information."""
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
                    self.es_client.pretty_print_json(ping_data)
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
                    self.es_client.pretty_print_json(error_data)
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
                self.es_client.pretty_print_json(error_data)
                return False

            # from utils import show_message_box
            self.es_client.show_message_box("Connection Error", f"❌ Connection Error: {str(e)}\nFailed to ping {self.es_client.host1}:{self.es_client.port}", message_style="bold white", panel_style="red")
            return False

    def handle_current_master(self):
        """Get current master node information with comprehensive details."""
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

                self.es_client.pretty_print_json(master_data)

            except Exception as e:
                # Fallback to simple output if there's an error
                master_data = {
                    'master_node_name': master_node_id,
                    'error': f"Error retrieving detailed information: {str(e)}"
                }
                self.es_client.pretty_print_json(master_data)
        else:
            self.es_client.print_enhanced_current_master(master_node_id)

    def handle_nodes(self):
        """Display cluster node information."""
        nodes = self.es_client.get_nodes()
        if self.args.format == 'json':
            self.es_client.pretty_print_json(nodes)
        elif self.args.format == 'data':
            data_nodes = self.es_client.filter_nodes_by_role(nodes, 'data')
            self.es_client.print_enhanced_nodes_table(data_nodes, show_data_only=True)
        else:
            self.es_client.print_enhanced_nodes_table(nodes)

    def handle_masters(self):
        """Display master node information."""
        nodes = self.es_client.get_nodes()
        master_nodes = self.es_client.filter_nodes_by_role(nodes, 'master')
        if self.args.format == 'json':
            self.es_client.pretty_print_json(master_nodes)
        else:
            self.es_client.print_enhanced_masters_info(master_nodes)

    def handle_health(self):
        """Comprehensive cluster health monitoring with multiple display modes."""
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
            self.es_client.pretty_print_json(health_data)
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
                    # Add master node information for classic mode
                    master_node = self.es_client.get_master_node()
                    health_data['_master_node'] = master_node
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
        snapshot_repository = self.location_config.get('elastic_s3snapshot_repo') or self.location_config.get('repository')

        # Create progress display
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console,
            transient=True
        ) as progress:
            # Main health gathering task
            health_task = progress.add_task("[bold blue]Gathering cluster health data...", total=100)

            # Step 1: Basic health info
            progress.update(health_task, advance=20, description="[bold blue]Getting basic health info...")
            time.sleep(0.5)
            health_data = self.es_client.get_cluster_health()

            # Step 2: Node information
            progress.update(health_task, advance=20, description="[bold blue]Analyzing node status...")
            time.sleep(0.5)
            nodes = self.es_client.get_nodes_fast()

            # Step 3: Storage information
            progress.update(health_task, advance=20, description="[bold blue]Calculating storage metrics...")
            time.sleep(0.5)
            storage_info = self.es_client.get_allocation_as_dict()

            # Step 4: Index statistics
            progress.update(health_task, advance=20, description="[bold blue]Gathering index statistics...")
            time.sleep(0.5)

            # Step 5: Final processing - add additional data to health_data
            progress.update(health_task, advance=20, description="[bold green]Processing dashboard data...")
            time.sleep(0.5)

            # Add the gathered additional data to health_data for the dashboard
            health_data['_nodes'] = nodes
            health_data['_storage_info'] = storage_info
            # Get master node information
            master_node = self.es_client.get_master_node()
            health_data['_master_node'] = master_node
            # Add other required data that the dashboard expects
            health_data['_recovery_status'] = []  # Will be gathered if needed
            health_data['_allocation_issues'] = {"has_issues": False}  # Default: no issues
            # Fetch snapshot stats using ultra-fast method
            if snapshot_repository:
                snapshot_stats = self.es_client.get_snapshot_stats_fast(snapshot_repository)
                health_data['_snapshots'] = snapshot_stats
            else:
                health_data['_snapshots'] = []

            progress.update(health_task, completed=100, description="[bold green]✅ Health data ready!")

        print()  # Add space after progress

        # Set the snapshot repository on the es_client for the dashboard to use
        self.es_client.snapshot_repo = snapshot_repository
        # Display the enhanced dashboard
        self.es_client.print_stylish_health_dashboard(health_data)

    def _handle_health_group(self):
        """Handle group health comparison across multiple locations."""
        output_format = getattr(self.args, 'format', 'table')
        self.es_client.print_multi_cluster_health_comparison(self.config_file, self.args.group, output_format)

    def _handle_health_compare(self):
        """Handle health comparison with another cluster."""
        # Get the comparison cluster configuration
        all_locations = self.es_client.load_config(self.config_file)
        if self.args.compare not in all_locations:
            print(f"❌ Comparison location '{self.args.compare}' not found in configuration.")
            return

        # Display side-by-side comparison
        self.es_client.print_cluster_health_comparison(
            self.config_file,
            self.current_location,
            self.args.compare
        )

    def _handle_health_quick(self):
        """Handle quick health check - only basic cluster health without additional diagnostics."""
        import json

        # Get only the basic cluster health data
        health_data = self.es_client.get_cluster_health()

        if self.args.format == 'json':
            self.es_client.pretty_print_json(health_data)
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
                table = Table.grid(padding=(0, 3))
                table.add_column(style="bold white", no_wrap=True)
                table.add_column(style="bold cyan")

                # Core health metrics only
                table.add_row("🏢 Cluster:", health_data.get('cluster_name', 'Unknown'))
                
                # Add version information if available
                cluster_version = health_data.get('cluster_version', 'Unknown')
                if cluster_version != 'Unknown':
                    table.add_row("🔧 ES Version:", f"v{cluster_version}")
                
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

                print()
                console.print(panel)
                print()

            except Exception as e:
                # Fallback to simple text output if rich formatting fails
                print(f"\n⚡ Quick Cluster Health:")
                print(f"🏢 Cluster: {health_data.get('cluster_name', 'Unknown')}")
                
                # Add version information if available
                cluster_version = health_data.get('cluster_version', 'Unknown')
                if cluster_version != 'Unknown':
                    print(f"🔧 ES Version: v{cluster_version}")
                    
                status = health_data.get('cluster_status', 'unknown').upper()
                status_icon = "🟢" if status == 'GREEN' else "🟡" if status == 'YELLOW' else "🔴" if status == 'RED' else "⚪"
                print(f"{status_icon} Status: {status}")
                print(f"🖥️  Nodes: {health_data.get('number_of_nodes', 0)}")
                print(f"💾 Data Nodes: {health_data.get('number_of_data_nodes', 0)}")
                print(f"🟢 Primary Shards: {health_data.get('active_primary_shards', 0):,}")
                print(f"🔵 Total Shards: {health_data.get('active_shards', 0):,}")
                unassigned = health_data.get('unassigned_shards', 0)
                if unassigned > 0:
                    print(f"🔴 Unassigned: {unassigned:,}")
                else:
                    print(f"✅ Assignment: Complete")
                active_percent = health_data.get('active_shards_percent', 0)
                print(f"📊 Shard Health: {active_percent:.1f}%")
                print()
