# Replica Management

Comprehensive dual-mode replica management with integrated health-check fixing and standalone operations for precise replica count control.

## Quick Reference

```bash
# Integrated health check + replica fixing (recommended)
./escmd.py cluster-check --fix-replicas 1 --dry-run   # Preview fixes
./escmd.py cluster-check --fix-replicas 1             # Execute fixes

# Standalone replica management (advanced)
./escmd.py set-replicas --no-replicas-only --dry-run  # Fix only 0-replica indices
./escmd.py set-replicas --pattern "logs-*" --count 2  # Pattern-based operations
./escmd.py set-replicas --indices "idx1,idx2" --count 1  # Specific indices
```

## Overview

escmd provides two complementary approaches for managing replica counts on indices:

1. **🏥 Integrated Health Check + Fixing** - Seamless workflow from discovery to resolution
2. **🔧 Standalone Replica Management** - Granular control for specific operations

## Integrated Health Check + Fixing

### 🚀 Recommended Workflow

The integrated approach combines cluster health assessment with immediate replica fixing capabilities:

```bash
# Discover and preview replica fixes during health check
./escmd.py cluster-check --fix-replicas 1 --dry-run

# Execute fixes for indices found during health check
./escmd.py cluster-check --fix-replicas 1

# Fix with custom shard size threshold
./escmd.py cluster-check --max-shard-size 100 --fix-replicas 1

# Skip confirmation prompts (automation)
./escmd.py cluster-check --fix-replicas 1 --force

# JSON output with replica fixing plan
./escmd.py cluster-check --fix-replicas 1 --dry-run --format json
```

### Integration Benefits

**🔍 Discovery First**: Identifies all cluster issues before fixing
- Complete health assessment shows ILM errors, shard sizes, and replica issues together
- Provides full context for informed decision-making
- Identifies related issues that might affect replica changes

**🎯 Targeted Fixing**: Only targets indices with 0 replicas found during health check
- Automatic filtering based on health assessment results
- No manual index identification required
- Focuses on actual issues, not theoretical scenarios

**📊 Comprehensive Context**: Shows full cluster health picture
- Complete understanding of cluster state before making changes
- Identifies potential conflicts or dependencies
- Provides recommendations based on overall cluster health

**⚡ One-Command Workflow**: Health assessment → Issue identification → Automated fixing
- Streamlined operations workflow
- Reduces command complexity and human error
- Perfect for daily maintenance routines

**🏥 Professional Reports**: Full-width tables and rich formatting for production use
- Clear visual progression from assessment to fixing
- Professional presentation suitable for operations teams
- Comprehensive documentation of actions taken

### Integrated Command Options

| Option | Description | Default |
|--------|-------------|---------|
| `--fix-replicas COUNT` | Set replica count for indices with 0 replicas | None |
| `--dry-run` | Preview replica fixes without applying them | `false` |
| `--force` | Skip confirmation prompts when fixing replicas | `false` |
| `--format json` | JSON output including replica fixing results | `table` |

## Standalone Replica Management

### 🔧 Advanced Control

The standalone approach provides granular control for specific replica management tasks:

```bash
# Fix only indices with 0 replicas
./escmd.py set-replicas --no-replicas-only --dry-run

# Set specific indices to 1 replica
./escmd.py set-replicas --indices "index1,index2,index3" --count 1

# Pattern-based replica setting
./escmd.py set-replicas --pattern "logs-*" --count 2 --dry-run

# Fix all matching indices (removes replica count filter)
./escmd.py set-replicas --pattern "temp-*" --count 0 --force

# Export replica management plan as JSON
./escmd.py set-replicas --no-replicas-only --format json > replica-plan.json
```

### Standalone Benefits

**🎛️ Granular Control**: Target specific indices or patterns
- Precise index selection with multiple filtering options
- Complex selection criteria beyond simple health checks
- Advanced pattern matching for bulk operations

**🔢 Flexible Counts**: Set any replica count (0, 1, 2, etc.)
- Not limited to fixing 0-replica indices
- Support for increasing or decreasing replica counts
- Handles complex replica management scenarios

**📋 Advanced Filtering**: Complex selection criteria and bulk operations
- Multiple targeting modes: indices, patterns, replica-based filtering
- Sophisticated pattern matching with wildcard support
- Boolean logic for complex selection criteria

**🚀 Dedicated Interface**: Focused entirely on replica management
- Specialized command interface optimized for replica operations
- Advanced features specific to replica management workflows
- No overhead from health checking when not needed

**⚙️ Automation Ready**: Perfect for scripts and maintenance workflows
- Command-line friendly with predictable behavior
- JSON output for integration with automation systems
- Batch processing capabilities for large-scale operations

### Standalone Command Options

| Option | Description | Default |
|--------|-------------|---------|
| `--count COUNT` | Target replica count | `1` |
| `--indices INDICES` | Comma-separated list of specific indices | None |
| `--pattern PATTERN` | Pattern to match indices (e.g., "logs-*") | None |
| `--no-replicas-only` | Only update indices with 0 replicas | `false` |
| `--dry-run` | Preview changes without applying them | `false` |
| `--force` | Skip confirmation prompts | `false` |
| `--format FORMAT` | Output format: `table` or `json` | `table` |

## Core Features

### 🛡️ Safety & Validation

**Comprehensive Planning**: Shows current → target replica counts before execution
```bash
# Planning output example
📋 Replica Update Plan Summary
📊 Total indices analyzed: 150
🔧 Indices requiring updates: 3
⏭️ Indices to skip: 0
🎯 Target replica count: 1
```

**Pre-flight Validation**: Checks index existence and current settings
- Validates all specified indices exist
- Confirms current replica settings
- Identifies any access or permission issues
- Warns about potential conflicts

**Dry-run Mode**: Preview changes without applying them
```bash
./escmd.py set-replicas --pattern "logs-*" --count 2 --dry-run
./escmd.py cluster-check --fix-replicas 1 --dry-run
```

**Safety Prompts**: Confirmation before making changes (bypass with `--force`)
- Interactive confirmation with impact summary
- Clear explanation of changes to be made
- Option to cancel before execution
- Force mode for automation scenarios

### 📊 Rich Progress Tracking

**Visual Progress Bars**: Real-time progress tracking during execution
```
🔧 Fixing replica counts... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 3/3 indices
```

**Live Status Updates**: Real-time status for each index operation
- Individual index processing status
- Success/failure indicators per index
- Real-time error reporting
- Completion timestamps

**Professional Formatting**: Full-width tables with color-coded status indicators
- Consistent Rich library styling
- Color-coded status indicators (green=success, red=error, yellow=warning)
- Professional table layouts with proper alignment
- Clear visual hierarchy and organization

**Performance Metrics**: Execution time and throughput information
- Total execution time
- Per-index processing time
- Throughput metrics (indices per second)
- API response time statistics

### 🔄 Output Formats

#### Rich Tables (Default)
Professional formatting with color-coded status indicators and full-width tables:

```
🔧 Indices to Update
┌─────────────────────────────────────┬─────────────────┬─────────────────┬──────────────────────┐
│ Index                               │ Current Replicas│ Target Replicas │ Status               │
├─────────────────────────────────────┼─────────────────┼─────────────────┼──────────────────────┤
│ logs-app-2024.01.01                 │ 0               │ 1               │ ✅ Updated successfully│
│ logs-api-2024.01.01                 │ 0               │ 1               │ ✅ Updated successfully│
│ logs-web-2024.01.01                 │ 0               │ 1               │ ✅ Updated successfully│
└─────────────────────────────────────┴─────────────────┴─────────────────┴──────────────────────┘
```

#### JSON Export
Machine-readable output for automation and monitoring:

```json
{
  "plan": {
    "indices_to_update": [
      {
        "index": "logs-app-2024.01.01",
        "current_replicas": 0,
        "target_replicas": 1
      }
    ],
    "total_candidates": 3,
    "total_updates_needed": 3,
    "target_count": 1
  },
  "execution": {
    "successful": 3,
    "failed": 0,
    "total_time": "2.34s",
    "details": [...]
  }
}
```

## Workflow Examples

### Production Maintenance Workflow

```bash
# 1. Assess cluster health and identify replica issues
./escmd.py -l production cluster-check

# 2. Plan replica fixes with dry-run
./escmd.py -l production cluster-check --fix-replicas 1 --dry-run

# 3. Execute fixes with confirmation
./escmd.py -l production cluster-check --fix-replicas 1

# 4. Verify changes took effect
./escmd.py -l production cluster-check
```

### Targeted Maintenance Workflow

```bash
# 1. Identify specific indices needing replica changes
./escmd.py set-replicas --pattern "logs-2024-*" --dry-run

# 2. Execute changes for specific pattern
./escmd.py set-replicas --pattern "logs-2024-*" --count 1

# 3. Verify with health check
./escmd.py cluster-check
```

### Automation Workflow

```bash
# Automated script-friendly execution
./escmd.py cluster-check --fix-replicas 1 --force --format json > replica-results.json

# Parse results for monitoring
jq '.replica_fixing.plan.total_updates_needed' replica-results.json
```

### Bulk Operations Workflow

```bash
# 1. Analyze current replica distribution
./escmd.py set-replicas --pattern "*" --dry-run --format json > current-state.json

# 2. Plan standardization (e.g., all indices to 1 replica)
./escmd.py set-replicas --pattern "logs-*" --count 1 --dry-run

# 3. Execute in batches with confirmation
./escmd.py set-replicas --pattern "logs-app-*" --count 1
./escmd.py set-replicas --pattern "logs-api-*" --count 1

# 4. Verify final state
./escmd.py cluster-check
```

## Advanced Use Cases

### Pattern-Based Operations

```bash
# Application-specific replica management
./escmd.py set-replicas --pattern "app-logs-*" --count 2 --dry-run
./escmd.py set-replicas --pattern "system-logs-*" --count 1 --dry-run

# Date-based operations
./escmd.py set-replicas --pattern "*2024-01*" --count 0 --dry-run  # Archive old data
./escmd.py set-replicas --pattern "*2024-08*" --count 2 --dry-run  # Increase current month

# Environment-specific operations
./escmd.py set-replicas --pattern "prod-*" --count 2 --dry-run     # Production redundancy
./escmd.py set-replicas --pattern "test-*" --count 0 --dry-run     # Test environment efficiency
```

### Governance and Compliance

```bash
# Compliance reporting (identify non-compliant indices)
./escmd.py cluster-check --format json | jq '.checks.no_replica_indices'

# Standardization enforcement
./escmd.py set-replicas --no-replicas-only --count 1 --dry-run  # Ensure minimum redundancy

# Policy validation
./escmd.py set-replicas --pattern "*" --dry-run --format json > replica-audit.json
```

### Disaster Recovery Preparation

```bash
# Increase replica counts before maintenance
./escmd.py set-replicas --pattern "*critical*" --count 2 --dry-run
./escmd.py set-replicas --pattern "*critical*" --count 2

# Restore normal replica counts after maintenance
./escmd.py set-replicas --pattern "*critical*" --count 1 --dry-run
./escmd.py set-replicas --pattern "*critical*" --count 1
```

## Best Practices

### 🎯 Choosing the Right Approach

**Use Integrated Mode When:**
- Performing routine daily health checks
- Fixing issues discovered during health assessment
- Need complete cluster context before making changes
- Working with operations teams requiring comprehensive reports

**Use Standalone Mode When:**
- Implementing specific replica management policies
- Performing bulk operations across many indices
- Automating replica management workflows
- Need granular control over index selection

### 🛡️ Safety Guidelines

1. **Always Use Dry-Run First**: Preview changes before execution
2. **Validate Index Names**: Ensure patterns match intended indices
3. **Consider Dependencies**: Check for application dependencies on replica counts
4. **Monitor During Execution**: Watch for errors during bulk operations
5. **Verify Results**: Run health checks after making changes

### ⚡ Performance Optimization

1. **Batch Operations**: Group related changes together
2. **Off-Peak Execution**: Schedule large operations during low-traffic periods
3. **Monitor Cluster Load**: Watch cluster performance during replica changes
4. **Progressive Rollout**: Make changes incrementally for large index sets

### 🤖 Automation Integration

1. **Use JSON Output**: Machine-readable format for monitoring systems
2. **Error Handling**: Check exit codes and parse error messages
3. **Idempotent Operations**: Design scripts to be safely re-runnable
4. **Logging**: Capture operation logs for audit and troubleshooting

## Troubleshooting

### Common Issues

**Index Not Found**:
- Verify index names and patterns
- Check for typos in index specifications
- Ensure indices exist and are accessible

**Permission Denied**:
- Verify Elasticsearch authentication and authorization
- Check user permissions for index management operations
- Validate cluster access credentials

**Operation Timeout**:
- Check cluster performance and load
- Consider breaking large operations into smaller batches
- Verify network connectivity and stability

**Partial Failures**:
- Review detailed error messages for specific indices
- Check individual index health and status
- Retry failed operations after addressing root causes

### Performance Considerations

**Large Index Sets**:
- Use patterns to process indices in logical groups
- Monitor cluster performance during operations
- Consider staggering operations to reduce load

**Network Latency**:
- Account for network delays in timeout settings
- Use local cluster access when possible
- Monitor operation timing and adjust expectations

**Cluster Load**:
- Schedule operations during low-traffic periods
- Monitor cluster health during and after operations
- Be prepared to pause operations if cluster performance degrades

## Related Commands

- [`cluster-check`](cluster-check.md) - Comprehensive health checks with integrated replica fixing
- [`health`](health-monitoring.md) - Basic cluster health monitoring
- [`indices`](index-operations.md) - Index listing and management
- [`allocation`](allocation-management.md) - Shard allocation management
