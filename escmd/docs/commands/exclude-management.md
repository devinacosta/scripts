# Exclude Management Commands

The ESCMD tool provides two different types of exclusion commands for managing shard allocation in Elasticsearch clusters:

1. **Index-level exclusion** - Exclude specific indices from specific hosts
2. **Cluster-level exclusion** - Exclude entire nodes from all allocations

## Index-Level Exclusion Commands

### `exclude` Command
Excludes a specific index from being allocated on a specific host.

**Syntax:**
```bash
./escmd.py exclude <index-name> --server <hostname>
./escmd.py exclude <index-name> -s <hostname>
```

**Parameters:**
- `<index-name>` - The name of the index to exclude (required)
- `--server` or `-s` - The hostname to exclude the index from (required)

**Examples:**
```bash
# Exclude a specific log index from node-1
./escmd.py exclude .ds-aex10-c01-logs-ueb-main-2025.04.03-000732 --server aex10-c01-ess01-1

# Exclude using short form
./escmd.py exclude my-index-001 -s node-2
```

**What it does:**
- Sets the Elasticsearch index setting `index.routing.allocation.exclude._name` for the specified index
- Causes Elasticsearch to move shards of that index away from the specified host
- Only affects the specified index, other indices remain unaffected
- The exclusion persists until manually removed

**Use cases:**
- Host has issues affecting only specific indices
- Need to move specific index away from a problematic node
- Targeted maintenance that only affects certain data

### `exclude-reset` Command
Removes exclusion settings for a specific index, allowing it to allocate on previously excluded hosts.

**Syntax:**
```bash
./escmd.py exclude-reset <index-name>
```

**Parameters:**
- `<index-name>` - The name of the index to reset exclusions for (required)

**Examples:**
```bash
# Reset exclusions for a specific index
./escmd.py exclude-reset .ds-aex10-c01-logs-ueb-main-2025.04.03-000732

# Allow index to allocate anywhere again
./escmd.py exclude-reset my-index-001
```

**What it does:**
- Removes the `index.routing.allocation.exclude._name` setting from the index
- Allows the index to allocate on any available node in the cluster
- Does not force immediate reallocation, but allows it to happen naturally

## Cluster-Level Exclusion Commands

### `allocation exclude add` Command
Excludes an entire node from receiving any shard allocations cluster-wide.

**Syntax:**
```bash
./escmd.py allocation exclude add <hostname>
```

**Parameters:**
- `<hostname>` - The hostname of the node to exclude (required)

**Examples:**
```bash
# Exclude entire node from all allocations
./escmd.py allocation exclude add node-1

# Exclude a specific server
./escmd.py allocation exclude add aex10-c01-ess01-1
```

**What it does:**
- Sets the cluster setting `cluster.routing.allocation.exclude._name`
- Prevents ALL indices from allocating shards on the excluded node
- Causes Elasticsearch to move existing shards away from the node
- Affects the entire cluster and all indices

**Use cases:**
- Node maintenance or decommissioning
- Hardware issues affecting the entire node
- Planned node removal from cluster

### `allocation exclude remove` Command
Removes a node from the cluster-wide exclusion list.

**Syntax:**
```bash
./escmd.py allocation exclude remove <hostname>
```

**Parameters:**
- `<hostname>` - The hostname to remove from exclusions (required)

**Examples:**
```bash
# Remove node from exclusion list
./escmd.py allocation exclude remove node-1

# Allow server to receive allocations again
./escmd.py allocation exclude remove aex10-c01-ess01-1
```

**What it does:**
- Removes the specified hostname from `cluster.routing.allocation.exclude._name`
- Allows the node to receive shard allocations again
- Does not force immediate allocation, but allows it to happen

### `allocation exclude reset` Command
**⚠️ DANGER: This command resets ALL cluster-level exclusions**

**Syntax:**
```bash
./escmd.py allocation exclude reset                    # Safe mode - requires confirmation
./escmd.py allocation exclude reset --yes-i-really-mean-it  # Bypass confirmation
```

**What it does:**
- Completely removes the `cluster.routing.allocation.exclude._name` setting
- Allows ALL previously excluded nodes to receive allocations
- Requires typing "RESET" to confirm (unless bypass flag is used)

**⚠️ WARNING:** Use this command with extreme caution. It will remove ALL node exclusions at once.

## Technical Details

### Elasticsearch Settings Used

**Index-level exclusions:**
- Setting: `index.routing.allocation.exclude._name`
- Scope: Single index
- Effect: Prevents specified index from allocating on excluded hosts

**Cluster-level exclusions:**
- Setting: `cluster.routing.allocation.exclude._name`
- Scope: Entire cluster
- Effect: Prevents ALL indices from allocating on excluded hosts

### How Exclusions Work

1. **Immediate Effect**: When an exclusion is set, Elasticsearch immediately begins moving shards away from excluded hosts
2. **Persistence**: Exclusions persist across cluster restarts until manually removed
3. **Priority**: Cluster-level exclusions take precedence over index-level settings
4. **Safety**: Elasticsearch ensures replica shards exist elsewhere before moving primary shards

### Monitoring Exclusions

To see current exclusion settings:
```bash
# View cluster allocation settings
./escmd.py allocation display

# View specific index settings (use Elasticsearch API directly)
curl -X GET "localhost:9200/my-index/_settings?include_defaults=false&pretty"
```

## Best Practices

### Choosing the Right Command

| Scenario | Recommended Command | Reason |
|----------|-------------------|---------|
| Single index issues | `exclude` | Minimal impact, targeted approach |
| Node maintenance | `allocation exclude add` | Comprehensive, affects all data |
| Node decommissioning | `allocation exclude add` | Ensures complete data migration |
| Temporary node issues | `allocation exclude add` | Can be easily reversed |
| Index-specific problems | `exclude` | Surgical precision, other data unaffected |

### Safety Guidelines

1. **Always have replicas**: Ensure your indices have replicas before excluding nodes
2. **Monitor cluster health**: Watch cluster status during exclusion operations
3. **Plan for capacity**: Ensure remaining nodes can handle the load
4. **Document exclusions**: Keep track of what's excluded and why
5. **Clean up**: Remove exclusions when no longer needed

### Recovery Procedures

**For index-level exclusions:**
```bash
# Check if exclusion exists
./escmd.py indices <index-name> | grep exclude

# Remove exclusion
./escmd.py exclude-reset <index-name>
```

**For cluster-level exclusions:**
```bash
# Check current exclusions
./escmd.py allocation display

# Remove specific node
./escmd.py allocation exclude remove <hostname>

# Or reset all (DANGER)
./escmd.py allocation exclude reset
```

## Troubleshooting

### Common Issues

1. **Shards stuck in RELOCATING**: Check cluster capacity and health
2. **Cannot exclude**: Verify node names match exactly
3. **Exclusion not working**: Check for typos in index/node names
4. **Performance impact**: Monitor cluster during large shard movements

### Getting Help

```bash
# General help
./escmd.py help exclude

# Command-specific help
./escmd.py exclude --help
./escmd.py allocation exclude --help
```

## Examples and Workflows

### Scenario 1: Node Maintenance
```bash
# 1. Exclude node from all allocations
./escmd.py allocation exclude add maintenance-node-1

# 2. Wait for shards to relocate (monitor with)
./escmd.py health

# 3. Perform maintenance

# 4. Remove exclusion when done
./escmd.py allocation exclude remove maintenance-node-1
```

### Scenario 2: Problematic Index
```bash
# 1. Exclude specific index from problematic host
./escmd.py exclude problem-index-2025.04.03 --server problematic-host

# 2. Monitor shard movement
./escmd.py indices problem-index-2025.04.03

# 3. Fix host issues

# 4. Reset exclusion
./escmd.py exclude-reset problem-index-2025.04.03
```

### Scenario 3: Emergency Recovery
```bash
# If you need to reset all exclusions quickly (EMERGENCY ONLY)
./escmd.py allocation exclude reset --yes-i-really-mean-it
```

---

**Remember**: Exclusions are powerful tools that immediately affect cluster behavior. Always monitor cluster health and ensure you have adequate replicas before making exclusion changes.
