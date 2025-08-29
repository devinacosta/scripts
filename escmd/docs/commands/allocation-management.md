# Allocation Management

Comprehensive shard allocation management with cluster-level controls, node exclusions, and allocation troubleshooting.

## Quick Reference

```bash
# Allocation status and control
./escmd.py allocation                 # Show current allocation settings
./escmd.py allocation enable          # Enable shard allocation
./escmd.py allocation disable         # Disable shard allocation

# Node exclusion management
./escmd.py allocation exclude add ess46       # Exclude node from allocation
./escmd.py allocation exclude remove ess46    # Remove exclusion
./escmd.py allocation exclude reset           # Clear all exclusions

# Allocation troubleshooting
./escmd.py allocation explain my-index        # Explain allocation decisions
./escmd.py allocation explain my-index --shard 2  # Explain specific shard
```

## Overview

Allocation management controls how Elasticsearch distributes shards across the cluster. These commands provide comprehensive control over shard placement, node exclusions, and allocation troubleshooting.

## Core Allocation Commands

### 📊 Display Allocation Settings

View current cluster allocation settings and status:

```bash
./escmd.py allocation                    # Current allocation settings (default: display)
./escmd.py allocation display            # Explicit display command
./escmd.py allocation display --format json  # JSON output for automation
```

**Information Displayed:**
- **Allocation Status**: Whether allocation is enabled or disabled
- **Excluded Nodes**: List of nodes excluded from allocation
- **Allocation Rules**: Current allocation awareness and filtering rules
- **Throttling Settings**: Allocation throttling and recovery limits
- **Cluster Settings**: Relevant cluster-level allocation settings

### ⚡ Enable/Disable Allocation

Control cluster-wide shard allocation:

```bash
# Enable shard allocation
./escmd.py allocation enable             # Enable with table output
./escmd.py allocation enable --format json  # Enable with JSON output

# Disable shard allocation (use with caution!)
./escmd.py allocation disable            # Disable with table output
./escmd.py allocation disable --format json  # Disable with JSON output
```

**When to Disable Allocation:**
- **Rolling Restarts**: Prevent unnecessary shard movement during restarts
- **Maintenance Windows**: Stop allocation during cluster maintenance
- **Emergency Situations**: Stop allocation when cluster is under stress
- **Node Replacement**: Prevent allocation during hardware replacement

**⚠️ Important Notes:**
- **Temporary Use Only**: Allocation should only be disabled temporarily
- **Re-enable Promptly**: Always re-enable allocation after maintenance
- **Monitor Carefully**: Watch for unassigned shards when disabled
- **Emergency Only**: Only disable during emergencies or planned maintenance

## Node Exclusion Management

### 🚫 Exclude Nodes from Allocation

Exclude specific nodes from shard allocation:

```bash
# Add node to exclusion list
./escmd.py allocation exclude add ess46         # Exclude node ess46
./escmd.py allocation exclude add server01      # Exclude server01
./escmd.py allocation exclude add node-name --format json  # JSON output

# Multiple exclusions (run multiple commands)
./escmd.py allocation exclude add ess46
./escmd.py allocation exclude add ess47
```

**Exclusion Use Cases:**
- **Node Decommissioning**: Move shards off nodes before removal
- **Hardware Maintenance**: Prevent allocation to nodes under maintenance
- **Performance Issues**: Exclude problematic nodes temporarily
- **Capacity Management**: Control which nodes receive new shards

### ✅ Remove Node Exclusions

Remove nodes from the exclusion list:

```bash
# Remove single node exclusion
./escmd.py allocation exclude remove ess46      # Remove ess46 from exclusions
./escmd.py allocation exclude remove server01   # Remove server01
./escmd.py allocation exclude remove node-name --format json  # JSON output

# Clear all exclusions at once
./escmd.py allocation exclude reset             # Clear all exclusions
./escmd.py allocation exclude reset --format json  # JSON output
```

**When to Remove Exclusions:**
- **Maintenance Complete**: Node is back online and healthy
- **Hardware Fixed**: Issues with the node have been resolved
- **Capacity Needed**: Need to use previously excluded nodes
- **Rebalancing**: Allow normal shard distribution

### Exclusion Workflow

```bash
# Safe node decommissioning workflow
# 1. Check current allocation
./escmd.py allocation display

# 2. Exclude node from allocation
./escmd.py allocation exclude add ess46

# 3. Monitor shard movement
./escmd.py health
./escmd.py shards --server ess46

# 4. Wait for shards to move off the node
# (Monitor until no shards remain on ess46)

# 5. Safely remove the node from cluster
# (External hardware/infrastructure operations)

# 6. Clean up exclusions if needed
./escmd.py allocation exclude remove ess46
# OR clear all exclusions
./escmd.py allocation exclude reset
```

## Allocation Troubleshooting

### 🔍 Allocation Explain

Understand why specific shards are or aren't allocated:

```bash
# Explain allocation for index (default shard 0)
./escmd.py allocation explain my-index-name     # Basic allocation explanation
./escmd.py allocation explain my-index --format json  # JSON output

# Explain specific shard
./escmd.py allocation explain my-index --shard 2      # Explain shard 2
./escmd.py allocation explain my-index -s 1           # Short form for shard 1

# Explain primary vs replica
./escmd.py allocation explain my-index --primary      # Force primary shard explanation
./escmd.py allocation explain my-index --shard 1 --primary  # Primary shard 1

# Complex troubleshooting
./escmd.py allocation explain problematic-index --shard 0 --format json  # Detailed JSON analysis
```

**Command Options:**

| Option | Type | Description | Example |
|--------|------|-------------|---------|
| `index` | string | Index name to explain | `my-index` |
| `--shard` / `-s` | integer | Shard number (default: 0) | `--shard 2` |
| `--primary` | flag | Explain primary shard | `--primary` |
| `--format` | choice | Output format (table, json) | `--format json` |

**Explanation Information:**
- **Current Allocation**: Where the shard is currently allocated
- **Allocation Decisions**: Why shard is placed on specific nodes
- **Failed Allocations**: Nodes that cannot accept the shard and why
- **Allocation Constraints**: Rules preventing allocation to certain nodes
- **Resource Constraints**: Disk space, memory, or other resource limits
- **Shard Routing**: Allocation awareness and routing preferences

**Common Allocation Issues:**
- **Disk Space**: Insufficient disk space on available nodes
- **Allocation Rules**: Custom allocation rules preventing placement
- **Node Attributes**: Missing or incompatible node attributes
- **Shard Size**: Shard too large for available nodes
- **Exclusions**: Nodes excluded from allocation
- **Throttling**: Allocation throttled due to cluster settings

### Troubleshooting Workflow

```bash
# 1. Identify unassigned shards
./escmd.py health  # Look for unassigned shards in cluster health

# 2. Find problematic indices
./escmd.py indices --status red    # Find red (problematic) indices

# 3. Explain allocation for problematic index
./escmd.py allocation explain problematic-index

# 4. Check allocation settings
./escmd.py allocation display

# 5. Investigate specific issues based on explanation
# - Check disk space: ./escmd.py storage
# - Check excluded nodes: ./escmd.py allocation display
# - Check node status: ./escmd.py nodes

# 6. Take corrective action
# - Remove exclusions if needed
# - Enable allocation if disabled
# - Free up disk space
# - Adjust allocation rules
```

## Advanced Allocation Management

### Allocation Awareness

Configure allocation awareness for better shard distribution:

```bash
# Check current allocation awareness (via cluster settings)
./escmd.py allocation display

# Allocation awareness is typically configured at the cluster level
# Example awareness attributes: rack, zone, region
```

### Performance Considerations

**Allocation Performance:**
- **Throttling**: Allocation operations are throttled to prevent cluster overload
- **Concurrent Recoveries**: Limited number of concurrent shard recoveries
- **Network Impact**: Shard movement consumes network bandwidth
- **Disk I/O**: Recovery operations increase disk I/O on target nodes

**Best Practices:**
- **Monitor During Changes**: Watch cluster performance during allocation changes
- **Gradual Changes**: Make allocation changes gradually
- **Off-Peak Operations**: Schedule allocation changes during low-traffic periods
- **Resource Planning**: Ensure adequate resources for shard movement

### Integration with Other Commands

Allocation management works closely with other escmd commands:

```bash
# Monitor allocation impact
./escmd.py health              # Overall cluster health
./escmd.py recovery            # Active recovery operations
./escmd.py shards --server ess46  # Shards on specific server

# Troubleshoot allocation issues
./escmd.py storage             # Check disk space
./escmd.py nodes               # Check node status
./escmd.py cluster-check       # Comprehensive health check
```

## Command Reference

### Main Command Options

| Command | Description | Options |
|---------|-------------|---------|
| `allocation` | Show allocation settings | `--format` |
| `allocation display` | Explicit display command | `--format` |
| `allocation enable` | Enable shard allocation | `--format` |
| `allocation disable` | Disable shard allocation | `--format` |

### Exclusion Commands

| Command | Description | Options |
|---------|-------------|---------|
| `allocation exclude add <hostname>` | Add node to exclusion list | `--format` |
| `allocation exclude remove <hostname>` | Remove node from exclusions | `--format` |
| `allocation exclude reset` | Clear all exclusions | `--format` |

### Explain Commands

| Command | Description | Options |
|---------|-------------|---------|
| `allocation explain <index>` | Explain allocation decisions | `--shard`, `--primary`, `--format` |

### Output Formats

All allocation commands support JSON output for automation:

```bash
./escmd.py allocation --format json
./escmd.py allocation enable --format json
./escmd.py allocation exclude add ess46 --format json
./escmd.py allocation explain my-index --format json
```

## Best Practices

### Operational Guidelines

1. **Monitor Before Changes**: Always check cluster health before allocation changes
2. **Use Dry-Run Mentality**: Understand impact before making changes
3. **Document Changes**: Keep records of allocation changes and reasons
4. **Coordinate with Team**: Communicate allocation changes with operations team
5. **Have Rollback Plan**: Know how to reverse allocation changes

### Emergency Procedures

**Unassigned Shards:**
1. Use `allocation explain` to understand why shards aren't assigned
2. Check for disabled allocation or excluded nodes
3. Verify adequate resources (disk space, memory)
4. Consider temporarily relaxing allocation rules

**Cluster Overload:**
1. Disable allocation temporarily to stop shard movement
2. Identify and resolve resource constraints
3. Re-enable allocation gradually
4. Monitor cluster performance during recovery

**Node Decommissioning:**
1. Exclude node from allocation
2. Wait for all shards to move off the node
3. Verify no data remains on the node
4. Safely remove node from cluster
5. Clean up exclusions

## Related Commands

- [`health`](health-monitoring.md) - Monitor cluster health and allocation status
- [`recovery`](maintenance-operations.md) - Monitor shard recovery operations
- [`shards`](index-operations.md) - View shard distribution and status
- [`storage`](maintenance-operations.md) - Check disk space and storage
- [`nodes`](maintenance-operations.md) - View node status and information
