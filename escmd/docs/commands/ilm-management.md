# Index Lifecycle Management (ILM)

Comprehensive ILM support with policy management, phase tracking, error monitoring, and usage analysis.

## Quick Reference

```bash
# ILM overview and status
./escmd.py ilm status                 # Complete ILM overview
./escmd.py ilm policies               # List all ILM policies

# Policy management
./escmd.py ilm policy my-policy       # Detailed policy view
./escmd.py ilm policy my-policy --show-all  # Include all indices using policy

# Error detection and analysis
./escmd.py ilm errors                 # Find indices with ILM errors
./escmd.py ilm explain my-index       # Explain specific index ILM status

# JSON output for automation
./escmd.py ilm status --format json   # JSON status output
./escmd.py ilm policies --format json # JSON policies output
```

## Overview

Index Lifecycle Management (ILM) automates index management throughout their lifecycle, from creation through deletion. escmd provides comprehensive ILM monitoring and management capabilities to help you understand and troubleshoot ILM operations.

## Core ILM Commands

### 📊 ILM Status Overview

Get a comprehensive overview of ILM status across the cluster:

```bash
./escmd.py ilm status                 # Complete ILM overview
./escmd.py ilm status --format json   # JSON output for automation
```

**Status Overview Features:**
- **Cluster ILM Health**: Overall ILM operation status
- **Policy Summary**: Count of policies and their usage
- **Index Statistics**: Managed vs unmanaged indices
- **Error Summary**: Quick view of ILM issues
- **Performance Metrics**: ILM operation statistics

**Information Displayed:**
- **Total Policies**: Number of ILM policies configured
- **Active Policies**: Policies currently in use
- **Managed Indices**: Indices under ILM management
- **Error Count**: Indices with ILM errors
- **Unmanaged Indices**: Indices without ILM policies

### 📋 Policy Management

#### List All Policies
```bash
./escmd.py ilm policies               # All policies overview
./escmd.py ilm policies --format json # JSON output
```

**Policy List Features:**
- **📋 Policy Matrix**: Shows which phases (🔥🟡🧊❄️🗑️) each policy covers
- **📊 Usage Statistics**: Number of indices using each policy
- **🎯 Phase Overview**: Quick view of policy lifecycle coverage
- **📁 Index Count**: Live count of indices managed by each policy

**Phase Indicators:**
- 🔥 **Hot Phase**: Active indexing and frequent searches
- 🟡 **Warm Phase**: Less frequent searches, read-only
- 🧊 **Cold Phase**: Infrequent searches, compressed storage
- ❄️ **Frozen Phase**: Very rare searches, minimal resources
- 🗑️ **Delete Phase**: Automatic index deletion

#### Detailed Policy View
```bash
./escmd.py ilm policy my-policy       # Basic policy details
./escmd.py ilm policy my-policy --show-all  # Include all using indices
```

**Detailed Policy Information:**
- **📊 Detailed Policy View**: Phase configurations, actions, transitions, and conditions
- **📁 Usage Analysis**: Live list of indices using the policy with current phase/action
- **🎯 Smart Display**: Shows first 10 indices by default, `--show-all` for complete list
- **🔄 Transition Rules**: Conditions and timing for phase transitions
- **⚙️ Action Details**: Specific actions configured for each phase

**Policy Configuration Display:**
- **Phase Definitions**: Detailed configuration for each lifecycle phase
- **Transition Conditions**: Size, age, and document count thresholds
- **Actions**: rollover, shrink, forcemerge, allocate, delete, etc.
- **Settings**: Index settings changes during lifecycle progression

### 🔍 Index Lifecycle Analysis

#### Explain Individual Index Status
```bash
./escmd.py ilm explain my-index-2024.01.01     # Basic explain
./escmd.py ilm explain my-index --format json  # JSON output
```

**Index Explain Features:**
- **🔍 Index Details**: Shows policy, current phase, action, step, and error status
- **🔄 Phase Tracking**: Visual phase indicators and lifecycle progression
- **⚡ Real-time Status**: Current action and step information
- **📊 Progress Tracking**: Time spent in current phase and step
- **🎯 Next Actions**: What will happen next in the lifecycle

**Information Provided:**
- **Current Policy**: Which ILM policy is managing the index
- **Current Phase**: hot, warm, cold, frozen, or delete
- **Current Action**: rollover, shrink, allocate, delete, etc.
- **Current Step**: Detailed step within the current action
- **Step Time**: How long the index has been in the current step
- **Phase Time**: Total time spent in the current phase
- **Age**: Index age since creation or last rollover

#### Find Indices with ILM Errors
```bash
./escmd.py ilm errors                 # List all ILM errors
./escmd.py ilm errors --format json   # JSON output for automation
```

**Error Detection Features:**
- **❌ Error Detection**: Identifies indices with ILM failures and error reasons
- **🔄 Retry Information**: Shows retry counts and retry strategies
- **📊 Error Categorization**: Groups errors by type and severity
- **🎯 Resolution Guidance**: Provides suggestions for fixing common errors

**Error Information:**
- **Index Name**: Affected index
- **Error Type**: Category of ILM error
- **Error Message**: Detailed error description
- **Retry Count**: Number of automatic retry attempts
- **Failed Step**: Which step in the lifecycle failed
- **Failure Time**: When the error first occurred

## Policy Management Commands

### 🗑️ Remove ILM Policies

Remove ILM policies from indices using patterns or file lists:

```bash
# Remove policies by pattern
./escmd.py ilm remove-policy "temp-*"           # Remove from temp indices
./escmd.py ilm remove-policy "old-logs-.*"      # Remove from old log indices

# Safe removal with dry-run
./escmd.py ilm remove-policy "test-*" --dry-run     # Preview removal
./escmd.py ilm remove-policy "backup-*" --dry-run --format json  # JSON preview

# Remove from file list
./escmd.py ilm remove-policy --file indices-to-clean.txt  # From file

# Advanced removal options
./escmd.py ilm remove-policy "staging-*" --save-json removed-policies.json  # Save for restoration
./escmd.py ilm remove-policy "temp-*" --yes --max-concurrent 10  # Skip confirmation, parallel
./escmd.py ilm remove-policy "logs-*" --continue-on-error  # Continue despite failures
```

**Remove Policy Options:**

| Option | Type | Description | Example |
|--------|------|-------------|---------|
| `pattern` | string | Regex pattern to match indices | `"temp-*"` |
| `--dry-run` | flag | Preview changes without executing | `--dry-run` |
| `--format` | choice | Output format (table, json) | `--format json` |
| `--yes` | flag | Skip confirmation prompts | `--yes` |
| `--max-concurrent` | integer | Maximum concurrent operations | `--max-concurrent 10` |
| `--continue-on-error` | flag | Continue if some indices fail | `--continue-on-error` |
| `--save-json` | string | Save removed indices to JSON file | `--save-json backup.json` |
| `--file` | string | Read index names from file | `--file indices.txt` |

### 📋 Set ILM Policies

Apply ILM policies to indices using patterns or restore from JSON:

```bash
# Set policies by pattern
./escmd.py ilm set-policy "logs-*" my-log-policy      # Apply to log indices
./escmd.py ilm set-policy "app-.*" app-retention      # Apply to app indices

# Safe application with dry-run
./escmd.py ilm set-policy "new-*" standard-policy --dry-run  # Preview assignment
./escmd.py ilm set-policy "temp-*" cleanup-policy --dry-run --format json  # JSON preview

# Restore from saved JSON
./escmd.py ilm set-policy --from-json removed-policies.json standard-policy  # Restore from file

# Advanced set options
./escmd.py ilm set-policy "logs-*" retention-30d --yes --max-concurrent 5  # Skip confirmation
./escmd.py ilm set-policy "staging-*" test-policy --continue-on-error  # Continue despite failures
```

**Set Policy Options:**

| Option | Type | Description | Example |
|--------|------|-------------|---------|
| `pattern` | string | Regex pattern to match indices | `"logs-*"` |
| `policy_name` | string | Name of ILM policy to apply | `my-policy` |
| `--dry-run` | flag | Preview changes without executing | `--dry-run` |
| `--format` | choice | Output format (table, json) | `--format json` |
| `--yes` | flag | Skip confirmation prompts | `--yes` |
| `--max-concurrent` | integer | Maximum concurrent operations | `--max-concurrent 5` |
| `--continue-on-error` | flag | Continue if some indices fail | `--continue-on-error` |
| `--from-json` | string | Read indices from JSON file | `--from-json backup.json` |

### Policy Management Workflow

```bash
# 1. Save current state before making changes
./escmd.py ilm remove-policy "logs-2023-*" --dry-run --save-json logs-2023-backup.json

# 2. Remove old policies
./escmd.py ilm remove-policy "logs-2023-*" --save-json logs-2023-backup.json

# 3. Apply new policies
./escmd.py ilm set-policy "logs-2023-*" archive-policy --dry-run
./escmd.py ilm set-policy "logs-2023-*" archive-policy

# 4. Verify changes
./escmd.py ilm errors
./escmd.py ilm policy archive-policy --show-all

# 5. Restore if needed (rollback)
./escmd.py ilm set-policy --from-json logs-2023-backup.json original-policy
```

## ILM Workflow Examples

### Daily ILM Monitoring
```bash
# 1. Check overall ILM health
./escmd.py ilm status

# 2. Review all policies and their coverage
./escmd.py ilm policies

# 3. Check for problematic indices
./escmd.py ilm errors

# 4. Investigate specific issues (if any)
./escmd.py ilm explain problematic-index-name
```

### Policy Analysis Workflow
```bash
# 1. List all policies to understand coverage
./escmd.py ilm policies

# 2. Investigate specific policy usage
./escmd.py ilm policy logs-retention-policy

# 3. See all indices using the policy
./escmd.py ilm policy logs-retention-policy --show-all

# 4. Check for errors in policy execution
./escmd.py ilm errors
```

### Troubleshooting Workflow
```bash
# 1. Identify problematic indices
./escmd.py ilm errors

# 2. Analyze specific index lifecycle status
./escmd.py ilm explain stuck-index-name

# 3. Review policy configuration
./escmd.py ilm policy policy-name

# 4. Export data for deeper analysis
./escmd.py ilm status --format json > ilm-analysis.json
./escmd.py ilm errors --format json > ilm-errors.json
```

### Automation and Monitoring
```bash
# Regular monitoring script
./escmd.py ilm status --format json > /var/log/ilm-status.json
./escmd.py ilm errors --format json > /var/log/ilm-errors.json

# Parse specific metrics
jq '.policies.total' /var/log/ilm-status.json
jq '.error_count' /var/log/ilm-errors.json

# Alert on errors
ERROR_COUNT=$(./escmd.py ilm errors --format json | jq length)
if [ "$ERROR_COUNT" -gt 0 ]; then
    echo "ILM errors detected: $ERROR_COUNT indices"
fi
```

## Output Formats

### 📊 Rich Formatted Output (Default)

**Professional Tables and Panels:**
- **Color-coded Status**: Green=healthy, Yellow=warning, Red=error
- **Visual Phase Indicators**: Emoji-based phase representation
- **Professional Layout**: Rich library formatting with bordered panels
- **Hierarchical Information**: Organized display of complex ILM data

**Policy Matrix Example:**
```
📋 ILM Policies Overview
┌─────────────────────────┬─────┬──────┬──────┬────────┬────────┬─────────┐
│ Policy Name             │ 🔥  │ 🟡   │ 🧊   │ ❄️     │ 🗑️     │ Indices │
├─────────────────────────┼─────┼──────┼──────┼────────┼────────┼─────────┤
│ logs-retention-30d      │ ✓   │ ✓    │ ✓    │ -      │ ✓      │ 1,247   │
│ metrics-retention-7d    │ ✓   │ -    │ -    │ -      │ ✓      │ 89      │
│ archive-long-term       │ ✓   │ ✓    │ ✓    │ ✓      │ -      │ 156     │
└─────────────────────────┴─────┴──────┴──────┴────────┴────────┴─────────┘
```

### 📄 JSON Output

Machine-readable format for automation and integration:

```json
{
  "cluster_name": "production-cluster",
  "ilm_status": {
    "policies": {
      "total": 12,
      "active": 10
    },
    "indices": {
      "managed": 1247,
      "unmanaged": 89,
      "errors": 3
    }
  },
  "policies": [
    {
      "name": "logs-retention-30d",
      "phases": ["hot", "warm", "cold", "delete"],
      "indices_using": 1247,
      "phase_config": {
        "hot": {
          "actions": ["rollover"],
          "rollover": {
            "max_size": "50gb",
            "max_age": "1d"
          }
        }
      }
    }
  ]
}
```

## ILM Best Practices

### 📋 Policy Design

**Phase Planning:**
1. **Hot Phase**: Design for active indexing with appropriate rollover triggers
2. **Warm Phase**: Optimize for read performance with replica reduction
3. **Cold Phase**: Focus on storage efficiency with compression and allocation
4. **Frozen Phase**: Minimize resources while maintaining searchability
5. **Delete Phase**: Ensure compliance with data retention requirements

**Rollover Configuration:**
- **Size-based**: Typically 50GB for optimal performance
- **Time-based**: Daily rollover for time-series data
- **Document-based**: Based on document count thresholds
- **Combined Triggers**: Use multiple triggers for flexible rollover

### 🔧 Monitoring and Maintenance

**Regular Monitoring:**
1. **Daily Status Checks**: Monitor overall ILM health
2. **Error Tracking**: Address ILM errors promptly
3. **Performance Monitoring**: Track ILM operation performance
4. **Policy Effectiveness**: Analyze policy performance and optimization opportunities

**Proactive Maintenance:**
1. **Policy Updates**: Regularly review and update ILM policies
2. **Threshold Tuning**: Adjust rollover and transition thresholds based on data patterns
3. **Resource Planning**: Plan storage and compute resources for lifecycle transitions
4. **Documentation**: Maintain documentation of policy decisions and changes

### 🚨 Error Resolution

**Common ILM Errors:**
1. **Rollover Failures**: Check alias configuration and rollover conditions
2. **Allocation Failures**: Verify node capacity and allocation rules
3. **Shrink Failures**: Ensure proper node configuration for shrink operations
4. **Delete Failures**: Check index locks and application dependencies

**Troubleshooting Steps:**
1. **Identify Pattern**: Look for patterns in ILM errors across indices
2. **Check Configuration**: Verify policy configuration and cluster settings
3. **Resource Validation**: Ensure adequate resources for ILM operations
4. **Step-by-Step Analysis**: Use explain command to understand failure points

## Integration with Cluster Health

ILM monitoring integrates seamlessly with escmd's cluster health features:

```bash
# Comprehensive health check including ILM
./escmd.py cluster-check                # Includes ILM error detection

# ILM-focused health analysis
./escmd.py cluster-check --show-details # Extended ILM information

# Skip ILM for older clusters
./escmd.py cluster-check --skip-ilm     # For clusters without ILM support
```

**Integration Benefits:**
- **Unified View**: ILM status alongside other cluster health metrics
- **Contextual Analysis**: Understand ILM issues in broader cluster context
- **Automated Detection**: Automatic identification of ILM issues during health checks
- **Comprehensive Reporting**: ILM status included in regular health reports

## Advanced Use Cases

### 📊 Capacity Planning

```bash
# Analyze index growth patterns
./escmd.py ilm policies --format json | jq '.policies[] | select(.name == "logs-policy")'

# Monitor rollover frequency
./escmd.py ilm explain logs-app-* --format json | jq '.phase_time'

# Track storage utilization by phase
./escmd.py ilm status --format json | jq '.indices_by_phase'
```

### 🔄 Policy Migration

```bash
# Before migration: Document current state
./escmd.py ilm status --format json > pre-migration-state.json
./escmd.py ilm policies --format json > current-policies.json

# After migration: Validate changes
./escmd.py ilm status --format json > post-migration-state.json
./escmd.py ilm errors  # Check for new errors

# Compare states
diff pre-migration-state.json post-migration-state.json
```

### 📈 Performance Analysis

```bash
# Identify slow ILM operations
./escmd.py ilm errors --format json | jq '.[] | select(.retry_count > 5)'

# Analyze phase transition times
./escmd.py ilm explain "*" --format json | jq '.[] | {index: .index, phase: .phase, phase_time: .phase_time}'

# Monitor rollover patterns
./escmd.py ilm explain "logs-*" --format json | jq '.[] | select(.action == "rollover")'
```

## Troubleshooting

### Common Issues

**ILM Not Working:**
- Verify ILM is enabled on the cluster
- Check Elasticsearch version compatibility
- Validate policy syntax and configuration

**Slow ILM Operations:**
- Monitor cluster performance during ILM operations
- Check resource availability (CPU, memory, disk)
- Review ILM operation frequency and timing

**Rollover Issues:**
- Verify index templates and aliases
- Check rollover conditions and triggers
- Validate write permissions and index creation

**Allocation Failures:**
- Review cluster allocation settings
- Check node capacity and availability
- Validate allocation awareness configuration

### Performance Optimization

**ILM Operation Timing:**
- Schedule ILM operations during low-traffic periods
- Stagger operations to avoid resource contention
- Monitor cluster performance during ILM transitions

**Resource Management:**
- Plan storage capacity for all lifecycle phases
- Ensure adequate compute resources for transitions
- Monitor memory usage during shrink and merge operations

**Policy Optimization:**
- Regular review of rollover triggers and thresholds
- Optimize phase transitions based on access patterns
- Balance storage efficiency with operational requirements

## Related Commands

- [`cluster-check`](cluster-check.md) - Comprehensive health checks including ILM monitoring
- [`indices`](index-operations.md) - Index listing and management
- [`health`](health-monitoring.md) - Cluster health monitoring
- [`allocation`](allocation-management.md) - Shard allocation management
