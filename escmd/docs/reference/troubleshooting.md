# Troubleshooting Guide

Comprehensive troubleshooting guide for common escmd issues and solutions.

## Connection Issues

### Cannot Connect to Elasticsearch Cluster

**Symptoms:**
- Connection timeout errors
- "Connection refused" messages
- SSL/TLS handshake failures

**Diagnostic Steps:**

```bash
# 1. Test basic connectivity
./escmd.py ping

# 2. Check specific cluster configuration
./escmd.py show-settings

# 3. Test with minimal configuration
./escmd.py -l cluster-name health --quick
```

**Common Solutions:**

#### Network Connectivity
```bash
# Test direct network connectivity
telnet elasticsearch-host 9200
curl -k https://elasticsearch-host:9200

# Check DNS resolution
nslookup elasticsearch-host
```

#### SSL/TLS Issues
```yaml
# Temporary: Disable certificate verification for testing
servers:
  - name: test-cluster
    hostname: your-host.com
    port: 9200
    use_ssl: true
    verify_certs: false  # Temporary for testing
```

**Production Fix:**
```yaml
# Proper SSL configuration
servers:
  - name: production
    hostname: prod-es.company.com
    port: 9200
    use_ssl: true
    verify_certs: true
    ca_certs_path: /path/to/ca-bundle.crt  # If using custom CA
```

#### Firewall/Proxy Issues
```yaml
# Configure proxy if behind corporate firewall
servers:
  - name: corporate-cluster
    hostname: es.company.com
    port: 9200
    proxy_host: proxy.company.com
    proxy_port: 8080
    proxy_username: proxy-user
    proxy_password: proxy-password
```

### Authentication Failures

**Symptoms:**
- 401 Unauthorized errors
- Authentication required messages
- Permission denied errors

**Diagnostic Steps:**

```bash
# 1. Verify credentials
./escmd.py show-settings  # Check configuration (passwords hidden)

# 2. Test with curl
curl -u username:password https://es-host:9200/_cluster/health

# 3. Check user permissions
curl -u username:password https://es-host:9200/_security/user/username
```

**Solutions:**

#### Incorrect Credentials
```yaml
# Verify username and password
servers:
  - name: cluster
    elastic_authentication: true
    elastic_username: correct-username
    elastic_password: correct-password
```

#### Environment-Based Password Issues
```yaml
# Check password resolution
passwords:
  prod:
    kibana_system: "actual-password-here"  # Ensure correct password

servers:
  - name: production
    env: prod
    use_env_password: true
    elastic_username: kibana_system  # Must match key in passwords.prod
```

#### Insufficient Permissions
```bash
# Check required permissions for escmd operations:
# - cluster:monitor/main
# - cluster:monitor/health
# - indices:monitor/*
# - cluster:admin/settings/get
```

## Configuration Issues

### Invalid YAML Syntax

**Symptoms:**
- "YAML parsing error" messages
- Configuration not loading
- Unexpected behavior

**Diagnostic Steps:**

```bash
# 1. Validate YAML syntax
python3 -c "import yaml; yaml.safe_load(open('elastic_servers.yml'))"

# 2. Check escmd parsing
./escmd.py show-settings

# 3. Use YAML validator online or with tools
yamllint elastic_servers.yml
```

**Common YAML Issues:**

#### Indentation Problems
```yaml
# WRONG: Inconsistent indentation
servers:
  - name: cluster1
    hostname: host1.com
     port: 9200  # Extra space

# CORRECT: Consistent indentation
servers:
  - name: cluster1
    hostname: host1.com
    port: 9200
```

#### Quotes and Special Characters
```yaml
# WRONG: Unescaped special characters
elastic_password: my@password!with:special&chars

# CORRECT: Properly quoted
elastic_password: "my@password!with:special&chars"
```

#### Boolean Values
```yaml
# WRONG: String instead of boolean
use_ssl: "true"
verify_certs: "false"

# CORRECT: Proper boolean values
use_ssl: true
verify_certs: false
```

### Missing Configuration

**Symptoms:**
- "No clusters configured" messages
- Default cluster not found
- Command execution failures

**Solutions:**

```bash
# 1. Check if configuration file exists
ls -la elastic_servers.yml

# 2. Verify configuration structure
./escmd.py show-settings

# 3. Create minimal configuration
cat > elastic_servers.yml << 'EOF'
servers:
  - name: default
    hostname: localhost
    port: 9200
    use_ssl: false
    verify_certs: false
    elastic_authentication: false
EOF
```

## Command Execution Issues

### Command Not Found

**Symptoms:**
- "Command not found" errors
- Python import errors
- Module missing errors

**Solutions:**

#### Python Path Issues
```bash
# Check Python version
python3 --version

# Check if escmd.py is executable
chmod +x escmd.py

# Run with explicit Python
python3 escmd.py --help
```

#### Missing Dependencies
```bash
# Install missing dependencies
pip3 install -r requirements.txt

# Check specific imports
python3 -c "import requests, yaml, rich"

# Update pip if needed
pip3 install --upgrade pip
```

#### Path Issues
```bash
# Run from escmd directory
cd /path/to/escmd
./escmd.py --help

# Or use absolute path
/path/to/escmd/escmd.py --help
```

### Permission Denied

**Symptoms:**
- "Permission denied" when running escmd
- Cannot read configuration file
- Cannot write log files

**Solutions:**

```bash
# Fix file permissions
chmod +x escmd.py
chmod 644 elastic_servers.yml

# Check directory permissions
ls -la

# Fix ownership if needed
sudo chown $USER:$USER escmd.py elastic_servers.yml
```

## Display and Formatting Issues

### Unicode/Emoji Display Problems

**Symptoms:**
- Strange characters instead of emojis
- Broken table formatting
- Garbled output

**Solutions:**

#### Enable ASCII Mode
```yaml
# Add to elastic_servers.yml
settings:
  ascii_mode: true  # Use ASCII-only characters
```

#### Terminal Configuration
```bash
# Check locale settings
locale

# Set UTF-8 locale if needed
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

# For persistent setting, add to ~/.bashrc or ~/.zshrc
echo 'export LANG=en_US.UTF-8' >> ~/.bashrc
```

#### Terminal Compatibility
```bash
# Test Unicode support
python3 -c "print('✅ 🔍 📊 🎯')"

# If not supported, use ASCII mode or different terminal
```

### Paging Issues

**Symptoms:**
- Output truncated unexpectedly
- Pager not working correctly
- Cannot exit pager

**Solutions:**

```yaml
# Disable paging if problematic
settings:
  enable_paging: false
```

```bash
# Override paging for specific command
./escmd.py indices --no-pager

# Set pager environment variable
export PAGER=less
export LESS="-R"  # For color support
```

### Table Formatting Issues

**Symptoms:**
- Tables not aligned properly
- Content overflow
- Missing borders

**Solutions:**

```yaml
# Try different box styles
settings:
  box_style: SIMPLE     # More compatible
  # or
  box_style: ASCII      # Maximum compatibility
```

```bash
# Check terminal width
echo $COLUMNS
tput cols

# Resize terminal if needed
# Or use JSON output for narrow terminals
./escmd.py indices --format json
```

## Performance Issues

### Slow Command Execution and Timeouts

**Symptoms:**
- Commands take long time to complete
- `ConnectionTimeout` or `ReadTimeoutError` messages
- Hanging operations
- "Read timed out" errors

**Common Timeout Errors:**
```
ConnectionTimeout caused by - ReadTimeoutError(HTTPSConnectionPool(host='cluster.com', port=9200): Read timed out. (read timeout=60))
```

**Diagnostic Steps:**

```bash
# 1. Use quick mode for health checks
./escmd.py health --quick

# 2. Check specific cluster performance
time ./escmd.py -l slow-cluster health

# 3. Test network latency
ping elasticsearch-host

# 4. Test direct API calls
curl -w "@curl-format.txt" -s -k https://elasticsearch-host:9200/_cluster/health
```

**Solutions:**

#### Configure Global Timeouts
Add timeout settings to your `elastic_servers.yml`:

```yaml
settings:
  # Global timeout configuration
  connection_timeout: 30      # Connection establishment (default: 30)
  read_timeout: 120          # Read operations (default: 60)

servers:
  - name: production
    hostname: prod-es.company.com
    # ... other settings
```

#### Per-Cluster Timeout Overrides
For specific slow clusters:

```yaml
servers:
  - name: slow-cluster
    hostname: slow-es.company.com
    port: 9200
    use_ssl: true
    verify_certs: true
    elastic_authentication: true
    elastic_username: kibana_system
    elastic_password: password
    read_timeout: 300          # 5 minutes for very slow operations
    
  - name: snapshot-cluster
    hostname: backup-es.company.com
    read_timeout: 600          # 10 minutes for snapshot operations
```

#### Quick Fixes for Immediate Relief
```bash
# For regular monitoring, use quick mode
./escmd.py health --quick
./escmd.py -l cluster health -q

# Skip heavy operations temporarily
./escmd.py cluster-check --skip-ilm

# Use specific commands instead of comprehensive checks
./escmd.py nodes  # Instead of full health check
```

#### Recommended Timeout Values

| Scenario | Connection Timeout | Read Timeout | Notes |
|----------|-------------------|--------------|-------|
| Local/Fast Network | 30 seconds | 60 seconds | Default values |
| Slow Network | 60 seconds | 180 seconds | 3 minutes for reads |
| Large Clusters | 30 seconds | 300 seconds | 5 minutes for complex operations |
| Snapshot Operations | 60 seconds | 600 seconds | 10 minutes for backups |
| Remote/WAN | 90 seconds | 300 seconds | High latency connections |

#### Network Optimization
```bash
# Test network performance
ping -c 10 elasticsearch-host
traceroute elasticsearch-host

# Check for network issues
netstat -i
ss -tuln
```

### Memory Issues

**Symptoms:**
- Python memory errors
- System running out of memory
- Slow performance with large outputs

**Solutions:**

```yaml
# Enable paging for large outputs
settings:
  enable_paging: true
  paging_threshold: 20  # Lower threshold
```

```bash
# Use JSON output and process with external tools
./escmd.py indices --format json | jq '.[] | select(.status == "red")'

# Process large outputs in chunks
./escmd.py indices | head -100
```

## API Compatibility Issues

### Elasticsearch Version Compatibility

**Symptoms:**
- API not available errors
- 405 Method Not Allowed
- Unknown API endpoints

**Common Version Issues:**

#### ILM API (Elasticsearch < 6.6)
```bash
# Skip ILM checks for older versions
./escmd.py cluster-check --skip-ilm
```

#### X-Pack Features
```bash
# Some features require X-Pack license
# Check cluster license status
curl -X GET "es-host:9200/_license"
```

### API Permission Issues

**Symptoms:**
- 403 Forbidden errors
- Missing privileges errors
- Partial data returned

**Required Permissions:**

```json
{
  "cluster": [
    "monitor",
    "manage_ilm"
  ],
  "indices": [
    {
      "names": ["*"],
      "privileges": ["monitor", "manage"]
    }
  ]
}
```

**Minimal Read-Only Permissions:**
```json
{
  "cluster": ["monitor"],
  "indices": [
    {
      "names": ["*"],
      "privileges": ["monitor"]
    }
  ]
}
```

## Data and State Issues

### Inconsistent Data

**Symptoms:**
- Data doesn't match between commands
- Stale information displayed
- Unexpected results

**Solutions:**

```bash
# 1. Check cluster state consistency
./escmd.py health
./escmd.py nodes

# 2. Verify data with direct API calls
curl -X GET "es-host:9200/_cluster/health"
curl -X GET "es-host:9200/_cluster/state"

# 3. Clear any local caching (if applicable)
# escmd doesn't cache, but check if any proxy/CDN is involved
```

### Missing or Unexpected Indices

**Symptoms:**
- Indices not showing up
- Different index counts
- Missing expected data

**Diagnostic Steps:**

```bash
# 1. Check index patterns and filters
./escmd.py indices

# 2. Look for hidden indices
curl -X GET "es-host:9200/_cat/indices?v&h=index,status,health"

# 3. Check aliases
curl -X GET "es-host:9200/_aliases"
```

## Recovery and Maintenance

### Cluster Stuck in Yellow/Red State

**Diagnostic Workflow:**

```bash
# 1. Check overall health
./escmd.py health

# 2. Identify unassigned shards
./escmd.py allocation explain

# 3. Check for node issues
./escmd.py nodes

# 4. Review recent operations
./escmd.py recovery
```

### Dangling Index Issues

**Safe Cleanup Process:**

```bash
# 1. Identify dangling indices
./escmd.py dangling

# 2. Document what will be deleted
./escmd.py dangling > dangling-backup-$(date +%Y%m%d).txt

# 3. Test cleanup process
./escmd.py dangling --cleanup-all --dry-run

# 4. Execute with logging
./escmd.py dangling --cleanup-all --log-file cleanup.log

# 5. Verify results
./escmd.py dangling
./escmd.py health
```

## Emergency Procedures

### Complete Cluster Outage

**Assessment Steps:**

```bash
# 1. Test basic connectivity
./escmd.py ping

# 2. If ping fails, check network/DNS
nslookup es-host
telnet es-host 9200

# 3. If cluster responds but unhealthy
./escmd.py health
./escmd.py nodes
```

### Data Loss Prevention

**Before Destructive Operations:**

```bash
# 1. Always use dry-run first
./escmd.py dangling --cleanup-all --dry-run
./escmd.py set-replicas --pattern "*" --count 0 --dry-run

# 2. Backup critical data
./escmd.py snapshots

# 3. Document current state
./escmd.py health > pre-operation-health.txt
./escmd.py indices > pre-operation-indices.txt
```

## Getting Additional Help

### Collecting Diagnostic Information

When reporting issues, collect this information:

```bash
# 1. Version information
./escmd.py version
python3 --version

# 2. Configuration (sanitized)
./escmd.py show-settings

# 3. Error reproduction
./escmd.py failing-command > error-output.txt 2>&1

# 4. System information
uname -a
pip3 list | grep -E "(requests|rich|yaml)"

# 5. Network connectivity
ping es-host
curl -I https://es-host:9200/
```

### Debug Mode

For detailed troubleshooting:

```bash
# Enable verbose output (if available)
./escmd.py --debug health

# Use Python debugging
python3 -u escmd.py health

# Network debugging
curl -v https://es-host:9200/_cluster/health
```

### Community Resources

- Check existing issues and documentation
- Provide complete error messages and steps to reproduce
- Include sanitized configuration and system information
- Be specific about expected vs actual behavior

## Related Documentation

- [Installation Guide](../configuration/installation.md) - Setup and installation issues
- [Cluster Setup Guide](../configuration/cluster-setup.md) - Configuration problems
- [Health Monitoring](../commands/health-monitoring.md) - Health check issues
- [Cluster Check](../commands/cluster-check.md) - Comprehensive troubleshooting commands
