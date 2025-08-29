"""
Argument parser module for escmd.
Handles all command-line argument parsing and subcommand configuration.
"""

import argparse


def create_argument_parser():
    """Create and return the main argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        description='Elasticsearch command-line tool', 
        add_help=False
    )
    
    # Global arguments
    parser.add_argument(
        "-l", "--locations", 
        help="Location (defaults to localhost)", 
        type=str, 
        default=None
    )
    parser.add_argument(
        "-h", "--help", 
        action="store_true", 
        help="Show this help message and exit"
    )

    # Create subparsers
    subparsers = parser.add_subparsers(dest='command', help='Sub-command help')
    
    # Add all subcommands
    _add_help_command(subparsers)
    _add_basic_commands(subparsers)
    _add_allocation_commands(subparsers)
    _add_snapshot_commands(subparsers) 
    _add_ilm_commands(subparsers)
    _add_utility_commands(subparsers)
    
    return parser


def _add_help_command(subparsers):
    """Add global help command for major functionality."""
    help_parser = subparsers.add_parser('help', help='Show detailed help for specific commands')
    help_parser.add_argument('topic', nargs='?', 
                           choices=['indices', 'ilm', 'health', 'nodes', 'allocation', 'snapshots', 'dangling', 'shards', 'exclude'],
                           help='Command to show help for')


def _add_basic_commands(subparsers):
    """Add basic node and cluster management commands."""
    
    # Health command with all its arguments
    health_parser = subparsers.add_parser('health', help='Show Cluster Health')
    health_parser.add_argument('--format', choices=['json', 'table'], nargs='?', default='table', 
                              help='Output format (json or table)')
    health_parser.add_argument('--style', choices=['dashboard', 'classic'], default=None, 
                              help='Display style (dashboard or classic table) - overrides config file setting')
    health_parser.add_argument('--classic-style', choices=['table', 'panel'], default=None, 
                              help='Classic display format (table or panel) - overrides config file setting')
    health_parser.add_argument('--compare', help='Compare with another cluster (e.g., --compare production). Forces classic style.')
    health_parser.add_argument('--group', help='Show health for all clusters in a group (e.g., --group att). Forces classic style.')
    health_parser.add_argument('-q', '--quick', action='store_true', 
                              help='Quick mode - only perform basic cluster health check and skip additional diagnostics')
    
    # Current master command
    current_master_parser = subparsers.add_parser('current-master', help='List Current Master')
    current_master_parser.add_argument('--format', choices=['json', 'table'], default='table', 
                                      help='Output format (json or table)')
    
    # Masters command
    masters_parser = subparsers.add_parser('masters', help='List ES Master nodes')
    masters_parser.add_argument('--format', choices=['json', 'table'], nargs='?', default='table', 
                                help='Output format (json or table)')
    
    # Nodes command
    nodes_parser = subparsers.add_parser('nodes', help='List Elasticsearch nodes')
    nodes_parser.add_argument('--format', choices=['data', 'json', 'table'], nargs='?', default='table', 
                             help='Output format (json or table)')
    
    # Indices command
    indices_parser = subparsers.add_parser('indices', help='Indices')
    indices_parser.add_argument('--cold', action="store_true", default=False)
    indices_parser.add_argument('--delete', action="store_true", default=False)
    indices_parser.add_argument('--format', choices=['json', 'table'], nargs='?', default='table', help='List indices')
    indices_parser.add_argument('--status', choices=['green', 'yellow', 'red'], nargs='?', default=None)
    indices_parser.add_argument('--pager', action="store_true", default=False, 
                               help='Force pager for scrolling (auto-enabled based on config: enable_paging/paging_threshold)')
    indices_parser.add_argument('regex', nargs='?', default=None, help='Regex')

    # Indice command (single index)
    indice_parser = subparsers.add_parser('indice', help='Indice - Single One')
    indice_parser.add_argument('indice', nargs='?', default=None)
    
    # Recovery command
    recovery_parser = subparsers.add_parser('recovery', help='List Recovery Jobs')
    recovery_parser.add_argument('--format', choices=['data', 'json', 'table'], nargs='?', default='table', 
                                help='Output format (json or table)')
    
    # Settings command
    settings_parser = subparsers.add_parser('settings', help='Actions for ES Allocation')
    settings_parser.add_argument('--format', choices=['table', 'json'], nargs='?', default='table', 
                                help='Output format (json or table)')
    settings_parser.add_argument('settings_cmd', choices=['display', 'show'], nargs='?', default='display', 
                                help='Show Settings')
    
    # Storage command
    storage_parser = subparsers.add_parser('storage', help='List ES Disk Usage')
    storage_parser.add_argument('--format', choices=['data', 'json', 'table'], nargs='?', default='table', 
                               help='Output format (json or table)')
    
    # Shards command
    shards_parser = subparsers.add_parser('shards', help='Show Shards')
    shards_parser.add_argument('--format', choices=['data', 'json', 'table'], nargs='?', default='table', 
                              help='Output format (json or table)')
    shards_parser.add_argument('--server', '-s', nargs=1, default=None, help='Limit by server (ie: ess46)')
    shards_parser.add_argument('--limit','-n', default=0, help="Limit by XX rows (ie: 10)")
    shards_parser.add_argument('--size', '-z', action="store_true", default=False, help="Sort by size")
    shards_parser.add_argument('--pager', action="store_true", default=False, 
                              help='Force pager for scrolling (auto-enabled based on config: enable_paging/paging_threshold)')
    shards_parser.add_argument('regex', nargs='?', default=None, help='Regex')
    
    # Shard colocation command
    shard_colocation_parser = subparsers.add_parser('shard-colocation', 
                                                   help='Find indices with primary and replica shards on the same host')
    shard_colocation_parser.add_argument('--format', choices=['json', 'table'], default='table', 
                                        help='Output format (json or table)')
    shard_colocation_parser.add_argument('--pager', action="store_true", default=False, 
                                        help='Force pager for scrolling (auto-enabled based on config: enable_paging/paging_threshold)')
    shard_colocation_parser.add_argument('regex', nargs='?', default=None, 
                                        help='Optional regex pattern to filter indices')
    
    # Rollover commands
    rollover_parser = subparsers.add_parser('rollover', help='Rollover Single Datastream')
    rollover_parser.add_argument('datastream', nargs='?', default=None, help='Datastream to match')
    
    autorollover_parser = subparsers.add_parser('auto-rollover', help='Rollover biggest shard')
    autorollover_parser.add_argument('host', nargs='?', default=None, help='Hostname (regex) to match.')

    # Ping command
    ping_parser = subparsers.add_parser('ping', help='Check ES Connection')
    ping_parser.add_argument('--format', choices=['json', 'table'], default='table', 
                            help='Output format (json or table)')

    # Dangling indices command (complex arguments)
    dangling_parser = subparsers.add_parser('dangling', help='List, analyze, and manage dangling indices')
    dangling_parser.add_argument('uuid', nargs='?', default=None, 
                                help='Index UUID to delete (optional)')
    dangling_parser.add_argument('--delete', action='store_true', 
                                help='Delete the specified dangling index by UUID')
    dangling_parser.add_argument('--cleanup-all', action='store_true', 
                                help='Automatically delete ALL found dangling indices')
    dangling_parser.add_argument('--dry-run', action='store_true', 
                                help='Show what would be deleted without actually deleting')
    dangling_parser.add_argument('--max-retries', type=int, default=3, 
                                help='Maximum retry attempts (default: 3)')
    dangling_parser.add_argument('--retry-delay', type=int, default=5, 
                                help='Delay between retries in seconds (default: 5)')
    dangling_parser.add_argument('--timeout', type=int, default=60, 
                                help='Operation timeout in seconds (default: 60)')
    dangling_parser.add_argument('--log-file', help='Path to log file (optional)')
    dangling_parser.add_argument('--yes-i-really-mean-it', action='store_true', 
                                help='Skip confirmation prompt for deletion (use with extreme caution)')
    dangling_parser.add_argument('--format', choices=['json', 'table'], default='table', 
                                help='Output format (json or table)')

    # Commands with specific arguments
    exclude_parser = subparsers.add_parser('exclude', help='Exclude Indice from Host')
    exclude_parser.add_argument('indice', nargs='?', default=None, help='Indice to exclude')
    exclude_parser.add_argument('--server', '-s', nargs=1, default=None, 
                               help='Server to exclude (ie: aex10-c01-ess01-1)')

    excludereset_parser = subparsers.add_parser('exclude-reset', help="Remove Settings from Indice")
    excludereset_parser.add_argument('indice', nargs='?', default=None, help="Indice to reset")

    flush_parser = subparsers.add_parser('flush', help='Perform Elasticsearch Flush')

    freeze_parser = subparsers.add_parser('freeze', help='Freeze an Elasticsearch index')
    freeze_parser.add_argument('indice', help='Name of the index to freeze')

    unfreeze_parser = subparsers.add_parser('unfreeze', help='Unfreeze an Elasticsearch index')
    unfreeze_parser.add_argument('pattern', help='Index name or regex pattern to unfreeze')
    unfreeze_parser.add_argument('--regex', '-r', action='store_true', help='Treat pattern as regex')
    unfreeze_parser.add_argument('--yes', '-y', action='store_true', help='Skip confirmation prompt')


def _add_allocation_commands(subparsers):
    """Add allocation management commands."""
    allocation_parser = subparsers.add_parser('allocation', help='Manage cluster allocation settings')
    allocation_parser.add_argument('--format', choices=['json', 'table'], default='table', 
                                  help='Output format (json or table)')
    
    # Allocation subcommands
    allocation_subparsers = allocation_parser.add_subparsers(dest='allocation_action', 
                                                           help='Allocation actions')
    
    # Display, enable, disable
    for action, help_text in [
        ('display', 'Show current allocation settings'),
        ('enable', 'Enable shard allocation'),
        ('disable', 'Disable shard allocation')
    ]:
        action_parser = allocation_subparsers.add_parser(action, help=help_text)
        action_parser.add_argument('--format', choices=['json', 'table'], default='table', 
                                 help='Output format (json or table)')

    # Exclude management
    exclude_parser = allocation_subparsers.add_parser('exclude', help='Manage node exclusions')
    exclude_subparsers = exclude_parser.add_subparsers(dest='exclude_action', help='Exclude actions')
    
    add_parser = exclude_subparsers.add_parser('add', help='Add node to exclusion list')
    add_parser.add_argument('hostname', help='Hostname to exclude')
    add_parser.add_argument('--format', choices=['json', 'table'], default='table', 
                           help='Output format (json or table)')
    
    remove_parser = exclude_subparsers.add_parser('remove', help='Remove node from exclusion list')
    remove_parser.add_argument('hostname', help='Hostname to remove from exclusion')
    remove_parser.add_argument('--format', choices=['json', 'table'], default='table', 
                              help='Output format (json or table)')
    
    reset_parser = exclude_subparsers.add_parser('reset', help='Reset all node exclusions')
    reset_parser.add_argument('--format', choices=['json', 'table'], default='table', 
                             help='Output format (json or table)')
    reset_parser.add_argument('--yes-i-really-mean-it', action='store_true',
                             help='Skip confirmation prompt (use with extreme caution)')

    # Explain allocation
    explain_parser = allocation_subparsers.add_parser('explain', 
                                                     help='Explain allocation decisions for specific index/shard')
    explain_parser.add_argument('index', help='Index name to explain allocation for')
    explain_parser.add_argument('--shard', '-s', type=int, default=0, 
                               help='Shard number (default: 0)')
    explain_parser.add_argument('--primary', action='store_true', 
                               help='Explain primary shard (default: auto-detect)')
    explain_parser.add_argument('--format', choices=['json', 'table'], default='table', 
                               help='Output format (json or table)')


def _add_snapshot_commands(subparsers):
    """Add snapshot management commands."""
    snapshots_parser = subparsers.add_parser('snapshots', help='Manage Elasticsearch snapshots')
    snapshots_subparsers = snapshots_parser.add_subparsers(dest='snapshots_action', help='Snapshot actions')
    
    # List snapshots
    list_parser = snapshots_subparsers.add_parser('list', help='List all snapshots from configured repository')
    list_parser.add_argument('pattern', nargs='?', default=None, 
                            help='Optional regex pattern to filter snapshots')
    list_parser.add_argument('--format', choices=['json', 'table'], nargs='?', default='table', 
                            help='Output format (json or table)')
    list_parser.add_argument('--pager', action="store_true", default=False, 
                            help='Force pager for scrolling (auto-enabled based on config: enable_paging/paging_threshold)')

    # Snapshot status
    status_parser = snapshots_subparsers.add_parser('status', help='Show detailed status of a specific snapshot')
    status_parser.add_argument('snapshot_name', help='Name of the snapshot to check status for')
    status_parser.add_argument('--format', choices=['json', 'table'], default='table', 
                              help='Output format (json or table)')
    status_parser.add_argument('--repository', help='Snapshot repository name (uses configured default if not specified)')


def _add_ilm_commands(subparsers):
    """Add ILM (Index Lifecycle Management) commands."""
    ilm_parser = subparsers.add_parser('ilm', help='Manage Index Lifecycle Management (ILM)')
    ilm_subparsers = ilm_parser.add_subparsers(dest='ilm_action', help='ILM actions')

    # Basic ILM commands
    basic_ilm_commands = [
        ('status', 'Show comprehensive ILM status and statistics'),
        ('policies', 'List all ILM policies'),
        ('errors', 'Show indices with ILM errors'),
    ]
    
    for action, help_text in basic_ilm_commands:
        parser = ilm_subparsers.add_parser(action, help=help_text)
        parser.add_argument('--format', choices=['json', 'table'], default='table', 
                           help='Output format (json or table)')

    # Policy details
    policy_parser = ilm_subparsers.add_parser('policy', help='Show detailed configuration for specific ILM policy')
    policy_parser.add_argument('policy_name', help='Policy name to show details for')
    policy_parser.add_argument('--format', choices=['json', 'table'], default='table', 
                              help='Output format (json or table)')
    policy_parser.add_argument('--show-all', action='store_true', 
                              help='Show all indices using this policy (default shows first 10)')

    # Explain ILM
    explain_parser = ilm_subparsers.add_parser('explain', help='Show ILM status for specific index (not policy)')
    explain_parser.add_argument('index', help='Index name to explain (use actual index name, not policy name)')
    explain_parser.add_argument('--format', choices=['json', 'table'], default='table', 
                               help='Output format (json or table)')

    # Policy management
    remove_policy_parser = ilm_subparsers.add_parser('remove-policy', 
                                                    help='Remove ILM policy from indices via regex pattern or file list')
    remove_policy_parser.add_argument('pattern', nargs='?', 
                                     help='Regex pattern to match index names (not used with --file)')
    remove_policy_parser.add_argument('--dry-run', action='store_true', 
                                     help='Preview changes without executing')
    remove_policy_parser.add_argument('--format', choices=['json', 'table'], default='table', 
                                     help='Output format (json or table)')
    remove_policy_parser.add_argument('--yes', action='store_true', help='Skip confirmation prompts')
    remove_policy_parser.add_argument('--max-concurrent', type=int, default=5, 
                                     help='Maximum concurrent operations (default: 5)')
    remove_policy_parser.add_argument('--file', help='File containing list of indices (JSON format)')

    # Set policy
    set_policy_parser = ilm_subparsers.add_parser('set-policy', 
                                                 help='Set ILM policy for indices via regex pattern or file list')
    set_policy_parser.add_argument('policy_name', help='ILM policy name to apply')
    set_policy_parser.add_argument('pattern', nargs='?', 
                                  help='Regex pattern to match index names (not used with --file)')
    set_policy_parser.add_argument('--dry-run', action='store_true', 
                                  help='Preview changes without executing')
    set_policy_parser.add_argument('--format', choices=['json', 'table'], default='table', 
                                  help='Output format (json or table)')
    set_policy_parser.add_argument('--yes', action='store_true', help='Skip confirmation prompts')
    set_policy_parser.add_argument('--max-concurrent', type=int, default=5, 
                                  help='Maximum concurrent operations (default: 5)')
    set_policy_parser.add_argument('--file', help='File containing list of indices (JSON format)')


def _add_utility_commands(subparsers):
    """Add utility and configuration commands."""
    
    # Simple utility commands
    utility_commands = [
        ('locations', 'Display All Configured Locations'),
        ('get-default', 'Show Default Cluster configured'),
        ('show-settings', 'Show current configuration settings'),
        ('version', 'Show version information'),
    ]
    
    for cmd_name, cmd_help in utility_commands:
        subparsers.add_parser(cmd_name, help=cmd_help)

    # Set default cluster
    setdefault_parser = subparsers.add_parser('set-default', help='Set Default Cluster to use for commands')
    setdefault_parser.add_argument('defaultcluster_cmd', nargs='?', default='default', help='Cluster name to set as default')

    # Datastreams
    datastreams_parser = subparsers.add_parser('datastreams', help='List datastreams or show datastream details')
    datastreams_parser.add_argument('name', nargs='?', default=None, help='Datastream name to show details for (optional)')
    datastreams_parser.add_argument('--format', choices=['json', 'table'], default='table', 
                                   help='Output format (json or table)')
    datastreams_parser.add_argument('--delete', action='store_true', help='Delete the specified datastream')

    # Cluster health check
    cluster_check_parser = subparsers.add_parser('cluster-check', help='Perform comprehensive cluster health checks')
    cluster_check_parser.add_argument('--format', choices=['json', 'table'], default='table', 
                                     help='Output format (json or table)')
    cluster_check_parser.add_argument('--max-shard-size', type=int, default=50, 
                                     help='Maximum shard size in GB to report (default: 50)')
    cluster_check_parser.add_argument('--show-details', action='store_true', 
                                     help='Show detailed information for each issue found')
    cluster_check_parser.add_argument('--skip-ilm', action='store_true', 
                                     help='Skip ILM checks (useful for older ES versions or clusters without ILM)')
    cluster_check_parser.add_argument('--fix-replicas', type=int, metavar='COUNT', 
                                     help='Fix indices with no replicas by setting replica count to COUNT')
    cluster_check_parser.add_argument('--dry-run', action='store_true', 
                                     help='Preview replica fixes without applying them (use with --fix-replicas)')
    cluster_check_parser.add_argument('--force', action='store_true', 
                                     help='Skip confirmation prompts when fixing replicas (use with --fix-replicas)')

    # Set replicas command
    set_replicas_parser = subparsers.add_parser('set-replicas', help='Manage replica count for indices')
    set_replicas_parser.add_argument('--count', type=int, default=1, help='Target replica count (default: 1)')
    set_replicas_parser.add_argument('--indices', help='Comma-separated list of specific indices to update')
    set_replicas_parser.add_argument('--pattern', help='Pattern to match indices (e.g., "logs-*")')
    set_replicas_parser.add_argument('--no-replicas-only', action='store_true', 
                                    help='Only update indices with 0 replicas')
    set_replicas_parser.add_argument('--dry-run', action='store_true', 
                                    help='Preview changes without applying them')
    set_replicas_parser.add_argument('--force', action='store_true', help='Skip confirmation prompts')
    set_replicas_parser.add_argument('--format', choices=['json', 'table'], default='table', 
                                    help='Output format (json or table)')


def _add_format_argument(parser):
    """Helper function to add format argument to parsers."""
    parser.add_argument('--format', choices=['json', 'table'], default='table', 
                       help='Output format (json or table)')
