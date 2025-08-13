# escmd.py

escmd is a command line utility to make interacting with Elasticsearch more enjoyable and efficient.

## Features

- **Enhanced Health Dashboard**: Comprehensive 6-panel visual dashboard with cluster overview, node topology, shard metrics, performance monitoring, backup status, and automatic allocation issue detection
- **Cluster Comparison**: Side-by-side health analysis between any two clusters with real-time metrics and visual status indicators
- **Cluster Management**: Advanced health monitoring with configurable display styles, settings management, and real-time status indicators
- **Node Operations**: Complete node information including master identification, client nodes, and allocation management
- **Index Management**: List, freeze, and manage indices with regex filtering, detailed per-index analysis, and configurable legend panels
- **Index Lifecycle Management (ILM)**: Comprehensive ILM support with policy management, phase tracking, error monitoring, and usage analysis
- **Shard Operations**: View shard distribution with balance metrics, rollover operations, per-node calculations, and enhanced state visualization
- **Shard Analysis**: Advanced shard colocation detection to identify availability risks where primary and replica shards are on the same host
- **Allocation Management**: Enhanced allocation explain functionality with comprehensive node decision analysis, barrier identification, and automatic health dashboard integration
- **Snapshot Management**: Full backup monitoring with repository health, success/failure tracking, and S3 integration
- **Recovery Monitoring**: Advanced recovery dashboard with progress tracking, stage visualization, and completion analytics
- **Performance Metrics**: Live monitoring of pending tasks, in-flight operations, and cluster performance indicators
- **Flush Auto-Retry**: Synced flush now automatically retries failed shards with a 10-second delay, up to 10 times, for robust and reliable operations
- **Multi-cluster Support**: Easy switching between different Elasticsearch clusters with per-cluster configurations
- **Rich Output**: Beautiful dashboards and tables with JSON export options and perfect emoji/text alignment
- **Smart Paging System**: Configurable auto-paging for large datasets with less-like navigation and manual override options
- **Enhanced Help System**: Visual command categorization with examples and rich formatting
- **Hierarchical Commands**: Intuitive command structure for complex operations

## Installation

escmd requires Python 3.6+, with a handful of Python modules.

### Install Python Requirements

```sh
pip3 install -r requirements.txt
```

### Configuration

Edit `elastic_servers.yml` to configure your Elasticsearch clusters:

```yaml
settings:
  # Options for box_style: SIMPLE, ASCII, SQUARE, ROUNDED, SQUARE_DOUBLE_HEAD
  box_style: SQUARE_DOUBLE_HEAD
  # Options for health_style: dashboard, classic
  health_style: dashboard
  # Options for classic_style: table, panel
  classic_style: panel
  # Paging configuration for large datasets
  enable_paging: true           # Enable automatic paging for large outputs
  paging_threshold: 50          # Auto-enable pager when items exceed this count
  # Show legend and quick actions panels at bottom of tables
  show_legend_panels: false     # Show Legend and Quick Actions panels (default: false)
  # ASCII mode for maximum terminal compatibility
  ascii_mode: false             # Use ASCII-only characters instead of emojis and Unicode symbols (default: false)

# Environment-based password configuration (recommended for new deployments)
passwords:
  prod:
    kibana_system: "production_kibana_system_password"
    elastic: "production_elastic_password"
  staging:
    kibana_system: "staging_kibana_system_password"
  dev:
    kibana: "kibana"  # Basic auth for development

servers:
  - name: default
    hostname: 192.168.1.100
    hostname2: 192.168.1.101    # Optional backup host
    port: 9200
    use_ssl: False 
    verify_certs: False         # Set to True for production
    elastic_authentication: False
    elastic_username: None 
    elastic_password: None
    elastic_s3snapshot_repo: "my-backup-repo"  # Optional: for snapshot operations
    
  # Example: Environment-based password (recommended)
  - name: production
    env: prod                   # Environment key for password lookup
    use_env_password: true      # Enable environment-based password resolution
    hostname: prod-es-01.company.com
    hostname2: prod-es-02.company.com
    port: 9200
    use_ssl: True
    verify_certs: True
    elastic_authentication: True
    elastic_username: kibana_system  # Will use passwords.prod.kibana_system
    elastic_s3snapshot_repo: "production-snapshots"
    health_style: dashboard  # Use dashboard style for this cluster
    
  # Example: Direct password reference
  - name: staging
    hostname: staging-es.company.com
    port: 9200
    use_ssl: True
    verify_certs: False
    elastic_authentication: True
    elastic_username: kibana_system
    elastic_password_ref: "staging.kibana_system"  # Direct reference
    elastic_s3snapshot_repo: "staging-backups"
    health_style: classic  # Use classic table style for this cluster
    classic_style: table   # Use original table format when classic style is used
    
  # Example: Traditional explicit password (backwards compatible)
  - name: legacy
    hostname: legacy-es.company.com
    port: 9200
    use_ssl: False
    elastic_authentication: True
    elastic_username: kibana
    elastic_password: explicit_password_here  # Traditional method

# Optional: Define cluster groups for grouped operations
cluster_groups:
  att:
    - iad51
    - sjc51
  production:
    - iad41
    - sjc01
  glip:
    - aex10
    - aex20
    - iad41
```

## Configuration Options

### Server Configuration

| Option | Description | Required | Default |
|--------|-------------|----------|---------|
| `name` | Unique identifier for the cluster | Yes | - |
| `hostname` | Primary Elasticsearch host | Yes | - |
| `hostname2` | Secondary/backup host | No | - |
| `port` | Elasticsearch port | No | 9200 |
| `use_ssl` | Enable SSL/HTTPS connections | No | False |
| `verify_certs` | Verify SSL certificates | No | False |
| `elastic_authentication` | Enable authentication | No | False |
| `elastic_username` | Username for authentication | No | None |
| `elastic_password` | Password for authentication (traditional) | No | None |
| `env` | Environment key for password resolution | No | None |
| `use_env_password` | Enable environment-based password lookup | No | False |
| `elastic_password_ref` | Direct password reference (e.g., "prod.kibana_system") | No | None |
| `elastic_s3snapshot_repo` | S3 snapshot repository name | No | None |
| `health_style` | Health display style | No | dashboard |
| `classic_style` | Classic format style | No | panel |

### Global Settings

| Option | Description | Values |
|--------|-------------|---------|
| `box_style` | Table border style | SIMPLE, ASCII, SQUARE, ROUNDED, SQUARE_DOUBLE_HEAD |
| `health_style` | Default health display style | dashboard, classic |
| `classic_style` | Classic format style | table, panel |
| `enable_paging` | Enable automatic paging for large datasets | true, false |
| `paging_threshold` | Auto-enable pager when items exceed count | integer (default: 50) |
| `show_legend_panels` | Show Legend and Quick Actions panels | true, false (default: false) |
| `ascii_mode` | Use ASCII-only characters for maximum terminal compatibility | true, false (default: false) |

### ASCII Mode
For terminals with poor Unicode/emoji support (like some Windows terminals or older terminal emulators):

```bash
# Enable ASCII mode temporarily
ESCMD_ASCII_MODE=true ./escmd.py get-default

# Enable ASCII mode permanently in config
# Set 'ascii_mode: true' in settings section of elastic_servers.yml

# View current settings including ASCII mode
./escmd.py show-settings
```

ASCII mode removes emojis and uses simple text labels for maximum compatibility across all terminal types.

## Password Management

### Environment-Based Password Management

escmd supports a modern, environment-based password management system that eliminates password duplication and simplifies maintenance. This feature allows you to define passwords once per environment and reference them across multiple clusters.

#### Password Configuration

Define passwords in the `passwords` section of your `elastic_servers.yml`:

```yaml
passwords:
  prod:
    kibana_system: "your_production_kibana_system_password"
    elastic: "your_production_elastic_password"
  ops:
    kibana_system: "your_ops_kibana_system_password"
  att:
    kibana_system: "your_att_kibana_system_password"
  legacy:
    kibana: "kibana"  # For basic auth clusters
```

#### Server Configuration Methods

You can configure server authentication using three different methods:

##### Method 1: Environment-Based Password (Recommended)
```yaml
- name: cluster_name
  env: prod  # Environment key
  use_env_password: true  # Enable environment-based resolution
  hostname: hostname.com
  elastic_authentication: true
  elastic_username: kibana_system
  # Password automatically resolved from passwords.prod.kibana_system
```

##### Method 2: Direct Password Reference
```yaml
- name: cluster_name
  hostname: hostname.com
  elastic_authentication: true
  elastic_username: kibana_system
  elastic_password_ref: "prod.kibana_system"  # Direct reference
```

##### Method 3: Traditional Explicit Password (Backwards Compatible)
```yaml
- name: cluster_name
  hostname: hostname.com
  elastic_authentication: true
  elastic_username: kibana_system
  elastic_password: "explicit_password_here"  # Traditional approach
```

#### Password Resolution Priority

The system resolves passwords in this order:
1. **Direct password reference** (`elastic_password_ref`)
2. **Environment-based password** (`use_env_password: true`)
3. **Traditional explicit password** (`elastic_password`)
4. **Default password** from settings

#### Benefits

- **Reduced Duplication**: Define each password once per environment
- **Easier Maintenance**: Update passwords in one central location
- **Better Organization**: Group passwords by environment (prod, ops, att, etc.)
- **Backwards Compatible**: Existing configurations continue to work unchanged
- **Flexible Migration**: Migrate clusters to the new scheme at your own pace

#### Migration Tools

```bash
# Analyze current password usage and get migration suggestions
python3 migrate_passwords.py --dry-run

# Perform automatic migration (with backup)
python3 migrate_passwords.py --backup
```

For detailed information, see [PASSWORD_MANAGEMENT.md](PASSWORD_MANAGEMENT.md).

## Usage

### Getting Started

#### Enhanced Help System

escmd features a beautiful, categorized help system that makes discovering commands intuitive:

```bash
# Show fancy help with command categories and examples
./escmd.py --help
```

**Help Features:**
- **📋 Visual Command Categories**: Commands organized by function (Cluster, Node, Index, Maintenance)
- **🎨 Color-Coded Sections**: Each category has distinct colors for easy navigation
- **🚀 Quick Examples**: Practical usage examples for common operations
- **📖 Rich Formatting**: Beautiful panels and tables for professional appearance
- **🔍 Feature Highlights**: Key capabilities highlighted (dashboard/classic/comparison/groups)

The help system provides a complete overview of:
- **🏢 Cluster Operations**: health, settings, ping, locations
- **🖥️ Node Management**: nodes, masters, current-master
- **📊 Index Operations**: indices, indice, freeze, shards
- **🔧 Maintenance**: snapshots, recovery, storage, allocation, ilm

### Cluster Selection

escmd supports multiple clusters. You can specify a cluster using the `-l` flag or set a default.

```bash
# Use specific cluster
./escmd.py -l production health

# Set default cluster
./escmd.py set-default production

# Check current default
./escmd.py get-default
```

### Cluster Management

#### Health Monitoring

The health command offers two display styles:

**⚡ Quick Mode (-q/--quick)**
- **Fast Response**: Only performs basic cluster health API call (~1-2 seconds)
- **Core Metrics Only**: Cluster name, status, nodes, shards, unassigned shards
- **Skip Diagnostics**: Bypasses recovery status, allocation issues, node details, snapshots
- **Minimal Output**: Clean, focused display of essential health information
- **Perfect for Monitoring**: Ideal for scripts, automation, or when you need quick status checks

**📊 Dashboard Style (Default)**
- **6-Panel Visual Dashboard**: Comprehensive cluster health overview with additional diagnostics
  - **📋 Cluster Overview**: Cluster name, current master node, total/data nodes, shard health progress
  - **🖥️ Node Information**: Complete node breakdown (total, data, master, client nodes) with data ratio
  - **🔄 Shard Status**: Primary/replica counts, shards per data node, unassigned status
  - **⚡ Performance**: Pending tasks, in-flight operations, recovery jobs, delayed shards with status indicators
  - **📦 Snapshots**: Repository status, backup counts (total/successful/failed), overall backup health
- **Smart Status Indicators**: Color-coded icons and progress bars throughout
- **Real-time Metrics**: Live cluster performance and health assessment with additional API calls
- **Compact Layout**: Efficient 2x3 grid design for maximum information density
- **Slower Response**: Takes 10-30 seconds due to comprehensive diagnostic checks

**📋 Classic Style**
- Traditional table format
- Compact display
- All metrics in key-value pairs
- Includes additional diagnostic information (unless quick mode is used)

```bash
# Check cluster health (uses configured style from elastic_servers.yml)
./escmd.py health

# Quick mode - only basic cluster health check (fast, no additional diagnostics)
./escmd.py health -q
./escmd.py health --quick

# Override config and force dashboard style
./escmd.py health --style dashboard

# Override config and force classic table format
./escmd.py health --style classic

# Force classic table format (original style)
./escmd.py health --style classic --classic-style table

# Force classic panel format (enhanced style)
./escmd.py health --style classic --classic-style panel

# Check cluster health (JSON format)
./escmd.py health --format json

# Quick mode with JSON output
./escmd.py health --quick --format json

# Compare two clusters side-by-side (forces classic style)
./escmd.py health --compare iad41
./escmd.py -l aex20 health --compare iad41

# Compare clusters with JSON output
./escmd.py health --compare iad41 --format json

# Show health for all clusters in a group (forces classic style)
./escmd.py health --group att
./escmd.py health --group production

# Group health with JSON output
./escmd.py health --group att --format json
```

**Dashboard Features:**
- **Master Node Identification**: See which node is currently the cluster master
- **Complete Node Topology**: Total, data, master, and client node counts with visual ratios
- **Shard Balance Metrics**: Shards per data node calculation for load assessment
- **Performance Monitoring**: Real-time pending tasks, in-flight operations, and recovery status
- **Backup Health**: Snapshot repository status with success/failure tracking
- **Status Indicators**: Visual health indicators (✅ 📊 ⚠️ ❌) throughout all panels

**Side-by-Side Comparison:**
- **Dual Cluster Analysis**: Compare health metrics between any two configured clusters
- **Real-time Data**: Live comparison of current cluster states
- **Visual Comparison**: Color-coded status panels for easy identification of differences
- **Key Metrics**: Status, nodes, shards, performance indicators, and shard distribution
- **Automatic Layout**: Tables positioned side-by-side with minimal spacing for easy comparison

**Configuration Options:**
- **Global Default**: Set `health_style: dashboard` in the `settings` section of `elastic_servers.yml`
- **Per-Cluster**: Add `health_style: classic` to individual server configurations
- **Command Override**: Use `--style` flag to override configuration settings
- **Classic Format**: Configure `classic_style: table` or `classic_style: panel` for classic display format

#### Cluster Groups

Define logical groups of clusters for bulk operations and organized health monitoring:

```bash
# Show health for all clusters in a group
./escmd.py health --group att

# Show health for production group with JSON output
./escmd.py health --group production --format json

# List available cluster groups
./escmd.py locations
```

**Group Configuration:**
- **Multi-Cluster Monitoring**: Monitor 2-3+ clusters simultaneously in a grid layout
- **Logical Organization**: Group clusters by environment (att, production, staging)
- **Bulk Operations**: Perform health checks across multiple related clusters
- **Comparative Analysis**: Side-by-side health status for related environments

**Group Display Features:**
- **Grid Layout**: 2-column layout for optimal space usage
- **Individual Status**: Each cluster shows its own health panel with status indicators
- **Error Handling**: Failed connections are clearly marked while showing successful ones
- **Consistent Formatting**: All clusters use the same enhanced panel format for easy comparison

#### Settings Management
```bash
# View cluster settings
./escmd.py settings

# View settings in JSON format
./escmd.py settings --format json
```

### Node Operations

#### List Nodes
```bash
# List all nodes
./escmd.py nodes

# List nodes in JSON format
./escmd.py nodes --format json

# List only master nodes
./escmd.py masters
```

#### Current Master
```bash
# Show current master node with detailed information
./escmd.py current-master

# Show in JSON format
./escmd.py current-master --format json
```

**Enhanced Features:**
- **Master Node Details**: Complete node information including hostname, node ID, and roles
- **Cluster Status Panel**: Real-time cluster health with node counts and status indicators
- **Role Analysis**: Shows if master is dedicated or has additional data/ingest roles
- **Visual Dashboard**: Two-panel layout with master details and cluster overview

### Allocation Management

The allocation commands use a hierarchical structure for better organization:

#### Display Allocation Settings
```bash
# Show current allocation settings
./escmd.py allocation display
```

#### Shard Allocation Control
```bash
# Enable shard allocation
./escmd.py allocation enable

# Disable shard allocation (primaries only)
./escmd.py allocation disable
```

#### Node Exclusion Management
```bash
# Add node to exclusion list
./escmd.py allocation exclude add server01

# Remove node from exclusion list  
./escmd.py allocation exclude remove server01

# Clear all exclusions
./escmd.py allocation exclude reset
```

#### Allocation Explain Analysis
```bash
# Explain allocation decisions for specific index/shard
./escmd.py allocation explain my-index-name

# Explain specific shard number
./escmd.py allocation explain my-index-name --shard 2

# Force primary shard analysis
./escmd.py allocation explain my-index-name --primary

# Export allocation explanation data
./escmd.py allocation explain my-index-name --format json
```

**Enhanced Features:**
- **Comprehensive Node Analysis**: Shows allocation decisions for all nodes with weight rankings
- **Allocation Status**: Current node placement with detailed node information
- **Barrier Identification**: Identifies why allocation is blocked on specific nodes
- **Smart Auto-detection**: Automatically detects primary vs replica shards
- **Visual Decision Table**: Color-coded decisions (✅ Yes, ❌ No, ⏸️ Throttle) for all nodes
- **Health Dashboard Integration**: Automatically appears on health screen when allocation issues exist

### Smart Paging System

escmd includes an intelligent paging system for handling large datasets with ease.

#### Configuration
Configure paging behavior in `elastic_servers.yml`:
```yaml
settings:
  enable_paging: true           # Enable/disable automatic paging
  paging_threshold: 50          # Auto-enable pager when items > threshold
```

#### Paging Commands
All major listing commands support paging:
```bash
# Auto-paging based on configuration
./escmd.py indices               # Pages when >threshold indices
./escmd.py shards                # Pages when >threshold shards  
./escmd.py snapshots list        # Pages when >threshold snapshots

# Force paging regardless of config
./escmd.py indices --pager       # Always use pager
./escmd.py shards --pager        # Always use pager
./escmd.py snapshots list --pager # Always use pager
```

#### Pager Navigation
When paging is active, use these controls:
- **Space**: Page down
- **b**: Page up
- **j/k**: Line up/down
- **q**: Quit pager
- **/text**: Search for text
- **n/N**: Next/previous search result

**Features:**
- Maintains full Rich formatting (colors, borders, emojis)
- Configurable activation thresholds
- Manual override with `--pager` flag
- Less-like navigation experience
- Works with filtered results and patterns

### Index Management

#### List Indices
```bash
# List all indices
./escmd.py indices

# List indices with regex filter
./escmd.py indices kibana

# List cold indices only
./escmd.py indices --cold

# List with specific status
./escmd.py indices --status yellow

# Use pager for large datasets
./escmd.py indices --pager

# Export to JSON
./escmd.py indices --format json
```

#### Index Operations
```bash
# View detailed index information with comprehensive metadata
./escmd.py indice my-index-name
# Displays: Overview (health, status, docs, size), Settings (UUID, creation date, 
# version, ILM policy/phase, shard config), Shards Distribution (states, nodes),
# and detailed per-shard information table

# Freeze an index
./escmd.py freeze my-index-name
```

### Index Lifecycle Management (ILM)

escmd provides comprehensive ILM support for managing index lifecycles across all phases.

#### ILM Overview
```bash
# Get comprehensive ILM status and phase distribution
./escmd.py ilm status

# Export ILM status data
./escmd.py ilm status --format json
```

**Enhanced Features:**
- **📊 ILM Status Panel**: Shows ILM enabled/disabled state, operation mode, and total managed indices
- **🔄 Phase Distribution**: Visual breakdown of indices across Hot, Warm, Cold, Frozen, Delete, and Unmanaged phases
- **🚀 Quick Actions**: Related commands and navigation options

#### Policy Management
```bash
# List all ILM policies with phase coverage matrix
./escmd.py ilm policies

# View detailed configuration for specific policy
./escmd.py ilm policy my-policy-name

# Show all indices using a policy (default shows first 10)
./escmd.py ilm policy my-policy-name --show-all

# Export policy data
./escmd.py ilm policies --format json
./escmd.py ilm policy my-policy-name --format json
```

**Policy Features:**
- **📋 Policy Matrix**: Shows which phases (🔥🟡🧊❄️🗑️) each policy covers
- **📊 Detailed Policy View**: Phase configurations, actions, transitions, and conditions
- **📁 Usage Analysis**: Live list of indices using each policy with current phase/action
- **🎯 Smart Display**: Shows first 10 indices by default, `--show-all` for complete list

#### Index Lifecycle Analysis
```bash
# Explain ILM status for specific index
./escmd.py ilm explain my-index-2024.01.01

# Find indices with ILM errors
./escmd.py ilm errors

# Export explain data
./escmd.py ilm explain my-index --format json
./escmd.py ilm errors --format json
```

**Analysis Features:**
- **🔍 Index Details**: Shows policy, current phase, action, step, and error status
- **❌ Error Detection**: Identifies indices with ILM failures and error reasons
- **🔄 Phase Tracking**: Visual phase indicators and lifecycle progression
- **⚡ Real-time Status**: Current action and step information

#### ILM Workflow Examples
```bash
# 1. Check overall ILM health
./escmd.py ilm status

# 2. Review all policies and their coverage
./escmd.py ilm policies

# 3. Investigate specific policy usage
./escmd.py ilm policy logs-retention-policy

# 4. Check for problematic indices
./escmd.py ilm errors

# 5. Analyze specific index lifecycle
./escmd.py ilm explain logs-app-2024.01.01

# 6. Export data for analysis
./escmd.py ilm status --format json > ilm-status.json
./escmd.py ilm policies --format json > ilm-policies.json
```

### Shard Management

#### List Shards
```bash
# List all shards with enhanced formatting and statistics
./escmd.py shards
# Displays: Statistics panel (total shards, states, types, hot/frozen counts)
# and detailed shards table with state, type, shard#, docs, size, and node info

# Filter by regex pattern
./escmd.py shards kibana

# Filter by server
./escmd.py shards --server ess01

# Sort by size and limit results
./escmd.py shards --size --limit 10

# Combine filters
./escmd.py shards --server ess01 --size --limit 5 my-pattern

# Use pager for large datasets
./escmd.py shards --pager
```

#### Rollover Operations
```bash
# Rollover specific datastream
./escmd.py rollover my-datastream

# Auto-rollover largest shard on host
./escmd.py auto-rollover hostname
```

### Datastream Operations
```bash
# List all datastreams
./escmd.py datastreams

# Show details for a specific datastream
./escmd.py datastreams my-datastream

# List datastreams in JSON format
./escmd.py datastreams --format json

# Show specific datastream details in JSON format
./escmd.py datastreams my-datastream --format json

# Delete a specific datastream (with confirmation prompt)
./escmd.py datastreams my-datastream --delete

# Example with the specific datastream name mentioned
./escmd.py datastreams rehydrated_ams02-c01-logs-igl-main --delete
```

### Shard Analysis

#### Shard Colocation Detection
Identify availability risks where primary and replica shards of the same index are located on the same physical host.

```bash
# Analyze all indices for colocation issues
./escmd.py shard-colocation

# Filter analysis by regex pattern
./escmd.py shard-colocation "logs-*"
./escmd.py shard-colocation "k8s-main"

# Export colocation analysis data
./escmd.py shard-colocation --format json
./escmd.py shard-colocation "logs-*" --format json
```

**Enhanced Features:**
- **Risk Assessment**: Categorizes issues as LOW, MEDIUM, HIGH, or CRITICAL based on affected indices
- **Comprehensive Statistics**: Shows total indices analyzed, affected indices, problematic shard groups, and risk percentages
- **Visual Status Indicators**: Color-coded risk levels with appropriate icons and themes
- **Detailed Issue Reporting**: Lists specific indices and shard groups with allocation details
- **Recommendation Engine**: Provides actionable guidance for resolving allocation issues
- **Pattern Filtering**: Supports regex patterns to focus analysis on specific index sets
- **Success Reporting**: Clean display when no colocation issues are found

**Risk Level Indicators:**
- **🟢 LOW**: 1-5% of indices affected
- **🟡 MEDIUM**: 6-15% of indices affected  
- **🟠 HIGH**: 16-30% of indices affected
- **🔴 CRITICAL**: >30% of indices affected

### Snapshot Management

Snapshot operations require `elastic_s3snapshot_repo` to be configured for the cluster.

#### List Snapshots
```bash
# List all snapshots
./escmd.py snapshots list

# Filter snapshots by pattern
./escmd.py snapshots list logs-application

# Use regex patterns
./escmd.py snapshots list "k8s-main"
./escmd.py snapshots list "2025.01.*"

# Use pager for large datasets
./escmd.py snapshots list --pager

# Export to JSON
./escmd.py snapshots list --format json
./escmd.py snapshots list logs-app --format json
```

### Recovery Monitoring

```bash
# Monitor recovery operations with enhanced dashboard
./escmd.py recovery

# Export recovery data
./escmd.py recovery --format json
```

**Enhanced Features:**
- **Recovery Summary Dashboard**: Overview of total shards, active recoveries, and completion rates
- **Stage Breakdown**: Visual tracking of recovery stages (Init → Index → Translog → Finalize → Done)
- **Progress Visualization**: Color-coded progress bars and completion percentages
- **Recovery Type Analysis**: Breakdown of different recovery types (replica, peer, snapshot)
- **Real-time Monitoring**: Live status updates with visual stage indicators
- **No Recovery State**: Clean display when no recovery operations are active

### Storage Information

```bash
# View storage usage
./escmd.py storage

# Export storage data
./escmd.py storage --format json
```

### Administrative Commands

#### Cluster Location Management
```bash
# List all configured clusters
./escmd.py locations
```

#### Maintenance Operations

##### Connection Testing
```bash
# Test connectivity with detailed cluster information
./escmd.py ping

# Export connection data
./escmd.py ping --format json
```

**Enhanced Features:**
- **🔗 Connection Details**: Host, port, SSL status, authentication info
- **📊 Cluster Overview**: Health status, node counts, cluster name
- **🚀 Quick Actions**: Related commands and next steps
- **⚠️ Error Handling**: Detailed connection failure reporting

##### Cluster Flush Operations
```bash
# Perform synced flush with detailed monitoring
./escmd.py flush
```

**Enhanced Features:**
- **📊 Operation Summary**: Shard statistics, success rates, failure tracking
- **⚙️ Progress Monitoring**: Real-time operation status with visual feedback
- **🔄 Auto-Retry**: Automatically retries failed shards with a 10-second delay, up to 10 times, until all shards are flushed or max retries are reached
- **🎉 Success Reporting**: Celebrates successful flushes, including those that required retries
- **❌ Persistent Failure Handling**: If failures persist after all retries, provides clear error reporting and troubleshooting guidance
- **⚠️ Failure Analysis**: Detailed per-shard error reporting for failed operations
- **🚀 Related Commands**: Quick access to health, shards, and recovery monitoring

##### Index Freeze Operations
```bash
# Freeze an index with comprehensive validation
./escmd.py freeze my-index-name
```

**Enhanced Features:**
- **✅ Index Validation**: Pre-freeze health, status, and size verification
- **⚙️ Operation Details**: Clear explanation of freeze effects and limitations
- **❌ Enhanced Errors**: Available indices list when target not found
- **🚀 Next Steps**: Post-operation guidance and verification commands

#### Version Information
```bash
# Show version
./escmd.py version
```

## Advanced Usage Examples

### Cluster Health Comparison
```bash
# Compare current cluster with another
./escmd.py health --compare production

# Compare specific clusters
./escmd.py -l staging health --compare production

# Compare multiple environments for capacity planning
./escmd.py -l production health --compare staging
./escmd.py -l iad41 health --compare sjc01

# Export comparison data for analysis
./escmd.py health --compare production --format json > cluster-comparison.json

# Quick health check across environments
./escmd.py -l production health --compare staging | grep -E "(Status|Nodes|Shards)"
```

### Cluster Groups
```bash
# Monitor entire environment groups
./escmd.py health --group att
./escmd.py health --group production

# Export group health data for analysis
./escmd.py health --group att --format json > att-cluster-health.json

# Quick group status overview
./escmd.py health --group production | grep -E "(Status|Total Nodes)"

# Monitor development vs production groups
./escmd.py health --group staging
./escmd.py health --group production
```

### Maintenance Workflow
```bash
# 1. Check cluster health before maintenance
./escmd.py -l production health

# 2. Disable allocation
./escmd.py -l production allocation disable

# 3. Perform maintenance on nodes...

# 4. Re-enable allocation
./escmd.py -l production allocation enable

# 5. Monitor recovery
./escmd.py -l production recovery
```

### Snapshot Management Workflow
```bash
# List recent snapshots
./escmd.py -l production snapshots list

# Find specific application snapshots
./escmd.py -l production snapshots list app-logs

# Export snapshot list for processing
./escmd.py -l production snapshots list --format json > snapshots.json
```

### Index Cleanup Workflow
```bash
# Find old indices
./escmd.py -l production indices old-pattern

# Check specific index details
./escmd.py -l production indice old-index-2024.01.01

# Freeze old index before deletion
./escmd.py -l production freeze old-index-2024.01.01
```

### ILM Management Workflow
```bash
# 1. Check overall ILM health and distribution
./escmd.py -l production ilm status

# 2. Review policy configurations and coverage
./escmd.py -l production ilm policies

# 3. Investigate specific policy usage
./escmd.py -l production ilm policy logs-retention-policy

# 4. Check for indices with ILM issues
./escmd.py -l production ilm errors

# 5. Analyze problematic index lifecycle
./escmd.py -l production ilm explain stuck-index-2024.01.01

# 6. Export ILM data for trend analysis
./escmd.py -l production ilm status --format json > ilm-health.json
./escmd.py -l production ilm policies --format json > policy-configs.json
```

### Shard Monitoring
```bash
# Find largest shards on specific node
./escmd.py -l production shards --server node01 --size --limit 10

# Monitor unassigned shards
./escmd.py -l production shards --server UNASSIGNED

# Export shard data for analysis
./escmd.py -l production shards --format json > shard-analysis.json
```

### Shard Analysis & Allocation Troubleshooting
```bash
# Check for availability risks across all indices
./escmd.py -l production shard-colocation

# Focus on specific application logs
./escmd.py -l production shard-colocation "app-logs-*"

# Export colocation analysis for reporting
./escmd.py -l production shard-colocation --format json > colocation-report.json

# Diagnose specific allocation issues
./escmd.py -l production allocation explain problematic-index-2024.01.01

# Investigate specific shard allocation
./escmd.py -l production allocation explain my-index --shard 2

# Export allocation explanation for detailed analysis
./escmd.py -l production allocation explain my-index --format json > allocation-analysis.json

# Combined troubleshooting workflow
./escmd.py -l production health                    # Check overall health (allocation issues auto-detected)
./escmd.py -l production shard-colocation          # Check for colocation risks
./escmd.py -l production allocation explain my-index # Diagnose specific allocation issue
```

## Output Formats

Most commands support both table and JSON output formats:

- **Table Format**: Human-readable tables with colors and formatting (default)
- **JSON Format**: Machine-readable JSON for scripting and automation

Use `--format json` with any supported command to get JSON output.

## Error Handling

escmd provides clear error messages and suggestions:

- **Configuration Errors**: Missing or invalid cluster configurations
- **Connection Errors**: Network connectivity issues with fallback to secondary hosts
- **Authentication Errors**: Invalid credentials or permissions
- **Repository Errors**: Missing or misconfigured snapshot repositories

## Tips and Best Practices

1. **Use Default Clusters**: Set up commonly used clusters as defaults to avoid typing `-l cluster` repeatedly
2. **JSON Export**: Use JSON format for automation and further processing with tools like `jq`
3. **Regex Filtering**: Use regex patterns to filter large result sets efficiently
4. **Snapshot Repositories**: Configure snapshot repositories in your cluster settings for full snapshot functionality
5. **Backup Hosts**: Configure `hostname2` for high availability
6. **SSL in Production**: Always use SSL and certificate verification in production environments
7. **Health Display Styles**: Set `health_style` globally or per-cluster to customize the health command appearance
8. **Classic Format Options**: Use `classic_style: panel` for enhanced table formatting or `classic_style: table` for original format
9. **Command Overrides**: Use command-line flags like `--style` and `--classic-style` to temporarily override configuration settings
10. **Cluster Comparisons**: Use `--compare` to quickly identify differences between environments (staging vs production)
11. **Quick Health Checks**: Use `--quick` or `-q` for fast health checks in scripts, monitoring, or when you need immediate cluster status without waiting for comprehensive diagnostics
11. **Cluster Groups**: Define logical groups in `cluster_groups` for bulk monitoring and organized operations
12. **Enhanced Help**: Use `./escmd.py --help` to discover commands with the visual categorized help system
13. **Load Balancing**: Use shards-per-node metrics in comparisons to identify unbalanced clusters
14. **ILM Monitoring**: Regularly check `ilm status` and `ilm errors` to ensure proper index lifecycle management
15. **Policy Analysis**: Use `ilm policy <name> --show-all` to audit which indices are using specific lifecycle policies
16. **Phase Distribution**: Monitor the phase distribution in `ilm status` to identify potential lifecycle bottlenecks
17. **Shard Colocation Monitoring**: Regularly run `shard-colocation` to identify availability risks before they impact production
18. **Allocation Troubleshooting**: Use `allocation explain` to diagnose why specific shards are unassigned or stuck
19. **Health Dashboard Integration**: Monitor the health command regularly as it will automatically show allocation issues when they occur
20. **Legend Panel Configuration**: Set `show_legend_panels: false` (default) for cleaner index displays, enable only when learning commands
21. **Pattern-based Analysis**: Use regex patterns with shard-colocation to focus on specific index families or applications
22. **Proactive Monitoring**: Combine health dashboard, shard-colocation, and allocation explain for comprehensive cluster health assessment
23. **Flush Reliability**: The flush command now automatically retries failed shards with a 10-second delay, up to 10 times, for maximum reliability. Monitor the output for retry progress and final status.

## Troubleshooting

### Common Issues

**"No 's3_snapshot_repo' configured"**
- Add `elastic_s3snapshot_repo: "repo-name"` to your cluster configuration

**Connection timeouts**
- Check if `hostname2` is configured as a fallback
- Verify network connectivity and firewall settings

**Authentication failures**
- Ensure `elastic_authentication: True` and correct credentials
- Check user permissions in Elasticsearch

**SSL certificate errors**
- Set `verify_certs: False` for testing (not recommended for production)
- Ensure proper SSL certificate configuration

## Contributing

Contributions are welcome! Please ensure new features include:
- Appropriate help text
- JSON output support where applicable
- Error handling
- Documentation updates
