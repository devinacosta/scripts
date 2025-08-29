"""
Help system module for escmd.
Provides beautiful Rich-formatted help display.
"""

import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from rich.text import Text


def show_custom_help():
    """Display the beautiful custom help interface."""
    console = Console()

    # Create title panel
    title_panel = Panel(
        Text("🛠️  Elasticsearch Command-Line Tool", style="bold cyan", justify="center"),
        subtitle="Advanced cluster management and monitoring",
        border_style="cyan",
        padding=(1, 2)
    )

    # Create command categories
    cluster_table = Table.grid(padding=(0, 3))
    cluster_table.add_column(style="bold yellow", no_wrap=True)
    cluster_table.add_column(style="white")
    cluster_table.add_row("🔍 health", "Cluster health monitoring (dashboard/classic/comparison/groups)")
    cluster_table.add_row("⚙️  settings", "View and manage cluster settings")
    cluster_table.add_row("🔧 show-settings", "Show current configuration settings")
    cluster_table.add_row("🎯 get-default", "Show current default cluster configuration")
    cluster_table.add_row("📌 set-default", "Set default cluster for commands")
    cluster_table.add_row("🏓 ping", "Test connectivity with cluster details and health overview")
    cluster_table.add_row("📍 locations", "List all configured clusters")

    node_table = Table.grid(padding=(0, 3))
    node_table.add_column(style="bold green", no_wrap=True)
    node_table.add_column(style="white")
    node_table.add_row("🖥️  nodes", "List all cluster nodes")
    node_table.add_row("👑 masters", "List master-eligible nodes")
    node_table.add_row("🎯 current-master", "Show current master node")

    index_table = Table.grid(padding=(0, 3))
    index_table.add_column(style="bold blue", no_wrap=True)
    index_table.add_column(style="white")
    index_table.add_row("📊 indices", "List and manage indices")
    index_table.add_row("📄 indice", "Show single index details")
    index_table.add_row("🔄 shards", "View shard distribution")
    index_table.add_row("🔗 shard-colocation", "Find primary/replica shards on same host")
    index_table.add_row("🗂️  datastreams", "Manage datastreams")
    index_table.add_row("❌ dangling", "Manage dangling indices")
    index_table.add_row("🧊 freeze", "Freeze indices")
    index_table.add_row("❄️  unfreeze", "Unfreeze indices")
    index_table.add_row("💧 flush", "Flush indices")

    ops_table = Table.grid(padding=(0, 3))
    ops_table.add_column(style="bold magenta", no_wrap=True)
    ops_table.add_column(style="white")
    ops_table.add_row("⚖️  allocation", "Manage shard allocation and explain allocation decisions")
    ops_table.add_row("💾 storage", "View disk usage")
    ops_table.add_row("🔄 recovery", "Monitor recovery operations")
    ops_table.add_row("📸 snapshots", "Manage snapshots")
    ops_table.add_row("🔄 rollover", "Rollover operations")
    ops_table.add_row("⚙️  ilm", "Index Lifecycle Management")
    ops_table.add_row("🏥 cluster-check", "Comprehensive cluster health checks (ILM errors, replicas, shard sizes)")
    ops_table.add_row("🔢 set-replicas", "Set replica count for indices")
    ops_table.add_row("📊 version", "Show version information")

    # Create panels for each category
    cluster_panel = Panel(cluster_table, title="[bold yellow]🏢 Cluster & Config[/bold yellow]", 
                         border_style="yellow", padding=(1, 1))
    node_panel = Panel(node_table, title="[bold green]🖥️  Nodes & Masters[/bold green]", 
                      border_style="green", padding=(1, 1))
    index_panel = Panel(index_table, title="[bold blue]📊 Indices & Data[/bold blue]", 
                       border_style="blue", padding=(1, 1))
    ops_panel = Panel(ops_table, title="[bold magenta]⚡ Operations[/bold magenta]", 
                     border_style="magenta", padding=(1, 1))

    # Usage examples
    usage_content = Text()
    usage_content.append("Basic Health:              ", style="bold white")
    usage_content.append("./escmd.py health\n", style="cyan")
    usage_content.append("Quick Health Check:        ", style="bold white")
    usage_content.append("./escmd.py health -q\n", style="cyan")
    usage_content.append("Compare Clusters:          ", style="bold white")
    usage_content.append("./escmd.py health --compare iad41\n", style="cyan")
    usage_content.append("Group Health:              ", style="bold white")
    usage_content.append("./escmd.py health --group att\n", style="cyan")
    usage_content.append("Allocation Explain:        ", style="bold white")
    usage_content.append("./escmd.py allocation explain my-index\n", style="cyan")
    usage_content.append("Cluster with Location:     ", style="bold white")
    usage_content.append("./escmd.py -l sjc01 health\n", style="cyan")
    usage_content.append("JSON Output:               ", style="bold white")
    usage_content.append("./escmd.py indices --format json\n", style="cyan")

    usage_panel = Panel(usage_content, title="[bold cyan]🚀 Quick Start Examples[/bold cyan]", 
                       border_style="cyan", padding=(1, 2))

    # Create layout
    print()
    console.print(title_panel)
    print()

    # Create a grid for perfect alignment
    grid_table = Table.grid()
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
