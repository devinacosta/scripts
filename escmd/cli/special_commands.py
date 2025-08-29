"""
Special command handlers for escmd.
Handles commands that don't require ES connection.
"""

import sys
import os
import json
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.align import Align


def show_welcome_screen(console):
    """Display a beautiful welcome screen when no command is provided."""
    
    # Create title panel
    title_table = Table.grid(padding=(0, 2))
    title_table.add_column(style="bold cyan", justify="center")
    title_table.add_row("🔍 ESCMD - Elasticsearch Command Line Tool")
    title_table.add_row("[dim]Advanced Elasticsearch CLI Management Tool v2.5.0[/dim]")
    
    title_panel = Panel(
        Align.center(title_table),
        title="[bold green]Welcome to ESCMD[/bold green]",
        border_style="green",
        padding=(1, 2)
    )
    
    # Dynamically get all available commands
    command_info = _get_dynamic_command_info()
    
    # Quick start commands (still curated for best UX)
    quick_start_table = Table(expand=True)
    quick_start_table.add_column("Command", style="bold yellow", no_wrap=True)
    quick_start_table.add_column("Description", style="white")
    
    # Keep curated quick commands for best user experience
    quick_commands = [
        ("./escmd.py health", "Show cluster health status"),
        ("./escmd.py indices", "List all indices"),
        ("./escmd.py nodes", "Show cluster nodes"),
        ("./escmd.py version", "Show detailed version & statistics"),
        ("./escmd.py locations", "Show configured clusters"),
        ("./escmd.py help", "Show detailed help system")
    ]
    
    for cmd, desc in quick_commands:
        quick_start_table.add_row(cmd, desc)
    
    quick_panel = Panel(
        quick_start_table,
        title="[bold blue]🚀 Quick Start Commands[/bold blue]",
        border_style="blue",
        padding=(1, 2)
    )
    
    # Dynamic command categories (compact version)
    categories_table = Table(expand=True)
    categories_table.add_column("Category", style="bold magenta", no_wrap=True)
    categories_table.add_column("Count", justify="right", style="cyan")
    categories_table.add_column("Examples", style="white")
    
    # Use dynamic data for categories
    for category, data in command_info['categories'].items():
        count = data['count']
        examples = ", ".join(data['examples'][:3])  # Show up to 3 examples
        categories_table.add_row(category, str(count), examples)
    
    # Add totals row
    categories_table.add_section()
    total_commands = command_info['total_commands']
    total_subcommands = command_info['total_subcommands']
    categories_table.add_row(
        "[bold white]TOTAL[/bold white]",
        f"[bold white]{total_commands + total_subcommands}[/bold white]",
        f"[dim]{total_commands} main + {total_subcommands} sub[/dim]"
    )
    
    categories_panel = Panel(
        categories_table,
        title="[bold magenta]📋 Categories Summary[/bold magenta]",
        border_style="magenta",
        padding=(1, 2)
    )
    
    # Complete command list with descriptions
    commands_table = _generate_complete_commands_table()
    
    commands_panel = Panel(
        commands_table,
        title="[bold cyan]📖 All Available Commands[/bold cyan]",
        border_style="cyan",
        padding=(1, 2)
    )
    
    # Usage tips
    tips_table = Table.grid(padding=(0, 1))
    tips_table.add_column(style="bold green", no_wrap=True)
    tips_table.add_column(style="white")
    
    tips_table.add_row("💡", "Use [bold]--format json[/bold] for machine-readable output")
    tips_table.add_row("🎯", "Use [bold]-l <cluster>[/bold] to target specific clusters")
    tips_table.add_row("📊", "Use [bold]--group <name>[/bold] for multi-cluster operations")
    tips_table.add_row("🔍", "Use [bold]./escmd.py help <topic>[/bold] for detailed help")
    tips_table.add_row("⚡", "Most commands support [bold]--pager[/bold] for large outputs")
    
    tips_panel = Panel(
        tips_table,
        title="[bold yellow]💡 Pro Tips[/bold yellow]",
        border_style="yellow",
        padding=(1, 2)
    )
    
    # Display all panels
    console.print()
    console.print(title_panel)
    console.print()
    
    # Display quick start and categories side by side if terminal is wide enough
    if console.size.width >= 120:
        console.print(Columns([quick_panel, categories_panel], equal=True))
    else:
        console.print(quick_panel)
        console.print()
        console.print(categories_panel)
    
    console.print()
    console.print(commands_panel)
    console.print()
    console.print(tips_panel)
    console.print()
    
    # Footer with dynamic count
    footer_text = f"[dim]Run [bold]./escmd.py version[/bold] for complete command statistics ({total_commands + total_subcommands} total commands) or [bold]./escmd.py help <topic>[/bold] for detailed help[/dim]"
    console.print(Align.center(footer_text))
    console.print()


def _generate_complete_commands_table():
    """Generate a comprehensive table of all commands with descriptions."""
    # Get both static descriptions and dynamically discovered commands
    static_descriptions = _get_static_command_descriptions()
    
    # Get dynamically discovered commands
    try:
        from cli.argument_parser import create_argument_parser
        parser = create_argument_parser()
        discovered_commands = set()
        for action in parser._actions:
            if hasattr(action, 'choices') and action.choices:
                discovered_commands.update(action.choices.keys())
                break
    except Exception:
        discovered_commands = set(static_descriptions.keys())
    
    # Combine static descriptions with any new commands
    commands_info = {}
    for cmd in discovered_commands:
        if cmd in static_descriptions:
            commands_info[cmd] = static_descriptions[cmd]
        else:
            # For new commands not in static list, provide a generic description
            commands_info[cmd] = f"Command: {cmd}"
    
    # Create the commands table with full width
    commands_table = Table(expand=True)  # This makes the table expand to full width
    commands_table.add_column("Command", style="bold yellow", no_wrap=True, width=22)
    commands_table.add_column("Description", style="white")
    
    # Sort commands alphabetically and add to table
    for cmd_name in sorted(commands_info.keys()):
        commands_table.add_row(cmd_name, commands_info[cmd_name])
    
    return commands_table


def _get_static_command_descriptions():
    """Static command descriptions as fallback."""
    return {
        'allocation': 'Manage cluster allocation settings',
        'auto-rollover': 'Rollover biggest shard',
        'cluster-check': 'Perform comprehensive cluster health checks',
        'current-master': 'List Current Master',
        'dangling': 'List, analyze, and manage dangling indices',
        'datastreams': 'List datastreams or show datastream details',
        'exclude': 'Exclude Indice from Host',
        'exclude-reset': 'Remove Settings from Indice',
        'flush': 'Perform Elasticsearch Flush',
        'freeze': 'Freeze an Elasticsearch index',
        'get-default': 'Show Default Cluster configured',
        'health': 'Show Cluster Health',
        'help': 'Show detailed help for specific commands',
        'ilm': 'Manage Index Lifecycle Management (ILM)',
        'indice': 'Indice - Single One',
        'indices': 'Indices',
        'locations': 'Display All Configured Locations',
        'masters': 'List ES Master nodes',
        'nodes': 'List Elasticsearch nodes',
        'ping': 'Check ES Connection',
        'recovery': 'List Recovery Jobs',
        'rollover': 'Rollover Single Datastream',
        'set-default': 'Set Default Cluster to use for commands',
        'set-replicas': 'Manage replica count for indices',
        'settings': 'Actions for ES Allocation',
        'shard-colocation': 'Find indices with primary and replica shards on the same host',
        'shards': 'Show Shards',
        'show-settings': 'Show current configuration settings',
        'snapshots': 'Manage Elasticsearch snapshots',
        'storage': 'List ES Disk Usage',
        'unfreeze': 'Unfreeze an Elasticsearch index',
        'version': 'Show version information'
    }


def _get_dynamic_command_info():
    """Dynamically discover all available commands and categorize them."""
    try:
        # Import the argument parser to discover commands
        from cli.argument_parser import create_argument_parser
        parser = create_argument_parser()
        
        # Extract all commands from subparsers
        discovered_commands = set()
        
        # More robust subparser discovery
        for action in parser._actions:
            if hasattr(action, 'choices') and action.choices:
                discovered_commands.update(action.choices.keys())
                break
        
        # Categorize the discovered commands
        categorized_commands = _categorize_discovered_commands(discovered_commands)
        
        # Get subcommand counts
        subcommand_counts = _get_subcommand_counts()
        
        # Calculate totals and create category info
        command_info = {
            'categories': {},
            'total_commands': 0,
            'total_subcommands': 0
        }
        
        for category, commands in categorized_commands.items():
            if not commands:  # Skip empty categories
                continue
                
            # Calculate subcounts for this category
            category_subcommands = sum(subcommand_counts.get(cmd, 0) for cmd in commands)
            
            command_info['categories'][category] = {
                'count': len(commands) + category_subcommands,
                'examples': sorted(commands)  # Will be truncated in display
            }
            
            command_info['total_commands'] += len(commands)
            command_info['total_subcommands'] += category_subcommands
        
        return command_info
        
    except Exception:
        # Fallback to static data if dynamic discovery fails
        return _get_static_command_info()


def _categorize_discovered_commands(commands):
    """Categorize discovered commands into logical groups."""
    command_categories = {
        "Cluster & Health": [],
        "Index Management": [],
        "Storage & Shards": [],
        "Allocation": [],
        "ILM & Lifecycle": [],
        "Snapshots": [],
        "Maintenance": [],
        "Utilities": []
    }
    
    # Command category mappings
    category_mapping = {
        "Cluster & Health": [
            "ping", "health", "current-master", "masters", "nodes", "recovery", 
            "cluster-check"
        ],
        "Index Management": [
            "indices", "indice", "freeze", "unfreeze", "flush", "exclude", 
            "exclude-reset", "set-replicas"
        ],
        "Storage & Shards": [
            "storage", "shards", "shard-colocation"
        ],
        "Allocation": [
            "allocation"
        ],
        "ILM & Lifecycle": [
            "ilm", "rollover", "auto-rollover", "datastreams"
        ],
        "Snapshots": [
            "snapshots"
        ],
        "Maintenance": [
            "dangling", "settings"
        ],
        "Utilities": [
            "help", "version", "locations", "get-default", "set-default", "show-settings"
        ]
    }
    
    # Assign discovered commands to categories
    for category, expected_commands in category_mapping.items():
        for cmd in expected_commands:
            if cmd in commands:
                command_categories[category].append(cmd)
    
    # Add any uncategorized commands to Utilities
    all_categorized = set()
    for cmds in command_categories.values():
        all_categorized.update(cmds)
    
    uncategorized = commands - all_categorized
    if uncategorized:
        command_categories["Utilities"].extend(sorted(uncategorized))
    
    # Only return non-empty categories
    return {k: v for k, v in command_categories.items() if v}


def _get_static_command_info():
    """Fallback static command information."""
    return {
        'categories': {
            "Cluster & Health": {'count': 7, 'examples': ["health", "nodes", "ping"]},
            "Index Management": {'count': 8, 'examples': ["indices", "freeze", "set-replicas"]},
            "Storage & Shards": {'count': 3, 'examples': ["storage", "shards"]},
            "ILM & Lifecycle": {'count': 12, 'examples': ["ilm", "rollover", "datastreams"]},
            "Snapshots": {'count': 3, 'examples': ["snapshots"]},
            "Allocation": {'count': 8, 'examples': ["allocation"]},
            "Maintenance": {'count': 2, 'examples': ["dangling", "settings"]},
            "Utilities": {'count': 14, 'examples': ["locations", "help", "version"]}
        },
        'total_commands': 32,
        'total_subcommands': 25
    }


def handle_version(version=None, date=None):
    """Display version information and command statistics."""
    console = Console()
    
    # Version information panel
    version_table = Table.grid(padding=(0, 3))
    version_table.add_column(style="bold cyan", no_wrap=True, min_width=12)
    version_table.add_column(style="white")
    
    version_table.add_row("Tool:", "escmd")
    version_table.add_row("Version:", version or "2.5.0")
    version_table.add_row("Released:", date or "08/29/2025") 
    version_table.add_row("Description:", "Advanced Elasticsearch CLI Management Tool")
    version_table.add_row("Author:", "Monitoring Team US")
    
    version_panel = Panel(
        version_table,
        title="[bold cyan]Version Information[/bold cyan]",
        border_style="cyan",
        padding=(1, 2)
    )
    
    # Command statistics
    stats_table = _generate_command_stats_table()
    
    stats_panel = Panel(
        stats_table,
        title="[bold green]Command Statistics[/bold green]",
        border_style="green",
        padding=(1, 2)
    )
    
    # System & Feature info
    feature_table = _generate_feature_info_table()
    
    feature_panel = Panel(
        feature_table,
        title="[bold magenta]Features & Capabilities[/bold magenta]",
        border_style="magenta",
        padding=(1, 2)
    )
    
    console.print(version_panel)
    console.print()
    console.print(stats_panel)
    console.print()
    console.print(feature_panel)


def _generate_feature_info_table():
    """Generate a table showing script features and capabilities."""
    from rich.table import Table
    import sys
    import platform
    import os
    from pathlib import Path
    
    feature_table = Table.grid(padding=(0, 3))
    feature_table.add_column(style="bold yellow", no_wrap=True, min_width=18)
    feature_table.add_column(style="white")
    
    # Python and system info
    feature_table.add_row("Python Version:", f"{sys.version.split()[0]}")
    feature_table.add_row("Python Executable:", sys.executable)
    feature_table.add_row("Platform:", f"{platform.system()} {platform.release()}")
    
    # Script location
    script_path = Path(__file__).parent.parent.resolve()
    feature_table.add_row("Script Location:", str(script_path))
    
    # Feature capabilities
    feature_table.add_row("", "")  # Separator
    feature_table.add_row("Output Formats:", "JSON, Table, Rich Dashboard")
    feature_table.add_row("Multi-Cluster:", "✓ Supported")
    feature_table.add_row("Configuration:", "YAML-based cluster configs")
    feature_table.add_row("Authentication:", "Basic Auth, SSL/TLS")
    feature_table.add_row("Paging Support:", "✓ Auto/Manual")
    feature_table.add_row("Color Output:", "✓ Rich Terminal UI")
    feature_table.add_row("Error Handling:", "✓ Retry Logic & Timeouts")
    feature_table.add_row("Dry Run Mode:", "✓ Safe Preview Mode")
    
    return feature_table


def _generate_command_stats_table():
    """Generate a table showing command statistics by category."""
    from rich.table import Table
    
    # Dynamically discover commands by importing the argument parser
    try:
        from cli.argument_parser import create_argument_parser
        parser = create_argument_parser()
        
        # Extract all commands from subparsers
        discovered_commands = set()
        if hasattr(parser, '_subparsers'):
            for action in parser._subparsers._actions:
                if hasattr(action, 'choices'):
                    discovered_commands.update(action.choices.keys())
        
        # Map discovered commands to categories
        command_categories = _categorize_commands(discovered_commands)
        
    except Exception:
        # Fallback to static command list if discovery fails
        command_categories = _get_static_command_categories()
    
    # Count subcommands for complex commands
    subcommand_counts = _get_subcommand_counts()
    
    # Create statistics table
    stats_table = Table()
    stats_table.add_column("Category", style="bold yellow", no_wrap=True)
    stats_table.add_column("Commands", justify="right", style="cyan")
    stats_table.add_column("Subcommands", justify="right", style="magenta")
    stats_table.add_column("Total", justify="right", style="bold green")
    
    total_commands = 0
    total_subcommands = 0
    
    for category, commands in command_categories.items():
        command_count = len(commands)
        subcommand_count = sum(subcommand_counts.get(cmd, 0) for cmd in commands)
        category_total = command_count + subcommand_count
        
        total_commands += command_count
        total_subcommands += subcommand_count
        
        stats_table.add_row(
            category,
            str(command_count),
            str(subcommand_count) if subcommand_count > 0 else "-",
            str(category_total)
        )
    
    # Add separator and totals
    stats_table.add_section()
    stats_table.add_row(
        "[bold white]TOTAL[/bold white]",
        f"[bold white]{total_commands}[/bold white]",
        f"[bold white]{total_subcommands}[/bold white]",
        f"[bold white]{total_commands + total_subcommands}[/bold white]"
    )
    
    return stats_table


def _categorize_commands(commands):
    """Categorize discovered commands."""
    command_categories = {
        "Cluster & Health": [],
        "Index Management": [],
        "Storage & Shards": [],
        "Allocation": [],
        "ILM & Lifecycle": [],
        "Snapshots": [],
        "Maintenance": [],
        "Utility": []
    }
    
    # Command category mappings
    category_mapping = {
        "Cluster & Health": [
            "ping", "health", "current-master", "masters", "nodes", "recovery", 
            "cluster-check"
        ],
        "Index Management": [
            "indices", "indice", "freeze", "unfreeze", "flush", "exclude", 
            "exclude-reset", "set-replicas"
        ],
        "Storage & Shards": [
            "storage", "shards", "shard-colocation"
        ],
        "Allocation": [
            "allocation"
        ],
        "ILM & Lifecycle": [
            "ilm", "rollover", "auto-rollover", "datastreams"
        ],
        "Snapshots": [
            "snapshots"
        ],
        "Maintenance": [
            "dangling", "settings"
        ],
        "Utility": [
            "help", "version", "locations", "get-default", "set-default", "show-settings"
        ]
    }
    
    # Assign discovered commands to categories
    for category, expected_commands in category_mapping.items():
        for cmd in expected_commands:
            if cmd in commands:
                command_categories[category].append(cmd)
    
    # Add any uncategorized commands to Utility
    all_categorized = set()
    for cmds in command_categories.values():
        all_categorized.update(cmds)
    
    uncategorized = commands - all_categorized
    command_categories["Utility"].extend(sorted(uncategorized))
    
    return {k: v for k, v in command_categories.items() if v}  # Only return non-empty categories


def _get_static_command_categories():
    """Fallback static command categories."""
    return {
        "Cluster & Health": [
            "ping", "health", "current-master", "masters", "nodes", "recovery", 
            "cluster-check"
        ],
        "Index Management": [
            "indices", "indice", "freeze", "unfreeze", "flush", "exclude", 
            "exclude-reset", "set-replicas"
        ],
        "Storage & Shards": [
            "storage", "shards", "shard-colocation"
        ],
        "Allocation": [
            "allocation"
        ],
        "ILM & Lifecycle": [
            "ilm", "rollover", "auto-rollover", "datastreams"
        ],
        "Snapshots": [
            "snapshots"
        ],
        "Maintenance": [
            "dangling", "settings"
        ],
        "Utility": [
            "help", "version", "locations", "get-default", "set-default", "show-settings"
        ]
    }


def _get_subcommand_counts():
    """Return subcommand counts for commands with subcommands."""
    return {
        "allocation": 7,  # display, enable, disable, exclude (add, remove, reset), explain
        "ilm": 8,  # status, policies, errors, policy, explain, remove-policy, set-policy
        "snapshots": 2,  # list, status
        "help": 8,  # indices, ilm, health, nodes, allocation, snapshots, dangling, shards
    }


def handle_locations(configuration_manager):
    """Display all configured cluster locations."""
    from rich.text import Text
    
    console = Console()
    
    if not configuration_manager.servers_dict:
        console.print("[yellow]No cluster configurations found.[/yellow]")
        return
    
    # Create a detailed table like the original
    locations_table = Table(title="Elasticsearch Configured Clusters")
    locations_table.add_column("Name", justify="left", style="cyan", no_wrap=True)
    locations_table.add_column("Hostname", justify="left", style="magenta")
    locations_table.add_column("Hostname2", justify="left", style="magenta")
    locations_table.add_column("Port", justify="right", style="green")
    locations_table.add_column("Use SSL", justify="center", style="red")
    locations_table.add_column("Verify Certs", justify="center", style="red")
    locations_table.add_column("Username", justify="left", style="yellow")
    locations_table.add_column("Password", justify="left", style="yellow")
    
    default_cluster = configuration_manager.get_default_cluster()
    
    # Sort by name and add data for each server
    sorted_servers = sorted(configuration_manager.servers_dict.items())
    for location, config in sorted_servers:
        # Add default marker to name
        name_display = f"{location} (default)" if location == default_cluster else location
        
        locations_table.add_row(
            name_display,
            config.get('hostname', ''),
            config.get('hostname2', ''),
            str(config.get('port', '')),
            str(config.get('use_ssl', '')),
            str(config.get('verify_certs', '')),
            config.get('elastic_username', ''),
            config.get('elastic_password', '')
        )
    
    console.print(locations_table)


def handle_get_default(configuration_manager):
    """Display the current default cluster configuration."""
    console = Console()
    
    current_cluster = configuration_manager.get_default_cluster()
    if not current_cluster:
        console.print("[yellow]No default cluster configured.[/yellow]")
        return
    
    # Try both the original case and lowercase version
    server_config = configuration_manager.servers_dict.get(current_cluster.lower())
    if not server_config:
        server_config = configuration_manager.servers_dict.get(current_cluster)
    
    if not server_config:
        console.print(f"[red]Default server '{current_cluster}' not found in configuration.[/red]")
        console.print("[yellow]Available clusters:[/yellow]")
        for cluster_name in sorted(configuration_manager.servers_dict.keys()):
            console.print(f"  • {cluster_name}")
        return
    
    # Create a table for the default configuration with better spacing
    config_table = Table.grid(padding=(0, 3))  # Add padding between columns
    config_table.add_column(style="bold cyan", no_wrap=True, min_width=15)
    config_table.add_column(style="white")
    
    config_table.add_row("Location:", current_cluster.lower())
    config_table.add_row("Cluster Name:", server_config.get('cluster_name', 'Unknown'))
    config_table.add_row("Host:", server_config.get('hostname', 'N/A'))
    config_table.add_row("Port:", str(server_config.get('port', 9200)))
    config_table.add_row("Username:", server_config.get('elastic_username', 'N/A'))
    config_table.add_row("SSL Verify:", str(server_config.get('verify_certs', True)))
    
    panel = Panel(
        config_table,
        title="[bold cyan]🎯 Current Default Cluster[/bold cyan]",
        border_style="cyan",
        padding=(1, 2)
    )
    
    console.print(panel)


def handle_set_default(location, configuration_manager):
    """Set a new default cluster."""
    console = Console()
    
    if not location:
        console.print("[red]Error: Location parameter is required for set-default command.[/red]")
        console.print("[yellow]Usage: ./escmd.py set-default <location>[/yellow]")
        return
    
    if location not in configuration_manager.servers_dict:
        console.print(f"[red]Error: Location '{location}' not found in configuration.[/red]")
        console.print("[yellow]Available locations:[/yellow]")
        for loc in configuration_manager.servers_dict.keys():
            console.print(f"  • {loc}")
        return
    
    # Update the default
    old_default = configuration_manager.get_default_cluster()
    configuration_manager.set_default_cluster(location)
    
    # Success message
    success_table = Table.grid(padding=(0, 3))  # Add padding for better spacing
    success_table.add_column(style="bold cyan", no_wrap=True, min_width=15)
    success_table.add_column(style="white")
    
    if old_default:
        success_table.add_row("Previous Default:", old_default)
    success_table.add_row("New Default:", location)
    success_table.add_row("Cluster Name:", configuration_manager.servers_dict[location].get('cluster_name', 'Unknown'))
    success_table.add_row("Host:", configuration_manager.servers_dict[location].get('hostname', 'N/A'))
    
    panel = Panel(
        success_table,
        title="[bold green]✅ Default Cluster Updated[/bold green]",
        border_style="green",
        padding=(1, 2)
    )
    
    console.print(panel)


def handle_show_settings(configuration_manager, format_output=None):
    """Display current configuration settings."""
    console = Console()
    
    if format_output == 'json':
        # JSON output
        default_cluster = configuration_manager.get_default_cluster()
        settings_data = {
            'default_server': default_cluster,
            'settings': configuration_manager.default_settings,
            'servers': configuration_manager.servers_dict
        }
        print(json.dumps(settings_data, indent=2))
        return
    
    # Get all settings from the configuration
    settings = configuration_manager.default_settings
    default_cluster = configuration_manager.get_default_cluster()
    
    # Main Settings Table
    settings_table = Table(title="Configuration Settings from elastic_servers.yml")
    settings_table.add_column("Setting", style="bold cyan", no_wrap=True)
    settings_table.add_column("Value", style="white")
    settings_table.add_column("Description", style="dim white")
    
    # Add default server info
    settings_table.add_row(
        "Default Server",
        default_cluster or "None",
        "Currently active cluster"
    )
    
    # Add all settings from the settings section
    setting_descriptions = {
        'box_style': 'Rich table border style',
        'health_style': 'Health command display mode',
        'classic_style': 'Classic health display format',
        'enable_paging': 'Auto-enable pager for long output',
        'paging_threshold': 'Line count threshold for paging',
        'show_legend_panels': 'Show legend panels in output',
        'ascii_mode': 'Use plain text instead of Unicode',
        'connection_timeout': 'ES connection timeout (seconds)',
        'read_timeout': 'ES read timeout (seconds)',
    }
    
    for key, value in settings.items():
        if key == 'dangling_cleanup':
            # Special handling for nested dangling_cleanup settings
            for sub_key, sub_value in value.items():
                setting_name = f"dangling_cleanup.{sub_key}"
                description = {
                    'max_retries': 'Max retries for dangling operations',
                    'retry_delay': 'Delay between retries (seconds)', 
                    'timeout': 'Operation timeout (seconds)',
                    'default_log_level': 'Default logging level',
                    'enable_progress_bar': 'Show progress bars',
                    'confirmation_required': 'Require user confirmation'
                }.get(sub_key, 'Dangling cleanup setting')
                
                settings_table.add_row(setting_name, str(sub_value), description)
        else:
            description = setting_descriptions.get(key, 'Configuration setting')
            settings_table.add_row(key, str(value), description)
    
    # Environment override info
    env_ascii = os.environ.get('ESCMD_ASCII_MODE', '').lower() in ('true', '1', 'yes')
    if env_ascii:
        settings_table.add_row(
            "ascii_mode (override)",
            "True",
            "Environment variable ESCMD_ASCII_MODE active"
        )
    
    console.print(settings_table)
    print()
    
    # Clusters Summary Table
    if configuration_manager.servers_dict:
        clusters_table = Table(title=f"Configured Clusters ({len(configuration_manager.servers_dict)} total)")
        clusters_table.add_column("Name", style="bold cyan", no_wrap=True)
        clusters_table.add_column("Environment", style="magenta", no_wrap=True)
        clusters_table.add_column("Primary Host", style="white")
        clusters_table.add_column("Port", style="green", justify="right")
        clusters_table.add_column("SSL", style="yellow", justify="center")
        clusters_table.add_column("Auth", style="red", justify="center")
        clusters_table.add_column("Status", style="blue")
        
        # Sort clusters by name and add data
        sorted_servers = sorted(configuration_manager.servers_dict.items())
        for location, config in sorted_servers:
            # Determine status - compare both the raw default and lowercase version
            raw_default = configuration_manager.get_default_cluster()
            if location == raw_default or location == raw_default.lower():
                status = "🏆 Default"
                name_style = "bold green"
            else:
                status = ""
                name_style = "white"
                
            # Get environment or empty
            env = config.get('env', '') 
            
            clusters_table.add_row(
                f"[{name_style}]{location}[/{name_style}]",
                env,
                config.get('hostname', 'N/A'),
                str(config.get('port', 9200)),
                "Yes" if config.get('use_ssl') else "No",
                "Yes" if config.get('elastic_authentication') else "No", 
                status
            )
        
        console.print(clusters_table)
    
    # Configuration file info
    print()
    console.print(f"[dim]Configuration file: {configuration_manager.config_file_path}[/dim]")
    console.print(f"[dim]State file: {configuration_manager.state_file_path}[/dim]")
