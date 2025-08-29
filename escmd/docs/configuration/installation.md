# Installation Guide

Complete installation and setup instructions for escmd.

## Requirements

escmd requires Python 3.6+ with several Python modules for rich terminal output and Elasticsearch connectivity.

### System Requirements

- **Python**: 3.6 or higher
- **Operating System**: Linux, macOS, or Windows
- **Terminal**: Any modern terminal with Unicode support (recommended)
- **Network**: Access to Elasticsearch clusters

### Python Dependencies

escmd uses the following key Python libraries:

- **requests**: For Elasticsearch API communication
- **rich**: For beautiful terminal output and formatting
- **PyYAML**: For configuration file parsing
- **urllib3**: For HTTP/HTTPS connectivity
- **certifi**: For SSL certificate verification

## Installation Steps

### 1. Clone or Download escmd

```bash
# Clone from repository (if using git)
git clone <repository-url> escmd
cd escmd

# Or download and extract archive
wget <download-url>
unzip escmd.zip
cd escmd
```

### 2. Install Python Dependencies

```bash
# Install all required dependencies
pip3 install -r requirements.txt

# Or install individual packages if requirements.txt is not available
pip3 install requests rich PyYAML urllib3 certifi
```

**Alternative Installation Methods:**

```bash
# Using a virtual environment (recommended for production)
python3 -m venv escmd-env
source escmd-env/bin/activate  # On Windows: escmd-env\Scripts\activate
pip install -r requirements.txt

# Using conda
conda create -n escmd python=3.8
conda activate escmd
pip install -r requirements.txt

# Using pipenv
pipenv install -r requirements.txt
pipenv shell
```

### 3. Verify Installation

```bash
# Test basic functionality
python3 escmd.py --help

# Check version
python3 escmd.py version

# Test configuration (should show error if not configured)
python3 escmd.py health
```

Expected output for `--help`:
```
usage: escmd.py [-h] [-l CLUSTER] [--version] ...

escmd - Enhanced Elasticsearch Command Line Tool
```

### 4. Make Executable (Optional)

```bash
# Make escmd executable directly
chmod +x escmd.py

# Test direct execution
./escmd.py --help

# Create symbolic link for global access (optional)
sudo ln -s $(pwd)/escmd.py /usr/local/bin/escmd
escmd --help
```

## Initial Configuration

After installation, you need to configure your Elasticsearch clusters:

### 1. Create Configuration File

```bash
# Copy example configuration
cp elastic_servers.yml.example elastic_servers.yml

# Or create new configuration file
touch elastic_servers.yml
```

### 2. Basic Configuration

Edit `elastic_servers.yml` with your cluster information:

```yaml
settings:
  box_style: SQUARE_DOUBLE_HEAD
  health_style: dashboard
  classic_style: panel
  enable_paging: true
  paging_threshold: 50

servers:
  - name: default
    hostname: your-elasticsearch-host.com
    port: 9200
    use_ssl: true
    verify_certs: true
    elastic_authentication: true
    elastic_username: kibana_system
    elastic_password: your-password-here
```

### 3. Test Configuration

```bash
# Test basic connectivity
python3 escmd.py ping

# Test cluster health
python3 escmd.py health

# List configured clusters
python3 escmd.py locations
```

## Advanced Installation Options

### Docker Installation

If you prefer to run escmd in a Docker container:

```dockerfile
# Create Dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
ENTRYPOINT ["python3", "escmd.py"]
```

```bash
# Build and run
docker build -t escmd .
docker run -v $(pwd)/elastic_servers.yml:/app/elastic_servers.yml escmd health
```

### System-Wide Installation

For system-wide installation accessible to all users:

```bash
# Copy to system location
sudo cp -r escmd /opt/escmd
sudo chmod +x /opt/escmd/escmd.py

# Create system-wide wrapper script
sudo tee /usr/local/bin/escmd << 'EOF'
#!/bin/bash
cd /opt/escmd
python3 escmd.py "$@"
EOF

sudo chmod +x /usr/local/bin/escmd

# Test system-wide access
escmd --help
```

### Development Installation

For development and contributing:

```bash
# Clone repository
git clone <repository-url> escmd-dev
cd escmd-dev

# Create development environment
python3 -m venv dev-env
source dev-env/bin/activate

# Install dependencies with development tools
pip install -r requirements.txt
pip install pylint black pytest  # Development tools

# Install in development mode
pip install -e .
```

## Platform-Specific Instructions

### macOS

```bash
# Install Python 3 if not available
brew install python3

# Install dependencies
pip3 install -r requirements.txt

# Make executable
chmod +x escmd.py
```

### Linux (Ubuntu/Debian)

```bash
# Install Python 3 and pip
sudo apt update
sudo apt install python3 python3-pip

# Install dependencies
pip3 install -r requirements.txt

# Make executable
chmod +x escmd.py
```

### Linux (RHEL/CentOS/Fedora)

```bash
# Install Python 3 and pip
sudo yum install python3 python3-pip  # RHEL/CentOS
# or
sudo dnf install python3 python3-pip  # Fedora

# Install dependencies
pip3 install -r requirements.txt

# Make executable
chmod +x escmd.py
```

### Windows

```powershell
# Install Python from python.org or Microsoft Store
# Open Command Prompt or PowerShell

# Install dependencies
pip install -r requirements.txt

# Run escmd
python escmd.py --help
```

**Windows-Specific Notes:**
- Use `python` instead of `python3` if Python 3 is your default
- Consider using Windows Subsystem for Linux (WSL) for better terminal experience
- Some Unicode characters may not display properly in older Windows terminals

## Troubleshooting Installation

### Common Issues

#### Python Version Issues
```bash
# Check Python version
python3 --version

# If python3 is not available, try:
python --version

# Ensure version is 3.6 or higher
```

#### Dependency Installation Failures
```bash
# Update pip first
pip3 install --upgrade pip

# Install with verbose output for debugging
pip3 install -v -r requirements.txt

# Install without cache if needed
pip3 install --no-cache-dir -r requirements.txt
```

#### Permission Issues
```bash
# Install to user directory instead of system-wide
pip3 install --user -r requirements.txt

# Or use virtual environment
python3 -m venv escmd-env
source escmd-env/bin/activate
pip install -r requirements.txt
```

#### SSL/Certificate Issues
```bash
# Update certificates
pip3 install --upgrade certifi

# If behind corporate firewall, use trusted hosts
pip3 install --trusted-host pypi.org --trusted-host pypi.python.org -r requirements.txt
```

#### Terminal Display Issues
```bash
# Test Unicode support
python3 -c "print('✅ 🔍 📊 🎯')"

# If Unicode doesn't display properly, enable ASCII mode
# Add to elastic_servers.yml:
# settings:
#   ascii_mode: true
```

### Performance Optimization

#### Large Cluster Optimization
```yaml
# Add to elastic_servers.yml for better performance with large clusters
settings:
  enable_paging: true
  paging_threshold: 30
  ascii_mode: false  # Keep rich formatting but reduce complexity if needed
```

#### Network Optimization
```yaml
# For slow networks or high-latency connections
settings:
  # Use quick mode by default
  default_quick_mode: true
  # Increase timeouts
  request_timeout: 60
```

### Validation

After installation, validate your setup:

```bash
# 1. Check version and basic functionality
python3 escmd.py version

# 2. Validate configuration file syntax
python3 escmd.py show-settings

# 3. Test cluster connectivity
python3 escmd.py ping

# 4. Test basic commands
python3 escmd.py health --quick

# 5. Test rich formatting
python3 escmd.py --help
```

Expected results:
- Version command shows current version
- Configuration is loaded without errors
- Ping succeeds and shows cluster information
- Health command returns cluster status
- Help displays with rich formatting and colors

## Next Steps

After successful installation:

1. **Configure Clusters**: See [Cluster Setup Guide](cluster-setup.md)
2. **Authentication**: Configure authentication in [Authentication Guide](authentication.md)
3. **Usage**: Start with [Quick Start Examples](../workflows/monitoring-workflows.md)
4. **Customization**: Explore configuration options for your environment

## Getting Help

If you encounter issues during installation:

1. **Check Requirements**: Ensure Python 3.6+ and all dependencies are installed
2. **Review Logs**: Look for specific error messages in installation output
3. **Test Components**: Test Python, pip, and individual dependencies separately
4. **Environment**: Consider using virtual environments to isolate dependencies
5. **Documentation**: Review platform-specific instructions above

For ongoing support and troubleshooting, see the [Troubleshooting Guide](../reference/troubleshooting.md).
