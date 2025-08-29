"""
Health-related command handlers for escmd.

This module contains handlers for health monitoring, cluster checks, and ping operations.
"""

import json
import time
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from rich.table import Table as InnerTable
from rich.prompt import Confirm

from .base_handler import BaseHandler


class HealthHandler(BaseHandler):
    """Handler for health monitoring and cluster checking commands."""

    def handle_health(self):
        """Handle cluster health display with various modes and formats."""
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

                # Create panel and display
                panel = Panel(
                    table,
                    title=f"⚡ Quick Health Check",
                    subtitle=f"Cluster: {health_data.get('cluster_name', 'Unknown')}",
                    border_style=status_color,
                    padding=(1, 2)
                )

                print()
                console.print(panel)
                print()

            except ImportError as e:
                # Fallback to basic output if rich components aren't available
                print(f"Cluster: {health_data.get('cluster_name', 'Unknown')}")
                print(f"Status: {health_data.get('cluster_status', 'unknown').upper()}")
                print(f"Nodes: {health_data.get('number_of_nodes', 0)}")
                print(f"Data Nodes: {health_data.get('number_of_data_nodes', 0)}")
                print(f"Primary Shards: {health_data.get('active_primary_shards', 0):,}")
                print(f"Total Shards: {health_data.get('active_shards', 0):,}")
                print(f"Unassigned Shards: {health_data.get('unassigned_shards', 0):,}")

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
                compare_config.get('read_timeout', 60),                # timeout
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
                    cluster_config.get('read_timeout', 60),                # timeout
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

    def handle_ping(self):
        """Enhanced ping command with Rich formatting and detailed connection information."""
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

            # from utils import show_message_box
            self.es_client.show_message_box("Connection Error", f"❌ Connection Error: {str(e)}\nFailed to ping {self.es_client.host1}:{self.es_client.port}", message_style="bold white", panel_style="red")
            return False

    def _get_cluster_connection_info(self):
        """Get cluster connection information for ping command."""
        return {
            'host': self.es_client.host1,
            'port': self.es_client.port,
            'ssl_enabled': self.es_client.use_ssl,
            'verify_certs': self.es_client.verify_certs,
            'username': self.es_client.elastic_username if self.es_client.elastic_username else None
        }

    def handle_cluster_check(self):
        """Handle comprehensive cluster health checking command."""
        import time

        max_shard_size = getattr(self.args, 'max_shard_size', 50)  # Default 50GB
        show_details = getattr(self.args, 'show_details', False)
        skip_ilm = getattr(self.args, 'skip_ilm', False)

        if self.args.format == 'json':
            # Gather all data for JSON output
            check_results = self.es_client.perform_cluster_health_checks(max_shard_size, skip_ilm)
            
            # Handle replica fixing if requested
            fix_replicas = getattr(self.args, 'fix_replicas', None)
            if fix_replicas is not None:
                replica_results = self._perform_replica_fixing_json(check_results, fix_replicas)
                check_results['replica_fixing'] = replica_results
                
            # Sanitize the data to ensure valid JSON
            sanitized_results = self._sanitize_for_json(check_results)
            print(json.dumps(sanitized_results, indent=2, ensure_ascii=True))
        else:
            # Rich formatted output with progress tracking
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=self.console,
                transient=True
            ) as progress:

                # Create main task (adjust total based on whether ILM is skipped)
                total_steps = 3 if skip_ilm else 4
                main_task = progress.add_task("[bold cyan]Running cluster health checks...", total=total_steps)

                # Step 1: ILM errors check (skip if requested)
                if not skip_ilm:
                    progress.update(main_task, description="[bold yellow]🔍 Checking for ILM errors...")
                    ilm_errors = self.es_client.check_ilm_errors()
                    progress.advance(main_task)
                    time.sleep(0.1)
                else:
                    ilm_errors = {'skipped': True, 'reason': 'ILM checks skipped via --skip-ilm flag'}

                # Step 2: No replicas check
                progress.update(main_task, description="[bold blue]📊 Checking indices with no replicas...")
                no_replica_indices = self.es_client.check_no_replica_indices()
                progress.advance(main_task)
                time.sleep(0.1)

                # Step 3: Large shards check
                progress.update(main_task, description="[bold orange1]📏 Checking for oversized shards...")
                large_shards = self.es_client.check_large_shards(max_shard_size)
                progress.advance(main_task)
                time.sleep(0.1)

                # Step 4: Generate report
                progress.update(main_task, description="[bold green]📋 Generating health report...")
                progress.advance(main_task)

            # Display comprehensive health report
            self.es_client.display_cluster_health_report({
                'ilm_results': ilm_errors,  # Pass as ilm_results to match new format
                'no_replica_indices': no_replica_indices,
                'large_shards': large_shards,
                'max_shard_size': max_shard_size,
                'show_details': show_details
            })
            
            # Handle replica fixing if requested
            fix_replicas = getattr(self.args, 'fix_replicas', None)
            if fix_replicas is not None:
                self._handle_replica_fixing_in_cluster_check(no_replica_indices, fix_replicas)

    def _handle_replica_fixing_in_cluster_check(self, no_replica_indices, target_count):
        """Handle replica fixing in table mode during cluster-check."""
        if not no_replica_indices:
            self.console.print("\n[green]✅ No indices found with 0 replicas - nothing to fix![/green]")
            return
        
        # Extract arguments
        dry_run = getattr(self.args, 'dry_run', False)
        force = getattr(self.args, 'force', False)
        
        try:
            # Initialize replica manager
            if not hasattr(self.es_client, 'replica_manager'):
                self.es_client.init_replica_manager()
            
            # Convert no_replica_indices to the format expected by ReplicaManager
            target_indices = [idx['index'] for idx in no_replica_indices]
            
            # Plan the updates
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=self.console,
                transient=True
            ) as progress:
                
                plan_task = progress.add_task("[bold cyan]Planning replica fixes...", total=1)
                plan_result = self.es_client.replica_manager.plan_replica_updates(
                    target_count=target_count,
                    indices=target_indices,
                    pattern=None,
                    no_replicas_only=False  # We already filtered to no-replica indices
                )
                progress.advance(plan_task)
            
            # Display the plan
            self.console.print(f"\n[bold cyan]🔧 Replica Fixing Plan (Target: {target_count} replica{'s' if target_count != 1 else ''})[/bold cyan]")
            self.es_client.replica_manager.display_update_plan(plan_result, dry_run)
            
            # Execute if not dry run and there are updates
            if not dry_run and plan_result['indices_to_update']:
                if not force:
                    if not Confirm.ask(f"\n⚠️  This will update {len(plan_result['indices_to_update'])} indices. Continue?"):
                        self.console.print("[yellow]Replica fixing cancelled.[/yellow]")
                        return
                
                # Execute the updates
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    console=self.console,
                    transient=True
                ) as progress:
                    
                    update_task = progress.add_task("[bold green]Fixing replica counts...", total=len(plan_result['indices_to_update']))
                    result = self.es_client.replica_manager.execute_replica_updates(
                        plan_result['indices_to_update'], 
                        target_count,
                        progress=progress,
                        task_id=update_task
                    )
                
                # Display results
                self.console.print(f"\n[bold green]✅ Replica Fixing Results[/bold green]")
                self.es_client.replica_manager.display_update_results(result)
                
        except Exception as e:
            self.console.print(f"[red]Error during replica fixing: {str(e)}[/red]")

    def _perform_replica_fixing_json(self, check_results, target_count):
        """Handle replica fixing in JSON mode during cluster-check."""
        try:
            # Initialize replica manager
            if not hasattr(self.es_client, 'replica_manager'):
                self.es_client.init_replica_manager()
            
            # Get no-replica indices from check results
            no_replica_indices = check_results.get('no_replica_indices', [])
            if not no_replica_indices:
                return {
                    'success': True,
                    'message': 'No indices found with 0 replicas - nothing to fix',
                    'indices_processed': 0,
                    'indices_updated': 0,
                    'results': []
                }
            
            # Convert to target indices list
            target_indices = [idx['index'] for idx in no_replica_indices]
            
            # Plan and execute the updates
            plan_result = self.es_client.replica_manager.plan_replica_updates(
                target_count=target_count,
                indices=target_indices,
                pattern=None,
                no_replicas_only=False  # We already filtered to no-replica indices
            )
            
            # Extract arguments
            dry_run = getattr(self.args, 'dry_run', False)
            
            if dry_run or not plan_result['indices_to_update']:
                return {
                    'success': True,
                    'dry_run': dry_run,
                    'target_count': target_count,
                    'indices_planned': len(plan_result['indices_to_update']),
                    'plan': plan_result
                }
            
            # Execute the updates
            result = self.es_client.replica_manager.execute_replica_updates(
                plan_result['indices_to_update'], 
                target_count
            )
            
            return {
                'success': True,
                'target_count': target_count,
                'indices_processed': len(plan_result['indices_to_update']),
                'execution_result': result
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'target_count': target_count
            }
