# Node Operations & Basic Cluster Commands

Node management, connectivity testing, and basic cluster configuration commands.

## Quick Reference

```bash
# Connectivity and basic operations
./escmd.py ping                     # Test cluster connectivity
./escmd.py locations                # List configured clusters
./escmd.py version                  # Show tool version

# Node information
./escmd.py nodes                    # List all cluster nodes
./escmd.py nodes --format json     # JSON output for automation
./escmd.py masters                  # List master-eligible nodes  
./escmd.py current-master          # Show current master node

# Cluster configuration
./escmd.py get-default             # Show current default cluster
./escmd.py set-default production  # Set default cluster
./escmd.py show-settings           # Show current tool configuration
./escmd.py settings                # View cluster settings

# Data operations  
./escmd.py storage                 # View disk usage across nodes
./escmd.py recovery                # Monitor recovery operations
./escmd.py flush                   # Perform index flush operations

# Datastream management
./escmd.py datastreams             # List all datastreams
./escmd.py datastreams my-stream   # Show specific datastream details

# Rollover operations
./escmd.py rollover my-datastream  # Manual datastream rollover
./escmd.py auto-rollover           # Rollover largest shards
```

## Connectivity & Testing

### 🏓 Ping Command

Test cluster connectivity with comprehensive connection details:

```bash
./escmd.py ping                    # Basic connectivity test
./escmd.py -l production ping      # Test specific cluster
./escmd.py ping --format json     # JSON output for automation
```

**Features:**
- **Connection Validation**: Tests HTTP/HTTPS connectivity to cluster
- **Cluster Information**: Returns basic cluster details (name, version)
- **Health Overview**: Quick health status check
- **Response Time**: Connection timing information
- **Authentication Test**: Validates credentials and permissions

**Use Cases:**
- **Initial Setup**: Verify cluster configuration before operations
- **Troubleshooting**: Diagnose connectivity issues
- **Monitoring**: Health check integration in scripts
- **Validation**: Confirm cluster accessibility after changes

## Node Management

### 🖥️ Nodes Command

List and analyze all cluster nodes with detailed information:

```bash
./escmd.py nodes                   # All nodes with default formatting
./escmd.py nodes --format json    # JSON output for automation  
./escmd.py nodes --format table   # Formatted table display
./escmd.py -l cluster nodes       # Specific cluster nodes
```

**Node Information Displayed:**
- **Node Names**: Unique node identifiers
- **Node Roles**: Master, data, ingest, coordinating roles
- **IP Addresses**: Network addresses for each node
- **Node Attributes**: Custom node attributes and tags
- **Status**: Node health and availability
- **Version**: Elasticsearch version per node

**Use Cases:**
- **Capacity Planning**: Assess cluster size and node distribution
- **Troubleshooting**: Identify problematic or missing nodes
- **Configuration**: Verify node roles and attributes
- **Monitoring**: Track node additions/removals

### 👑 Masters Command

List all master-eligible nodes:

```bash
./escmd.py masters                 # Master-eligible nodes
./escmd.py masters --format json  # JSON output
```

**Master Node Information:**
- **Master-Eligible Nodes**: All nodes capable of becoming master
- **Current Role**: Whether node is currently master or eligible
- **Node Priorities**: Master election priorities if configured
- **Voting Configuration**: Quorum and voting members

### 🎯 Current Master Command

Show the currently elected master node:

```bash
./escmd.py current-master         # Current master details
./escmd.py current-master --format json  # JSON output
```

**Master Information:**
- **Master Node**: Currently elected master node name
- **Master IP**: Network address of master node  
- **Election Time**: When current master was elected
- **Master Tasks**: Pending cluster state tasks

## Configuration Management

### 📍 Locations Command

List all configured cluster connections:

```bash
./escmd.py locations              # All configured clusters
```

**Cluster Configuration Display:**
- **Cluster Names**: All configured cluster aliases
- **Connection URLs**: Endpoint addresses for each cluster
- **Authentication**: Authentication method indicators
- **Default Cluster**: Current default cluster setting
- **Group Assignments**: Cluster group memberships

### 📌 Default Cluster Management

Manage default cluster settings:

```bash
./escmd.py get-default            # Show current default cluster
./escmd.py set-default production # Set new default cluster
```

**Default Cluster Features:**
- **Current Default**: Display currently configured default cluster
- **Change Default**: Update default cluster for subsequent commands
- **Validation**: Verify cluster exists before setting as default
- **Persistence**: Settings saved to configuration file

### 🔧 Configuration Display

View current tool configuration:

```bash
./escmd.py show-settings          # Display current configuration
```

**Configuration Information:**
- **Tool Settings**: Paging, formatting, display preferences
- **Cluster Connections**: All configured cluster endpoints
- **Default Values**: Current default settings
- **File Locations**: Configuration file paths

### ⚙️ Cluster Settings

View and manage Elasticsearch cluster settings:

```bash
./escmd.py settings               # Current cluster settings
./escmd.py settings --format json # JSON output
```

**Settings Categories:**
- **Persistent Settings**: Cluster-wide persistent configuration
- **Transient Settings**: Temporary cluster settings  
- **Default Settings**: Built-in Elasticsearch defaults
- **Dynamic Settings**: Runtime-changeable settings

## Storage & Performance

### 💾 Storage Command

View disk usage and storage metrics across all nodes:

```bash
./escmd.py storage                # Disk usage overview
./escmd.py storage --format json # JSON output for automation
```

**Storage Metrics:**
- **Disk Usage**: Used/available disk space per node
- **Shard Storage**: Storage consumption by index/shard
- **Node Capacity**: Total storage capacity per node
- **Usage Percentages**: Disk utilization ratios
- **Storage Trends**: Growth patterns and capacity planning

**Use Cases:**
- **Capacity Monitoring**: Track disk usage across cluster
- **Performance Analysis**: Identify storage bottlenecks
- **Planning**: Forecast storage requirements
- **Alerting**: Monitor for high disk usage

### 🔄 Recovery Command

Monitor shard recovery operations:

```bash
./escmd.py recovery               # Active recovery operations
./escmd.py recovery --format json # JSON output
```

**Recovery Information:**
- **Active Recoveries**: Currently running shard recoveries
- **Recovery Types**: Primary, replica, relocation recoveries
- **Progress**: Percentage complete for each recovery
- **Transfer Rates**: Data transfer speeds
- **Time Estimates**: Estimated completion times

### 💧 Flush Command

Perform index flush operations:

```bash
./escmd.py flush                  # Flush all indices
```

**Flush Operations:**
- **Memory Flush**: Force flush of in-memory segments to disk
- **All Indices**: Flushes all indices in the cluster
- **Performance Impact**: Ensures data persistence
- **Memory Relief**: Frees up memory used by unflushed segments

## Datastream Management

### 🗂️ Datastreams Command

Manage Elasticsearch datastreams:

```bash
./escmd.py datastreams                    # List all datastreams
./escmd.py datastreams my-logs           # Show specific datastream
./escmd.py datastreams --format json    # JSON output
./escmd.py datastreams my-stream --delete # Delete datastream
```

**Datastream Information:**
- **Datastream Names**: All configured datastreams
- **Backing Indices**: Indices behind each datastream
- **Index Templates**: Associated index templates
- **Lifecycle Policies**: ILM policies attached to datastreams
- **Write Index**: Current write target for each datastream

## Rollover Operations

### 🔄 Rollover Command

Manual datastream and index alias rollover:

```bash
./escmd.py rollover my-datastream         # Rollover specific datastream
./escmd.py rollover                      # Interactive rollover selection
```

**Rollover Features:**
- **Manual Control**: Trigger rollover operations on demand
- **Datastream Support**: Works with datastreams and aliases  
- **Condition Checking**: Evaluates rollover conditions
- **New Index Creation**: Creates new target indices

### ⚡ Auto-Rollover Command

Automatically rollover indices based on size or other criteria:

```bash
./escmd.py auto-rollover                 # Auto-select largest indices
./escmd.py auto-rollover hostname-pattern # Target specific hosts
```

**Auto-Rollover Logic:**
- **Size-Based**: Targets largest shards for rollover
- **Performance**: Improves performance by managing shard sizes
- **Automation**: Reduces manual intervention requirements
- **Host Targeting**: Can focus on specific nodes/hosts

## Tool Information

### 📊 Version Command

Display tool version and build information:

```bash
./escmd.py version                # Show version information
```

**Version Information:**
- **Tool Version**: Current escmd version number
- **Build Information**: Build date and commit information
- **Python Version**: Runtime Python version
- **Dependencies**: Key library versions

## Integration Examples

### Monitoring Script Integration

```bash
#!/bin/bash
# Daily cluster health check

CLUSTERS=("production" "staging" "development")

for cluster in "${CLUSTERS[@]}"; do
    echo "=== Checking $cluster ==="
    
    # Test connectivity
    if ! ./escmd.py -l $cluster ping > /dev/null 2>&1; then
        echo "ERROR: Cannot connect to $cluster"
        continue
    fi
    
    # Get basic info
    ./escmd.py -l $cluster nodes | grep -c "data"
    ./escmd.py -l $cluster current-master
    ./escmd.py -l $cluster storage | tail -1
done
```

### Configuration Validation

```bash
#!/bin/bash
# Validate cluster configuration

echo "=== Configuration Validation ==="
./escmd.py locations
./escmd.py get-default
./escmd.py show-settings

echo "=== Testing All Clusters ==="
for cluster in $(./escmd.py locations | grep -v "Default" | awk '{print $1}'); do
    echo "Testing $cluster..."
    ./escmd.py -l $cluster ping
done
```

## Related Documentation

- [Health Monitoring](health-monitoring.md) - Comprehensive health checks
- [Index Operations](index-operations.md) - Index management commands
- [Allocation Management](allocation-management.md) - Shard allocation control
- [Configuration Setup](../configuration/cluster-setup.md) - Initial cluster configuration
