# escmd.py

🚀 **Enhanced Elasticsearch Command Line Tool** - Making Elasticsearch operations more enjoyable and efficient.

![Version](https://img.shields.io/badge/version-2.4.0-blue)
![Python](https://img.shields.io/badge/python-3.6%2B-green)
![License](https://img.shields.io/badge/license-MIT-blue)

## Overview

escmd is a comprehensive command-line utility that transforms how you interact with Elasticsearch clusters. With rich terminal output, comprehensive health monitoring, and powerful automation capabilities, escmd makes complex Elasticsearch operations simple and intuitive.

## 🌟 Key Features

- **🏥 Comprehensive Health Monitoring** - Multi-panel dashboards with real-time cluster insights
- **🔧 Dual-Mode Replica Management** - Integrated health-check fixing and standalone operations
- **📋 Advanced ILM Management** - Policy tracking, error detection, and lifecycle analysis
- **⚠️ Smart Index Operations** - Dangling cleanup, freezing, and shard optimization
- **🎨 Rich Terminal Output** - Beautiful tables, panels, and progress indicators
- **🔍 Deep Cluster Analysis** - Shard colocation, allocation issues, and performance insights
- **🚀 Multi-Cluster Support** - Easy switching between environments with group monitoring
- **🤖 Automation Ready** - JSON output and script-friendly operations

## 🚀 Quick Start

### Installation

\`\`\`bash
# Install dependencies
pip3 install -r requirements.txt

# Make executable
chmod +x escmd.py

# Test installation
./escmd.py --help
\`\`\`

### Basic Configuration

Create \`elastic_servers.yml\`:

\`\`\`yaml
settings:
  health_style: dashboard
  enable_paging: true

servers:
  - name: local
    hostname: localhost
    port: 9200
    use_ssl: false
    elastic_authentication: false

  - name: production
    hostname: prod-es.company.com
    port: 9200
    use_ssl: true
    verify_certs: true
    elastic_authentication: true
    elastic_username: kibana_system
    elastic_password: your-password
\`\`\`

### Essential Commands

\`\`\`bash
# Cluster health monitoring
./escmd.py health                    # Rich dashboard view
./escmd.py health --quick            # Fast status check
./escmd.py -l production health      # Specific cluster

# Comprehensive health analysis
./escmd.py cluster-check             # Full health assessment
./escmd.py cluster-check --fix-replicas 1  # Fix replica issues

# Index operations
./escmd.py indices                   # List all indices
./escmd.py indices --status red      # Filter unhealthy indices
./escmd.py indices "logs-*" --delete # Delete indices by pattern
./escmd.py dangling --cleanup-all --dry-run  # Preview cleanup
./escmd.py set-replicas --no-replicas-only   # Fix replica counts

# ILM management
./escmd.py ilm status               # ILM overview
./escmd.py ilm errors               # Find ILM issues
./escmd.py ilm remove-policy "temp-*" --dry-run  # Preview policy removal
\`\`\`

## 📚 Documentation

### 🛠️ Setup & Configuration
- **[Installation Guide](docs/configuration/installation.md)** - Complete setup instructions
- **[Cluster Setup](docs/configuration/cluster-setup.md)** - Configure your Elasticsearch clusters

### 📖 Command Reference
- **[Health Monitoring](docs/commands/health-monitoring.md)** - Cluster health dashboards and monitoring
- **[Node Operations](docs/commands/node-operations.md)** - Node management, connectivity testing, and basic cluster operations
- **[Cluster Check](docs/commands/cluster-check.md)** - Comprehensive health analysis and issue detection
- **[Replica Management](docs/commands/replica-management.md)** - Dual-mode replica count management
- **[Index Operations](docs/commands/index-operations.md)** - Index management, deletion, and dangling cleanup
- **[ILM Management](docs/commands/ilm-management.md)** - Index Lifecycle Management and policy operations
- **[Allocation Management](docs/commands/allocation-management.md)** - Shard allocation control and troubleshooting
- **[Snapshot Management](docs/commands/snapshot-management.md)** - Backup monitoring and snapshot analysis

### 🔄 Workflows & Examples
- **[Monitoring Workflows](docs/workflows/monitoring-workflows.md)** - Daily operations and automation

### 📋 Reference
- **[Troubleshooting Guide](docs/reference/troubleshooting.md)** - Common issues and solutions
- **[Changelog](docs/reference/changelog.md)** - Version history and updates

## 💡 Common Use Cases

### Daily Operations
\`\`\`bash
# Morning health check routine
./escmd.py health --group production
./escmd.py cluster-check --fix-replicas 1 --dry-run

# Monitor specific issues
./escmd.py ilm errors
./escmd.py dangling
\`\`\`

### Maintenance Tasks
\`\`\`bash
# Pre-maintenance preparation
./escmd.py cluster-check > pre-maintenance-\$(date +%Y%m%d).txt
./escmd.py set-replicas --pattern "critical-*" --count 2
./escmd.py allocation exclude add ess46     # Exclude node for maintenance

# Post-maintenance validation
./escmd.py health
./escmd.py cluster-check --show-details
./escmd.py allocation exclude remove ess46  # Re-enable node
./escmd.py snapshots list | head -5         # Check recent backups
\`\`\`

### Automation & Monitoring
\`\`\`bash
# Script-friendly health monitoring
./escmd.py health --format json | jq '.status'

# Automated replica management
./escmd.py cluster-check --fix-replicas 1 --force --format json

# ILM monitoring integration
./escmd.py ilm errors --format json | jq 'length'
\`\`\`

## 🔧 Advanced Features

### Multi-Cluster Management
\`\`\`bash
# Compare clusters side-by-side
./escmd.py -l prod1 health --compare prod2

# Monitor cluster groups
./escmd.py health --group production
./escmd.py health --group staging
\`\`\`

### Rich Output Formats
- **Dashboard Mode**: 6-panel visual health dashboard
- **Classic Mode**: Traditional table-based display
- **JSON Mode**: Machine-readable output for automation
- **ASCII Mode**: Maximum terminal compatibility

### Intelligent Operations
- **Dry-Run Mode**: Preview all operations before execution
- **Progress Tracking**: Real-time progress bars and status updates
- **Error Recovery**: Automatic retries and graceful error handling
- **Safety Checks**: Comprehensive validation and confirmation prompts

## 🎯 What's New in v2.4.0

### 🏥 Comprehensive Cluster Health Monitoring
- **New \`cluster-check\` command** for deep health analysis
- **ILM error detection** with detailed failure analysis
- **Unmanaged indices reporting** for governance insights
- **Shard size monitoring** with configurable thresholds

### 🔧 Dual-Mode Replica Management
- **Integrated replica fixing** with \`cluster-check --fix-replicas\`
- **Standalone \`set-replicas\` command** for advanced operations
- **Pattern-based operations** for bulk replica management
- **Safety features** with dry-run and confirmation prompts

[**See complete changelog →**](docs/reference/changelog.md)

## 🚦 Getting Help

### Quick Help
\`\`\`bash
./escmd.py --help                    # Main help with command categories
./escmd.py health --help             # Specific command help
./escmd.py cluster-check --help      # Comprehensive health options
\`\`\`

### Documentation Navigation
- **New to escmd?** Start with [Installation Guide](docs/configuration/installation.md)
- **Setting up clusters?** See [Cluster Setup](docs/configuration/cluster-setup.md)
- **Need to monitor health?** Check [Health Monitoring](docs/commands/health-monitoring.md)
- **Having issues?** Review [Troubleshooting Guide](docs/reference/troubleshooting.md)

### Support
- **Issues**: Report bugs and request features via GitHub issues
- **Documentation**: Complete documentation in the \`docs/\` directory
- **Examples**: Real-world workflows in [Monitoring Workflows](docs/workflows/monitoring-workflows.md)

## 🔗 Quick Links

| Category | Documentation |
|----------|---------------|
| **🛠️ Setup** | [Installation](docs/configuration/installation.md) • [Configuration](docs/configuration/cluster-setup.md) |
| **📖 Commands** | [Health](docs/commands/health-monitoring.md) • [Nodes](docs/commands/node-operations.md) • [Cluster Check](docs/commands/cluster-check.md) • [Replicas](docs/commands/replica-management.md) • [Indices](docs/commands/index-operations.md) • [ILM](docs/commands/ilm-management.md) • [Allocation](docs/commands/allocation-management.md) • [Snapshots](docs/commands/snapshot-management.md) |
| **🔄 Workflows** | [Monitoring](docs/workflows/monitoring-workflows.md) |
| **📋 Reference** | [Troubleshooting](docs/reference/troubleshooting.md) • [Changelog](docs/reference/changelog.md) |

---

**escmd** - Making Elasticsearch operations simple, powerful, and enjoyable! 🎉
