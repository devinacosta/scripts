# Snapshot Management

Comprehensive snapshot management with repository monitoring, snapshot listing, and status tracking.

## Quick Reference

```bash
# List snapshots
./escmd.py snapshots list                    # List all snapshots
./escmd.py snapshots list "backup-*"         # Filter by pattern
./escmd.py snapshots list --format json      # JSON output

# Snapshot status
./escmd.py snapshots status my-snapshot      # Get snapshot status
./escmd.py snapshots status backup-2024-01-01 --format json  # JSON status
```

## Overview

Snapshot management provides comprehensive monitoring and analysis of Elasticsearch snapshots. This includes listing snapshots from configured repositories, checking snapshot status, and analyzing backup health across your cluster.

## Core Snapshot Commands

### 📋 List Snapshots

View all snapshots from your configured repository with filtering capabilities:

```bash
# Basic snapshot listing
./escmd.py snapshots list                    # All snapshots from default repository
./escmd.py snapshots list --format json      # JSON output for automation

# Pattern-based filtering
./escmd.py snapshots list "backup-*"         # Snapshots matching pattern
./escmd.py snapshots list ".*2024.*"         # Snapshots containing "2024"
./escmd.py snapshots list "daily-.*"         # Daily backup snapshots
./escmd.py snapshots list "monthly-.*"       # Monthly backup snapshots

# Large output handling
./escmd.py snapshots list --pager            # Force pager for scrolling
./escmd.py snapshots list "backup-*" --pager # Pattern with pager
```

**Command Options:**

| Option | Type | Description | Example |
|--------|------|-------------|---------|
| `pattern` | string | Regex pattern to filter snapshots | `"backup-*"` |
| `--format` | choice | Output format (table, json) | `--format json` |
| `--pager` | flag | Force pager for large outputs | `--pager` |

**Snapshot Information Displayed:**
- **Snapshot Name**: Full snapshot identifier
- **Status**: SUCCESS, FAILED, IN_PROGRESS, PARTIAL
- **Start Time**: When the snapshot operation began
- **End Time**: When the snapshot operation completed
- **Duration**: Total time taken for the snapshot
- **Indices**: Number of indices included in snapshot
- **Shards**: Total number of shards backed up
- **Size**: Total size of the snapshot data
- **Failures**: Any failures encountered during snapshot

### 📊 Snapshot Status

Get detailed status information for specific snapshots:

```bash
# Basic status check
./escmd.py snapshots status my-snapshot       # Basic status information
./escmd.py snapshots status backup-2024-01-01 # Specific snapshot status

# Detailed status with JSON
./escmd.py snapshots status my-snapshot --format json  # Detailed JSON status

# Custom repository
./escmd.py snapshots status my-snapshot --repository custom-repo  # Specific repository
```

**Command Options:**

| Option | Type | Description | Example |
|--------|------|-------------|---------|
| `snapshot_name` | string | Name of snapshot to check | `backup-2024-01-01` |
| `--format` | choice | Output format (table, json) | `--format json` |
| `--repository` | string | Snapshot repository name | `--repository custom-repo` |

**Status Information Includes:**
- **Overall Status**: SUCCESS, FAILED, IN_PROGRESS, PARTIAL
- **Progress Information**: Percentage complete for in-progress snapshots
- **Shard Details**: Per-shard status and progress
- **Index Breakdown**: Status of each index in the snapshot
- **Error Information**: Detailed error messages for failed snapshots
- **Performance Metrics**: Throughput and timing information
- **Resource Usage**: Storage and network utilization

### Snapshot Analysis Features

**Status Indicators:**
- ✅ **SUCCESS**: Snapshot completed successfully
- ❌ **FAILED**: Snapshot failed completely
- 🔄 **IN_PROGRESS**: Snapshot currently running
- ⚠️ **PARTIAL**: Some shards failed but snapshot partially completed

**Rich Display Features:**
- **Color-coded Status**: Visual indicators for snapshot health
- **Progress Bars**: Real-time progress for active snapshots
- **Time Formatting**: Human-readable duration and timestamp display
- **Size Formatting**: Readable size information (GB, TB, etc.)
- **Error Highlighting**: Clear display of errors and failures

## Repository Configuration

Snapshots are managed through repositories configured in your `elastic_servers.yml`:

```yaml
servers:
  - name: production
    hostname: prod-es.company.com
    port: 9200
    use_ssl: true
    verify_certs: true
    elastic_authentication: true
    elastic_username: kibana_system
    elastic_password: password
    elastic_s3snapshot_repo: "production-snapshots"  # Default repository
```

**Repository Types Supported:**
- **S3 Repositories**: AWS S3 bucket storage
- **File System Repositories**: Local or network file system
- **Azure Repositories**: Azure Blob Storage
- **GCS Repositories**: Google Cloud Storage
- **HDFS Repositories**: Hadoop Distributed File System

## Snapshot Monitoring Workflows

### Daily Snapshot Monitoring

```bash
# 1. Check recent snapshots
./escmd.py snapshots list --pager

# 2. Look for recent failures
./escmd.py snapshots list ".*$(date +%Y-%m).*"  # Current month snapshots

# 3. Check specific failed snapshots
./escmd.py snapshots status failed-snapshot-name

# 4. Export snapshot data for analysis
./escmd.py snapshots list --format json > daily-snapshot-report-$(date +%Y%m%d).json
```

### Snapshot Health Assessment

```bash
# 1. List all snapshots to get overview
./escmd.py snapshots list

# 2. Check status of recent snapshots
./escmd.py snapshots status latest-backup
./escmd.py snapshots status $(date +backup-%Y-%m-%d)

# 3. Look for patterns in failures
./escmd.py snapshots list "backup-*" --format json | jq '.[] | select(.status == "FAILED")'

# 4. Verify backup coverage
./escmd.py snapshots list --format json | jq 'group_by(.status) | map({status: .[0].status, count: length})'
```

### Backup Validation Workflow

```bash
# 1. Check latest snapshot status
LATEST_SNAPSHOT=$(./escmd.py snapshots list --format json | jq -r '.[0].name')
./escmd.py snapshots status $LATEST_SNAPSHOT

# 2. Verify snapshot completeness
./escmd.py snapshots status $LATEST_SNAPSHOT --format json | jq '.shards'

# 3. Check for any partial failures
./escmd.py snapshots status $LATEST_SNAPSHOT --format json | jq '.failures'

# 4. Cross-reference with cluster health
./escmd.py health
./escmd.py cluster-check
```

## Advanced Snapshot Operations

### Pattern-Based Analysis

```bash
# Analyze backup patterns
./escmd.py snapshots list "daily-*"     # Daily backups
./escmd.py snapshots list "weekly-*"    # Weekly backups
./escmd.py snapshots list "monthly-*"   # Monthly backups

# Date-based analysis
./escmd.py snapshots list ".*2024-01.*" # January 2024 snapshots
./escmd.py snapshots list ".*$(date +%Y).*"  # Current year snapshots

# Environment-specific snapshots
./escmd.py snapshots list "prod-*"      # Production snapshots
./escmd.py snapshots list "staging-*"   # Staging snapshots
```

### Performance Analysis

```bash
# Check snapshot performance trends
./escmd.py snapshots list --format json | jq '.[] | {name: .name, duration: .duration, size: .size}'

# Identify slow snapshots
./escmd.py snapshots list --format json | jq '.[] | select(.duration > "1h")'

# Size analysis
./escmd.py snapshots list --format json | jq 'sort_by(.size) | reverse | .[0:10]'  # Largest snapshots
```

### Failure Analysis

```bash
# Find all failed snapshots
./escmd.py snapshots list --format json | jq '.[] | select(.status == "FAILED")'

# Get detailed failure information
./escmd.py snapshots status failed-snapshot-name --format json | jq '.failures'

# Pattern analysis of failures
./escmd.py snapshots list --format json | jq '[.[] | select(.status == "FAILED")] | group_by(.failure_reason) | map({reason: .[0].failure_reason, count: length})'
```

## Integration with Cluster Health

Snapshot management integrates with escmd's cluster health monitoring:

```bash
# Health dashboard includes snapshot status
./escmd.py health  # Shows backup health in dashboard

# Comprehensive health check
./escmd.py cluster-check  # May include snapshot-related health checks

# Combined monitoring
./escmd.py health && ./escmd.py snapshots list | head -10
```

**Health Integration Features:**
- **Backup Status Panel**: Shows repository health and backup status
- **Recent Backup Tracking**: Displays information about recent backup operations
- **Failure Alerting**: Highlights backup failures in cluster health
- **Repository Connectivity**: Monitors connection to snapshot repositories

## Automation and Monitoring

### Automated Snapshot Monitoring

```bash
#!/bin/bash
# snapshot-monitor.sh - Daily snapshot monitoring script

CLUSTER="production"
DATE=$(date +%Y-%m-%d)
REPORT_FILE="/var/log/snapshot-report-$DATE.json"

echo "Checking snapshots for cluster: $CLUSTER"

# Get snapshot list
./escmd.py -l $CLUSTER snapshots list --format json > "$REPORT_FILE"

# Check for failures
FAILED_COUNT=$(jq '[.[] | select(.status == "FAILED")] | length' "$REPORT_FILE")

if [ "$FAILED_COUNT" -gt 0 ]; then
    echo "ALERT: $FAILED_COUNT failed snapshots found"
    # Send alert to monitoring system
    curl -X POST "http://monitoring-system/alert" \
         -d "cluster=$CLUSTER&type=snapshot_failures&count=$FAILED_COUNT"
fi

# Check latest snapshot
LATEST_SNAPSHOT=$(jq -r '.[0].name' "$REPORT_FILE")
echo "Latest snapshot: $LATEST_SNAPSHOT"

./escmd.py -l $CLUSTER snapshots status "$LATEST_SNAPSHOT"
```

### Snapshot Metrics Collection

```bash
# Collect snapshot metrics for monitoring
./escmd.py snapshots list --format json | jq '{
  total_snapshots: length,
  successful: [.[] | select(.status == "SUCCESS")] | length,
  failed: [.[] | select(.status == "FAILED")] | length,
  in_progress: [.[] | select(.status == "IN_PROGRESS")] | length,
  latest_snapshot: .[0].name,
  latest_status: .[0].status,
  total_size: [.[] | .size] | add
}'
```

## Best Practices

### Monitoring Guidelines

1. **Regular Monitoring**: Check snapshot status daily
2. **Failure Investigation**: Investigate failures immediately
3. **Trend Analysis**: Monitor backup size and duration trends
4. **Retention Validation**: Verify snapshots are being retained properly
5. **Repository Health**: Monitor repository connectivity and capacity

### Performance Optimization

1. **Timing**: Schedule snapshots during low-traffic periods
2. **Incremental Backups**: Use incremental snapshots when possible
3. **Repository Performance**: Ensure repository has adequate performance
4. **Parallel Snapshots**: Avoid overlapping snapshot operations
5. **Resource Monitoring**: Monitor cluster resources during snapshots

### Operational Procedures

1. **Backup Validation**: Regularly test snapshot restoration
2. **Retention Management**: Implement proper snapshot retention policies
3. **Disaster Recovery**: Document snapshot-based recovery procedures
4. **Monitoring Integration**: Integrate with existing monitoring systems
5. **Alert Configuration**: Set up alerts for snapshot failures

## Troubleshooting

### Common Issues

**Repository Connection Issues:**
- Verify repository configuration in cluster settings
- Check network connectivity to repository
- Validate authentication and permissions

**Snapshot Failures:**
- Check cluster health during snapshot operations
- Verify adequate disk space and resources
- Review Elasticsearch logs for detailed error information

**Performance Issues:**
- Monitor cluster performance during snapshots
- Check repository performance and bandwidth
- Consider snapshot timing and frequency

**Status Command Issues:**
- Verify snapshot name spelling and existence
- Check repository accessibility
- Ensure proper permissions for snapshot operations

## Related Commands

- [`health`](health-monitoring.md) - Includes snapshot status in cluster health dashboard
- [`cluster-check`](cluster-check.md) - May include snapshot-related health checks
- [`storage`](maintenance-operations.md) - Monitor storage usage and capacity
- [`recovery`](maintenance-operations.md) - Monitor recovery operations during restore
