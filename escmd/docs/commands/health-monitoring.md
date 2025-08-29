# Health Monitoring & Cluster Operations

Comprehensive cluster health monitoring with multiple display styles and comparison capabilities.

## Quick Reference

```bash
# Basic health monitoring
./escmd.py health                    # Dashboard view (default)
./escmd.py -l production health      # Specific cluster health  
./escmd.py health --quick            # Fast response mode

# Advanced health features
./escmd.py health --compare staging  # Compare two clusters
./escmd.py health --group production # Monitor cluster groups
./escmd.py health --format json     # JSON output for automation
```

## Health Command Overview

The health command offers comprehensive cluster monitoring with multiple display styles optimized for different use cases.

### Display Styles

#### ⚡ Quick Mode (`-q/--quick`)
- **Fast Response**: Only performs basic cluster health API call (~1-2 seconds)
- **Core Metrics Only**: Cluster name, status, nodes, shards, unassigned shards
- **Skip Diagnostics**: Bypasses recovery status, allocation issues, node details, snapshots
- **Minimal Output**: Clean, focused display of essential health information
- **Perfect for Monitoring**: Ideal for scripts, automation, or when you need quick status checks

```bash
./escmd.py health --quick
./escmd.py -l production health -q
./escmd.py health --format json -q   # Quick mode with JSON output
```

#### 📊 Dashboard Style (Default)
**6-Panel Visual Dashboard**: Comprehensive cluster health overview with additional diagnostics
- **📋 Cluster Overview**: Cluster name, current master node, total/data nodes, shard health progress
- **🖥️ Node Information**: Complete node breakdown (total, data, master, client nodes) with data ratio
- **🔄 Shard Status**: Primary/replica counts, shards per data node, unassigned status
- **⚡ Performance**: Pending tasks, in-flight operations, recovery jobs, delayed shards with status indicators
- **📦 Snapshots**: Repository status, backup counts (total/successful/failed), overall backup health
- **⚖️ Allocation Issues**: Automatic detection and display of unassigned shards with allocation explanations

```bash
./escmd.py health                    # Default dashboard
./escmd.py -l cluster health         # Specific cluster dashboard
```

**Dashboard Features:**
- **Visual Status Indicators**: Color-coded panels (🟢 green = healthy, 🟡 yellow = warning, 🔴 red = critical)
- **Rich Formatting**: Professional layout with bordered panels and organized information
- **Comprehensive Metrics**: All key cluster health indicators in a single view
- **Automatic Diagnostics**: Built-in detection of common issues with actionable information

#### 🔧 Classic Style
Traditional table-based display with two sub-styles:

**Panel Style:**
```bash
./escmd.py health --classic          # Classic panel view
```

**Table Style:**
```bash
./escmd.py health --classic --table  # Classic table view
```

### Advanced Features

#### 📊 Cluster Comparison
Compare two clusters side-by-side with real-time metrics:

```bash
# Compare current cluster with another
./escmd.py -l production health --compare staging

# Compare any two clusters
./escmd.py -l cluster1 health --compare cluster2
```

**Comparison Features:**
- **Side-by-Side Layout**: Clusters displayed in parallel columns for easy comparison
- **Metric Alignment**: Identical metrics positioned for direct comparison
- **Status Highlighting**: Visual indicators show which cluster has issues
- **Comprehensive Coverage**: All dashboard metrics included in comparison view
- **Automatic Layout**: Tables positioned side-by-side with minimal spacing for easy comparison

#### 🏢 Group Monitoring
Monitor multiple clusters simultaneously in a grid layout:

```bash
# Monitor cluster groups
./escmd.py health --group production    # All 'production' clusters
./escmd.py health --group staging       # All 'staging' clusters
./escmd.py health --group att           # All 'att' clusters
```

**Group Features:**
- **Multi-Cluster Monitoring**: Monitor 2-3+ clusters simultaneously in a grid layout
- **Logical Organization**: Group clusters by environment (att, production, staging)
- **Quick Overview**: Rapid assessment of cluster health across an entire environment
- **Scalable Display**: Adapts to different numbers of clusters in the group

## Command Options

The health command supports extensive customization options:

| Option | Type | Description | Example |
|--------|------|-------------|---------|
| `--format` | choice | Output format (table, json) | `--format json` |
| `--style` | choice | Display style (dashboard, classic) | `--style classic` |
| `--classic-style` | choice | Classic format (table, panel) | `--classic-style table` |
| `--compare` | string | Compare with another cluster | `--compare staging` |
| `--group` | string | Show group of clusters | `--group production` |
| `-q`/`--quick` | flag | Quick mode - basic health only | `--quick` |

### Advanced Usage Examples

```bash
# Style customization
./escmd.py health --style dashboard      # Force dashboard style
./escmd.py health --style classic        # Force classic style
./escmd.py health --classic-style table  # Classic with table format
./escmd.py health --classic-style panel  # Classic with panel format

# Output format control
./escmd.py health --format json          # JSON output for scripts
./escmd.py health --format table         # Rich table format (default)

# Cluster operations
./escmd.py -l prod1 health --compare prod2       # Compare two production clusters
./escmd.py health --group staging               # All staging clusters
./escmd.py health --group production --format json  # Group JSON output

# Quick monitoring
./escmd.py health --quick                # Fast basic health
./escmd.py health -q --format json       # Quick mode with JSON
./escmd.py -l slow-cluster health --quick  # Quick mode for slow clusters

# Combined options
./escmd.py health --style classic --classic-style table --format json
./escmd.py health --compare staging --format json
```

### Configuration

#### Global Health Style
Set default health display style in `elastic_servers.yml`:

```yaml
settings:
  health_style: dashboard  # Options: dashboard, classic
  classic_style: panel     # Options: panel, table (when health_style is classic)
```

#### Per-Cluster Configuration
Override health style for specific clusters:

```yaml
servers:
  - name: production
    hostname: prod-es-01.company.com
    health_style: classic  # This cluster uses classic style
    # ... other settings
```

### Output Formats

#### Table Format (Default)
Rich formatted output with colors, panels, and visual indicators.

#### JSON Format
Machine-readable output for automation and monitoring systems:

```bash
./escmd.py health --format json
./escmd.py health --compare staging --format json
./escmd.py health --group production --format json
```

**JSON Structure:**
```json
{
  "cluster_name": "production-cluster",
  "status": "green",
  "nodes": {
    "total": 6,
    "data": 3,
    "master": 3
  },
  "shards": {
    "active_primary": 150,
    "active": 300,
    "unassigned": 0
  },
  "performance": {
    "pending_tasks": 0,
    "in_flight_fetch": 0
  }
}
```

## Troubleshooting

### Common Issues

#### Slow Health Checks
- **Use Quick Mode**: Add `--quick` flag for faster response
- **Check Network**: Verify connectivity to Elasticsearch cluster
- **Reduce Diagnostics**: Quick mode skips time-consuming diagnostic checks

#### Connection Errors
- **Verify Configuration**: Check `elastic_servers.yml` settings
- **Test Connectivity**: Use `./escmd.py ping` to test basic connectivity
- **Check Authentication**: Verify credentials and permissions

#### Missing Metrics
- **Insufficient Permissions**: Some metrics require elevated privileges
- **Elasticsearch Version**: Some features require newer Elasticsearch versions
- **API Availability**: Ensure required APIs are enabled and accessible

### Best Practices

1. **Use Quick Mode for Monitoring**: Regular automated checks should use `--quick`
2. **Dashboard for Investigation**: Use full dashboard when investigating issues
3. **Group Monitoring**: Monitor related clusters together with `--group`
4. **JSON for Automation**: Use `--format json` for scripts and monitoring systems
5. **Comparison for Changes**: Use `--compare` when validating changes between environments

## Related Commands

- [`cluster-check`](health-monitoring.md) - Comprehensive health checks with issue detection
- [`ping`](cluster-operations.md) - Basic connectivity testing
- [`allocation`](allocation-management.md) - Shard allocation troubleshooting
- [`recovery`](maintenance-operations.md) - Recovery status monitoring
