# Monitoring Workflows

Comprehensive workflows for daily operations, maintenance, and troubleshooting using escmd.

## Daily Monitoring Workflows

### Morning Health Check Routine

**Objective**: Quick assessment of all critical clusters before business hours.

```bash
# 1. Check overall cluster health across environments
./escmd.py health --group production
./escmd.py health --group staging

# 2. Run comprehensive health checks on critical clusters
./escmd.py -l prod-primary cluster-check
./escmd.py -l prod-analytics cluster-check

# 3. Quick ILM status check
./escmd.py -l prod-primary ilm status
./escmd.py -l prod-primary ilm errors

# 4. Check for any dangling indices
./escmd.py -l prod-primary dangling
```

**Expected Time**: 5-10 minutes
**Escalation**: Any red status or errors require immediate investigation

### Continuous Monitoring Script

For automated monitoring integration:

```bash
#!/bin/bash
# daily-cluster-check.sh

CLUSTERS=("prod-primary" "prod-analytics" "prod-logs")
ALERT_THRESHOLD_ERRORS=5
LOG_FILE="/var/log/escmd-monitoring.log"

echo "$(date): Starting daily cluster health checks" >> $LOG_FILE

for cluster in "${CLUSTERS[@]}"; do
    echo "Checking cluster: $cluster" >> $LOG_FILE
    
    # Health check with JSON output for parsing
    HEALTH_STATUS=$(./escmd.py -l $cluster health --quick --format json)
    STATUS=$(echo $HEALTH_STATUS | jq -r '.status')
    
    if [ "$STATUS" != "green" ]; then
        echo "ALERT: Cluster $cluster status is $STATUS" >> $LOG_FILE
        # Send alert to monitoring system
        curl -X POST "http://monitoring-system/alert" \
             -d "cluster=$cluster&status=$STATUS"
    fi
    
    # Check for ILM errors
    ILM_ERRORS=$(./escmd.py -l $cluster cluster-check --format json | jq '.checks.ilm_results.error_count // 0')
    
    if [ "$ILM_ERRORS" -gt "$ALERT_THRESHOLD_ERRORS" ]; then
        echo "ALERT: Cluster $cluster has $ILM_ERRORS ILM errors" >> $LOG_FILE
        # Send ILM alert
        curl -X POST "http://monitoring-system/alert" \
             -d "cluster=$cluster&type=ilm_errors&count=$ILM_ERRORS"
    fi
done

echo "$(date): Daily cluster health checks completed" >> $LOG_FILE
```

## Weekly Maintenance Workflows

### Comprehensive Cluster Assessment

**Objective**: Deep analysis of cluster health, performance, and optimization opportunities.

```bash
# 1. Comprehensive health assessment with details
./escmd.py -l production cluster-check --show-details > weekly-health-$(date +%Y%m%d).txt

# 2. Detailed ILM analysis
./escmd.py -l production ilm status --format json > ilm-status-$(date +%Y%m%d).json
./escmd.py -l production ilm policies > ilm-policies-$(date +%Y%m%d).txt

# 3. Index analysis and optimization opportunities
./escmd.py -l production indices > indices-$(date +%Y%m%d).txt
./escmd.py -l production shards > shards-$(date +%Y%m%d).txt

# 4. Shard colocation analysis
./escmd.py -l production shard-colocation > colocation-$(date +%Y%m%d).txt

# 5. Storage and capacity analysis
./escmd.py -l production storage > storage-$(date +%Y%m%d).txt
```

### Index Lifecycle Review

**Objective**: Review and optimize index lifecycle management policies.

```bash
# 1. Review ILM policy effectiveness
./escmd.py -l production ilm policies

# 2. Identify problematic policies
./escmd.py -l production ilm errors

# 3. Analyze policy usage patterns
for policy in $(./escmd.py -l production ilm policies --format json | jq -r '.policies[].name'); do
    echo "Analyzing policy: $policy"
    ./escmd.py -l production ilm policy $policy --show-all
done

# 4. Check for unmanaged indices
./escmd.py -l production cluster-check --format json | jq '.checks.ilm_results.no_policy[]'
```

## Incident Response Workflows

### Cluster Health Degradation

**Triggered by**: Yellow or red cluster status, high unassigned shards, or performance issues.

```bash
# 1. Immediate assessment
./escmd.py -l affected-cluster health --show-details

# 2. Identify specific issues
./escmd.py -l affected-cluster cluster-check --show-details

# 3. Check allocation issues
./escmd.py -l affected-cluster allocation explain

# 4. Review recent recovery operations
./escmd.py -l affected-cluster recovery

# 5. Check node status
./escmd.py -l affected-cluster nodes

# 6. Export detailed information for analysis
./escmd.py -l affected-cluster health --format json > incident-health-$(date +%Y%m%d-%H%M).json
./escmd.py -l affected-cluster cluster-check --format json > incident-details-$(date +%Y%m%d-%H%M).json
```

### ILM Failure Investigation

**Triggered by**: High number of ILM errors or stuck indices.

```bash
# 1. Identify error scope
./escmd.py -l affected-cluster ilm errors

# 2. Analyze specific failing indices
for index in $(./escmd.py -l affected-cluster ilm errors --format json | jq -r '.[].index'); do
    echo "Investigating index: $index"
    ./escmd.py -l affected-cluster ilm explain $index
done

# 3. Review policy configuration
FAILING_POLICIES=$(./escmd.py -l affected-cluster ilm errors --format json | jq -r '.[].policy' | sort -u)
for policy in $FAILING_POLICIES; do
    echo "Reviewing policy: $policy"
    ./escmd.py -l affected-cluster ilm policy $policy
done

# 4. Check cluster resources and allocation
./escmd.py -l affected-cluster allocation explain
./escmd.py -l affected-cluster storage
```

### Replica Count Issues

**Triggered by**: Discovery of indices with 0 replicas or replica imbalance.

```bash
# 1. Assess replica situation
./escmd.py -l affected-cluster cluster-check

# 2. Plan replica fixes
./escmd.py -l affected-cluster cluster-check --fix-replicas 1 --dry-run

# 3. Execute fixes with confirmation
./escmd.py -l affected-cluster cluster-check --fix-replicas 1

# 4. Verify fixes
./escmd.py -l affected-cluster cluster-check

# 5. For complex scenarios, use standalone replica management
./escmd.py -l affected-cluster set-replicas --pattern "critical-*" --count 2 --dry-run
./escmd.py -l affected-cluster set-replicas --pattern "critical-*" --count 2
```

## Maintenance Workflows

### Pre-Maintenance Preparation

**Objective**: Prepare cluster for planned maintenance activities.

```bash
# 1. Document current state
./escmd.py -l target-cluster health > pre-maintenance-health-$(date +%Y%m%d).txt
./escmd.py -l target-cluster cluster-check > pre-maintenance-check-$(date +%Y%m%d).txt

# 2. Ensure data redundancy
./escmd.py -l target-cluster cluster-check --fix-replicas 1 --dry-run
./escmd.py -l target-cluster cluster-check --fix-replicas 1

# 3. Complete any pending snapshots
./escmd.py -l target-cluster snapshots

# 4. Check for any ongoing recovery operations
./escmd.py -l target-cluster recovery

# 5. Disable allocation if needed (manual step)
echo "Consider disabling allocation: PUT _cluster/settings {\"persistent\":{\"cluster.routing.allocation.enable\":\"none\"}}"
```

### Post-Maintenance Validation

**Objective**: Verify cluster health after maintenance activities.

```bash
# 1. Basic connectivity and health
./escmd.py -l target-cluster ping
./escmd.py -l target-cluster health

# 2. Comprehensive health assessment
./escmd.py -l target-cluster cluster-check --show-details

# 3. Verify data integrity
./escmd.py -l target-cluster indices | grep -E "(red|yellow)"

# 4. Check recovery operations
./escmd.py -l target-cluster recovery

# 5. Validate ILM operations resumed
./escmd.py -l target-cluster ilm errors

# 6. Document post-maintenance state
./escmd.py -l target-cluster health > post-maintenance-health-$(date +%Y%m%d).txt

# 7. Re-enable allocation if disabled (manual step)
echo "Re-enable allocation: PUT _cluster/settings {\"persistent\":{\"cluster.routing.allocation.enable\":\"all\"}}"
```

### Dangling Index Cleanup

**Objective**: Safely clean up dangling indices.

```bash
# 1. Identify dangling indices
./escmd.py -l target-cluster dangling

# 2. Assess impact and document
./escmd.py -l target-cluster dangling > dangling-indices-$(date +%Y%m%d).txt

# 3. Preview cleanup operation
./escmd.py -l target-cluster dangling --cleanup-all --dry-run

# 4. Execute cleanup with logging
./escmd.py -l target-cluster dangling --cleanup-all --log-file dangling-cleanup-$(date +%Y%m%d).log

# 5. Verify cleanup completion
./escmd.py -l target-cluster dangling

# 6. Check cluster health after cleanup
./escmd.py -l target-cluster health
```

## Performance Optimization Workflows

### Shard Optimization

**Objective**: Optimize shard size and distribution for better performance.

```bash
# 1. Analyze current shard distribution
./escmd.py -l target-cluster shards

# 2. Identify oversized shards
./escmd.py -l target-cluster cluster-check --max-shard-size 30

# 3. Check shard colocation issues
./escmd.py -l target-cluster shard-colocation

# 4. Review ILM policies for shard size optimization
./escmd.py -l target-cluster ilm policies

# 5. Plan index template updates for future indices
echo "Review index templates for optimal shard configuration"
```

### Replica Strategy Optimization

**Objective**: Optimize replica counts for balance between redundancy and resource usage.

```bash
# 1. Analyze current replica distribution
./escmd.py -l target-cluster set-replicas --pattern "*" --dry-run --format json > replica-analysis-$(date +%Y%m%d).json

# 2. Identify optimization opportunities
cat replica-analysis-$(date +%Y%m%d).json | jq '.plan.indices_to_update[] | select(.current_replicas > 2)'

# 3. Plan replica optimization by index pattern
./escmd.py -l target-cluster set-replicas --pattern "logs-old-*" --count 0 --dry-run  # Archive data
./escmd.py -l target-cluster set-replicas --pattern "logs-current-*" --count 1 --dry-run  # Standard redundancy
./escmd.py -l target-cluster set-replicas --pattern "critical-*" --count 2 --dry-run  # High redundancy

# 4. Execute optimizations gradually
./escmd.py -l target-cluster set-replicas --pattern "logs-old-*" --count 0
./escmd.py -l target-cluster set-replicas --pattern "logs-current-*" --count 1
./escmd.py -l target-cluster set-replicas --pattern "critical-*" --count 2

# 5. Monitor impact
./escmd.py -l target-cluster health
./escmd.py -l target-cluster storage
```

## Automation and Integration

### Monitoring System Integration

**Example Prometheus/Grafana Integration:**

```bash
#!/bin/bash
# prometheus-metrics-collector.sh

CLUSTERS=("prod-primary" "prod-analytics")
METRICS_FILE="/var/lib/prometheus/escmd-metrics.prom"

> $METRICS_FILE  # Clear previous metrics

for cluster in "${CLUSTERS[@]}"; do
    # Collect cluster health metrics
    HEALTH=$(./escmd.py -l $cluster health --quick --format json)
    STATUS=$(echo $HEALTH | jq -r '.status')
    NODES=$(echo $HEALTH | jq -r '.nodes.total')
    SHARDS_ACTIVE=$(echo $HEALTH | jq -r '.shards.active')
    SHARDS_UNASSIGNED=$(echo $HEALTH | jq -r '.shards.unassigned')
    
    # Convert status to numeric
    case $STATUS in
        "green") STATUS_NUM=0 ;;
        "yellow") STATUS_NUM=1 ;;
        "red") STATUS_NUM=2 ;;
        *) STATUS_NUM=3 ;;
    esac
    
    # Write Prometheus metrics
    echo "elasticsearch_cluster_status{cluster=\"$cluster\"} $STATUS_NUM" >> $METRICS_FILE
    echo "elasticsearch_nodes_total{cluster=\"$cluster\"} $NODES" >> $METRICS_FILE
    echo "elasticsearch_shards_active{cluster=\"$cluster\"} $SHARDS_ACTIVE" >> $METRICS_FILE
    echo "elasticsearch_shards_unassigned{cluster=\"$cluster\"} $SHARDS_UNASSIGNED" >> $METRICS_FILE
    
    # Collect ILM metrics
    ILM_STATUS=$(./escmd.py -l $cluster cluster-check --format json)
    ILM_ERRORS=$(echo $ILM_STATUS | jq '.checks.ilm_results.error_count // 0')
    ILM_UNMANAGED=$(echo $ILM_STATUS | jq '.checks.ilm_results.unmanaged_count // 0')
    REPLICA_ISSUES=$(echo $ILM_STATUS | jq '.checks.no_replica_indices | length')
    
    echo "elasticsearch_ilm_errors{cluster=\"$cluster\"} $ILM_ERRORS" >> $METRICS_FILE
    echo "elasticsearch_ilm_unmanaged{cluster=\"$cluster\"} $ILM_UNMANAGED" >> $METRICS_FILE
    echo "elasticsearch_replica_issues{cluster=\"$cluster\"} $REPLICA_ISSUES" >> $METRICS_FILE
done
```

### Alert Management

**Example alerting script:**

```bash
#!/bin/bash
# cluster-alerting.sh

send_alert() {
    local cluster=$1
    local severity=$2
    local message=$3
    
    # Send to Slack
    curl -X POST -H 'Content-type: application/json' \
         --data "{\"text\":\"[$severity] Cluster $cluster: $message\"}" \
         $SLACK_WEBHOOK_URL
    
    # Send to PagerDuty (for critical alerts)
    if [ "$severity" = "CRITICAL" ]; then
        curl -X POST 'https://events.pagerduty.com/v2/enqueue' \
             -H 'Content-Type: application/json' \
             -d "{
                 \"routing_key\": \"$PAGERDUTY_ROUTING_KEY\",
                 \"event_action\": \"trigger\",
                 \"payload\": {
                     \"summary\": \"Elasticsearch Cluster Alert: $cluster\",
                     \"source\": \"escmd-monitoring\",
                     \"severity\": \"critical\",
                     \"custom_details\": {\"message\": \"$message\"}
                 }
             }"
    }"
    fi
}
```

## Memory Optimization Workflows

### Index Freeze/Unfreeze Management

**Objective**: Optimize memory usage by freezing rarely accessed indices while maintaining searchability.

#### Memory Pressure Response

**Triggered by**: High heap memory usage, performance degradation, or cost optimization needs.

```bash
# 1. Assess current memory usage
./escmd.py -l production cluster-check --show-details

# 2. Identify candidate indices for freezing (historical/archive data)
./escmd.py -l production indices | grep -E "(logs-old|archive-|historical-)"

# 3. Analyze access patterns (requires external log analysis)
# Freeze indices based on access patterns - start with oldest

# 4. Freeze historical indices (older than 90 days)
./escmd.py -l production freeze "logs-2023-*" --regex

# 5. Monitor impact on memory and performance
./escmd.py -l production health
./escmd.py -l production cluster-check
```

#### Planned Freeze Operations

**Use Case**: Regular freezing of aging data based on retention policies.

```bash
# 1. Plan freeze operation based on date patterns
FREEZE_DATE=$(date -d "90 days ago" +%Y-%m)
echo "Planning to freeze indices older than: $FREEZE_DATE"

# 2. Preview indices to be frozen
./escmd.py -l production indices "logs-${FREEZE_DATE}-*"

# 3. Execute freeze with confirmation
./escmd.py -l production freeze "logs-${FREEZE_DATE}-*" --regex

# 4. Verify freeze operations
./escmd.py -l production indices "logs-${FREEZE_DATE}-*" | grep -i frozen
```

#### Emergency Unfreeze Operations

**Use Case**: Urgent need to access frozen data or restore write operations.

```bash
# 1. Identify frozen indices that need urgent access
./escmd.py -l production indices | grep -i frozen

# 2. Emergency single index unfreeze
./escmd.py -l production unfreeze critical-index-2024-01

# 3. Batch unfreeze for urgent data access
./escmd.py -l production unfreeze "urgent-logs-*" --regex --yes

# 4. Monitor cluster during unfreeze operations
./escmd.py -l production health --quick
```

#### Automated Freeze/Unfreeze Workflow

**Automation script for regular freeze operations:**

```bash
#!/bin/bash
# automated-freeze-management.sh

CLUSTER="production"
FREEZE_AGE_DAYS=90
LOG_FILE="/var/log/escmd-freeze-$(date +%Y%m%d).log"

echo "$(date): Starting automated freeze management" >> $LOG_FILE

# Calculate freeze date
FREEZE_DATE=$(date -d "$FREEZE_AGE_DAYS days ago" +%Y-%m)

# Freeze old log indices
echo "$(date): Freezing indices older than $FREEZE_DATE" >> $LOG_FILE
./escmd.py -l $CLUSTER freeze "logs-${FREEZE_DATE}-*" --regex --yes >> $LOG_FILE 2>&1

# Freeze old application indices  
./escmd.py -l $CLUSTER freeze "app-logs-${FREEZE_DATE}-*" --regex --yes >> $LOG_FILE 2>&1

# Health check after freeze operations
echo "$(date): Post-freeze health check" >> $LOG_FILE
HEALTH_STATUS=$(./escmd.py -l $CLUSTER health --quick)
echo "$HEALTH_STATUS" >> $LOG_FILE

# Alert if health degraded
if echo "$HEALTH_STATUS" | grep -q "red"; then
    send_alert "CRITICAL" "Cluster health degraded after freeze operations"
fi

echo "$(date): Automated freeze management completed" >> $LOG_FILE
```

4. **Testing**: Test workflows in non-production environments
5. **Continuous Improvement**: Regularly optimize workflows based on experience

## Related Documentation

- [Health Monitoring Commands](../commands/health-monitoring.md) - Detailed command reference
- [Cluster Check Commands](../commands/cluster-check.md) - Comprehensive health checking
- [Index Operations Commands](../commands/index-operations.md) - Freeze/unfreeze operations
- [Replica Management](../commands/replica-management.md) - Replica management workflows
- [Troubleshooting Guide](../reference/troubleshooting.md) - Common issues and solutions

# Check critical clusters
CRITICAL_CLUSTERS=("prod-primary" "prod-analytics")

for cluster in "${CRITICAL_CLUSTERS[@]}"; do
    STATUS=$(./escmd.py -l $cluster health --quick --format json | jq -r '.status')
    
    case $STATUS in
        "red")
            send_alert $cluster "CRITICAL" "Cluster status is RED"
            ;;
        "yellow")
            send_alert $cluster "WARNING" "Cluster status is YELLOW"
            ;;
    esac
    
    # Check ILM errors
    ILM_ERRORS=$(./escmd.py -l $cluster cluster-check --format json | jq '.checks.ilm_results.error_count // 0')
    if [ "$ILM_ERRORS" -gt 10 ]; then
        send_alert $cluster "WARNING" "High number of ILM errors: $ILM_ERRORS"
    fi
done
```

## Best Practices

### Workflow Design

1. **Document Everything**: Always log workflow execution and results
2. **Use Dry-Run**: Preview operations before execution
3. **Incremental Changes**: Make changes gradually and verify each step
4. **Automation**: Automate routine workflows but maintain manual oversight
5. **Error Handling**: Plan for failure scenarios and recovery procedures

### Monitoring Strategy

1. **Layered Monitoring**: Combine real-time alerts with periodic deep analysis
2. **Baseline Establishment**: Understand normal behavior patterns
3. **Threshold Management**: Set appropriate thresholds for different environments
4. **Historical Analysis**: Maintain historical data for trend analysis
5. **Integration**: Integrate with existing monitoring and alerting systems

### Operational Guidelines

1. **Regular Reviews**: Periodically review and update workflows
2. **Team Training**: Ensure team members understand workflows and tools
3. **Documentation**: Maintain up-to-date documentation and runbooks
4. **Testing**: Test workflows in non-production environments
5. **Continuous Improvement**: Regularly optimize workflows based on experience

## Related Documentation

- [Health Monitoring Commands](../commands/health-monitoring.md) - Detailed command reference
- [Cluster Check Commands](../commands/cluster-check.md) - Comprehensive health checking
- [Replica Management](../commands/replica-management.md) - Replica management workflows
- [Troubleshooting Guide](../reference/troubleshooting.md) - Common issues and solutions
