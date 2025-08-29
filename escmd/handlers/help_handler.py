"""
Help handler for escmd global help system.

Provides detailed help and examples for major commands.
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .base_handler import BaseHandler


class HelpHandler(BaseHandler):
    """Handler for global help command."""
    
    def handle_help(self):
        """Handle help command for various topics."""
        if not hasattr(self.args, 'topic') or not self.args.topic:
            self._show_general_help()
        else:
            self._show_command_help(self.args.topic)
    
    def _show_general_help(self):
        """Show general help with all available help topics."""
        console = Console()
        
        # Create help topics table
        topics_table = Table.grid(padding=(0, 3))
        topics_table.add_column(style="bold cyan", min_width=16)
        topics_table.add_column(style="white")
        
        topics_table.add_row("📊 indices", "Index management operations and examples")
        topics_table.add_row("🔄 ilm", "Index Lifecycle Management commands")
        topics_table.add_row("❤️  health", "Cluster health monitoring options")
        topics_table.add_row("🖥️  nodes", "Node management and information")
        topics_table.add_row("⚖️  allocation", "Shard allocation management")
        topics_table.add_row("� exclude", "Index exclusion from specific hosts")
        topics_table.add_row("�📸 snapshots", "Backup and snapshot operations")
        topics_table.add_row("❌ dangling", "Dangling index management")
        topics_table.add_row("🔄 shards", "Shard distribution and analysis")
        
        # Examples table
        examples_table = Table.grid(padding=(0, 3))
        examples_table.add_column(style="bold green", min_width=12)
        examples_table.add_column(style="dim white")
        
        examples_table.add_row("Get help:", "./escmd.py help")
        examples_table.add_row("Index help:", "./escmd.py help indices")
        examples_table.add_row("ILM help:", "./escmd.py help ilm")
        examples_table.add_row("Health help:", "./escmd.py help health")
        examples_table.add_row("Exclude help:", "./escmd.py help exclude")
        
        print()
        console.print(Panel(
            topics_table,
            title="🆘 Available Help Topics",
            border_style="blue",
            padding=(1, 2)
        ))
        
        print()
        console.print(Panel(
            examples_table,
            title="💡 Usage Examples",
            border_style="green",
            padding=(1, 2)
        ))
        print()
    
    def _show_command_help(self, command):
        """Show detailed help for a specific command."""
        help_methods = {
            'indices': self._help_indices,
            'ilm': self._help_ilm,
            'health': self._help_health,
            'nodes': self._help_nodes,
            'allocation': self._help_allocation,
            'exclude': self._help_exclude,
            'snapshots': self._help_snapshots,
            'dangling': self._help_dangling,
            'shards': self._help_shards
        }
        
        if command in help_methods:
            help_methods[command]()
        else:
            self._show_general_help()
    
    def _help_indices(self):
        """Show detailed help for indices commands."""
        console = Console()
        
        # Commands table
        commands_table = Table.grid(padding=(0, 3))
        commands_table.add_column(style="bold cyan", min_width=32)
        commands_table.add_column(style="white")
        
        commands_table.add_row("📊 indices", "List and filter indices with various options")
        commands_table.add_row("📄 indice <name>", "Show detailed information for single index")
        commands_table.add_row("🔄 shards", "View shard distribution across nodes")
        commands_table.add_row("🔗 shard-colocation", "Find primary/replica shards on same host")
        commands_table.add_row("🧊 freeze <index>", "Freeze an index to reduce memory usage")
        commands_table.add_row("❄️  unfreeze <pattern>", "Unfreeze indices (supports regex with -r)")
        commands_table.add_row("💧 flush <index>", "Force flush index to disk")
        
        # Examples table
        examples_table = Table.grid(padding=(0, 3))
        examples_table.add_column(style="bold green", min_width=32)
        examples_table.add_column(style="dim white")
        
        examples_table.add_row("List all indices:", "./escmd.py indices")
        examples_table.add_row("Filter by pattern:", "./escmd.py indices 'logs-*'")
        examples_table.add_row("Delete indices:", "./escmd.py indices 'logs-*' --delete")
        examples_table.add_row("Show red indices:", "./escmd.py indices --status red")
        examples_table.add_row("Index details:", "./escmd.py indice myindex-001")
        examples_table.add_row("Shard distribution:", "./escmd.py shards")
        examples_table.add_row("Check colocation:", "./escmd.py shard-colocation")
        examples_table.add_row("Freeze index:", "./escmd.py freeze myindex-001")
        examples_table.add_row("Unfreeze single:", "./escmd.py unfreeze myindex-001")
        examples_table.add_row("Unfreeze pattern:", "./escmd.py unfreeze 'logs-*' -r")
        examples_table.add_row("JSON output:", "./escmd.py indices --format json")
        
        # Detailed usage scenarios
        usage_table = Table.grid(padding=(0, 3))
        usage_table.add_column(style="bold magenta", min_width=32)
        usage_table.add_column(style="dim cyan")
        
        usage_table.add_row("🔍 Daily Health Check:", "Monitor index health by checking for red/yellow status indices")
        usage_table.add_row("   Command:", "./escmd.py indices --status red")
        usage_table.add_row("   Follow-up:", "./escmd.py indice <problematic-index>")
        usage_table.add_row("   Purpose:", "Detailed analysis of problematic indices")
        usage_table.add_row("", "")
        usage_table.add_row("🗂️ Space Management:", "Identify large indices consuming disk space")
        usage_table.add_row("   Command:", "./escmd.py indices")
        usage_table.add_row("   Action:", "Sort by size column to find largest indices")
        usage_table.add_row("   Next Steps:", "Consider ILM policies or manual cleanup for large indices")
        usage_table.add_row("", "")
        usage_table.add_row("⚡ Performance Issues:", "Check shard distribution and colocation problems")
        usage_table.add_row("   Step 1:", "./escmd.py shards --size")
        usage_table.add_row("   Purpose:", "See largest shards affecting performance")
        usage_table.add_row("   Step 2:", "./escmd.py shard-colocation")
        usage_table.add_row("   Purpose:", "Find problematic shard distribution")
        usage_table.add_row("", "")
        usage_table.add_row("🧹 Maintenance Tasks:", "Freeze/unfreeze indices to manage memory usage")
        usage_table.add_row("   Find Old:", "./escmd.py indices 'logs-2024-*'")
        usage_table.add_row("   Freeze:", "./escmd.py freeze <old-index-name>")
        usage_table.add_row("   Unfreeze Single:", "./escmd.py unfreeze <index-name>")
        usage_table.add_row("   Unfreeze Multiple:", "./escmd.py unfreeze 'temp-*' -r")
        usage_table.add_row("   Benefit:", "Manage memory usage for data lifecycle")
        usage_table.add_row("", "")
        usage_table.add_row("📊 Automation Scripts:", "JSON output for scripting and monitoring")
        usage_table.add_row("   Command:", "./escmd.py indices --format json")
        usage_table.add_row("   Filter:", "| jq '.[] | select(.status == \"red\")'")
        usage_table.add_row("   Use Case:", "Parse output for alerting systems and dashboards")
        
        self._display_help_panels(console, commands_table, examples_table, 
                                 "📊 Index Management Commands", "🚀 Index Examples",
                                 usage_table, "🎯 Typical Use Cases & Workflows")
    
    def _help_ilm(self):
        """Show detailed help for ILM commands."""
        console = Console()
        
        # Commands table
        commands_table = Table.grid(padding=(0, 3))
        commands_table.add_column(style="bold cyan", min_width=32)
        commands_table.add_column(style="white")
        
        commands_table.add_row("📊 ilm status", "Show comprehensive ILM status and statistics")
        commands_table.add_row("📋 ilm policies", "List all ILM policies with configurations")
        commands_table.add_row("🔍 ilm policy <name>", "Show detailed policy configuration")
        commands_table.add_row("🔎 ilm explain <index>", "Show ILM status for specific index")
        commands_table.add_row("⚠️  ilm errors", "Show indices with ILM errors")
        commands_table.add_row("➕ ilm set-policy <policy> <pattern>", "Assign policy to indices")
        commands_table.add_row("➖ ilm remove-policy <pattern>", "Remove policy from indices")
        
        # Examples table
        examples_table = Table.grid(padding=(0, 3))
        examples_table.add_column(style="bold green", min_width=32)
        examples_table.add_column(style="dim white")
        
        examples_table.add_row("ILM status:", "./escmd.py ilm status")
        examples_table.add_row("List policies:", "./escmd.py ilm policies")
        examples_table.add_row("Policy details:", "./escmd.py ilm policy logs")
        examples_table.add_row("Check index:", "./escmd.py ilm explain myindex-001")
        examples_table.add_row("Set policy:", "./escmd.py ilm set-policy 30-days-default 'logs-*'")
        examples_table.add_row("Remove policy:", "./escmd.py ilm remove-policy 'temp-*'")
        examples_table.add_row("Check errors:", "./escmd.py ilm errors")
        
        # Detailed usage scenarios
        usage_table = Table.grid(padding=(0, 3))
        usage_table.add_column(style="bold magenta", min_width=32)
        usage_table.add_column(style="dim cyan")
        
        usage_table.add_row("🚀 Setting Up ILM:", "Configure lifecycle policies for new indices")
        usage_table.add_row("   Step 1:", "./escmd.py ilm policies")
        usage_table.add_row("   Purpose:", "See existing policies")
        usage_table.add_row("   Step 2:", "./escmd.py ilm set-policy 30-days-default 'logs-*'")
        usage_table.add_row("   Verify:", "./escmd.py ilm explain logs-2024-001")
        usage_table.add_row("   Purpose:", "Confirm policy was applied")
        usage_table.add_row("", "")
        usage_table.add_row("🔍 Troubleshooting ILM:", "Debug lifecycle management issues")
        usage_table.add_row("   Check Errors:", "./escmd.py ilm errors")
        usage_table.add_row("   Purpose:", "Find stuck indices")
        usage_table.add_row("   Investigate:", "./escmd.py ilm explain <problem-index>")
        usage_table.add_row("   Purpose:", "Get detailed error information")
        usage_table.add_row("   Monitor:", "./escmd.py ilm status")
        usage_table.add_row("   Purpose:", "See overall health")
        usage_table.add_row("", "")
        usage_table.add_row("📊 Daily Operations:", "Regular ILM maintenance tasks")
        usage_table.add_row("   Health Check:", "./escmd.py ilm status")
        usage_table.add_row("   Error Review:", "./escmd.py ilm errors")
        usage_table.add_row("   Policy Audit:", "./escmd.py ilm policies")
        usage_table.add_row("", "")
        usage_table.add_row("🔄 Policy Management:", "Updating and maintaining ILM policies")
        usage_table.add_row("   Apply New:", "./escmd.py ilm set-policy new-policy 'application-*'")
        usage_table.add_row("   Remove Old:", "./escmd.py ilm remove-policy 'temp-*'")
        usage_table.add_row("   Purpose:", "Cleanup temporary indices")
        usage_table.add_row("   Review Impact:", "./escmd.py ilm status")
        usage_table.add_row("   Purpose:", "Check status after policy changes")
        usage_table.add_row("", "")
        usage_table.add_row("🗄️ Data Lifecycle:", "Manage data retention and storage costs")
        usage_table.add_row("   Hot → Warm:", "Policies automatically move older data to cheaper storage")
        usage_table.add_row("   Monitor Command:", "./escmd.py ilm explain <index>")
        usage_table.add_row("   Shows:", "Current phase of the index")
        usage_table.add_row("   Cost Control:", "ILM reduces storage costs via automated management")
        
        self._display_help_panels(console, commands_table, examples_table,
                                 "🔄 Index Lifecycle Management Commands", "🚀 ILM Examples",
                                 usage_table, "🎯 ILM Workflows & Best Practices")
    
    def _help_health(self):
        """Show detailed help for health commands."""
        console = Console()
        
        # Commands table
        commands_table = Table.grid(padding=(0, 3))
        commands_table.add_column(style="bold cyan", min_width=32)
        commands_table.add_column(style="white")
        
        commands_table.add_row("❤️  health", "Show comprehensive cluster health")
        commands_table.add_row("❤️  health --style dashboard", "Modern dashboard view")
        commands_table.add_row("❤️  health --style classic", "Traditional table format")
        commands_table.add_row("❤️  health --compare <cluster>", "Compare with another cluster")
        commands_table.add_row("❤️  health --group <prefix>", "Group clusters by prefix")
        commands_table.add_row("❤️  health -q", "Quick health check")
        
        # Examples table
        examples_table = Table.grid(padding=(0, 3))
        examples_table.add_column(style="bold green", min_width=32)
        examples_table.add_column(style="dim white")
        
        examples_table.add_row("Basic health:", "./escmd.py health")
        examples_table.add_row("Dashboard style:", "./escmd.py health --style dashboard")
        examples_table.add_row("Quick check:", "./escmd.py health -q")
        examples_table.add_row("Compare clusters:", "./escmd.py health --compare prod")
        examples_table.add_row("Group by prefix:", "./escmd.py health --group us")
        examples_table.add_row("JSON format:", "./escmd.py health --format json")
        
        # Detailed usage scenarios
        usage_table = Table.grid(padding=(0, 3))
        usage_table.add_column(style="bold magenta", min_width=22)
        usage_table.add_column(style="dim cyan")
        
        usage_table.add_row("🚨 Incident Response:", "Quick cluster status during outages")
        usage_table.add_row("   Command:", "./escmd.py health -q")
        usage_table.add_row("   Purpose:", "Immediate status for emergency situations")
        usage_table.add_row("   Follow-up:", "./escmd.py health --style dashboard")
        usage_table.add_row("   Purpose:", "Detailed view for thorough analysis")
        usage_table.add_row("", "")
        usage_table.add_row("📊 Daily Monitoring:", "Regular cluster health checks")
        usage_table.add_row("   Morning Check:", "./escmd.py health --style dashboard")
        usage_table.add_row("   Automation:", "./escmd.py health --format json")
        usage_table.add_row("   Pipeline:", "| monitor_script.py")
        usage_table.add_row("", "")
        usage_table.add_row("🔄 Multi-Cluster Ops:", "Managing multiple environments")
        usage_table.add_row("   Compare:", "./escmd.py health --compare production")
        usage_table.add_row("   Group View:", "./escmd.py health --group us")
        usage_table.add_row("   Note:", "Works with clusters like us-east, us-west")
        usage_table.add_row("", "")
        usage_table.add_row("⚡ Performance Tuning:", "Identify bottlenecks and issues")
        usage_table.add_row("   Command:", "./escmd.py health --style dashboard")
        usage_table.add_row("   Shows:", "CPU, memory, disk metrics")
        usage_table.add_row("   Compare:", "./escmd.py health --compare <cluster>")
        usage_table.add_row("   Shows:", "Historical data comparison")
        usage_table.add_row("", "")
        usage_table.add_row("🔧 Troubleshooting:", "Deep-dive health analysis")
        usage_table.add_row("   Full Check:", "./escmd.py health")
        usage_table.add_row("   Includes:", "All diagnostics and detailed analysis")
        usage_table.add_row("   Quick Test:", "./escmd.py health -q")
        usage_table.add_row("   Includes:", "Basic health check only")
        
        self._display_help_panels(console, commands_table, examples_table,
                                 "❤️ Cluster Health Commands", "🚀 Health Examples",
                                 usage_table, "🎯 Monitoring & Troubleshooting Workflows")
    
    def _help_nodes(self):
        """Show detailed help for node commands."""
        console = Console()
        
        # Commands table  
        commands_table = Table.grid(padding=(0, 3))
        commands_table.add_column(style="bold cyan", min_width=32)
        commands_table.add_column(style="white")
        
        commands_table.add_row("🖥️  nodes", "List all cluster nodes with details")
        commands_table.add_row("👑 masters", "Show master-eligible nodes")
        commands_table.add_row("🎯 current-master", "Show current active master node")
        commands_table.add_row("💾 storage", "View node disk usage statistics")
        commands_table.add_row("🔄 recovery", "Monitor node recovery operations")
        
        # Examples table
        examples_table = Table.grid(padding=(0, 3))
        examples_table.add_column(style="bold green", min_width=32)
        examples_table.add_column(style="dim white")
        
        examples_table.add_row("All nodes:", "./escmd.py nodes")
        examples_table.add_row("Master nodes:", "./escmd.py masters")  
        examples_table.add_row("Current master:", "./escmd.py current-master")
        examples_table.add_row("Disk usage:", "./escmd.py storage")
        examples_table.add_row("Recovery status:", "./escmd.py recovery")
        examples_table.add_row("JSON output:", "./escmd.py nodes --format json")
        
        # Detailed usage scenarios
        usage_table = Table.grid(padding=(0, 3))
        usage_table.add_column(style="bold magenta", min_width=32)
        usage_table.add_column(style="dim cyan")
        
        usage_table.add_row("🔍 Cluster Overview:", "Get comprehensive view of cluster topology")
        usage_table.add_row("   Node Status:", "./escmd.py nodes")
        usage_table.add_row("   Purpose:", "See all node health")
        usage_table.add_row("   Master Check:", "./escmd.py current-master")
        usage_table.add_row("   Purpose:", "Get leader info")
        usage_table.add_row("   Storage Health:", "./escmd.py storage")
        usage_table.add_row("   Purpose:", "Monitor disk usage")
        usage_table.add_row("", "")
        usage_table.add_row("⚠️ Troubleshooting:", "Diagnose node-related cluster issues")
        usage_table.add_row("   Failed Masters:", "./escmd.py masters")
        usage_table.add_row("   Purpose:", "Check master election")
        usage_table.add_row("   Recovery Issues:", "./escmd.py recovery")
        usage_table.add_row("   Purpose:", "See stuck operations")
        usage_table.add_row("   Resource Issues:", "./escmd.py nodes")
        usage_table.add_row("   Purpose:", "Identify overloaded nodes")
        usage_table.add_row("", "")
        usage_table.add_row("📊 Capacity Planning:", "Monitor resource usage and plan scaling")
        usage_table.add_row("   Disk Usage:", "./escmd.py storage --format table")
        usage_table.add_row("   Purpose:", "Detailed analysis of disk usage")
        usage_table.add_row("   Node Load:", "./escmd.py nodes")
        usage_table.add_row("   Purpose:", "Check CPU, memory usage")
        usage_table.add_row("   Growth Trends:", "Regular monitoring for capacity planning")
        usage_table.add_row("", "")
        usage_table.add_row("🔧 Maintenance Mode:", "Prepare for node maintenance operations")
        usage_table.add_row("   Pre-maintenance:", "./escmd.py nodes")
        usage_table.add_row("   Purpose:", "Identify target node")
        usage_table.add_row("   Check Master:", "./escmd.py masters")
        usage_table.add_row("   Purpose:", "If maintaining master node")
        usage_table.add_row("   Monitor Impact:", "./escmd.py recovery")
        usage_table.add_row("   Purpose:", "Watch during maintenance")
        
        self._display_help_panels(console, commands_table, examples_table,
                                 "🖥️ Node Management Commands", "🚀 Node Examples",
                                 usage_table, "🎯 Node Operations & Monitoring")
    
    def _help_allocation(self):
        """Show detailed help for allocation commands."""
        console = Console()
        
        # Commands table
        commands_table = Table.grid(padding=(0, 3))
        commands_table.add_column(style="bold cyan", min_width=32)
        commands_table.add_column(style="white")
        
        commands_table.add_row("⚖️  allocation display", "Show current allocation settings")
        commands_table.add_row("⚖️  allocation enable", "Enable shard allocation")
        commands_table.add_row("⚖️  allocation disable", "Disable shard allocation") 
        commands_table.add_row("⚖️  allocation explain <index>", "Explain shard allocation decisions")
        commands_table.add_row("⚖️  allocation exclude add <host>", "Exclude node from allocation")
        commands_table.add_row("⚖️  allocation exclude remove <host>", "Remove node exclusion")
        commands_table.add_row("⚖️  allocation exclude reset", "Reset all exclusions")
        
        # Examples table
        examples_table = Table.grid(padding=(0, 3))
        examples_table.add_column(style="bold green", min_width=32)
        examples_table.add_column(style="dim white")
        
        examples_table.add_row("Show settings:", "./escmd.py allocation display")
        examples_table.add_row("Enable allocation:", "./escmd.py allocation enable")
        examples_table.add_row("Disable allocation:", "./escmd.py allocation disable")
        examples_table.add_row("Explain allocation:", "./escmd.py allocation explain myindex-001")
        examples_table.add_row("Exclude node:", "./escmd.py allocation exclude add node-1")
        examples_table.add_row("Remove exclusion:", "./escmd.py allocation exclude remove node-1")
        examples_table.add_row("Reset exclusions:", "./escmd.py allocation exclude reset")
        
        # Detailed usage scenarios
        usage_table = Table.grid(padding=(0, 3))
        usage_table.add_column(style="bold magenta", min_width=32)
        usage_table.add_column(style="dim cyan")
        
        usage_table.add_row("🔧 Allocation Control:", "Manage cluster-wide shard allocation")
        usage_table.add_row("   Enable:", "./escmd.py allocation enable")
        usage_table.add_row("   Purpose:", "Allow shards to move and allocate")
        usage_table.add_row("   Disable:", "./escmd.py allocation disable")
        usage_table.add_row("   Purpose:", "Prevent shard movement during maintenance")
        usage_table.add_row("", "")
        usage_table.add_row("🚫 Node Exclusions:", "Exclude specific nodes from allocation")
        usage_table.add_row("   Exclude Node:", "./escmd.py allocation exclude add node-1")
        usage_table.add_row("   Purpose:", "Prevent shards from being allocated to specific node")
        usage_table.add_row("   Remove Node:", "./escmd.py allocation exclude remove node-1")
        usage_table.add_row("   Purpose:", "Allow node to receive shards again")
        usage_table.add_row("", "")
        usage_table.add_row("⚠️ DANGER: Reset All:", "Reset all node exclusions (CLUSTER-WIDE)")
        usage_table.add_row("   Safe Reset:", "./escmd.py allocation exclude reset")
        usage_table.add_row("   Safety:", "Requires typing 'RESET' to confirm")
        usage_table.add_row("   Bypass Safety:", "./escmd.py allocation exclude reset --yes-i-really-mean-it")
        usage_table.add_row("   Warning:", "Use bypass flag with EXTREME caution!")
        usage_table.add_row("", "")
        usage_table.add_row("🔍 Troubleshooting:", "Understand allocation decisions")
        usage_table.add_row("   Explain:", "./escmd.py allocation explain myindex-001")
        usage_table.add_row("   Purpose:", "See why shards are allocated where they are")
        usage_table.add_row("   Display Settings:", "./escmd.py allocation display")
        usage_table.add_row("   Purpose:", "View current allocation configuration")
        
        self._display_help_panels(console, commands_table, examples_table,
                                 "⚖️ Allocation Management Commands", "🚀 Allocation Examples",
                                 usage_table, "🎯 Allocation Workflows & Safety")
    
    def _help_exclude(self):
        """Show detailed help for exclude commands (both index-level and cluster-level)."""
        console = Console()
        
        # Commands table
        commands_table = Table.grid(padding=(0, 3))
        commands_table.add_column(style="bold cyan", min_width=40)
        commands_table.add_column(style="white")
        
        commands_table.add_row("🚫 exclude <index> --server <host>", "Exclude specific index from specific host")
        commands_table.add_row("🔄 exclude-reset <index>", "Reset exclusion settings for specific index")
        commands_table.add_row("", "")
        commands_table.add_row("⚖️  allocation exclude add <host>", "Exclude entire node from all allocations")
        commands_table.add_row("⚖️  allocation exclude remove <host>", "Remove node from cluster exclusion list")
        commands_table.add_row("⚖️  allocation exclude reset", "Reset all cluster-level exclusions")
        
        # Examples table
        examples_table = Table.grid(padding=(0, 3))
        examples_table.add_column(style="bold green", min_width=40)
        examples_table.add_column(style="dim white")
        
        examples_table.add_row("Index exclusion:", "./escmd.py exclude .ds-logs-2025.04.03-000732 -s node-1")
        examples_table.add_row("Reset index exclusion:", "./escmd.py exclude-reset .ds-logs-2025.04.03-000732")
        examples_table.add_row("", "")
        examples_table.add_row("Cluster node exclusion:", "./escmd.py allocation exclude add node-1")
        examples_table.add_row("Remove node exclusion:", "./escmd.py allocation exclude remove node-1")
        examples_table.add_row("Reset all exclusions:", "./escmd.py allocation exclude reset")
        
        # Detailed usage scenarios
        usage_table = Table.grid(padding=(0, 3))
        usage_table.add_column(style="bold magenta", min_width=40)
        usage_table.add_column(style="dim cyan")
        
        usage_table.add_row("📍 INDEX-LEVEL EXCLUSION:", "Exclude specific index from specific host")
        usage_table.add_row("   Command:", "./escmd.py exclude <index-name> --server <hostname>")
        usage_table.add_row("   Purpose:", "Prevent ONE index from allocating on ONE host")
        usage_table.add_row("   Scope:", "Affects only the specified index")
        usage_table.add_row("   Use Case:", "Host has issues but only affecting specific index")
        usage_table.add_row("   Example:", "./escmd.py exclude .ds-aex10-logs-2025.04.03-000732 -s aex10-c01-ess01-1")
        usage_table.add_row("", "")
        usage_table.add_row("🔄 INDEX EXCLUSION RESET:", "Remove exclusion for specific index")
        usage_table.add_row("   Command:", "./escmd.py exclude-reset <index-name>")
        usage_table.add_row("   Purpose:", "Allow index to allocate on previously excluded host")
        usage_table.add_row("   Example:", "./escmd.py exclude-reset .ds-aex10-logs-2025.04.03-000732")
        usage_table.add_row("", "")
        usage_table.add_row("🏢 CLUSTER-LEVEL EXCLUSION:", "Exclude entire node from all allocations")
        usage_table.add_row("   Command:", "./escmd.py allocation exclude add <hostname>")
        usage_table.add_row("   Purpose:", "Prevent ALL shards from allocating on node")
        usage_table.add_row("   Scope:", "Affects ALL indices in cluster")
        usage_table.add_row("   Use Case:", "Node maintenance, hardware issues, decommissioning")
        usage_table.add_row("   Example:", "./escmd.py allocation exclude add node-1")
        usage_table.add_row("", "")
        usage_table.add_row("🔓 CLUSTER EXCLUSION REMOVAL:", "Remove node from exclusion list")
        usage_table.add_row("   Command:", "./escmd.py allocation exclude remove <hostname>")
        usage_table.add_row("   Purpose:", "Allow node to receive shards again")
        usage_table.add_row("   Example:", "./escmd.py allocation exclude remove node-1")
        usage_table.add_row("", "")
        usage_table.add_row("⚠️  DANGER: RESET ALL EXCLUSIONS:", "Reset all cluster-level exclusions")
        usage_table.add_row("   Command:", "./escmd.py allocation exclude reset")
        usage_table.add_row("   Safety:", "Requires typing 'RESET' to confirm")
        usage_table.add_row("   Bypass Safety:", "./escmd.py allocation exclude reset --yes-i-really-mean-it")
        usage_table.add_row("   Warning:", "Use bypass flag with EXTREME caution!")
        usage_table.add_row("", "")
        usage_table.add_row("🎯 CHOOSING THE RIGHT COMMAND:", "Index-level vs Cluster-level")
        usage_table.add_row("   Index-level:", "Use when problem is specific to one index")
        usage_table.add_row("   Cluster-level:", "Use when entire node needs to be excluded")
        usage_table.add_row("   Recovery:", "Index-level: exclude-reset, Cluster-level: exclude remove")
        usage_table.add_row("", "")
        usage_table.add_row("🔧 TECHNICAL DETAILS:", "How exclusions work")
        usage_table.add_row("   Index Setting:", "index.routing.allocation.exclude._name")
        usage_table.add_row("   Cluster Setting:", "cluster.routing.allocation.exclude._name")
        usage_table.add_row("   Effect:", "Elasticsearch moves shards away from excluded hosts")
        usage_table.add_row("   Duration:", "Exclusions persist until manually removed")
        
        self._display_help_panels(console, commands_table, examples_table,
                                 "🚫 Exclude Commands (Index & Cluster Level)", "🚀 Exclude Examples",
                                 usage_table, "🎯 Exclude Workflows & Safety Guide")

    def _help_snapshots(self):
        """Show detailed help for snapshot commands."""
        console = Console()
        
        # Commands table
        commands_table = Table.grid(padding=(0, 3))
        commands_table.add_column(style="bold cyan", min_width=32)
        commands_table.add_column(style="white")
        
        commands_table.add_row("📸 snapshots list", "List all available snapshots")
        commands_table.add_row("📸 snapshots list <pattern>", "Filter snapshots by pattern")
        commands_table.add_row("📸 snapshots list --pager", "Use pager for large lists")
        commands_table.add_row("📸 snapshots info <name>", "Show detailed snapshot information")
        commands_table.add_row("📸 snapshots create <name>", "Create new snapshot")
        commands_table.add_row("📸 snapshots delete <name>", "Delete existing snapshot")
        
        # Examples table
        examples_table = Table.grid(padding=(0, 3))
        examples_table.add_column(style="bold green", min_width=32)
        examples_table.add_column(style="dim white")
        
        examples_table.add_row("List snapshots:", "./escmd.py snapshots list")
        examples_table.add_row("Filter by pattern:", "./escmd.py snapshots list 'logs-*'")
        examples_table.add_row("With pager:", "./escmd.py snapshots list --pager")
        examples_table.add_row("Snapshot details:", "./escmd.py snapshots info backup-001")
        examples_table.add_row("JSON output:", "./escmd.py snapshots list --format json")
        
        # Detailed usage scenarios
        usage_table = Table.grid(padding=(0, 3))
        usage_table.add_column(style="bold magenta", min_width=32)
        usage_table.add_column(style="dim cyan")
        
        usage_table.add_row("💾 Backup Strategy:", "Regular data protection and recovery planning")
        usage_table.add_row("   Daily Backup:", "./escmd.py snapshots create daily-$(date +%Y%m%d)")
        usage_table.add_row("   Verify Status:", "./escmd.py snapshots info daily-20250828")
        usage_table.add_row("   Monitor Space:", "./escmd.py snapshots list")
        usage_table.add_row("   Purpose:", "Track backup storage usage")
        usage_table.add_row("", "")
        usage_table.add_row("🔄 Disaster Recovery:", "Restore operations during incidents")
        usage_table.add_row("   List Available:", "./escmd.py snapshots list --format json")
        usage_table.add_row("   Filter:", "| filter latest")
        usage_table.add_row("   Check Integrity:", "./escmd.py snapshots info <backup-name>")
        usage_table.add_row("   Purpose:", "Verify backup health before restore")
        usage_table.add_row("   Recovery Point:", "Use snapshot timestamp for recovery planning")
        usage_table.add_row("", "")
        usage_table.add_row("🧹 Backup Maintenance:", "Managing backup lifecycle and cleanup")
        usage_table.add_row("   Find Old:", "./escmd.py snapshots list")
        usage_table.add_row("   Filter:", "| grep old-date-pattern")
        usage_table.add_row("   Space Cleanup:", "./escmd.py snapshots delete <old-backup-name>")
        usage_table.add_row("   Retention Policy:", "Delete snapshots older than retention period")
        usage_table.add_row("", "")
        usage_table.add_row("📊 Backup Monitoring:", "Track backup health and performance")
        usage_table.add_row("   Status Check:", "./escmd.py snapshots list --pager")
        usage_table.add_row("   Purpose:", "For large environments with many snapshots")
        usage_table.add_row("   Success Rate:", "Monitor for failed snapshots and investigate")
        usage_table.add_row("   Storage Growth:", "Track backup storage consumption over time")
        usage_table.add_row("", "")
        usage_table.add_row("⚡ Emergency Procedures:", "Quick backup and restore operations")
        usage_table.add_row("   Quick Backup:", "./escmd.py snapshots create emergency-backup")
        usage_table.add_row("   Verify Quick:", "./escmd.py snapshots info emergency-backup")
        usage_table.add_row("   List Recent:", "./escmd.py snapshots list")
        usage_table.add_row("   Filter:", "| head -10")
        
        self._display_help_panels(console, commands_table, examples_table,
                                 "📸 Snapshot Management Commands", "🚀 Snapshot Examples",
                                 usage_table, "🎯 Backup & Recovery Workflows")
    
    def _help_dangling(self):
        """Show detailed help for dangling index commands."""
        console = Console()
        
        # Commands table
        commands_table = Table.grid(padding=(0, 3))
        commands_table.add_column(style="bold cyan", min_width=32)
        commands_table.add_column(style="white")
        
        commands_table.add_row("❌ dangling", "List all dangling indices")
        commands_table.add_row("❌ dangling <uuid>", "Show details for specific dangling index")
        commands_table.add_row("❌ dangling <uuid> --delete", "Delete specific dangling index")
        commands_table.add_row("❌ dangling --cleanup", "Interactive cleanup of all dangling indices")
        
        # Examples table
        examples_table = Table.grid(padding=(0, 3))
        examples_table.add_column(style="bold green", min_width=32)
        examples_table.add_column(style="dim white")
        
        examples_table.add_row("List dangling:", "./escmd.py dangling")
        examples_table.add_row("Show details:", "./escmd.py dangling abc123-def456")
        examples_table.add_row("Delete specific:", "./escmd.py dangling abc123-def456 --delete")
        examples_table.add_row("Cleanup all:", "./escmd.py dangling --cleanup")
        examples_table.add_row("JSON output:", "./escmd.py dangling --format json")
        
        self._display_help_panels(console, commands_table, examples_table,
                                 "❌ Dangling Index Commands", "🚀 Dangling Examples")
    
    def _help_shards(self):
        """Show detailed help for shard commands."""
        console = Console()
        
        # Commands table
        commands_table = Table.grid(padding=(0, 3))
        commands_table.add_column(style="bold cyan", min_width=32)
        commands_table.add_column(style="white")
        
        commands_table.add_row("🔄 shards", "Show shard distribution across nodes")
        commands_table.add_row("🔗 shard-colocation", "Find primary/replica shards on same host")
        commands_table.add_row("🔢 set-replicas", "Manage replica count for indices")
        
        # Examples table
        examples_table = Table.grid(padding=(0, 3))
        examples_table.add_column(style="bold green", min_width=32)
        examples_table.add_column(style="dim white")
        
        examples_table.add_row("View shards:", "./escmd.py shards")
        examples_table.add_row("Check colocation:", "./escmd.py shard-colocation")
        examples_table.add_row("Set replicas:", "./escmd.py set-replicas --count 1 --indices myindex")
        examples_table.add_row("Set by pattern:", "./escmd.py set-replicas --count 0 --pattern 'temp-*'")
        examples_table.add_row("JSON output:", "./escmd.py shards --format json")
        
        self._display_help_panels(console, commands_table, examples_table,
                                 "🔄 Shard Management Commands", "🚀 Shard Examples")
    
    def _display_help_panels(self, console, commands_table, examples_table, commands_title, examples_title, usage_table=None, usage_title=None):
        """Helper method to display help panels consistently."""
        print()
        console.print(Panel(
            commands_table,
            title=commands_title,
            border_style="blue",
            padding=(1, 2)
        ))
        
        print()
        console.print(Panel(
            examples_table,
            title=examples_title,
            border_style="green",
            padding=(1, 2)
        ))
        
        if usage_table and usage_title:
            print()
            console.print(Panel(
                usage_table,
                title=usage_title,
                border_style="yellow",
                padding=(1, 2)
            ))
        
        print()
