# Index Operations

Comprehensive index management including listing, freezing, dangling index cleanup, and shard analysis.

## Quick Reference

```bash
# Index listing and management
./escmd.py indices                    # List all indices
./escmd.py indices --status red       # Filter by health status
./escmd.py indices "logs-*"           # Filter by regex pattern
./escmd.py indices --delete "temp-*"  # Delete indices matching pattern
./escmd.py indice my-index-name       # Single index details
./escmd.py freeze my-index-name       # Freeze an index
./escmd.py unfreeze my-index-name     # Unfreeze an index
./escmd.py unfreeze "logs-*" --regex  # Unfreeze indices matching pattern

# Index exclusion and allocation control
./escmd.py exclude my-index --server ess46  # Exclude index from specific server
./escmd.py exclude-reset my-index           # Reset exclusion settings

# Dangling index management
./escmd.py dangling                  # List dangling indices
./escmd.py dangling --cleanup-all --dry-run  # Preview cleanup
./escmd.py dangling --cleanup-all    # Execute cleanup

# Shard operations
./escmd.py shards                    # View shard distribution
./escmd.py shards --server ess46     # Filter by server
./escmd.py shard-colocation          # Find colocation issues
```

## Index Listing & Management

### 📊 List All Indices

Display comprehensive index information with rich formatting and powerful filtering options:

```bash
# Basic listing
./escmd.py indices                   # All indices with default formatting
./escmd.py indices --format json     # JSON output for automation

# Pattern-based filtering
./escmd.py indices "logs-*"          # Filter by regex pattern
./escmd.py indices "^app-"           # Indices starting with "app-"
./escmd.py indices ".*2024.*"        # Indices containing "2024"

# Status-based filtering
./escmd.py indices --status red      # Only red (unhealthy) indices
./escmd.py indices --status yellow   # Only yellow (warning) indices
./escmd.py indices --status green    # Only green (healthy) indices

# Special filtering options
./escmd.py indices --cold            # Show cold indices (ILM cold phase)
./escmd.py indices --pager           # Force pager for large outputs

# Combined filtering
./escmd.py indices "logs-*" --status red     # Red indices matching pattern
./escmd.py indices --status yellow --pager  # Yellow indices with pager
```

**Command Options:**

| Option | Type | Description | Example |
|--------|------|-------------|---------|
| `pattern` | string | Regex pattern to filter indices | `"logs-*"` |
| `--status` | choice | Filter by health status (green, yellow, red) | `--status red` |
| `--cold` | flag | Show only indices in ILM cold phase | `--cold` |
| `--delete` | flag | Delete indices (use with pattern) | `--delete` |
| `--format` | choice | Output format (table, json) | `--format json` |
| `--pager` | flag | Force pager for large outputs | `--pager` |

**Features:**
- **Rich Formatting**: Color-coded status indicators and professional tables
- **Comprehensive Information**: Name, status, health, documents, size, creation date
- **Status Indicators**: Visual status (🟢 open, 🔴 close, 🧊 frozen)
- **Sorting**: Intelligent sorting by name, size, or date
- **Advanced Filtering**: Pattern matching, status filtering, and ILM phase detection
- **Legend Panels**: Optional legend and quick actions (configurable)
- **Smart Paging**: Automatic paging for large datasets

**Index Information Displayed:**
- **Index Name**: Full index name with pattern recognition
- **Status**: open, close, frozen with visual indicators
- **Health**: green, yellow, red health status
- **Document Count**: Total documents in the index
- **Primary Size**: Size of primary shards
- **Total Size**: Combined primary and replica size
- **Creation Date**: When the index was created

### 📄 Single Index Details

Get detailed information about a specific index:

```bash
./escmd.py indice my-index-name              # Basic index details
./escmd.py indice my-index-name --format json  # JSON output
```

**Detailed Information:**
- **Settings**: Index configuration and mappings
- **Statistics**: Document counts, sizes, and performance metrics
- **Shards**: Shard distribution and status
- **Aliases**: Index aliases and routing
- **Lifecycle**: ILM policy and current phase (if applicable)

### 🧊 Index Freezing

Freeze indices to reduce memory usage while maintaining searchability:

```bash
./escmd.py freeze my-index-name      # Freeze a specific index
./escmd.py freeze pattern-*          # Freeze indices matching pattern
```

**Freezing Features:**
- **Validation**: Checks index status before freezing
- **Confirmation**: Interactive confirmation with impact warnings
- **Progress Tracking**: Real-time progress for multiple indices
- **Detailed Feedback**: Success/failure reporting with reasons
- **Rollback Information**: Instructions for unfreezing if needed

**When to Freeze Indices:**
- **Rarely Accessed Data**: Historical data accessed infrequently
- **Memory Optimization**: Reduce heap memory usage
- **Cost Reduction**: Lower resource consumption for archived data
- **Compliance**: Keep data searchable but reduce operational overhead

### ❄️ Unfreeze Indices

Unfreeze indices to restore full functionality and enable write operations:

```bash
./escmd.py unfreeze my-index-name            # Unfreeze a specific index
./escmd.py unfreeze "pattern-*" --regex      # Unfreeze indices matching regex pattern
./escmd.py unfreeze "logs-*" --regex --yes   # Batch unfreeze with confirmation skip
```

**Unfreeze Features:**
- **Single Index**: Unfreeze specific indices by exact name
- **Pattern Matching**: Use `--regex` flag for pattern-based unfreezing
- **Batch Operations**: Automatically find and unfreeze multiple matching indices
- **Safety Confirmations**: Interactive prompts when multiple indices match
- **Automation Support**: Use `--yes` flag to skip confirmations for scripts
- **Detailed Feedback**: Clear success/failure reporting with reasons

**Unfreeze Command Options:**
- `--regex, -r`: Treat pattern as regex to match multiple indices
- `--yes, -y`: Skip confirmation prompts (useful for automation)

**Usage Examples:**

```bash
# Unfreeze a single index
./escmd.py unfreeze app-logs-2024-01

# Unfreeze multiple indices with pattern
./escmd.py unfreeze "app-logs-2024-*" --regex

# Batch unfreeze with confirmation skip (automation)
./escmd.py unfreeze "temp-*" --regex --yes

# Interactive unfreezing (will prompt if multiple matches)
./escmd.py unfreeze "logs-" --regex
```

**When to Unfreeze Indices:**
- **Resuming Write Operations**: When you need to index new documents
- **Full Search Performance**: Restore optimal search performance
- **Index Management**: Before applying settings changes or reindexing
- **Data Updates**: When historical data needs modifications

### � Index Exclusion Operations

Exclude indices from specific nodes or reset exclusion settings:

```bash
./escmd.py exclude my-index                    # Exclude index from allocation
./escmd.py exclude my-index --server ess46     # Exclude index from specific server
./escmd.py exclude-reset my-index             # Reset exclusion settings for index
```

**Index Exclusion Features:**
- **Server-Specific Exclusion**: Exclude index from specific nodes/servers
- **Allocation Control**: Control where indices can be allocated
- **Temporary Exclusions**: Temporarily move indices away from problematic nodes
- **Reset Capability**: Clear exclusion settings to restore normal allocation

**Exclusion Use Cases:**
- **Node Maintenance**: Move indices away from nodes undergoing maintenance
- **Performance Issues**: Exclude indices from underperforming nodes
- **Hardware Problems**: Temporarily exclude indices from nodes with hardware issues
- **Load Balancing**: Redistribute indices for better load balance

**Usage Examples:**

```bash
# Exclude index from a specific problematic server
./escmd.py exclude app-logs-2024 --server ess46

# Reset exclusions to allow normal allocation
./escmd.py exclude-reset app-logs-2024

# Exclude multiple indices (use with scripting)
for index in app-logs-2024-01 app-logs-2024-02; do
    ./escmd.py exclude $index --server problematic-node
done
```

### �🗑️ Index Deletion

Delete indices matching patterns with built-in safety features:

```bash
# Preview deletion (always do this first!)
./escmd.py indices "temp-*" --delete --dry-run   # Preview temp indices deletion
./escmd.py indices "old-logs-*" --delete         # Delete old log indices

# Status-based deletion
./escmd.py indices --status red --delete         # Delete unhealthy indices
./escmd.py indices "test-*" --status yellow --delete  # Delete yellow test indices

# Pattern-based deletion examples
./escmd.py indices ".*2023.*" --delete           # Delete indices containing "2023"
./escmd.py indices "^temp-" --delete             # Delete indices starting with "temp-"
./escmd.py indices "backup-.*" --delete          # Delete backup indices
```

**Deletion Safety Features:**
- **Interactive Confirmation**: Always prompts before deletion
- **Pattern Validation**: Shows exactly which indices will be deleted
- **Dry-Run Support**: Preview operations before execution (recommended)
- **Status Filtering**: Can combine with status filters for targeted cleanup
- **Rich Display**: Clear visualization of indices to be deleted

**Deletion Examples:**

```bash
# Safe deletion workflow
# 1. First, see what matches your pattern
./escmd.py indices "old-data-*"

# 2. Preview the deletion
./escmd.py indices "old-data-*" --delete --dry-run

# 3. Execute the deletion with confirmation
./escmd.py indices "old-data-*" --delete
```

**⚠️ Important Safety Notes:**
- **Always use dry-run first**: Preview operations before execution
- **Verify patterns carefully**: Ensure regex matches intended indices only
- **Check dependencies**: Verify indices aren't needed by applications
- **Backup critical data**: Ensure proper backups exist before deletion
- **Use status filters**: Combine with `--status` for safer targeted deletion

## Dangling Index Management

### ⚠️ Dangling Index Overview

Dangling indices are indices that exist in the cluster state but have lost their metadata. They represent orphaned data that needs careful management.

```bash
./escmd.py dangling                  # List all dangling indices
./escmd.py dangling --format json    # JSON output for automation
```

**What Creates Dangling Indices:**
- **Cluster Restoration**: Restoring from backup without proper metadata
- **Node Failures**: Catastrophic node failures with incomplete recovery
- **Data Directory Issues**: Manual data directory manipulation
- **Split-Brain Recovery**: Recovery from split-brain scenarios

### 🚀 Bulk Cleanup Operations

Advanced bulk cleanup with comprehensive safety features:

```bash
# Safe preview of cleanup operations
./escmd.py dangling --cleanup-all --dry-run

# Interactive cleanup with confirmations
./escmd.py dangling --cleanup-all

# Automated cleanup for scripts
./escmd.py dangling --cleanup-all --yes-i-really-mean-it

# Cleanup with detailed logging
./escmd.py dangling --cleanup-all --log-file cleanup.log
```

### Advanced Cleanup Features

**🛡️ Safety Features:**
- **Dry-Run Mode**: Preview operations without making changes
- **Interactive Confirmation**: Detailed impact warnings for destructive operations
- **Pre-flight Checks**: Validate cluster state before operations begin
- **Comprehensive Logging**: Detailed operation logs with timestamps
- **Partial Success Tracking**: Handle and report partial operation failures

**⚡ Advanced Retry Logic:**
```bash
# Configure retry behavior
./escmd.py dangling --cleanup-all --max-retries 5 --retry-delay 10 --timeout 120
```

**Retry Configuration:**
- `--max-retries`: Maximum retry attempts (default: 3)
- `--retry-delay`: Delay between retries in seconds (default: 5)
- `--timeout`: Operation timeout in seconds (default: 60)

**📊 Progress Tracking:**
- **Real-time Progress Bars**: Visual progress with ETA calculations
- **Bulk Processing**: Efficient handling of multiple indices simultaneously
- **Performance Metrics**: Throughput and timing information
- **Error Recovery**: Graceful handling of partial failures

**💾 Comprehensive Logging:**
```bash
# Enable detailed logging
./escmd.py dangling --cleanup-all --log-file /var/log/escmd-cleanup.log

# Different log levels
./escmd.py dangling --cleanup-all --log-file cleanup.log --debug
```

**Log Features:**
- **Structured Output**: JSON-formatted logs for parsing
- **Operation Summaries**: Detailed results with success/failure statistics
- **Timing Information**: Execution times and performance metrics
- **Error Details**: Complete error information for troubleshooting

### Individual Index Management

```bash
# Delete single dangling index
./escmd.py dangling <uuid> --delete

# Get detailed information about specific dangling index
./escmd.py dangling <uuid>
```

### Dangling Index Safety Guidelines

**⚠️ Important Considerations:**
1. **Data Loss**: Dangling indices represent data that may be lost forever if deleted
2. **Business Impact**: Verify indices are truly obsolete before deletion
3. **Backup Strategy**: Ensure proper backups exist before cleanup
4. **Gradual Approach**: Consider deleting indices gradually rather than all at once

**🔍 Before Cleanup Checklist:**
- [ ] Identify what data the indices contain
- [ ] Verify the data is not needed for business operations
- [ ] Confirm proper backups exist
- [ ] Test the cleanup process with dry-run
- [ ] Ensure cluster stability before beginning operations

## Shard Operations

### 🔄 Shard Distribution Analysis

View comprehensive shard distribution information with advanced filtering and analysis:

```bash
# Basic shard listing
./escmd.py shards                    # All shards with statistics
./escmd.py shards --format json      # JSON output for automation
./escmd.py shards --format data      # Raw data format

# Server-specific analysis
./escmd.py shards --server ess46     # Shards on specific server
./escmd.py shards -s ess46           # Short form server filter

# Pattern-based filtering
./escmd.py shards "logs-*"           # Shards for indices matching pattern
./escmd.py shards "app-.*"           # Application-specific shards

# Size and performance analysis
./escmd.py shards --size             # Sort by shard size (largest first)
./escmd.py shards -z                 # Short form size sorting
./escmd.py shards --limit 20         # Show only top 20 shards
./escmd.py shards -n 10              # Show only top 10 shards

# Combined analysis
./escmd.py shards "logs-*" --server ess46 --size    # Large log shards on specific server
./escmd.py shards --size --limit 10 --pager         # Top 10 largest shards with pager
```

**Command Options:**

| Option | Type | Description | Example |
|--------|------|-------------|---------|
| `pattern` | string | Regex pattern to filter indices | `"logs-*"` |
| `--server` / `-s` | string | Filter by server hostname | `--server ess46` |
| `--limit` / `-n` | integer | Limit results to N rows | `--limit 20` |
| `--size` / `-z` | flag | Sort by shard size (largest first) | `--size` |
| `--format` | choice | Output format (table, json, data) | `--format json` |
| `--pager` | flag | Force pager for large outputs | `--pager` |

**Shard Information:**
- **Statistics Panel**: Total shards, states, types, hot/frozen counts
- **Detailed Table**: Shard state, type, shard number, documents, size, node info
- **Performance Metrics**: Shard distribution balance and efficiency
- **Health Indicators**: Shard health status and issues

**Shard Analysis Features:**
- **Balance Metrics**: Even distribution analysis across nodes
- **Hot/Frozen Classification**: Shard temperature and access patterns
- **Size Distribution**: Shard size analysis and optimization opportunities
- **Performance Impact**: Identify shards affecting cluster performance
- **Server-Specific Analysis**: Focus on specific nodes for troubleshooting
- **Pattern Matching**: Filter by index patterns for targeted analysis

### ⚠️ Shard Colocation Detection

Identify availability risks where primary and replica shards are on the same host:

```bash
# Basic colocation analysis
./escmd.py shard-colocation          # Find colocation issues
./escmd.py shard-colocation --format json  # JSON output for automation

# Pattern-based colocation analysis
./escmd.py shard-colocation "logs-*"        # Check colocation for log indices
./escmd.py shard-colocation "app-.*"        # Check application indices
./escmd.py shard-colocation ".*prod.*"      # Check production indices

# Large output handling
./escmd.py shard-colocation --pager         # Force pager for large results
./escmd.py shard-colocation "logs-*" --pager  # Pattern with pager
```

**Command Options:**

| Option | Type | Description | Example |
|--------|------|-------------|---------|
| `pattern` | string | Regex pattern to filter indices | `"logs-*"` |
| `--format` | choice | Output format (table, json) | `--format json` |
| `--pager` | flag | Force pager for large outputs | `--pager` |

**Colocation Analysis:**
- **Risk Detection**: Identify single points of failure
- **Host-Level Analysis**: Group shards by physical host
- **Availability Impact**: Assess data availability risks
- **Recommendations**: Suggest shard relocation strategies

**What Colocation Problems Indicate:**
- **Configuration Issues**: Suboptimal shard allocation configuration
- **Hardware Constraints**: Insufficient nodes for proper distribution
- **Allocation Rules**: Missing or incorrect allocation awareness rules
- **Capacity Planning**: Need for additional nodes or better distribution

**Risk Mitigation:**
- **Shard Allocation Awareness**: Configure allocation awareness for physical hosts
- **Replica Placement**: Ensure replicas are placed on different hosts
- **Capacity Planning**: Add nodes to improve distribution options
- **Monitoring**: Regular colocation checks to catch issues early

## Configuration

### Paging System

escmd includes intelligent paging for large index lists:

```yaml
# elastic_servers.yml configuration
settings:
  enable_paging: true           # Enable automatic paging
  paging_threshold: 50          # Auto-enable when items exceed this count
```

**Paging Features:**
- **Automatic Activation**: Enables when output exceeds threshold
- **Less-like Navigation**: Familiar navigation controls
- **Manual Override**: `--no-pager` to disable paging
- **Configurable Threshold**: Adjust based on terminal size and preferences

### Legend Panels

Configure visibility of legend and quick actions:

```yaml
settings:
  show_legend_panels: false     # Show Legend and Quick Actions panels
```

**Legend Panel Features:**
- **Command Reference**: Quick reference for common operations
- **Status Indicators**: Explanation of color codes and symbols
- **Quick Actions**: Common command patterns and examples
- **Learning Mode**: Enable when learning escmd, disable for production use

### ASCII Mode

Maximum terminal compatibility mode:

```yaml
settings:
  ascii_mode: false             # Use ASCII-only characters
```

**ASCII Mode Benefits:**
- **Terminal Compatibility**: Works with any terminal type
- **Remote Access**: Reliable display over SSH and remote connections
- **Legacy Systems**: Compatible with older terminal emulators
- **Scripting**: Consistent output for parsing and automation

## Best Practices

### Index Management

1. **Regular Review**: Periodically review index lists for optimization opportunities
2. **Naming Conventions**: Use consistent naming patterns for easier management
3. **Lifecycle Planning**: Implement proper index lifecycle management
4. **Size Monitoring**: Monitor index sizes for performance optimization

### Dangling Index Cleanup

1. **Regular Audits**: Schedule regular dangling index audits
2. **Gradual Cleanup**: Delete dangling indices gradually to minimize impact
3. **Backup Verification**: Ensure proper backups before cleanup operations
4. **Documentation**: Document cleanup operations for audit trails

### Shard Management

1. **Balance Monitoring**: Regularly check shard distribution balance
2. **Colocation Prevention**: Implement proper allocation awareness
3. **Size Optimization**: Monitor and optimize shard sizes
4. **Performance Impact**: Consider shard operations' impact on cluster performance

### Freezing Strategy

1. **Access Patterns**: Freeze indices based on actual access patterns
2. **Resource Planning**: Plan freezing operations during low-usage periods
3. **Monitoring**: Monitor memory usage before and after freezing
4. **Unfreezing Plan**: Have a plan for unfreezing indices when needed

## Troubleshooting

### Index Access Issues

**Permission Problems:**
- Verify user permissions for index operations
- Check Elasticsearch security configuration
- Validate authentication credentials

**Index State Issues:**
- Check index health and status
- Verify index is not in read-only mode
- Ensure index is not corrupted or damaged

### Dangling Index Issues

**Cleanup Failures:**
- Check cluster health before cleanup operations
- Verify sufficient permissions for index deletion
- Review detailed error logs for specific failure reasons

**Performance Impact:**
- Monitor cluster performance during cleanup operations
- Consider breaking large cleanup operations into smaller batches
- Schedule cleanup during low-usage periods

### Shard Operations Issues

**Allocation Problems:**
- Check cluster allocation settings and rules
- Verify node capacity and availability
- Review allocation explain information for specific shards

**Performance Concerns:**
- Monitor cluster performance during shard operations
- Consider shard size and distribution optimization
- Plan shard operations during maintenance windows

## Related Commands

- [`cluster-check`](cluster-check.md) - Comprehensive health checks including shard analysis
- [`set-replicas`](replica-management.md) - Replica count management
- [`allocation`](allocation-management.md) - Shard allocation troubleshooting
- [`ilm`](ilm-management.md) - Index lifecycle management
- [`health`](health-monitoring.md) - Cluster health monitoring
