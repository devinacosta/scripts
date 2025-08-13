#!/usr/bin/env python3
"""
Administration tool for ElasticSearch, simplifies admin tasks.
"""

# Import Modules
import argparse
import getpass
import json
import os
import re
import yaml

from esclient import ElasticsearchClient
from rich import print
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

def should_use_ascii_mode(config_manager):
    """
    Check if ASCII mode should be used by checking environment variable first, then configuration.

    Args:
        config_manager: Configuration manager instance

    Returns:
        bool: True if ASCII mode should be used
    """
    # Environment variable takes precedence
    env_ascii = os.environ.get('ESCMD_ASCII_MODE', '').lower() in ('true', '1', 'yes')
    if env_ascii:
        return True

    # Fall back to configuration file setting
    return config_manager.get_ascii_mode()
from command_handler import CommandHandler
from configuration_manager import ConfigurationManager
from utils import show_message_box, find_matching_index, find_matching_node, show_locations, print_json_as_table, convert_dict_list_to_dict

VERSION = '2.1.0'
DATE = "08/12/2025"

if __name__ == "__main__":
    # Start Status Console
    console = Console()

    # Run Main Function
    parser = argparse.ArgumentParser(description='Elasticsearch command-line tool', add_help=False)
    subparsers = parser.add_subparsers(dest='command', help='Sub-command help')

    # Parameters
    parser.add_argument("-l", "--locations", help="Location ( defaults to localhost )", type=str, default=None)
    parser.add_argument("-h", "--help", action="store_true", help="Show this help message and exit")

    # Nodes command
    allocation_parser = subparsers.add_parser('allocation', help='Manage cluster allocation settings')
    current_master_parser = subparsers.add_parser('current-master', help='List Current Master')
    exclude_parser = subparsers.add_parser('exclude', help='Exclude Indice from Host')
    excludereset_parser = subparsers.add_parser('exclude-reset', help="Remove Settings from Indice")
    flush_parser = subparsers.add_parser('flush', help='Perform Elasticsearch Flush')
    freeze_parser = subparsers.add_parser('freeze', help='Freeze an Elasticsearch index')
    health_parser = subparsers.add_parser('health', help='Show Cluster Health')
    indice_parser = subparsers.add_parser('indice', help='Indice - Single One')
    indices_parser = subparsers.add_parser('indices', help='Indices')
    locations_parser = subparsers.add_parser('locations', help='Display All Configured Locations')
    masters_parser = subparsers.add_parser('masters', help='List ES Master nodes')
    nodes_parser = subparsers.add_parser('nodes', help='List Elasticsearch nodes')
    # Dangling indices command
    dangling_parser = subparsers.add_parser('dangling', help='List cluster dangling indices or delete specific dangling index')
    dangling_parser.add_argument('uuid', nargs='?', default=None, help='Index UUID to delete (optional)')
    dangling_parser.add_argument('--delete', action='store_true', help='Delete the specified dangling index by UUID')
    dangling_parser.add_argument('--yes-i-really-mean-it', action='store_true', help='Skip confirmation prompt for deletion (use with extreme caution)')
    dangling_parser.add_argument('--format', choices=['json', 'table'], default='table', help='Output format (json or table)')
    ping_parser = subparsers.add_parser('ping', help='Check ES Connection')
    ping_parser.add_argument('--format', choices=['json', 'table'], default='table', help='Output format (json or table)')
    recovery_parser = subparsers.add_parser('recovery', help='List Recovery Jobs')
    settings_parser = subparsers.add_parser('settings', help='Actions for ES Allocation')
    storage_parser = subparsers.add_parser('storage', help='List ES Disk Usage')
    getdefault_parser = subparsers.add_parser('get-default', help='Show Default Cluster configured.')
    setdefault_parser = subparsers.add_parser('set-default', help='Set Default Cluster to use for commands.')
    settings_show_parser = subparsers.add_parser('show-settings', help='Show current configuration settings.')
    shards_parser = subparsers.add_parser('shards', help='Show Shards')
    shard_colocation_parser = subparsers.add_parser('shard-colocation', help='Find indices with primary and replica shards on the same host')
    rollover_parser = subparsers.add_parser('rollover', help="Rollover Single Datastream")
    autorollover_parser = subparsers.add_parser('auto-rollover', help='Rollover biggest shard')
    snapshots_parser = subparsers.add_parser('snapshots', help='Manage Elasticsearch snapshots')
    ilm_parser = subparsers.add_parser('ilm', help='Manage Index Lifecycle Management (ILM)')
    datastreams_parser = subparsers.add_parser('datastreams', help='List datastreams or show datastream details')
    version = subparsers.add_parser('version', help='Show Version Number')

    # Allocation subcommands
    allocation_subparsers = allocation_parser.add_subparsers(dest='allocation_action', help='Allocation actions')

    # Main allocation commands
    display_parser = allocation_subparsers.add_parser('display', help='Show current allocation settings')
    display_parser.add_argument('--format', choices=['json', 'table'], default='table', help='Output format (json or table)')

    enable_parser = allocation_subparsers.add_parser('enable', help='Enable shard allocation')
    enable_parser.add_argument('--format', choices=['json', 'table'], default='table', help='Output format (json or table)')

    disable_parser = allocation_subparsers.add_parser('disable', help='Disable shard allocation')
    disable_parser.add_argument('--format', choices=['json', 'table'], default='table', help='Output format (json or table)')

    # Exclude sub-commands
    exclude_allocation_parser = allocation_subparsers.add_parser('exclude', help='Manage node exclusions')
    exclude_subparsers = exclude_allocation_parser.add_subparsers(dest='exclude_action', help='Exclusion actions')

    add_parser = exclude_subparsers.add_parser('add', help='Add hostname to exclusion list')
    add_parser.add_argument('hostname', help='Hostname to exclude')
    add_parser.add_argument('--format', choices=['json', 'table'], default='table', help='Output format (json or table)')

    remove_parser = exclude_subparsers.add_parser('remove', help='Remove hostname from exclusion list')
    remove_parser.add_argument('hostname', help='Hostname to remove from exclusion')
    remove_parser.add_argument('--format', choices=['json', 'table'], default='table', help='Output format (json or table)')

    reset_parser = exclude_subparsers.add_parser('reset', help='Clear all exclusions')
    reset_parser.add_argument('--format', choices=['json', 'table'], default='table', help='Output format (json or table)')

    # Allocation explain sub-command
    explain_parser = allocation_subparsers.add_parser('explain', help='Explain allocation decisions for specific index/shard')
    explain_parser.add_argument('index', help='Index name to explain allocation for')
    explain_parser.add_argument('--shard', '-s', type=int, default=0, help='Shard number (default: 0)')
    explain_parser.add_argument('--primary', action='store_true', help='Explain primary shard (default: auto-detect)')
    explain_parser.add_argument('--format', choices=['json', 'table'], default='table', help='Output format (json or table)')

    # Add format to main allocation command for default display
    allocation_parser.add_argument('--format', choices=['json', 'table'], default='table', help='Output format (json or table)')

    # Snapshots subcommands
    snapshots_subparsers = snapshots_parser.add_subparsers(dest='snapshots_action', help='Snapshot actions')
    list_snapshots_parser = snapshots_subparsers.add_parser('list', help='List all snapshots from configured repository')
    list_snapshots_parser.add_argument('pattern', nargs='?', default=None, help='Optional regex pattern to filter snapshots')
    list_snapshots_parser.add_argument('--format', choices=['json', 'table'], nargs='?', default='table', help='Output format (json or table)')
    list_snapshots_parser.add_argument('--pager', action="store_true", default=False, help='Force pager for scrolling (auto-enabled based on config: enable_paging/paging_threshold)')

    # ILM subcommands
    ilm_subparsers = ilm_parser.add_subparsers(dest='ilm_action', help='ILM actions')

    ilm_status_parser = ilm_subparsers.add_parser('status', help='Show comprehensive ILM status and statistics')
    ilm_status_parser.add_argument('--format', choices=['json', 'table'], default='table', help='Output format (json or table)')

    ilm_policies_parser = ilm_subparsers.add_parser('policies', help='List all ILM policies')
    ilm_policies_parser.add_argument('--format', choices=['json', 'table'], default='table', help='Output format (json or table)')

    ilm_policy_parser = ilm_subparsers.add_parser('policy', help='Show detailed configuration for specific ILM policy')
    ilm_policy_parser.add_argument('policy_name', help='Policy name to show details for')
    ilm_policy_parser.add_argument('--format', choices=['json', 'table'], default='table', help='Output format (json or table)')
    ilm_policy_parser.add_argument('--show-all', action='store_true', help='Show all indices using this policy (default shows first 10)')

    ilm_explain_parser = ilm_subparsers.add_parser('explain', help='Show ILM status for specific index (not policy)')
    ilm_explain_parser.add_argument('index', help='Index name to explain (use actual index name, not policy name)')
    ilm_explain_parser.add_argument('--format', choices=['json', 'table'], default='table', help='Output format (json or table)')

    ilm_errors_parser = ilm_subparsers.add_parser('errors', help='Show indices with ILM errors')
    ilm_errors_parser.add_argument('--format', choices=['json', 'table'], default='table', help='Output format (json or table)')

    # Add Json Parameters
    current_master_parser.add_argument('--format', choices=['json', 'table'], default='table', help='Output format (json or table)')
    health_parser.add_argument('--format', choices=['json', 'table'], nargs='?', default='table', help='Output format (json or table)')
    health_parser.add_argument('--style', choices=['dashboard', 'classic'], default=None, help='Display style (dashboard or classic table) - overrides config file setting')
    health_parser.add_argument('--classic-style', choices=['table', 'panel'], default=None, help='Classic display format (table or panel) - overrides config file setting')
    health_parser.add_argument('--compare', help='Compare with another cluster (e.g., --compare production). Forces classic style.')
    health_parser.add_argument('--group', help='Show health for all clusters in a group (e.g., --group att). Forces classic style.')
    health_parser.add_argument('-q', '--quick', action='store_true', help='Quick mode - only perform basic cluster health check and skip additional diagnostics')
    indice_parser.add_argument('indice', nargs='?', default=None)
    indices_parser.add_argument('--cold', action="store_true", default=False)
    indices_parser.add_argument('--delete', action="store_true", default=False)
    indices_parser.add_argument('--format', choices=['json', 'table'], nargs='?', default='table', help='List indices')
    indices_parser.add_argument('--status', choices=['green', 'yellow', 'red'], nargs='?', default=None)
    indices_parser.add_argument('--pager', action="store_true", default=False, help='Force pager for scrolling (auto-enabled based on config: enable_paging/paging_threshold)')
    indices_parser.add_argument('regex', nargs='?', default=None, help='Regex')
    masters_parser.add_argument('--format', choices=['json', 'table'], nargs='?', default='table', help='Ouptput format (json or table)')
    nodes_parser.add_argument('--format', choices=['data', 'json', 'table'], nargs='?', default='table', help='Ouptput format (json or table)')
    recovery_parser.add_argument('--format', choices=['data', 'json', 'table'], nargs='?', default='table', help='Ouptput format (json or table)')
    settings_parser.add_argument('--format', choices=['table', 'json'], nargs='?', default='table', help='Output format (json or table)')
    settings_parser.add_argument('settings_cmd', choices=['display', 'show'], nargs='?', default='display', help='Show Settings')
    setdefault_parser.add_argument('defaultcluster_cmd', nargs='?', default='default')
    storage_parser.add_argument('--format', choices=['data', 'json', 'table'], nargs='?', default='table', help='Ouptput format (json or table)')
    shards_parser.add_argument('--format', choices=['data', 'json', 'table'], nargs='?', default='table', help='Ouptput format (json or table)')
    shards_parser.add_argument('--server', '-s', nargs=1, default=None, help='Limit by server (ie: ess46)')
    shards_parser.add_argument('--limit','-n', default=0, help="Limit by XX rows (ie: 10)")
    shards_parser.add_argument('--size', '-z', action="store_true", default=False, help="Sort by size")
    shards_parser.add_argument('--pager', action="store_true", default=False, help='Force pager for scrolling (auto-enabled based on config: enable_paging/paging_threshold)')
    shards_parser.add_argument('regex', nargs='?', default=None, help='Regex')
    shard_colocation_parser.add_argument('--format', choices=['json', 'table'], default='table', help='Output format (json or table)')
    shard_colocation_parser.add_argument('--pager', action="store_true", default=False, help='Force pager for scrolling (auto-enabled based on config: enable_paging/paging_threshold)')
    shard_colocation_parser.add_argument('regex', nargs='?', default=None, help='Optional regex pattern to filter indices')
    rollover_parser.add_argument('datastream', nargs='?', default=None, help='Datastream to match')
    autorollover_parser.add_argument('host', nargs='?', default=None, help='Hostname (regex) to match.')
    datastreams_parser.add_argument('name', nargs='?', default=None, help='Datastream name to show details for (optional)')
    datastreams_parser.add_argument('--format', choices=['json', 'table'], default='table', help='Output format (json or table)')
    datastreams_parser.add_argument('--delete', action='store_true', help='Delete the specified datastream')
    exclude_parser.add_argument('indice', nargs='?', default=None, help='Indice to exclude')
    exclude_parser.add_argument('--server', '-s', nargs=1, default=None, help='Server to exclude (ie: aex10-c01-ess01-1)')
    excludereset_parser.add_argument('indice', nargs='?', default=None, help="Indice to reset")
    freeze_parser.add_argument('indice', help='Name of the index to freeze')

    # Parse Arguments
    args = parser.parse_args()

    # Custom fancy help display
    if args.help:
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        from rich.columns import Columns
        from rich.text import Text

        console = Console()

        # Create title panel
        title_panel = Panel(
            Text("🛠️  Elasticsearch Command-Line Tool", style="bold cyan", justify="center"),
            subtitle="Advanced cluster management and monitoring",
            border_style="cyan",
            padding=(1, 2)
        )

        # Create command categories
        cluster_table = Table.grid(padding=(0, 1))
        cluster_table.add_column(style="bold yellow", no_wrap=True)
        cluster_table.add_column(style="white")
        cluster_table.add_row("🔍 health", "Cluster health monitoring (dashboard/classic/comparison/groups)")
        cluster_table.add_row("⚙️  settings", "View and manage cluster settings")
        cluster_table.add_row("🔧 show-settings", "Show current configuration settings")
        cluster_table.add_row("🎯 get-default", "Show current default cluster configuration")
        cluster_table.add_row("📌 set-default", "Set default cluster for commands")
        cluster_table.add_row("🏓 ping", "Test connectivity with cluster details and health overview")
        cluster_table.add_row("📍 locations", "List all configured clusters")

        node_table = Table.grid(padding=(0, 1))
        node_table.add_column(style="bold green", no_wrap=True)
        node_table.add_column(style="white")
        node_table.add_row("🖥️  nodes", "List all cluster nodes")
        node_table.add_row("👑 masters", "List master-eligible nodes")
        node_table.add_row("🎯 current-master", "Show current master node")

        index_table = Table.grid(padding=(0, 1))
        index_table.add_column(style="bold blue", no_wrap=True)
        index_table.add_column(style="white")
        index_table.add_row("📊 indices", "List and manage indices")
        index_table.add_row("📄 indice", "Show single index details")
        index_table.add_row("🧊 freeze", "Freeze an index with validation and detailed feedback")
        index_table.add_row("🔄 shards", "View shard distribution")
        index_table.add_row("⚠️  shard-colocation", "Find indices with primary and replica on same host")

        ops_table = Table.grid(padding=(0, 1))
        ops_table.add_column(style="bold magenta", no_wrap=True)
        ops_table.add_column(style="white")
        ops_table.add_row("⚖️  allocation", "Manage shard allocation and explain allocation decisions")
        ops_table.add_row("🔧 recovery", "Monitor recovery jobs")
        ops_table.add_row("🔄 flush", "Perform synced flush with detailed results")
        ops_table.add_row("💾 storage", "View disk usage")
        ops_table.add_row("📦 snapshots", "Manage snapshots")
        ops_table.add_row("📋 ilm", "Index Lifecycle Management")
        ops_table.add_row("🗂️  datastreams", "List, view details, or delete datastreams")
        ops_table.add_row("⚠️  dangling", "List and analyze dangling indices")

        # Create panels for table cells
        cluster_panel = Panel(cluster_table, title="[bold yellow]🏢 Cluster Operations[/bold yellow]", border_style="yellow")
        node_panel = Panel(node_table, title="[bold green]🖥️  Node Management[/bold green]", border_style="green")
        index_panel = Panel(index_table, title="[bold blue]📊 Index Operations[/bold blue]", border_style="blue")
        ops_panel = Panel(ops_table, title="[bold magenta]🔧 Maintenance[/bold magenta]", border_style="magenta")

        # Create usage examples
        usage_table = Table.grid(padding=(0, 1))
        usage_table.add_column(style="bold cyan", no_wrap=True)
        usage_table.add_column(style="dim white")
        usage_table.add_row("Basic Health:", "./escmd.py health")
        usage_table.add_row("Compare Clusters:", "./escmd.py health --compare iad41")
        usage_table.add_row("Group Health:", "./escmd.py health --group att")
        usage_table.add_row("Shard Analysis:", "./escmd.py shard-colocation")
        usage_table.add_row("Dangling Indices:", "./escmd.py dangling")
        usage_table.add_row("Allocation Explain:", "./escmd.py allocation explain my-index")
        usage_table.add_row("JSON Output:", "./escmd.py health --format json")

        usage_panel = Panel(usage_table, title="[bold cyan]🚀 Quick Examples[/bold cyan]", border_style="cyan")

        # Display everything
        print()
        console.print(title_panel)
        print()

        # Create perfect 2x2 table grid with equal column widths
        grid_table = Table(show_header=False, show_edge=False, box=None, padding=0, expand=True)
        grid_table.add_column(style="", ratio=1)  # Column 1 - 50% width
        grid_table.add_column(style="", ratio=1)  # Column 2 - 50% width

        # Add rows with panels
        grid_table.add_row(cluster_panel, node_panel)   # Row 1
        grid_table.add_row(index_panel, ops_panel)      # Row 2

        # Display the perfect grid
        console.print(grid_table)
        print()
        console.print(usage_panel)
        print()

        # Footer with global options
        footer_text = Text("Global Options: ", style="bold white")
        footer_text.append("-l <cluster>", style="bold yellow")
        footer_text.append(" (specify cluster)  ", style="white")
        footer_text.append("--help", style="bold yellow")
        footer_text.append(" (show this help)", style="white")

        footer_panel = Panel(footer_text, border_style="dim white")
        console.print(footer_panel)
        print()
        exit()

    # Initialize Configuration Manager
    script_directory = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(script_directory, 'elastic_servers.yml')
    state_file = os.path.join(script_directory, 'escmd.json')
    config_manager = ConfigurationManager(config_file, state_file)

    # Handle special commands first
    if args.command == 'set-default':
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text

        console = Console()
        cluster_name = args.defaultcluster_cmd

        # Validate cluster exists
        try:
            server_config = config_manager.get_server_config(cluster_name)
            if not server_config:
                console.print(f"[red]❌ Error: Cluster '{cluster_name}' not found in configuration![/red]")
                available_clusters = list(config_manager.servers_dict.keys())
                console.print(f"[yellow]💡 Available clusters: {', '.join(available_clusters)}[/yellow]")
                exit(1)
        except Exception as e:
            console.print(f"[red]❌ Error validating cluster '{cluster_name}': {str(e)}[/red]")
            exit(1)

        # Set the new default
        config_manager.set_default_cluster(cluster_name)

        # Create confirmation display
        table = Table.grid(padding=(0, 1))
        table.add_column(style="bold white", no_wrap=True)
        table.add_column(style="bold green")

        # Add cluster details
        table.add_row("🎯 New Default:", cluster_name)
        table.add_row("🖥️  Primary Host:", server_config.get('hostname', 'Not configured'))

        if server_config.get('hostname2'):
            table.add_row("🔄 Backup Host:", server_config.get('hostname2'))

        table.add_row("🔌 Port:", str(server_config.get('port', 9200)))

        # SSL status
        ssl_status = "🔒 Enabled" if server_config.get('use_ssl') else "🔓 Disabled"
        table.add_row("🛡️  SSL:", ssl_status)

        # Authentication status
        auth_status = "🔐 Enabled" if server_config.get('elastic_authentication') else "🚪 Disabled"
        table.add_row("🔑 Authentication:", auth_status)

        # Create success panel
        panel = Panel(
            table,
            title="[bold green]✅ Default Cluster Updated Successfully[/bold green]",
            subtitle=f"[dim]You can now run commands without '-l {cluster_name}'[/dim]",
            border_style="green",
            padding=(1, 2),
            expand=False
        )

        print()
        console.print(panel)
        print()

        # Add usage example
        usage_text = Text("💡 Quick Test: ", style="bold yellow")
        usage_text.append(f"./escmd.py health", style="bold cyan")
        usage_text.append(f" (will now use {cluster_name})", style="dim white")
        console.print(usage_text)
        print()

        exit()

    if args.command == 'get-default':
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table

        console = Console()
        current_cluster = config_manager.get_default_cluster()

        try:
            server_config = config_manager.get_server_config(current_cluster)

            # Create table with icons and enhanced formatting
            table = Table.grid(padding=(0, 1))
            table.add_column(style="bold white", no_wrap=True)
            table.add_column(style="bold cyan")

            # Add configuration details with icons (ASCII fallback support)
            use_ascii = should_use_ascii_mode(config_manager)

            if use_ascii:
                # ASCII-only mode for maximum compatibility
                table.add_row("Cluster Name:", current_cluster)
                table.add_row("Primary Host:", server_config.get('hostname', 'Not configured'))

                if server_config.get('hostname2'):
                    table.add_row("Backup Host:", server_config.get('hostname2'))

                table.add_row("Port:", str(server_config.get('port', 9200)))

                # SSL Configuration
                ssl_status = "Enabled" if server_config.get('use_ssl') else "Disabled"
                table.add_row("SSL:", ssl_status)

                if server_config.get('use_ssl'):
                    cert_verify = "Verified" if server_config.get('verify_certs') else "Unverified"
                    table.add_row("Certificates:", cert_verify)

                # Authentication
                auth_status = "Enabled" if server_config.get('elastic_authentication') else "Disabled"
                table.add_row("Authentication:", auth_status)

                if server_config.get('elastic_authentication'):
                    username = server_config.get('elastic_username', 'Not configured')
                    table.add_row("Username:", username)

                    password_status = "Configured" if server_config.get('elastic_password') else "Not configured"
                    table.add_row("Password:", password_status)

                # Snapshot repository
                if server_config.get('elastic_s3snapshot_repo'):
                    table.add_row("Snapshot Repo:", server_config.get('elastic_s3snapshot_repo'))

                # Health display style
                health_style = server_config.get('health_style', 'dashboard')
                table.add_row("Health Style:", health_style.title())

                # Classic style if configured
                if server_config.get('classic_style'):
                    classic_style = server_config.get('classic_style')
                    table.add_row("Classic Format:", classic_style.title())
            else:
                # Unicode/emoji mode for modern terminals
                table.add_row("🏷️  Cluster Name:", current_cluster)
                table.add_row("🖥️  Primary Host:", server_config.get('hostname', 'Not configured'))

                if server_config.get('hostname2'):
                    table.add_row("🔄 Backup Host:", server_config.get('hostname2'))

                table.add_row("🔌 Port:", str(server_config.get('port', 9200)))

                # SSL Configuration
                ssl_status = "🔒 Enabled" if server_config.get('use_ssl') else "🔓 Disabled"
                table.add_row("🛡️  SSL:", ssl_status)

                if server_config.get('use_ssl'):
                    cert_verify = "✅ Verified" if server_config.get('verify_certs') else "⚠️  Unverified"
                    table.add_row("📜 Certificates:", cert_verify)

                # Authentication
                auth_status = "🔐 Enabled" if server_config.get('elastic_authentication') else "🚪 Disabled"
                table.add_row("🔑 Authentication:", auth_status)

                if server_config.get('elastic_authentication'):
                    username = server_config.get('elastic_username', 'Not configured')
                    table.add_row("👤 Username:", username)

                    # Don't show actual password, just indicate if configured
                    password_status = "✅ Configured" if server_config.get('elastic_password') else "❌ Not configured"
                    table.add_row("🔐 Password:", password_status)

                # Snapshot repository
                if server_config.get('elastic_s3snapshot_repo'):
                    table.add_row("📦 Snapshot Repo:", server_config.get('elastic_s3snapshot_repo'))

                # Health display style
                health_style = server_config.get('health_style', 'dashboard')
                style_icon = "📊" if health_style == 'dashboard' else "📋"
                table.add_row(f"{style_icon} Health Style:", health_style.title())

                # Classic style if configured
                if server_config.get('classic_style'):
                    classic_style = server_config.get('classic_style')
                    classic_icon = "📄" if classic_style == 'table' else "🎛️"
                    table.add_row(f"{classic_icon} Classic Format:", classic_style.title())

            # Create panel with ASCII fallback for better terminal compatibility
            use_ascii = should_use_ascii_mode(config_manager)

            if use_ascii:
                title_text = "Default Cluster Configuration"
                border_style = "white"
            else:
                title_text = "🎯 Default Cluster Configuration"
                border_style = "cyan"

            panel = Panel(
                table,
                title=f"[bold cyan]{title_text}[/bold cyan]",
                subtitle=f"[dim]Active cluster: {current_cluster}[/dim]",
                border_style=border_style,
                padding=(1, 2)
            )

        except KeyError:
            # Error case with consistent styling and ASCII fallback
            use_ascii = should_use_ascii_mode(config_manager)

            error_table = Table.grid(padding=(0, 1))
            error_table.add_column(style="bold red", justify="center")

            if use_ascii:
                error_table.add_row("No Configuration Found")
                title_text = "Configuration Error"
            else:
                error_table.add_row("❌ No Configuration Found")
                title_text = "⚠️ Configuration Error"

            error_table.add_row(f"Cluster '{current_cluster}' is not configured in elastic_servers.yml")

            panel = Panel(
                error_table,
                title=f"[bold red]{title_text}[/bold red]",
                border_style="red",
                padding=(1, 2),
                width=80
            )

        print()
        console.print(panel)
        exit()

    if args.command == 'show-settings':
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table

        console = Console()
        use_ascii = should_use_ascii_mode(config_manager)

        # Create settings table
        table = Table.grid(padding=(0, 1))
        table.add_column(style="bold white", no_wrap=True)
        table.add_column(style="bold cyan")

        # Add all configuration settings
        settings = config_manager.default_settings

        if use_ascii:
            table.add_row("Box Style:", settings.get('box_style', 'SQUARE_DOUBLE_HEAD'))
            table.add_row("Health Style:", settings.get('health_style', 'dashboard'))
            table.add_row("Classic Style:", settings.get('classic_style', 'panel'))
            table.add_row("Enable Paging:", str(settings.get('enable_paging', False)))
            table.add_row("Paging Threshold:", str(settings.get('paging_threshold', 50)))
            table.add_row("Show Legend Panels:", str(settings.get('show_legend_panels', False)))
            table.add_row("ASCII Mode:", str(settings.get('ascii_mode', False)))

            # Environment override info
            env_ascii = os.environ.get('ESCMD_ASCII_MODE', '').lower() in ('true', '1', 'yes')
            if env_ascii:
                table.add_row("ASCII Mode Override:", "Environment variable enabled")

            title_text = "Current Configuration Settings"
            border_style = "white"
        else:
            table.add_row("📦 Box Style:", settings.get('box_style', 'SQUARE_DOUBLE_HEAD'))
            table.add_row("📊 Health Style:", settings.get('health_style', 'dashboard'))
            table.add_row("📋 Classic Style:", settings.get('classic_style', 'panel'))
            table.add_row("📄 Enable Paging:", str(settings.get('enable_paging', False)))
            table.add_row("🔢 Paging Threshold:", str(settings.get('paging_threshold', 50)))
            table.add_row("📖 Show Legend Panels:", str(settings.get('show_legend_panels', False)))
            table.add_row("🔤 ASCII Mode:", str(settings.get('ascii_mode', False)))

            # Environment override info
            env_ascii = os.environ.get('ESCMD_ASCII_MODE', '').lower() in ('true', '1', 'yes')
            if env_ascii:
                table.add_row("⚡ ASCII Mode Override:", "Environment variable enabled")

            title_text = "⚙️ Current Configuration Settings"
            border_style = "cyan"

        # Create panel
        panel = Panel(
            table,
            title=f"[bold cyan]{title_text}[/bold cyan]",
            subtitle=f"[dim]From: elastic_servers.yml[/dim]",
            border_style=border_style,
            padding=(1, 2)
        )

        print()
        console.print(panel)

        # Add usage information
        if use_ascii:
            usage_text = """
Configuration File: elastic_servers.yml
Environment Override: ESCMD_ASCII_MODE=true ./escmd.py <command>
To enable ASCII mode permanently, set 'ascii_mode: true' in settings section
"""
        else:
            usage_text = """
📁 Configuration File: elastic_servers.yml
🌍 Environment Override: ESCMD_ASCII_MODE=true ./escmd.py <command>
💡 To enable ASCII mode permanently, set 'ascii_mode: true' in settings section
"""

        console.print(f"[dim]{usage_text.strip()}[/dim]")
        print()
        exit()

    # Define which commands should not preprocess indices
    if args.command == 'version':
        # Enhanced version display with consistent styling
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        import sys
        import platform

        console = Console()

        # Create version table with health panel style
        table = Table.grid(padding=(0, 1))
        table.add_column(style="bold white", no_wrap=True)
        table.add_column(style="bold cyan")

        table.add_row("🛠️  Version:", VERSION)
        table.add_row("📅 Released:", DATE)
        table.add_row("📦 Build:", "Stable")
        table.add_row("🐍 Python:", f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} (Running)")

        # Create panel with consistent styling
        version_panel = Panel(
            table,
            title="[bold cyan]📋 escmd.py[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
            width=60
        )

        print()
        console.print(version_panel)
        print()
        exit()

    # Determine which location to use
    es_location = args.locations if args.locations else config_manager.get_default_cluster()
    location_config = config_manager.get_server_config_by_location(es_location)

    if not location_config:
        text = (f"Location: {es_location} not found.\nPlease check your elastic_settings.yml config file.")
        console.print(Panel.fit(text, title="Configuration Error"))
        exit(1)

    # Get configuration values
    elastic_host = location_config['elastic_host']
    elastic_host2 = location_config['elastic_host2']
    elastic_port = location_config['elastic_port']
    elastic_use_ssl = location_config['use_ssl']
    elastic_username = location_config['elastic_username']
    elastic_password = location_config['elastic_password']
    elastic_authentication = location_config.get('elastic_authentication', False)
    elastic_verify_certs = location_config.get('verify_certs', False)

    # Define which commands should not preprocess indices
    commands_no_preprocess = ['health', 'set-default', 'get-default', 'show-settings', 'version', 'dangling']

    # If no arguments passed, display help
    if vars(args)['command'] == None:
        parser.print_help()
    else:
        # Prompt for password if needed
        if elastic_authentication == True and (elastic_password == None or elastic_password == "None"):
            elastic_password = getpass.getpass(prompt="Enter your Password: ")

        # Initialize Elasticsearch client
        preprocess_indices = args.command not in commands_no_preprocess
        es_client = ElasticsearchClient(
            host1=elastic_host,
            host2=elastic_host2,
            port=elastic_port,
            use_ssl=elastic_use_ssl,
            timeout=60,
            verify_certs=elastic_verify_certs,
            elastic_authentication=elastic_authentication,
            elastic_username=elastic_username,
            elastic_password=elastic_password,
            preprocess_indices=preprocess_indices,
            box_style=config_manager.box_style
        )

        # Create and execute command handler
        command_handler = CommandHandler(es_client, args, console, config_file, location_config, es_location)
        # Dangling indices support
        if args.command == 'dangling':
            command_handler.handle_dangling()
        else:
            command_handler.execute()
