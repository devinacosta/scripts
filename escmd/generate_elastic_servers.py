#!/usr/bin/env python3
"""
Elasticsearch Servers Configuration Generator

This script reads crosscluster YAML configuration files and generates
a new elastic_servers.yml configuration by connecting to each cluster,
discovering nodes, and selecting 2 data nodes per cluster.

Usage:
    python generate_elastic_servers.py [--output OUTPUT_FILE] [--dry-run]

Author: Automated Script Generator
"""

import os
import sys
import yaml
import json
import hashlib
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConnectionError, AuthenticationException, AuthorizationException, NotFoundError
from elasticsearch import exceptions
import urllib3
import warnings
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich import print as rprint
import requests

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore", message=".*verify_certs=False.*", category=Warning)

# Suppress Elasticsearch warnings
from elasticsearch import ElasticsearchWarning
warnings.filterwarnings("ignore", category=ElasticsearchWarning)
warnings.filterwarnings("ignore", message=".*unable to verify that the server is Elasticsearch.*", category=Warning)

class ElasticsearchServerGenerator:
    """
    Elasticsearch Servers Configuration Generator
    
    This class manages two types of environments:
    1. config_env: Source environment from crosscluster files (us, stress, att, eu, etc.)
                   - Used for tracking which environment file a server came from
                   - Used for merge logic to avoid cross-environment deletions
    2. env: Password environment (prod, eu, lab, ops, etc.)
            - Used for credential mapping based on location
            - Multiple config_envs can map to the same password env
    
    This separation prevents accidental deletion of servers from different
    crosscluster files that happen to use the same password environment.
    """
    
    def __init__(self, yml_directory: str = "yml", output_file: str = "elastic_servers_new.yml", 
                 environment: str = "all", update_mode: bool = False):
        self.yml_directory = yml_directory
        self.output_file = output_file
        self.environment = environment
        self.update_mode = update_mode
        self.clusters_config = {}
        self.generated_servers = []
        self.passwords = {}
        self.existing_config = None
        self.console = Console()
        
        # Environment to crosscluster file mapping
        self.env_file_mapping = {
            'biz': 'crosscluster.nodes_att.yml',
            'eu': 'crosscluster.nodes_eu.yml',
            'in': 'crosscluster.nodes_in.yml',
            'lab': 'crosscluster.nodes_lab.yml',
            'ops': 'crosscluster.nodes_ops.yml',
            'stress': 'crosscluster.nodes_stress.yml',
            'us': 'crosscluster.nodes_us.yml'
        }
        
        # Location to environment mapping
        self.location_env_mapping = {
            'lab': 'lab',
            'ops': 'ops', 
            'stress': 'stress',
            'na_sa': 'prod',  # US/APAC prod
            'apac': 'prod',   # US/APAC prod  
            'eu': 'eu',       # EU prod
            'india': 'in',    # India prod
            'biz': 'biz'      # Biz prod
        }
        
        # Environment-specific password fallback chains
        # Some environments like ATT might have clusters using different password environments
        self.env_password_chains = {
            'biz': ['biz', 'prod'],  # ATT/BIZ environment: try BIZ first, then PROD
            'att': ['att', 'prod'],  # ATT alternative: try ATT, then PROD  
            'eu': ['eu'],            # EU uses only EU passwords
            'lab': ['lab'],          # LAB uses only LAB passwords
            'ops': ['ops'],          # OPS uses only OPS passwords
            'stress': ['stress'],    # STRESS uses only STRESS passwords
            'us': ['prod'],          # US uses only PROD passwords
            'in': ['in']             # India uses only India passwords
        }
        
        # Generate password hashes first
        self._generate_password_hashes()
        
        # Load existing configuration if in update mode
        if self.update_mode:
            self._load_existing_config()
    
    def _generate_password_hashes(self):
        """Generate SHA512 password hashes for different environments"""
        password_seeds = {
            'lab': 'kibana_lab',
            'ops': 'kibana_ops',
            'stress': 'kibana_stress',
            'prod': 'kibana_us',  # US/APAC
            'eu': 'kibana_eu',
            'in': 'kibana_in',
            'biz': 'kibana_biz'
        }
        
        for env, seed in password_seeds.items():
            # Generate SHA512 hash
            hash_result = hashlib.sha512(seed.encode()).hexdigest()
            self.passwords[env] = {
                'kibana_system': hash_result
            }
        
        # Add Default password for old systems
        self.passwords['default'] = {
            'kibana': 'kibana'
        }
        
        self.console.print(f"✅ Generated password hashes for environments: {list(self.passwords.keys())}", style="green")
    
    def _load_existing_config(self):
        """Load existing configuration file if it exists"""
        if os.path.exists(self.output_file):
            try:
                with open(self.output_file, 'r') as f:
                    self.existing_config = yaml.safe_load(f)
                self.console.print(f"📁 Loaded existing configuration from {self.output_file}", style="blue")
                
                # Use existing passwords if available, but don't overwrite newly generated ones
                if self.existing_config and 'passwords' in self.existing_config:
                    existing_passwords = self.existing_config['passwords']
                    # Only preserve existing passwords for environments we didn't regenerate
                    for env, creds in existing_passwords.items():
                        if env not in self.passwords:
                            self.passwords[env] = creds
                        # Don't merge/update - keep the newly generated passwords as they are
                
            except Exception as e:
                self.console.print(f"⚠️  Warning: Could not load existing configuration: {e}", style="yellow")
                self.existing_config = None
        else:
            self.console.print(f"ℹ️  No existing configuration found at {self.output_file}", style="cyan")
    
    def read_crosscluster_files(self) -> Dict:
        """Read crosscluster YAML files from the yml directory (filtered by environment if specified)"""
        crosscluster_configs = {}
        yml_path = Path(self.yml_directory)
        
        if not yml_path.exists():
            raise FileNotFoundError(f"Directory {self.yml_directory} not found")
        
        # Determine which files to process
        if self.environment == 'all':
            # Find all crosscluster.nodes_*.yml files
            crosscluster_files = list(yml_path.glob("crosscluster.nodes_*.yml"))
        else:
            # Process only the specified environment
            if self.environment not in self.env_file_mapping:
                raise ValueError(f"Unknown environment: {self.environment}. Valid options: {list(self.env_file_mapping.keys())}")
            
            target_file = yml_path / self.env_file_mapping[self.environment]
            if not target_file.exists():
                raise FileNotFoundError(f"Environment file not found: {target_file}")
            
            crosscluster_files = [target_file]
        
        if not crosscluster_files:
            raise FileNotFoundError(f"No crosscluster.nodes_*.yml files found in {self.yml_directory}")
        
        self.console.print(f"🌍 Processing environment(s): {self.environment}", style="bold cyan")
        
        # Use Rich progress bar for file reading
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=self.console
        ) as progress:
            
            file_task = progress.add_task("Reading configuration files...", total=len(crosscluster_files))
            
            for file_path in crosscluster_files:
                progress.update(file_task, description=f"Reading {file_path.name}")
                try:
                    with open(file_path, 'r') as f:
                        config = yaml.safe_load(f)
                        if config:
                            # Extract environment name from filename (e.g., crosscluster.nodes_us.yml -> us)
                            env_name = file_path.stem.replace('crosscluster.nodes_', '')
                            crosscluster_configs[env_name] = config
                            self.console.print(f"  ✅ Loaded {len(config)} clusters from {file_path.name}", style="green")
                except yaml.YAMLError as e:
                    self.console.print(f"  ❌ Error reading {file_path.name}: {e}", style="red")
                    continue
                
                progress.advance(file_task)
        
        return crosscluster_configs
    
    def resolve_hostname_via_racktables(self, hostname: str) -> Optional[str]:
        """
        Resolve hostname using RackTables API when DNS resolution fails.
        Tries production RT first, then stage RT if not found.
        
        Args:
            hostname: The hostname to resolve (e.g., 'aex09-c01-esm01')
            
        Returns:
            The resolved FQDN if found, None otherwise
        """
        # RackTables API endpoints
        rt_urls = [
            "http://rt.ringcentral.com/api/hosts/search",      # Production
            "http://rt.stage.ringcentral.com/api/hosts/search"  # Stage
        ]
        
        for rt_url in rt_urls:
            try:
                # Query RackTables API
                params = {
                    'q': f'name~{hostname}$',
                    'fields': 'fqdn'
                }
                
                self.console.print(f"    🔍 Querying RackTables: {rt_url.split('//')[1].split('/')[0]}", style="cyan")
                
                response = requests.get(rt_url, params=params, timeout=30)
                response.raise_for_status()
                
                # RackTables returns plain text, not JSON
                resolved_fqdn = response.text.strip()
                
                # Check if we got a valid response
                if resolved_fqdn and '.' in resolved_fqdn:
                    # Validate that it looks like a valid FQDN
                    self.console.print(f"    ✅ RackTables resolved '{hostname}' → '{resolved_fqdn}'", style="green")
                    return resolved_fqdn
                    
                self.console.print(f"    ❌ No valid FQDN found in RackTables response: '{resolved_fqdn}'", style="yellow")
                
            except requests.exceptions.RequestException as e:
                self.console.print(f"    ⚠️ RackTables query failed: {e}", style="yellow")
            except (ValueError, KeyError) as e:
                self.console.print(f"    ⚠️ Invalid RackTables response format: {e}", style="yellow")
        
        self.console.print(f"    ❌ Could not resolve '{hostname}' via RackTables", style="red")
        return None

    def test_basic_connectivity(self, host: str, port: int, ssl: bool) -> Tuple[bool, str]:
        """
        Test basic HTTP connectivity without authentication.
        If DNS resolution fails, try to resolve via RackTables API.
        
        Returns:
            Tuple[bool, str]: (success, resolved_hostname)
        """
        protocol = 'https' if ssl else 'http'
        url = f"{protocol}://{host}:{port}/"
        
        try:
            self.console.print(f"    🔗 Testing basic connectivity to {url}...", style="dim cyan")
            response = requests.get(url, verify=False, timeout=5)
            if response.status_code == 200:
                self.console.print(f"    ✅ Basic connectivity test: HTTP {response.status_code}", style="green")
            else:
                self.console.print(f"    ⚠️  Basic connectivity test: HTTP {response.status_code}", style="yellow")
            return True, host
        except requests.exceptions.RequestException as e:
            self.console.print(f"    ❌ Basic connectivity failed: {e}", style="red")
            
            # Check if this is a DNS resolution error
            if "Failed to establish a new connection" in str(e) or "nodename nor servname provided" in str(e):
                self.console.print(f"    🔧 DNS resolution failed, trying RackTables API...", style="yellow")
                
                # Try to resolve hostname via RackTables
                resolved_hostname = self.resolve_hostname_via_racktables(host)
                if resolved_hostname:
                    # Retry connectivity with resolved hostname
                    resolved_url = f"{protocol}://{resolved_hostname}:{port}/"
                    try:
                        self.console.print(f"    🔗 Retrying connectivity with resolved hostname: {resolved_url}...", style="dim cyan")
                        response = requests.get(resolved_url, verify=False, timeout=5)
                        if response.status_code == 200:
                            self.console.print(f"    ✅ RackTables-resolved connectivity: HTTP {response.status_code}", style="green")
                        else:
                            self.console.print(f"    ⚠️  RackTables-resolved connectivity: HTTP {response.status_code}", style="yellow")
                        return True, resolved_hostname
                    except requests.exceptions.RequestException as retry_e:
                        self.console.print(f"    ❌ Even resolved hostname failed: {retry_e}", style="red")
                        return False, host
                else:
                    self.console.print(f"    ❌ RackTables resolution failed, cannot proceed", style="red")
                    return False, host
            else:
                # Non-DNS error, don't try RackTables
                return False, host
    
    def get_credential_chains_for_location(self, location: str, file_env: str = None) -> List[Tuple[str, str, str]]:
        """Get list of credentials to try for a location (username, password, env_name)"""
        env = self.location_env_mapping.get(location.lower(), 'prod')
        
        # Smart fallback: if location is unknown/missing, use the file environment
        if location.lower() in ['unknown', ''] and file_env:
            # Map file environment to password environment
            file_env_mapping = {
                'eu': 'eu',
                'lab': 'lab', 
                'ops': 'ops',
                'stress': 'stress',
                'att': 'att',
                'in': 'in',
                'us': 'prod',  # US maps to prod
                'biz': 'biz'   # BIZ maps to biz
            }
            env = file_env_mapping.get(file_env, 'prod')
            self.console.print(f"    🔑 Location missing → Using file environment '{file_env}' → Password env '{env}'", style="dim cyan")
        
        # Get password chain for this environment (allows multiple passwords to try)
        password_envs = self.env_password_chains.get(file_env if file_env else env, [env])
        
        credentials_list = []
        for pwd_env in password_envs:
            if pwd_env in self.passwords:
                if 'kibana_system' in self.passwords[pwd_env]:
                    credentials_list.append(('kibana_system', self.passwords[pwd_env]['kibana_system'], pwd_env))
                elif 'kibana' in self.passwords[pwd_env]:
                    credentials_list.append(('kibana', self.passwords[pwd_env]['kibana'], pwd_env))
        
        # Add default fallback
        if not credentials_list:
            credentials_list.append(('kibana', 'kibana', 'default'))
        
        return credentials_list
    
    def connect_to_elasticsearch(self, discovery_host: str, ssl: bool, location: str, file_env: str = None) -> Optional[Tuple[Elasticsearch, str]]:
        """Connect to Elasticsearch cluster and return client"""
        host, port = discovery_host.split(':') if ':' in discovery_host else (discovery_host, '9200')
        port = int(port)
        
        # Get credential chains for this location (supports multiple passwords to try)
        credential_chains = self.get_credential_chains_for_location(location, file_env)
        
        # Base ES connection configuration
        es_config = {
            'hosts': [{'host': host, 'port': port}],
            'use_ssl': ssl,
            'verify_certs': False,
            'ssl_show_warn': False,
            'timeout': 10,  # Reduced timeout to fail faster on blocked requests
            'max_retries': 1,  # Reduced retries for faster debugging
            'retry_on_timeout': False
        }
        
        # Try each credential set in the chain
        for i, (username, password, env_name) in enumerate(credential_chains):
            es_config['http_auth'] = (username, password)
            
            try:
                attempt_info = f"{username} ({env_name})" if len(credential_chains) > 1 else f"{username}"
                if i > 0:
                    self.console.print(f"    🔄 Trying alternative credentials: {attempt_info}...", style="yellow")
                else:
                    self.console.print(f"    🔌 Connecting to {host}:{port} (SSL: {ssl}) with {attempt_info}...", style="cyan")
                
                es = Elasticsearch(**es_config)
                
                # Test connection with detailed error handling
                try:
                    cluster_info = es.info()
                    cluster_name = cluster_info.get('cluster_name', 'unknown')
                    success_msg = f"✅ Connected successfully to cluster: [bold green]{cluster_name}[/bold green]"
                    if i > 0:
                        success_msg += f" (using {env_name} credentials)"
                    self.console.print(f"    {success_msg}")
                    return es, env_name
                except exceptions.AuthorizationException as e:
                    if i == len(credential_chains) - 1:  # Last attempt
                        self.console.print(f"    🚫 Authorization failed (403 Forbidden) with {attempt_info}: {e}", style="red")
                    continue  # Try next credential set
                except exceptions.AuthenticationException as e:
                    if i == len(credential_chains) - 1:  # Last attempt
                        self.console.print(f"    🔒 Authentication failed (401 Unauthorized) with {attempt_info}: {e}", style="red")
                    continue  # Try next credential set
                except exceptions.ConnectionError as e:
                    self.console.print(f"    📡 Connection error with {attempt_info}: {e}", style="red")
                    return None  # Connection issues won't be resolved by different credentials
                except Exception as e:
                    if i == len(credential_chains) - 1:  # Last attempt
                        self.console.print(f"    ❌ Error testing connection with {attempt_info}: {e}", style="red")
                    continue  # Try next credential set
                    
            except Exception as e:
                if i == len(credential_chains) - 1:  # Last attempt
                    self.console.print(f"    ❌ Failed to connect to {host}:{port}: {e}", style="red")
                continue  # Try next credential set
        
        # All credential attempts failed, try final fallback
        self.console.print(f"    🔄 All configured credentials failed, trying kibana:kibana as final fallback...", style="yellow")
        es_config['http_auth'] = ('kibana', 'kibana')
        try:
            es = Elasticsearch(**es_config)
            cluster_info = es.info()
            cluster_name = cluster_info.get('cluster_name', 'unknown')
            self.console.print(f"    ✅ Connected successfully with fallback credentials to cluster: [bold green]{cluster_name}[/bold green]")
            return es, 'default'
        except exceptions.AuthorizationException as e:
            self.console.print(f"    🛡️  403 Forbidden even with kibana:kibana - ReadonlyREST blocking: {e}", style="red")
            return None
        except Exception as e:
            self.console.print(f"    ❌ Final fallback also failed: {e}", style="red")
            return None
    
    def get_cluster_nodes(self, es_client: Elasticsearch) -> List[Dict]:
        """Get all nodes from the cluster and filter for data nodes"""
        try:
            # Get nodes information
            nodes_info = es_client.nodes.info()
            nodes_stats = es_client.nodes.stats()
            
            data_nodes = []
            
            for node_id, node_info in nodes_info['nodes'].items():
                # Check if node is a data node
                node_roles = node_info.get('roles', [])
                if 'data' in node_roles or 'data_content' in node_roles or 'data_hot' in node_roles:
                    node_name = node_info.get('name', node_id)
                    node_host = node_info.get('host', 'unknown')
                    
                    # Get node stats for additional info
                    node_stat = nodes_stats['nodes'].get(node_id, {})
                    
                    data_nodes.append({
                        'id': node_id,
                        'name': node_name,
                        'host': node_host,
                        'roles': node_roles,
                        'transport_address': node_info.get('transport_address', ''),
                        'http_address': node_info.get('http', {}).get('publish_address', '')
                    })
            
            self.console.print(f"    📊 Found {len(data_nodes)} data nodes", style="green")
            return data_nodes
            
        except Exception as e:
            self.console.print(f"    ❌ Error getting cluster nodes: {e}", style="red")
            return []
    
    def select_best_data_nodes(self, data_nodes: List[Dict], cluster_name: str) -> List[Dict]:
        """Select the best 2 different data nodes from the available nodes"""
        if len(data_nodes) == 0:
            self.console.print(f"    ⚠️  Warning: No data nodes found for cluster {cluster_name}", style="yellow")
            return []
        
        if len(data_nodes) == 1:
            self.console.print(f"    ⚠️  Warning: Only 1 data node found for cluster {cluster_name}", style="yellow")
            return data_nodes
        
        # Sort nodes by name for consistent selection
        sorted_nodes = sorted(data_nodes, key=lambda x: x['name'])
        
        # Select first 2 different nodes
        selected = sorted_nodes[:2]
        node_names = [node['name'] for node in selected]
        self.console.print(f"    🎯 Selected data nodes: [bold blue]{', '.join(node_names)}[/bold blue]")
        
        return selected
    
    def create_minimal_config(self, cluster_name: str, discovery_host: str, ssl: bool, location: str, file_env: str) -> Dict:
        """Create minimal configuration using discovery host when node discovery fails"""
        self.console.print(f"    🔧 Creating minimal config for {cluster_name} using discovery host", style="yellow")
        
        # Extract host and port
        host, port = discovery_host.split(':') if ':' in discovery_host else (discovery_host, '9200')
        port = int(port)
        
        # For minimal config, use the first password environment from the chain
        # since we couldn't actually test which one would work
        password_envs = self.env_password_chains.get(file_env, ['prod'])
        env = password_envs[0]  # Use the first (preferred) password environment
        
        # Create server configuration using discovery host
        server_config = {
            'name': cluster_name,
            'env': env,  # Preferred password environment for this file_env
            'config_env': file_env,  # Source environment from crosscluster file (us, stress, att, etc.) - used for merge logic
            'hostname': host,  # Use discovery host
            'port': port,
            'use_ssl': ssl,
            'verify_certs': False,
            'elastic_authentication': True,
            'elastic_username': 'kibana_system'
        }
        
        # Add comment explaining the fallback
        fallback_comment = f"# Using discovery host (node discovery failed - possibly ReadonlyREST): {discovery_host}"
        server_config['_primary_node_comment'] = fallback_comment
        
        self.console.print(f"    ✅ Generated minimal config for {cluster_name}: [bold]{host}:{port}[/bold] (discovery host fallback)", style="green")
        return server_config
    
    def extract_hostname_from_transport(self, transport_address: str) -> Tuple[str, str]:
        """Extract hostname/IP from transport address
        
        Returns:
            Tuple[str, str]: (ip_or_hostname, original_address)
        """
        # Transport address format is usually "hostname:port" or "ip:port"
        if ':' in transport_address:
            address = transport_address.split(':')[0]
            return address, transport_address
        return transport_address, transport_address
    
    def process_cluster(self, cluster_key: str, cluster_config: Dict, file_env: str) -> Optional[Dict]:
        """Process a single cluster configuration"""
        self.console.print(f"  🔍 Processing cluster: [bold cyan]{cluster_key}[/bold cyan]")
        
        cluster_name = cluster_config.get('cluster.name', cluster_key)
        discovery_host = cluster_config.get('discovery.host')
        ssl = cluster_config.get('ssl', False)
        location = cluster_config.get('location', 'unknown')
        
        if not discovery_host:
            self.console.print(f"    ❌ Error: No discovery.host found for cluster {cluster_key}", style="red")
            return None
        
        # Test basic connectivity first
        host, port = discovery_host.split(':') if ':' in discovery_host else (discovery_host, '9200')
        port = int(port)
        
        connectivity_success, resolved_host = self.test_basic_connectivity(host, port, ssl)
        if not connectivity_success:
            self.console.print(f"    ⏭️  Basic connectivity failed - skipping cluster {cluster_name}", style="yellow")
            return None
        
        # Use resolved hostname if different from original
        effective_discovery_host = discovery_host
        if resolved_host != host:
            # Update discovery host to use resolved hostname
            effective_discovery_host = f"{resolved_host}:{port}"
            self.console.print(f"    🔄 Using resolved hostname for ES connection: {effective_discovery_host}", style="cyan")
        
        # Connect to Elasticsearch
        connection_result = self.connect_to_elasticsearch(effective_discovery_host, ssl, location, file_env)
        if not connection_result:
            # If connection failed, try to create a minimal config using discovery host
            self.console.print(f"    🔧 ES connection failed, creating minimal config using discovery host", style="yellow")
            return self.create_minimal_config(cluster_name, effective_discovery_host, ssl, location, file_env)
        
        es_client, successful_password_env = connection_result
        
        # Get data nodes
        data_nodes = self.get_cluster_nodes(es_client)
        if not data_nodes:
            # If node discovery failed (ReadonlyREST blocking), use discovery host
            self.console.print(f"    🔧 Node discovery failed (possibly ReadonlyREST), using discovery host as fallback", style="yellow")
            return self.create_minimal_config(cluster_name, effective_discovery_host, ssl, location, file_env)
        
        # Select best 2 data nodes
        selected_nodes = self.select_best_data_nodes(data_nodes, cluster_name)
        if not selected_nodes:
            return None
        
        # Extract hostnames and IPs from selected data nodes
        host_data = []
        for node in selected_nodes:
            # Try to extract hostname from transport address first
            address, original_transport = self.extract_hostname_from_transport(node['transport_address'])
            if address and address != 'unknown':
                host_data.append({
                    'address': address,
                    'original_hostname': node['name'],
                    'transport_address': original_transport,
                    'host_field': node['host']
                })
            else:
                # Fallback to host field
                host_data.append({
                    'address': node['host'],
                    'original_hostname': node['name'],
                    'transport_address': node['transport_address'],
                    'host_field': node['host']
                })
        
        # Ensure we have at least one hostname
        if not host_data:
            self.console.print(f"    ❌ Error: Could not extract hostnames for cluster {cluster_name}", style="red")
            return None
        
        # Get port from discovery host
        port = int(discovery_host.split(':')[1]) if ':' in discovery_host else 9200
        
        # Use the password environment that actually worked for authentication
        env = successful_password_env
        
        # Create server configuration
        server_config = {
            'name': cluster_name,
            'env': env,  # Password environment that actually worked (biz, prod, eu, lab, etc.)
            'config_env': file_env,  # Source environment from crosscluster file (us, stress, att, etc.) - used for merge logic
            'hostname': host_data[0]['address'],  # Use IP address of first data node
            'port': port,
            'use_ssl': ssl,
            'verify_certs': False,
            'elastic_authentication': True,
            'elastic_username': 'kibana_system'
        }
        
        # Add hostname comment for primary host
        primary_comment = f"# Primary data node: {host_data[0]['original_hostname']} ({host_data[0]['transport_address']})"
        server_config['_primary_node_comment'] = primary_comment
        
        # Add second hostname if we have a second data node
        if len(host_data) > 1:
            server_config['hostname2'] = host_data[1]['address']  # Use IP address of second data node
            secondary_comment = f"# Secondary data node: {host_data[1]['original_hostname']} ({host_data[1]['transport_address']})"
            server_config['_secondary_node_comment'] = secondary_comment
        
        hostname2_info = f" + {host_data[1]['address']}" if len(host_data) > 1 else ""
        selected_node_names = [node['original_hostname'] for node in host_data]
        self.console.print(f"    ✅ Generated config for [bold green]{cluster_name}[/bold green]: {host_data[0]['address']}:{port}{hostname2_info} (data nodes: {', '.join(selected_node_names)})")
        return server_config
    
    def _yaml_to_string_with_comments(self, config: Dict) -> str:
        """Convert configuration to YAML string with comments"""
        # First convert to YAML without comment keys
        clean_config = self._remove_comment_keys(config)
        yaml_content = yaml.dump(clean_config, default_flow_style=False, sort_keys=False, indent=2)
        
        # Add comments for servers
        lines = yaml_content.split('\n')
        output_lines = []
        
        for i, line in enumerate(lines):
            output_lines.append(line)
            
            # Check if this line defines a server hostname
            if '  hostname:' in line and i > 0:
                # Find the corresponding server config
                server_name = None
                for j in range(i-1, -1, -1):
                    if lines[j].startswith('- name:'):
                        server_name = lines[j].replace('- name:', '').strip()
                        break
                
                if server_name:
                    # Find the original server config with comments
                    for server in config.get('servers', []):
                        if server.get('name') == server_name:
                            if '_primary_node_comment' in server:
                                output_lines.append(f"  {server['_primary_node_comment']}")
                            break
            
            # Check if this line defines a server hostname2
            elif '  hostname2:' in line:
                # Find the corresponding server config
                server_name = None
                for j in range(i-1, -1, -1):
                    if lines[j].startswith('- name:'):
                        server_name = lines[j].replace('- name:', '').strip()
                        break
                
                if server_name:
                    # Find the original server config with comments
                    for server in config.get('servers', []):
                        if server.get('name') == server_name:
                            if '_secondary_node_comment' in server:
                                output_lines.append(f"  {server['_secondary_node_comment']}")
                            break
        
        return '\n'.join(output_lines)
    
    def _remove_comment_keys(self, config: Dict) -> Dict:
        """Remove comment keys from configuration recursively"""
        if isinstance(config, dict):
            clean_config = {}
            for key, value in config.items():
                if not key.startswith('_') or not key.endswith('_comment'):
                    clean_config[key] = self._remove_comment_keys(value)
            return clean_config
        elif isinstance(config, list):
            return [self._remove_comment_keys(item) for item in config]
        else:
            return config
    
    def _write_yaml_with_comments(self, config: Dict, filename: str):
        """Write configuration to YAML file with comments"""
        yaml_content = self._yaml_to_string_with_comments(config)
        with open(filename, 'w') as f:
            f.write(yaml_content)
    
    def _merge_configurations(self, new_servers: List[Dict]) -> Dict:
        """Merge new servers with existing configuration"""
        if not self.existing_config:
            # No existing config, create new one
            return {
                'settings': {
                    'box_style': 'SQUARE_DOUBLE_HEAD',
                    'health_style': 'dashboard',
                    'classic_style': 'panel',
                    'enable_paging': False,
                    'paging_threshold': 50,
                    'show_legend_panels': False,
                    'ascii_mode': False,
                    'dangling_cleanup': {
                        'max_retries': 3,
                        'retry_delay': 5,
                        'timeout': 60,
                        'default_log_level': 'INFO',
                        'enable_progress_bar': True,
                        'confirmation_required': True
                    }
                },
                'cluster_groups': {},
                'passwords': self.passwords,
                'servers': new_servers
            }
        
        # Merge with existing configuration
        merged_config = dict(self.existing_config)
        
        # Update passwords
        merged_config['passwords'] = self.passwords
        
        # Get environment being processed
        if self.environment == 'all':
            # Replace all servers
            merged_config['servers'] = new_servers
        else:
            # Remove existing servers from the same CONFIG environment and add new ones
            existing_servers = merged_config.get('servers', [])
            
            # Find config environments being processed (not password environments)
            processed_config_envs = set()
            for server in new_servers:
                processed_config_envs.add(server.get('config_env', server.get('env')))  # fallback to env for older configs
            
            # Keep servers from other config environments
            filtered_servers = [
                server for server in existing_servers
                if server.get('config_env', server.get('env')) not in processed_config_envs
            ]
            
            # Add new servers
            merged_config['servers'] = filtered_servers + new_servers
            
            self.console.print(f"🗑️  Removed {len(existing_servers) - len(filtered_servers)} existing servers for config environment(s): {processed_config_envs}", style="yellow")
            self.console.print(f"➕ Added {len(new_servers)} new servers", style="green")
        
        return merged_config
    
    def generate_config(self, dry_run: bool = False, replace_mode: bool = False) -> Dict:
        """Generate the complete elastic_servers.yml configuration"""
        # Auto-enable update mode when processing single environment (unless explicitly processing 'all' or using --replace)
        auto_update_mode = self.environment != 'all' and not self.update_mode and not replace_mode
        effective_update_mode = self.update_mode or auto_update_mode
        
        mode_msg = f"Processing environment: {self.environment}"
        if effective_update_mode:
            if auto_update_mode:
                mode_msg += " (AUTO-MERGE MODE - preserving other environments)"
            else:
                mode_msg += " (UPDATE MODE)"
        
        # Create a nice header panel
        header_panel = Panel(
            Text(f"🚀 Elasticsearch Servers Configuration Generator\n{mode_msg}", justify="center"),
            style="bold cyan",
            border_style="cyan"
        )
        self.console.print(header_panel)
        
        # Auto-load existing config if we're going to merge and haven't loaded yet
        if effective_update_mode and not self.existing_config:
            self._load_existing_config()
        
        # Read crosscluster files (filtered by environment if specified)
        crosscluster_configs = self.read_crosscluster_files()
        
        generated_servers = []
        
        # Count total clusters for progress tracking
        total_clusters = sum(len(clusters) for clusters in crosscluster_configs.values())
        
        # Process each environment file with progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=self.console
        ) as progress:
            
            main_task = progress.add_task("Processing clusters...", total=total_clusters)
            
            for file_env, clusters in crosscluster_configs.items():
                env_panel = Panel(
                    f"📂 Processing environment file: [bold yellow]{file_env}[/bold yellow] ({len(clusters)} clusters)",
                    style="blue",
                    border_style="blue"
                )
                self.console.print(env_panel)
                
                for cluster_key, cluster_config in clusters.items():
                    if not isinstance(cluster_config, dict):
                        progress.advance(main_task)
                        continue
                    
                    progress.update(main_task, description=f"Processing {cluster_key}")
                    # Pass the command line environment, not the extracted filename environment
                    server_config = self.process_cluster(cluster_key, cluster_config, self.environment if self.environment != 'all' else file_env)
                    if server_config:
                        generated_servers.append(server_config)
                    
                    progress.advance(main_task)
        
        # Generate final configuration (merge if in update mode or auto-merge mode)
        if effective_update_mode:
            final_config = self._merge_configurations(generated_servers)
        else:
            final_config = {
                'settings': {
                    'box_style': 'SQUARE_DOUBLE_HEAD',
                    'health_style': 'dashboard',
                    'classic_style': 'panel',
                    'enable_paging': False,
                    'paging_threshold': 50,
                    'show_legend_panels': False,
                    'ascii_mode': False,
                    'dangling_cleanup': {
                        'max_retries': 3,
                        'retry_delay': 5,
                        'timeout': 60,
                        'default_log_level': 'INFO',
                        'enable_progress_bar': True,
                        'confirmation_required': True
                    }
                },
                'cluster_groups': {},  # Can be populated later
                'passwords': self.passwords,
                'servers': generated_servers
            }
        
        total_servers = len(final_config['servers'])
        
        # Create summary table
        summary_table = Table(title="🎯 Generation Summary", style="bold")
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="green")
        
        summary_table.add_row("Environment", self.environment)
        summary_table.add_row("Total Servers", str(total_servers))
        summary_table.add_row("Generated/Updated", str(len(generated_servers)))
        summary_table.add_row("Mode", "Auto-Merge" if effective_update_mode and auto_update_mode else "Update" if effective_update_mode else "Replace")
        
        self.console.print(summary_table)
        
        if not dry_run:
            # Write to file with comments
            self._write_yaml_with_comments(final_config, self.output_file)
            self.console.print(f"📁 Configuration written to [bold green]{self.output_file}[/bold green]")
        else:
            self.console.print("[bold yellow]🔍 DRY RUN - Configuration not written to file[/bold yellow]")
            if len(generated_servers) <= 5:  # Only show preview for small number of servers
                self.console.print(f"\n📋 Generated configuration preview:")
                # In dry run, just show the newly generated servers
                preview_config = dict(final_config)
                preview_config['servers'] = generated_servers
                preview_yaml = self._yaml_to_string_with_comments(preview_config)
                # Limit output length for readability
                if len(preview_yaml) > 2000:
                    preview_yaml = preview_yaml[:2000] + "\n... (truncated)"
                self.console.print(preview_yaml)
        
        return final_config

def main():
    parser = argparse.ArgumentParser(description='Generate Elasticsearch servers configuration')
    parser.add_argument('--output', '-o', default='elastic_servers_new.yml',
                       help='Output file name (default: elastic_servers_new.yml)')
    parser.add_argument('--yml-dir', default='yml',
                       help='Directory containing crosscluster YAML files (default: yml)')
    parser.add_argument('--environment', '--env', 
                       choices=['biz', 'eu', 'in', 'lab', 'ops', 'stress', 'us', 'all'],
                       default='all',
                       help='Process specific environment only (default: all)')
    parser.add_argument('--update', action='store_true',
                       help='Update existing configuration file instead of replacing it')
    parser.add_argument('--replace', action='store_true',
                       help='Replace entire file even when processing single environment (disables auto-merge)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be generated without writing to file')
    
    args = parser.parse_args()
    
    try:
        generator = ElasticsearchServerGenerator(
            yml_directory=args.yml_dir,
            output_file=args.output,
            environment=args.environment,
            update_mode=args.update
        )
        
        config = generator.generate_config(dry_run=args.dry_run, replace_mode=args.replace)
        
        console = Console()
        
        if not args.dry_run:
            if args.update or (args.environment != 'all' and not args.replace):
                success_panel = Panel(
                    Text(f"✅ Success! Updated configuration saved to: {args.output}", style="bold green"),
                    style="green",
                    border_style="green"
                )
                console.print(success_panel)
                if args.environment != 'all' and not args.replace:
                    console.print(f"🔀 Environment '{args.environment}' has been merged (other environments preserved)", style="cyan")
                else:
                    console.print(f"➕ Environment '{args.environment}' has been updated/added", style="cyan")
            else:
                success_panel = Panel(
                    Text(f"✅ Success! Generated configuration saved to: {args.output}", style="bold green"),
                    style="green",
                    border_style="green"
                )
                console.print(success_panel)
                if args.replace and args.environment != 'all':
                    console.print(f"🔄 File replaced with only environment '{args.environment}' (--replace mode)", style="yellow")
            
            # Create next steps table
            steps_table = Table(title="📋 Next Steps", style="bold")
            steps_table.add_column("Step", style="cyan", width=5)
            steps_table.add_column("Action", style="white")
            
            steps_table.add_row("1.", f"Review the generated configuration: {args.output}")
            steps_table.add_row("2.", "Test the configuration with a few clusters")
            
            if not args.update and (args.environment == 'all' or args.replace):
                steps_table.add_row("3.", "Backup your current elastic_servers.yml")
                steps_table.add_row("4.", f"Replace elastic_servers.yml with {args.output}")
            else:
                steps_table.add_row("3.", "The configuration has been incrementally updated")
                steps_table.add_row("4.", "Test the new/updated clusters")
            
            console.print(steps_table)
        
    except Exception as e:
        console = Console()
        error_panel = Panel(
            Text(f"❌ Error: {e}", style="bold red"),
            style="red",
            border_style="red"
        )
        console.print(error_panel)
        sys.exit(1)

if __name__ == "__main__":
    main()
