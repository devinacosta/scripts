# Cluster Setup Guide

Comprehensive guide for configuring Elasticsearch clusters with escmd.

## Overview

escmd uses the `elastic_servers.yml` configuration file to define Elasticsearch clusters, authentication methods, and operational settings. This guide covers all configuration options and best practices.

## Basic Configuration

### Minimal Configuration

```yaml
servers:
  - name: local
    hostname: localhost
    port: 9200
    use_ssl: false
    verify_certs: false
    elastic_authentication: false
```

### Production Configuration

```yaml
settings:
  box_style: SQUARE_DOUBLE_HEAD
  health_style: dashboard
  enable_paging: true

servers:
  - name: production
    hostname: prod-es-01.company.com
    hostname2: prod-es-02.company.com  # Backup host
    port: 9200
    use_ssl: true
    verify_certs: true
    elastic_authentication: true
    elastic_username: kibana_system
    elastic_password: secure-password-here
    elastic_s3snapshot_repo: production-snapshots
```

## Configuration Sections

### Global Settings

The `settings` section defines global behavior and display preferences:

```yaml
settings:
  # Visual styling options
  box_style: SQUARE_DOUBLE_HEAD    # SIMPLE, ASCII, SQUARE, ROUNDED, SQUARE_DOUBLE_HEAD
  health_style: dashboard          # dashboard, classic
  classic_style: panel             # table, panel (when health_style is classic)
  
  # Terminal and display options
  enable_paging: true              # Auto-enable pager for large outputs
  paging_threshold: 50             # Items threshold for auto-paging
  show_legend_panels: false        # Show legend and quick actions
  ascii_mode: false                # ASCII-only mode for compatibility
  
  # Network timeout configuration
  connection_timeout: 30           # Connection timeout in seconds (default: 30)
  read_timeout: 60                 # Read timeout in seconds (default: 60)
  
  # Cluster health check configuration
  dangling_cleanup:
    max_retries: 3                 # Maximum retry attempts
    retry_delay: 5                 # Delay between retries (seconds)
    timeout: 60                    # Operation timeout (seconds)
    default_log_level: INFO        # Default logging level
    enable_progress_bar: true      # Show progress bars
    confirmation_required: true    # Require confirmations for destructive operations
```

### Server Configuration

Each server entry defines an Elasticsearch cluster:

#### Basic Server Options

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `name` | string | ✅ | Unique cluster identifier |
| `hostname` | string | ✅ | Primary Elasticsearch host |
| `hostname2` | string | ❌ | Backup host for failover |
| `port` | integer | ✅ | Elasticsearch port (typically 9200) |
| `use_ssl` | boolean | ✅ | Enable HTTPS connections |
| `verify_certs` | boolean | ✅ | Verify SSL certificates |

#### Authentication Options

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `elastic_authentication` | boolean | ✅ | Enable authentication |
| `elastic_username` | string | * | Username for authentication |
| `elastic_password` | string | * | Password for authentication |
| `use_env_password` | boolean | ❌ | Use environment-based passwords |
| `env` | string | ❌ | Environment key for password lookup |

*Required when `elastic_authentication` is `true`

#### Optional Features

| Option | Type | Description |
|--------|------|-------------|
| `elastic_s3snapshot_repo` | string | Default S3 snapshot repository |
| `health_style` | string | Override global health style for this cluster |
| `description` | string | Human-readable cluster description |
| `environment` | string | Environment tag (prod, staging, dev, etc.) |
| `connection_timeout` | integer | Override global connection timeout for this cluster |
| `read_timeout` | integer | Override global read timeout for this cluster |

## Authentication Methods

### Method 1: Direct Password Configuration

```yaml
servers:
  - name: production
    hostname: prod-es-01.company.com
    port: 9200
    use_ssl: true
    verify_certs: true
    elastic_authentication: true
    elastic_username: kibana_system
    elastic_password: direct-password-here
```

**Use When:**
- Simple setups with few clusters
- Development environments
- Testing configurations

### Method 2: Environment-Based Passwords (Recommended)

```yaml
# Define passwords by environment
passwords:
  prod:
    kibana_system: "production-kibana-password"
    elastic: "production-elastic-password"
  staging:
    kibana_system: "staging-kibana-password"
  dev:
    kibana: "development-password"

servers:
  - name: production
    env: prod                      # Environment key
    use_env_password: true         # Enable environment lookup
    hostname: prod-es-01.company.com
    port: 9200
    use_ssl: true
    verify_certs: true
    elastic_authentication: true
    elastic_username: kibana_system  # Will use passwords.prod.kibana_system
```

**Benefits:**
- **Reduced Duplication**: Define passwords once per environment
- **Easier Maintenance**: Update passwords in one location
- **Better Organization**: Group passwords by environment
- **Scalable**: Easy to add new clusters in existing environments

### Method 3: External Password Files

```yaml
servers:
  - name: production
    hostname: prod-es-01.company.com
    port: 9200
    use_ssl: true
    verify_certs: true
    elastic_authentication: true
    elastic_username: kibana_system
    elastic_password_file: /secure/path/prod-password.txt
```

**Use When:**
- High security environments
- Passwords managed by external systems
- Compliance requirements for credential storage

## Multi-Cluster Configuration

### Environment-Based Organization

```yaml
passwords:
  prod:
    kibana_system: "prod-password"
  staging:
    kibana_system: "staging-password"

servers:
  # Production clusters
  - name: prod-primary
    env: prod
    use_env_password: true
    hostname: prod-es-01.company.com
    hostname2: prod-es-02.company.com
    elastic_username: kibana_system
    health_style: dashboard
    
  - name: prod-analytics
    env: prod
    use_env_password: true
    hostname: analytics-01.company.com
    elastic_username: kibana_system
    
  # Staging clusters
  - name: staging-main
    env: staging
    use_env_password: true
    hostname: staging-es-01.company.com
    elastic_username: kibana_system
    health_style: classic
```

### Geographic Distribution

```yaml
servers:
  # US East
  - name: us-east-prod
    hostname: use1-es-01.company.com
    hostname2: use1-es-02.company.com
    description: "US East Production Cluster"
    environment: production
    
  # US West
  - name: us-west-prod
    hostname: usw1-es-01.company.com
    hostname2: usw1-es-02.company.com
    description: "US West Production Cluster"
    environment: production
    
  # Europe
  - name: eu-prod
    hostname: eu-es-01.company.com
    hostname2: eu-es-02.company.com
    description: "Europe Production Cluster"
    environment: production
```

## Cluster Groups

Cluster groups allow monitoring multiple related clusters simultaneously:

```yaml
servers:
  # Group: production (environment-based)
  - name: prod-app1
    environment: production
    hostname: app1-es-01.company.com
    
  - name: prod-app2
    environment: production
    hostname: app2-es-01.company.com
    
  # Group: staging
  - name: staging-app1
    environment: staging
    hostname: staging-app1-es.company.com
    
  - name: staging-app2
    environment: staging
    hostname: staging-app2-es.company.com
```

**Using Groups:**
```bash
# Monitor all production clusters
./escmd.py health --group production

# Monitor all staging clusters
./escmd.py health --group staging
```

## SSL/TLS Configuration

### Basic SSL Configuration

```yaml
servers:
  - name: secure-cluster
    hostname: secure-es.company.com
    port: 9200
    use_ssl: true
    verify_certs: true          # Verify SSL certificates
    elastic_authentication: true
```

### Custom Certificate Configuration

```yaml
servers:
  - name: custom-certs
    hostname: internal-es.company.com
    port: 9200
    use_ssl: true
    verify_certs: true
    ca_certs_path: /path/to/ca-bundle.crt     # Custom CA bundle
    client_cert_path: /path/to/client.crt     # Client certificate
    client_key_path: /path/to/client.key      # Client private key
```

### Self-Signed Certificates

```yaml
servers:
  - name: self-signed
    hostname: test-es.internal
    port: 9200
    use_ssl: true
    verify_certs: false         # Disable verification for self-signed
    elastic_authentication: true
```

## Advanced Configuration

### High Availability Setup

```yaml
servers:
  - name: ha-cluster
    hostname: es-vip.company.com        # Virtual IP or load balancer
    hostname2: es-backup.company.com    # Direct backup connection
    port: 9200
    use_ssl: true
    verify_certs: true
    elastic_authentication: true
    elastic_username: kibana_system
    elastic_password: password
    connection_timeout: 30              # Extended timeout for HA
    read_timeout: 60
```

### Proxy Configuration

```yaml
servers:
  - name: proxy-cluster
    hostname: es-proxy.company.com
    port: 9200
    use_ssl: true
    verify_certs: true
    proxy_host: corporate-proxy.company.com
    proxy_port: 8080
    proxy_username: proxy-user          # If proxy requires authentication
    proxy_password: proxy-password
```

### Custom Headers

```yaml
servers:
  - name: custom-headers
    hostname: es.company.com
    port: 9200
    custom_headers:
      X-Custom-Header: "custom-value"
      Authorization-Extra: "bearer-token"
```

### Timeout Configuration

Configure timeouts for slow networks or large clusters to prevent connection errors:

```yaml
settings:
  # Global timeout defaults
  connection_timeout: 30      # Connection establishment timeout
  read_timeout: 60           # Read operation timeout

servers:
  # Standard cluster with default timeouts
  - name: fast-cluster
    hostname: fast-es.company.com
    port: 9200
    use_ssl: true
    verify_certs: true
    elastic_authentication: true
    elastic_username: kibana_system
    elastic_password: password
    
  # Slow cluster with extended timeouts
  - name: slow-cluster
    hostname: slow-es.company.com
    port: 9200
    use_ssl: true
    verify_certs: true
    elastic_authentication: true
    elastic_username: kibana_system
    elastic_password: password
    read_timeout: 180          # 3 minutes for slow operations
    
  # Remote cluster with very long timeouts
  - name: remote-cluster
    hostname: remote-es.company.com
    port: 9200
    use_ssl: true
    verify_certs: true
    elastic_authentication: true
    elastic_username: kibana_system
    elastic_password: password
    connection_timeout: 60     # 1 minute to establish connection
    read_timeout: 300          # 5 minutes for read operations
```

**When to Increase Timeouts:**
- **Slow Networks**: High latency or low bandwidth connections
- **Large Clusters**: Clusters with many indices or large datasets
- **Remote Clusters**: Geographically distant Elasticsearch clusters
- **Heavy Operations**: Snapshots, large queries, or bulk operations
- **Resource Constrained**: Clusters under high load or with limited resources

**Timeout Guidelines:**
- **Connection Timeout**: Usually 30-60 seconds is sufficient
- **Read Timeout**: 60-300 seconds depending on operation complexity
- **Snapshot Operations**: May require 5-10 minutes or more
- **Large Clusters**: Consider 2-5 minutes for comprehensive health checks

## Validation and Testing

### Configuration Validation

```bash
# Test configuration syntax
./escmd.py show-settings

# List all configured clusters
./escmd.py locations

# Test specific cluster connectivity
./escmd.py -l cluster-name ping
```

### Connection Testing

```bash
# Basic connectivity test
./escmd.py ping

# Detailed cluster information
./escmd.py -l production ping

# Test authentication
./escmd.py -l production health --quick
```

### Health Check Validation

```bash
# Test cluster health
./escmd.py health

# Test specific cluster
./escmd.py -l production health

# Test cluster comparison
./escmd.py -l prod1 health --compare prod2

# Test group monitoring
./escmd.py health --group production
```

## Best Practices

### Security Best Practices

1. **Use Environment-Based Passwords**: Reduce credential duplication
2. **Enable SSL/TLS**: Always use encrypted connections in production
3. **Verify Certificates**: Don't disable certificate verification in production
4. **Least Privilege**: Use accounts with minimal required permissions
5. **Rotate Credentials**: Regularly update passwords and certificates

### Configuration Management

1. **Version Control**: Store configuration in version control (excluding passwords)
2. **Environment Separation**: Use separate configurations for different environments
3. **Documentation**: Document cluster purposes and configurations
4. **Backup**: Maintain backups of working configurations
5. **Validation**: Test configurations before deployment

### Performance Optimization

1. **Use Backup Hosts**: Configure `hostname2` for high availability
2. **Adjust Timeouts**: Configure appropriate timeouts for your network
3. **Enable Paging**: Use paging for large clusters
4. **Optimize Display**: Choose appropriate display styles for your use cases

### Operational Guidelines

1. **Naming Conventions**: Use consistent, descriptive cluster names
2. **Environment Tags**: Tag clusters by environment for easy grouping
3. **Health Styles**: Configure health styles appropriate for each cluster's use
4. **Default Cluster**: Set a default cluster for common operations

## Troubleshooting Configuration

### Common Configuration Issues

**Connectivity Problems:**
```bash
# Test basic connectivity
./escmd.py ping

# Check specific cluster
./escmd.py -l cluster-name ping
```

**Authentication Failures:**
```bash
# Verify credentials
./escmd.py -l cluster-name health --quick

# Check username/password combination
./escmd.py show-settings  # Review configuration (passwords hidden)
```

**SSL/Certificate Issues:**
```bash
# Test with certificate verification disabled (temporarily)
# Add to configuration: verify_certs: false

# Check certificate paths and permissions
ls -la /path/to/certificates/
```

**Configuration Syntax Errors:**
```bash
# Validate YAML syntax
python3 -c "import yaml; yaml.safe_load(open('elastic_servers.yml'))"

# Check escmd configuration parsing
./escmd.py show-settings
```

### Migration and Updates

When updating configurations:

1. **Backup**: Save current working configuration
2. **Test**: Validate new configuration in non-production environment
3. **Gradual**: Update one cluster at a time
4. **Verify**: Test all functionality after updates
5. **Document**: Record changes and rationale

## Related Documentation

- [Installation Guide](installation.md) - Basic installation and setup
- [Authentication Guide](authentication.md) - Detailed authentication configuration
- [Troubleshooting Guide](../reference/troubleshooting.md) - Common issues and solutions
- [Monitoring Workflows](../workflows/monitoring-workflows.md) - Using configured clusters for monitoring
