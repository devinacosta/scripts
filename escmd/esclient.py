#!/usr/bin/python3
from elasticsearch import Elasticsearch, ElasticsearchWarning, exceptions, helpers
from elasticsearch.exceptions import NotFoundError, RequestError
from requests.auth import HTTPBasicAuth
from datetime import datetime

from rich import print
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich.progress import BarColumn, Progress, TextColumn
from rich import box

import json
import re
import requests
import urllib3
import warnings
import sys

# Suppress only the InsecureRequestWarning from urllib3 needed for Elasticsearch
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
requests.packages.urllib3.disable_warnings(DeprecationWarning)

# Suppress the UserWarning and SecurityWarning
warnings.filterwarnings("ignore", category=UserWarning, module="elasticsearch")
warnings.filterwarnings("ignore", category=ElasticsearchWarning)
warnings.filterwarnings("ignore", message=".*verify_certs=False.*", category=Warning)

# Check Elasticsearch client version for compatibility
try:
    from elasticsearch import __version__ as es_version
    if isinstance(es_version, tuple):
        ES_VERSION_MAJOR = es_version[0]
    elif isinstance(es_version, str):
        ES_VERSION_MAJOR = int(es_version.split('.')[0])
    else:
        ES_VERSION_MAJOR = 7  # Default fallback
except (ImportError, AttributeError, ValueError, IndexError):
    # Default to assume version 7.x if we can't detect
    ES_VERSION_MAJOR = 7

class ElasticsearchClient:

    def list_dangling_indices(self):
        """Return dangling indices from the cluster."""
        # Use the low-level client for this endpoint
        try:
            # This endpoint is available in ES 7.4+ (/_dangling)
            resp = self.es.transport.perform_request('GET', '/_dangling')
            # Handle both dictionary response (older versions) and TransportApiResponse (newer versions)
            if hasattr(resp, 'body'):
                return resp.body
            elif hasattr(resp, 'get'):
                return resp
            else:
                # If it's not a dict-like object, try to convert it
                return dict(resp) if resp else {}
        except Exception as e:
            return {"error": str(e)}

    def delete_dangling_index(self, uuid):
        """Delete a dangling index by its UUID."""
        try:
            # Use the low-level client for the DELETE endpoint
            # DELETE /_dangling/<index-uuid>?accept_data_loss=true
            # Handle version compatibility between ES client 7.x and 8.x

            if ES_VERSION_MAJOR >= 8:
                # ES client 8.x+ - query parameters included in URL path
                try:
                    resp = self.es.transport.perform_request(
                        'DELETE',
                        f'/_dangling/{uuid}?accept_data_loss=true'
                    )
                except TypeError:
                    # Fallback to 7.x style if the 8.x approach fails
                    resp = self.es.transport.perform_request(
                        'DELETE',
                        f'/_dangling/{uuid}',
                        params={'accept_data_loss': 'true'}
                    )
            else:
                # ES client 7.x - use params keyword argument
                try:
                    resp = self.es.transport.perform_request(
                        'DELETE',
                        f'/_dangling/{uuid}',
                        params={'accept_data_loss': 'true'}
                    )
                except TypeError:
                    # Fallback to 8.x style if the 7.x approach fails
                    resp = self.es.transport.perform_request(
                        'DELETE',
                        f'/_dangling/{uuid}?accept_data_loss=true'
                    )

            # Handle both dictionary response (older versions) and TransportApiResponse (newer versions)
            if hasattr(resp, 'body'):
                return resp.body
            elif hasattr(resp, 'get'):
                return resp
            else:
                # If it's not a dict-like object, try to convert it
                return dict(resp) if resp else {}
        except Exception as e:
            return {"error": str(e)}

    def resolve_node_ids_to_hostnames(self, node_ids, node_id_to_hostname_map=None):
        """Resolve a list of node IDs to their corresponding hostnames.

        Args:
            node_ids: List of node IDs to resolve
            node_id_to_hostname_map: Optional pre-built mapping to avoid API calls
        """
        try:
            # Use provided mapping or get fresh node data
            if node_id_to_hostname_map is None:
                # Get node information
                nodes_data = self.get_nodes()

                # Create mapping of node ID to hostname
                node_id_to_hostname_map = {}
                for node in nodes_data:
                    node_id_to_hostname_map[node['nodeid']] = node['hostname']

            # Resolve node IDs to hostnames
            resolved_nodes = []
            for node_id in node_ids:
                hostname = node_id_to_hostname_map.get(node_id, f"Unknown({node_id[:8]})")
                resolved_nodes.append(hostname)

            return resolved_nodes

        except Exception as e:
            # If resolution fails, return node IDs with error indication
            return [f"Error({node_id[:8]})" for node_id in node_ids]

    def get_node_id_to_hostname_map(self):
        """Get a mapping of node IDs to hostnames for efficient bulk resolution."""
        try:
            nodes_data = self.get_nodes()
            node_id_to_hostname_map = {}
            for node in nodes_data:
                node_id_to_hostname_map[node['nodeid']] = node['hostname']
            return node_id_to_hostname_map
        except Exception as e:
            return {}
    def __init__(self, host1='localhost', host2='localhost', port=9200, use_ssl=False, verify_certs=False, timeout=60, elastic_authentication=False, elastic_username=None, elastic_password=None, preprocess_indices=True, box_style=box.SIMPLE):
        self.host1 = host1
        self.host2 = host2
        self.port = port
        self.use_ssl = use_ssl
        self.verify_certs = verify_certs
        self.timeout = timeout
        self.box_style = box_style
        self.elastic_authentication = elastic_authentication
        self.elastic_username = elastic_username
        self.elastic_password = elastic_password
        self.elastic_host = host1
        self.timeout = timeout
        self.elastic_port = port
        self.preprocess_indices = preprocess_indices
        self.console = Console()

        # Set Authentication to True if Username/Password NOT None
        if (self.elastic_username != None and self.elastic_password != None):
            self.elastic_authentication = True

        # Create ES connection trying with host1.
        self.es = self.create_es_client(self.host1)

        if not self.es.ping() and self.host2:
            print(f"Connection to {self.host1} failed. Attempting to connect to {self.host2}...")
            self.es = self.create_es_client(self.host2)

            if not self.es.ping():
                attempted_settings1 = f"host:{self.host1}, port:{self.port}, ssl:{self.use_ssl}, verify_certs:{self.verify_certs}"
                attempted_settings2 = f"host:{self.host2}, port:{self.port}, ssl:{self.use_ssl}, verify_certs:{self.verify_certs}"
                self.show_message_box("Connection Error", f"ERROR: There was a 'Connection Error' trying to connect to ES.\nSettings: {attempted_settings1}\nSettings: {attempted_settings2}", message_style="bold white", panel_style="red")
                exit(1)

        if self.preprocess_indices:
            # Get all indices, check for unique patterns, and get latest datastream for each indice
            self.cluster_indices = self.list_indices_stats()
            self.cluster_indices_patterns = self.extract_unique_patterns(self.cluster_indices)
            self.cluster_indices_hot_indexes = self.find_latest_indices(self.cluster_indices)

    def pretty_print_json(self, data, indent=2):
        """
        Pretty print JSON data with Rich formatting if outputting to terminal,
        otherwise use standard JSON output for pipe/redirect compatibility.
        
        Args:
            data: Data to serialize to JSON
            indent: Indentation level for pretty printing (default: 2)
        """
        if sys.stdout.isatty():
            # Output is going to terminal - use Rich pretty printing
            from rich.syntax import Syntax
            from rich.console import Console
            json_str = json.dumps(data, indent=indent, ensure_ascii=False)
            syntax = Syntax(json_str, "json", theme="monokai", line_numbers=False)
            # Create a fresh console instance to avoid any global state issues
            console = Console(file=sys.stdout, force_terminal=True)
            console.print(syntax)
        else:
            # Output is piped/redirected - use standard JSON with no formatting
            json.dump(data, sys.stdout, separators=(',', ':'), ensure_ascii=False)
            sys.stdout.write('\n')  # Add single newline

    def _call_with_version_compatibility(self, method, primary_kwargs, fallback_kwargs):
        """
        Call an Elasticsearch method with version compatibility fallback.

        Args:
            method: The Elasticsearch client method to call
            primary_kwargs: Primary set of keyword arguments to try
            fallback_kwargs: Fallback set of keyword arguments for older versions

        Returns:
            The result of the method call

        Raises:
            The last exception if both attempts fail
        """
        try:
            return method(**primary_kwargs)
        except TypeError as e:
            if "unexpected keyword argument" in str(e):
                # Try fallback parameters for older versions
                return method(**fallback_kwargs)
            else:
                raise e

    def create_es_client(self, host):
        if self.elastic_authentication:
            return Elasticsearch([{'host': host, 'port': self.port, 'use_ssl': self.use_ssl}],
                               timeout=self.timeout,
                               verify_certs=self.verify_certs,
                               http_auth=(self.elastic_username, self.elastic_password))
        else:
            return Elasticsearch([{'host': host, 'port': self.port, 'use_ssl': self.use_ssl}],
                               timeout=self.timeout,
                               verify_certs=self.verify_certs)

    def delete_indices(self, indice_data):

        with self.console.status("Starting...") as status:

            # Loop over indice data and delete.
            for indice in indice_data:
                indice_name = indice['index']
                status.update(f"Action: Deleting indice {indice_name}")
                try:
                    response = self.es.indices.delete(index=indice_name)
                    if response.get("acknowledged", False):
                        self.console.log(f"Deleted indice: {indice_name}")
                    else:
                        self.console.log(f"Failed to delete index: {indice_name}")
                except NotFoundError:
                    self.console.log(f"Indice Not Found: {indice_name} ")
                except Exception as e:
                    self.console.log(f"Error occured: {e}")
            self.console.log("Process has been completed.")

    def print_enhanced_recovery_status(self, recovery_status):
        """Print enhanced recovery status with Rich formatting"""
        from rich.panel import Panel
        from rich.text import Text
        from rich.columns import Columns
        from rich.table import Table as InnerTable
        from rich.progress import Progress, BarColumn, TextColumn, SpinnerColumn

        console = Console()

        if not recovery_status:
            no_recovery_panel = Panel(
                Text("🎉 No active recovery operations", style="bold green", justify="center"),
                title="🔄 Cluster Recovery Status",
                border_style="green",
                padding=(2, 4)
            )
            print()
            console.print(no_recovery_panel)
            return

        # Calculate recovery statistics
        total_shards = 0
        completed_shards = 0
        active_recoveries = 0
        recovery_types = {}
        stage_counts = {}

        for index, shards in recovery_status.items():
            for shard in shards:
                total_shards += 1
                active_recoveries += 1

                # Count recovery types
                shard_type = shard.get('type', 'unknown')
                recovery_types[shard_type] = recovery_types.get(shard_type, 0) + 1

                # Count stages
                stage = shard.get('stage', 'unknown')
                stage_counts[stage] = stage_counts.get(stage, 0) + 1

                # Check completion
                translog_ops_percent = shard.get('translog_ops_percent', '0%')
                try:
                    percent_value = float(translog_ops_percent.replace('%', '').strip())
                    if percent_value >= 100:
                        completed_shards += 1
                except:
                    pass

        # Create title panel
        title_panel = Panel(
            Text("🔄 Cluster Recovery Status", style="bold blue", justify="center"),
            subtitle=f"Active recovery operations: {active_recoveries}",
            border_style="blue",
            padding=(1, 2)
        )

        # Recovery summary panel
        summary_table = InnerTable(show_header=False, box=None, padding=(0, 1))
        summary_table.add_column("Label", style="bold", no_wrap=True)
        summary_table.add_column("Icon", justify="left", width=3)
        summary_table.add_column("Value", no_wrap=True)

        summary_table.add_row("Total Shards:", "📊", str(total_shards))
        summary_table.add_row("Active Recoveries:", "🔄", str(active_recoveries))

        if total_shards > 0:
            completion_rate = (completed_shards / total_shards) * 100
            summary_table.add_row("Completion Rate:", "✅", f"{completion_rate:.1f}%")

        # Recovery types breakdown
        if recovery_types:
            type_text = ", ".join([f"{count} {rtype}" for rtype, count in recovery_types.items()])
            summary_table.add_row("Recovery Types:", "🔧", type_text)

        summary_panel = Panel(
            summary_table,
            title="📈 Recovery Summary",
            border_style="blue",
            padding=(1, 2)
        )

        # Stage breakdown panel
        if stage_counts:
            stage_table = InnerTable(show_header=False, box=None, padding=(0, 1))
            stage_table.add_column("Stage", style="bold", no_wrap=True)
            stage_table.add_column("Icon", justify="left", width=3)
            stage_table.add_column("Count", no_wrap=True)

            stage_icons = {
                'init': '🔨',
                'index': '📚',
                'start': '🚀',
                'translog': '📝',
                'finalize': '🏁',
                'done': '✅'
            }

            for stage, count in stage_counts.items():
                icon = stage_icons.get(stage, '⚙️')
                stage_table.add_row(stage.title(), icon, str(count))

            stage_panel = Panel(
                stage_table,
                title="🎯 Recovery Stages",
                border_style="cyan",
                padding=(1, 2)
            )
        else:
            stage_panel = Panel(
                Text("No stage information available", style="dim", justify="center"),
                title="🎯 Recovery Stages",
                border_style="dim",
                padding=(1, 2)
            )

        # Detailed recovery table
        recovery_table = Table(show_header=True, header_style="bold white", expand=True)
        recovery_table.add_column("📚 Index", no_wrap=True)
        recovery_table.add_column("🗂️ Shard", justify="center", width=8)
        recovery_table.add_column("🎯 Stage", justify="center", width=12)
        recovery_table.add_column("📤 Source Node", no_wrap=True)
        recovery_table.add_column("📥 Target Node", no_wrap=True)
        recovery_table.add_column("🔧 Type", justify="center", width=10)
        recovery_table.add_column("📊 Progress", justify="center", width=15)

        for index, shards in recovery_status.items():
            for shard in shards:
                shard_id = shard.get('shard', 'N/A')
                stage = shard.get('stage', 'N/A')
                source = shard.get('source_node', 'N/A')
                target = shard.get('target_node', 'N/A')
                shard_type = shard.get('type', 'N/A')
                translog_ops_percent = shard.get('translog_ops_percent', '0%')

                # Determine progress and styling
                try:
                    percent_value = float(translog_ops_percent.replace('%', '').strip())
                    progress_display = self.show_progress_static(int(percent_value))

                    if percent_value >= 100:
                        row_style = "green"
                    elif percent_value >= 75:
                        row_style = "yellow"
                    elif percent_value >= 25:
                        row_style = "cyan"
                    else:
                        row_style = "red"

                except (ValueError, AttributeError):
                    progress_display = "❓ Unknown"
                    row_style = "dim"

                # Format stage with appropriate styling
                stage_styled = stage.title()
                if stage.lower() == 'done':
                    stage_styled = "✅ Done"
                elif stage.lower() == 'finalize':
                    stage_styled = "🏁 Finalize"
                elif stage.lower() == 'translog':
                    stage_styled = "📝 Translog"
                elif stage.lower() == 'index':
                    stage_styled = "📚 Index"
                elif stage.lower() == 'init':
                    stage_styled = "🔨 Init"
                elif stage.lower() == 'start':
                    stage_styled = "🚀 Start"

                recovery_table.add_row(
                    index,
                    shard_id,
                    stage_styled,
                    source,
                    target,
                    shard_type,
                    progress_display,
                    style=row_style
                )

        # Display everything
        print()
        console.print(title_panel)
        print()
        console.print(Columns([summary_panel, stage_panel], expand=True))
        print()
        console.print(Panel(
            recovery_table,
            title="🔄 Active Recovery Operations",
            border_style="blue",
            padding=(1, 2)
        ))

    def exclude_index_from_host(self, index_name=None, host_to_exclude=None):
        """
        Excludes an indice from allocation on a host.

        :param index_name: Name of Index
        :param param host_to_exclude: Hostname to exclude from host.
        :return: True or False if successful.
        """
        settings = {
            "settings": {
                "index.routing.allocation.exclude._name": host_to_exclude
            }
        }
        response = self.es.indices.put_settings(index=index_name, body=settings)
        if response.get('acknowledged'):
            return True
        else:
            return False

    def exclude_index_reset(self, index_name=None):
        """
        Removes Index Settings for _name

        :param index_name: Name of Index
        :return: True or False if successful.
        """
        settings = {
            "settings": {
                "index.routing.allocation.exclude._name": None
            }
        }
        try:
            response = self.es.indices.put_settings(index=index_name, body=settings)
            if response.get('acknowledged'):
                return True, None
            else:
                return False, None
        except NotFoundError as e:
                return False, e

    def extract_unique_patterns(self, data):
        pattern_regex = re.compile(r'^(.*?)-\d{4}\.\d{2}\.\d{2}-\d+$')
        unique_patterns = set()

        for entry in data:
            index = entry.get('index', '')
            match = pattern_regex.match(index)
            if match:
                unique_patterns.add(match.group(1))

        return list(unique_patterns)

    def filter_indices(self, pattern=None, status=None):
        """
        Filters a list of Elasticsearch indices based on a regex pattern or status.

        :param indices: List of index objects (JSON format)
        :param pattern: Regex pattern to match index names (optional, wildcard applied)
        :param status: Status to filter by (optional)
        :return: Filtered list of index objects
        """
        filtered_indices = self.cluster_indices  # Start with full list

        # Apply pattern filter if provided
        if pattern:
            # Check if pattern contains shell-style wildcards
            if '*' in pattern or '?' in pattern:
                # Convert shell-style wildcards to regex
                # Escape regex special chars but preserve * and ?
                escaped = re.escape(pattern)
                # Convert escaped wildcards back to regex equivalents
                escaped = escaped.replace(r'\*', '.*').replace(r'\?', '.')
                regex = re.compile(f"^{escaped}$")  # Exact match with wildcards
            else:
                # Original behavior: substring match
                regex = re.compile(f".*{re.escape(pattern)}.*")  # Wildcard around the pattern
            
            filtered_indices = [index for index in filtered_indices if regex.search(index.get("index", ""))]

        # Apply status filter if provided
        if status:
            filtered_indices = [index for index in filtered_indices if index.get("health") == status.lower()]

        return filtered_indices

    def find_latest_indices(self, data):
        pattern_regex = re.compile(r'^(.*?)-(\d{4}\.\d{2}\.\d{2})-(\d+)$')
        latest_indices = {}

        for entry in data:
            index = entry.get('index', '')
            match = pattern_regex.match(index)
            if match:
                base_pattern, date_str, suffix = match.groups()
                date = datetime.strptime(date_str, "%Y.%m.%d")
                suffix = int(suffix)  # Convert suffix to an integer for proper comparison

                if (base_pattern not in latest_indices or
                    date > latest_indices[base_pattern]["date"] or
                    (date == latest_indices[base_pattern]["date"] and suffix > latest_indices[base_pattern]["suffix"])):

                    latest_indices[base_pattern] = {"index": index, "date": date, "suffix": suffix}

        return [item["index"] for item in latest_indices.values()]

    def flush_synced_elasticsearch(self, host, port, use_ssl=False, authentication=False, username=None, password=None):
        """
        Issue a POST request to Elasticsearch's _flush/synced endpoint.

        Args:
        - host (str): The hostname or IP address of the Elasticsearch instance.
        - port (int): The port number of the Elasticsearch instance.
        - use_ssl (bool): Whether to use SSL/TLS for the connection.
        - authentication (bool): Whether to use HTTP authentication.
        - username (str): The username for HTTP authentication.
        - password (str): The password for HTTP authentication.

        Returns:
        - dict: The JSON response from Elasticsearch.
        """
        scheme = 'https' if use_ssl else 'http'
        url = f"{scheme}://{host}:{port}/_flush/synced"

        if authentication:
            response = requests.post(url, auth=(username, password), verify=False)
        else:
            response = requests.post(url, verify=False)

        return response.json()


    def filter_nodes_by_role(self, nodes_list, role):
        filtered_nodes = []
        for node in nodes_list:
            if role in node['roles']:
                filtered_nodes.append(node)
        return filtered_nodes

    def format_bytes(self, size_in_bytes):
        # Function to convert bytes to a human-readable format
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_in_bytes < 1024.0:
                return f"{size_in_bytes:.2f} {unit}"
            size_in_bytes /= 1024.0

    def size_to_bytes(self, size_str):
        """
        Convert a storage size string to bytes.
        Supports B, KB, MB, GB, TB, PB (case insensitive)
        Examples: '24.9mb', '25M', '103.3M', '1.2GB'

        Args:
            size_str (str): Size string to convert

        Returns:
            int: Size in bytes

        Raises:
            ValueError: If the input format is invalid
        """

        if size_str == None:
            return 0

        # Clean and standardize input
        size_str = size_str.strip().upper()

        # Define unit multipliers
        units = {
            'B': 1,
            'KB': 1024,
            'MB': 1024 ** 2,
            'GB': 1024 ** 3,
            'TB': 1024 ** 4,
            'PB': 1024 ** 5
        }

        # Find the numeric part and unit
        import re
        match = re.match(r'^([\d.]+)([A-Z]+)$', size_str)
        if not match:
            raise ValueError(f"Invalid size format: {size_str}")

        number, unit = match.groups()

        # Handle cases where unit might be shortened (e.g., 'M' instead of 'MB')
        if unit == 'M':
            unit = 'MB'
        elif unit == 'G':
            unit = 'GB'
        elif unit == 'K':
            unit = 'KB'
        elif unit == 'T':
            unit = 'TB'
        elif unit == 'P':
            unit = 'PB'

        # Verify unit is valid
        if unit not in units:
            raise ValueError(f"Invalid unit: {unit}")

        try:
            # Convert size to float and multiply by unit multiplier
            return int(float(number) * units[unit])
        except ValueError:
            raise ValueError(f"Invalid number format: {number}")

    def get_template(self, name=None):
        if name:
            return self.es.indices.get_template(name)
        else:
            return self.es.indices.get_template()

    def get_nodes_fast(self):
        """
        Get basic node information quickly for dashboard (minimal API calls).
        
        Returns:
            list: Basic node information without expensive details
        """
        try:
            # Only get basic node stats - skip detailed info and shard allocation
            stats = self.es.nodes.stats()
            node_stats = self.parse_node_stats(stats)
            
            # Skip version info and shard allocation for speed
            # Just add minimal defaults
            for node in node_stats:
                node.update({
                    'version': 'N/A',  # Skip version lookup for speed
                    'build_hash': None,
                    'build_date': '',
                    'indices_count': 0  # Skip shard allocation lookup for speed
                })
            
            return sorted(node_stats, key=lambda x: x['name'])
            
        except Exception:
            return []

    def get_nodes(self):
        # Get node statistics
        stats = self.es.nodes.stats()
        node_stats = self.parse_node_stats(stats)
        
        # Get node information (including version details)
        try:
            nodes_info = self.es.nodes.info()
            # Create a map of node_id -> version info
            version_info = {}
            for node_id, node_data in nodes_info.get('nodes', {}).items():
                version_data = node_data.get('version', {})
                
                # Handle different version response formats
                if isinstance(version_data, dict):
                    # Standard format: {"number": "7.17.29", "build_hash": "...", ...}
                    version = version_data.get('number', 'Unknown')
                    build_hash = version_data.get('build_hash', '')[:8] if version_data.get('build_hash') else None
                    build_date = version_data.get('build_date', '')
                elif isinstance(version_data, str):
                    # Simple string format: "7.17.29"
                    version = version_data
                    build_hash = None
                    build_date = ''
                else:
                    version = 'Unknown'
                    build_hash = None
                    build_date = ''
                
                version_info[node_id] = {
                    'version': version,
                    'build_hash': build_hash,
                    'build_date': build_date
                }
            
            # Merge version info into node stats
            for node in node_stats:
                node_id = node.get('nodeid')
                if node_id in version_info:
                    node.update(version_info[node_id])
                else:
                    # Fallback if version info not available for this node
                    node.update({
                        'version': 'Unknown',
                        'build_hash': None,
                        'build_date': ''
                    })
                    
        except Exception:
            # If we can't get version info, add defaults
            for node in node_stats:
                node.update({
                    'version': 'Unknown',
                    'build_hash': None,
                    'build_date': ''
                })
        
        # Get actual indices per node by checking shard allocation
        try:
            # Get shard allocation information
            shards = self.es.cat.shards(format='json')
            
            # Create a map of node -> set of unique indices
            indices_per_node = {}
            for shard in shards:
                node_name = shard.get('node')
                index_name = shard.get('index')
                if node_name and index_name:
                    if node_name not in indices_per_node:
                        indices_per_node[node_name] = set()
                    indices_per_node[node_name].add(index_name)
            
            # Update node stats with actual indices count
            for node in node_stats:
                node_name = node.get('name')
                if node_name in indices_per_node:
                    node['indices_count'] = len(indices_per_node[node_name])
                else:
                    node['indices_count'] = 0
                    
        except Exception:
            # If we can't get shard allocation info, fall back to 0
            for node in node_stats:
                node['indices_count'] = 0
        
        nodes_sorted = sorted(node_stats, key=lambda x: x['name'])
        return nodes_sorted

    def get_all_index_settings(self):
        """
        Fetch the settings of all indices in the cluster.

        :return: A Python dictionary containing the settings of all indices.
        """
        try:
            # Fetch settings for all indices
            settings = self.es.indices.get_settings(index="_all")
            return settings
        except Exception as e:
            print(f"Error fetching all index settings: {e}")
            return {}

    def get_all_nodes_stats(self):
        nodes_stats = self.es.nodes.stats()
        return nodes_stats['nodes']

    def get_cluster_info(self):
        """
        Get comprehensive cluster information including version details.
        
        Returns:
            dict: Cluster information including name, version, build details
        """
        try:
            # Get cluster stats for comprehensive information
            cluster_stats = self.es.cluster.stats()
            
            # Extract version information - ES returns versions as simple list in nodes.versions
            versions_list = cluster_stats.get('nodes', {}).get('versions', [])
            if versions_list:
                # For mixed-version clusters, take the first version or most common one
                if len(versions_list) == 1:
                    cluster_version = versions_list[0]
                    version_count = cluster_stats.get('nodes', {}).get('count', {}).get('total', 1)
                else:
                    # In mixed version clusters, take the first version
                    cluster_version = versions_list[0]
                    version_count = 1
            else:
                cluster_version = 'Unknown'
                version_count = 0
            
            # Get cluster name and basic stats
            cluster_name = cluster_stats.get('cluster_name', 'Unknown')
            total_nodes = cluster_stats.get('nodes', {}).get('count', {}).get('total', 0)
            
            # Try to get build information from individual node
            try:
                nodes_info = self.es.nodes.info()
                build_hash = None
                build_date = None
                
                # Get build info from the first available node
                for node_id, node_data in nodes_info.get('nodes', {}).items():
                    version_data = node_data.get('version', {})
                    if version_data:
                        build_hash = version_data.get('build_hash', '')[:8]  # Short hash
                        build_date = version_data.get('build_date', '')
                        break
                        
            except Exception:
                build_hash = None
                build_date = None
            
            return {
                'cluster_name': cluster_name,
                'version': cluster_version,
                'build_hash': build_hash,
                'build_date': build_date,
                'version_count': version_count,
                'total_nodes': total_nodes,
                'mixed_versions': len(versions_list) > 1,
                'all_versions': versions_list if len(versions_list) > 1 else []
            }
            
        except Exception as e:
            # Fallback to basic cluster health for cluster name
            try:
                health = self.es.cluster.health()
                return {
                    'cluster_name': health.get('cluster_name', 'Unknown'),
                    'version': 'Unknown',
                    'build_hash': None,
                    'build_date': None,
                    'version_count': 0,
                    'total_nodes': health.get('number_of_nodes', 0),
                    'mixed_versions': False,
                    'all_versions': [],
                    'error': str(e)
                }
            except:
                return {
                    'cluster_name': 'Unknown',
                    'version': 'Unknown',
                    'build_hash': None,
                    'build_date': None,
                    'version_count': 0,
                    'total_nodes': 0,
                    'mixed_versions': False,
                    'all_versions': [],
                    'error': str(e)
                }

    def get_cluster_health(self, include_version=True):

        # Retrieve cluster health
        cluster_health = self.es.cluster.health()
        cluster_data = {
            'cluster_name': cluster_health['cluster_name'],
            'cluster_status': cluster_health['status'],
            'number_of_nodes': cluster_health['number_of_nodes'],
            'number_of_data_nodes': cluster_health['number_of_data_nodes'],
            'active_primary_shards': cluster_health['active_primary_shards'],
            'active_shards': cluster_health['active_shards'],
            'unassigned_shards': cluster_health['unassigned_shards'],
            'delayed_unassigned_shards': cluster_health['delayed_unassigned_shards'],
            'number_of_pending_tasks': cluster_health['number_of_pending_tasks'],
            'number_of_in_flight_fetch': cluster_health['number_of_in_flight_fetch'],
            'active_shards_percent': cluster_health['active_shards_percent_as_number']
        }

        # Add version information if requested
        if include_version:
            try:
                cluster_info = self.get_cluster_info()
                cluster_data.update({
                    'cluster_version': cluster_info['version'],
                    'build_hash': cluster_info['build_hash'],
                    'build_date': cluster_info['build_date'],
                    'mixed_versions': cluster_info['mixed_versions'],
                    'all_versions': cluster_info['all_versions']
                })
            except Exception:
                cluster_data.update({
                    'cluster_version': 'Unknown',
                    'build_hash': None,
                    'build_date': None,
                    'mixed_versions': False,
                    'all_versions': []
                })

        return cluster_data

    def get_state_color(self, state):
        if state == 'open':
            return 'green'
        elif state == 'closed':
            return 'red'
        elif state == 'readonly':
            return 'yellow'
        else:
            return 'unknown'

    def get_allocation_as_dict(self):

        allocation = self.es.cat.allocation(format='json', bytes='b')

        allocation_dict = {}
        for entry in allocation:
            node = entry['node']
            allocation_dict[node] = {
                'shards': int(entry['shards']),
                'disk.percent': float(entry['disk.percent']) if entry['disk.percent'] is not None else 0,
                'disk.used': int(entry['disk.used']) if entry['disk.used'] is not None else 0,
                'disk.avail': int(entry['disk.avail']) if entry['disk.avail'] is not None else 0,
                'disk.total': int(entry['disk.total']) if entry['disk.total'] is not None else 0
            }

        # Sort the dictionary by keys alphabetically
        sorted_allocation_dict = dict(sorted(allocation_dict.items()))

        return sorted_allocation_dict

    def get_index_allocation_explain(self, index_name, shard_number, is_primary):
        '''
        Get indice allocation explain
        '''
        # Get Allocation information
        request_body = {
            "index": index_name,
            "shard": shard_number,
            "primary": is_primary
        }
        response = self.es.cluster.allocation_explain(body=request_body)

        return response

    def get_enhanced_allocation_explain(self, index_name, shard_number, is_primary):
        """
        Get comprehensive allocation explanation with enhanced details.

        Args:
            index_name (str): Name of the index
            shard_number (int): Shard number
            is_primary (bool): True for primary shard, False for replica

        Returns:
            dict: Enhanced allocation explanation with detailed information
        """
        try:
            # Get basic allocation explanation
            request_body = {
                "index": index_name,
                "shard": shard_number,
                "primary": is_primary
            }
            allocation_explain = self.es.cluster.allocation_explain(body=request_body)

            # Get additional context information
            try:
                # Get cluster nodes information
                nodes_info = self.es.nodes.info()
                nodes_stats = self.es.nodes.stats()

                # Get index information
                index_settings = self.es.indices.get_settings(index=index_name)
                index_stats = self.es.indices.stats(index=index_name)

                # Get cluster settings that might affect allocation
                cluster_settings = self.es.cluster.get_settings()

                # Get shard information for this index
                shards_data = self.get_shards_as_dict()
                index_shards = [s for s in shards_data if s['index'] == index_name]

            except Exception as e:
                # If we can't get additional info, continue with basic explain
                nodes_info = None
                nodes_stats = None
                index_settings = None
                index_stats = None
                cluster_settings = None
                index_shards = []

            # Build enhanced response
            enhanced_result = {
                "basic_explanation": allocation_explain,
                "index_name": index_name,
                "shard_number": shard_number,
                "is_primary": is_primary,
                "shard_type": "primary" if is_primary else "replica",
                "enhancement_metadata": {
                    "nodes_available": len(nodes_info['nodes']) if nodes_info else 0,
                    "total_shards_for_index": len(index_shards),
                    "analysis_timestamp": self._get_current_timestamp()
                }
            }

            # Extract current allocation info
            current_node = allocation_explain.get('current_node')
            if current_node:
                enhanced_result['current_allocation'] = {
                    "allocated": True,
                    "node_id": current_node.get('id'),
                    "node_name": current_node.get('name'),
                    "weight_ranking": current_node.get('weight_ranking'),
                    "allocation_details": current_node
                }
            else:
                enhanced_result['current_allocation'] = {
                    "allocated": False,
                    "reason": "Shard is unassigned"
                }

                # Add unassigned info if available
                unassigned_info = allocation_explain.get('unassigned_info', {})
                enhanced_result['unassigned_details'] = {
                    "reason": unassigned_info.get('reason'),
                    "at": unassigned_info.get('at'),
                    "last_allocation_status": unassigned_info.get('last_allocation_status'),
                    "failed_attempts": unassigned_info.get('failed_allocation_attempts', 0)
                }

            # Process node allocation decisions
            node_allocation_decisions = allocation_explain.get('node_allocation_decisions', [])
            enhanced_result['node_decisions'] = []

            for decision in node_allocation_decisions:
                node_decision = {
                    "node_id": decision.get('node_id'),
                    "node_name": decision.get('node_name'),
                    "transport_address": decision.get('transport_address'),
                    "node_attributes": decision.get('node_attributes', {}),
                    "node_decision": decision.get('node_decision'),
                    "weight_ranking": decision.get('weight_ranking', 0),
                    "deciders": []
                }

                # Process allocation deciders
                for decider in decision.get('deciders', []):
                    decider_info = {
                        "decider": decider.get('decider'),
                        "decision": decider.get('decision'),
                        "explanation": decider.get('explanation')
                    }
                    node_decision['deciders'].append(decider_info)

                enhanced_result['node_decisions'].append(node_decision)

            # Add summary statistics
            enhanced_result['summary'] = self._generate_allocation_summary(enhanced_result)

            return enhanced_result

        except Exception as e:
            # Return basic error information if enhancement fails
            return {
                "error": f"Failed to get allocation explanation: {str(e)}",
                "index_name": index_name,
                "shard_number": shard_number,
                "is_primary": is_primary
            }

    def _get_current_timestamp(self):
        """Get current timestamp for metadata."""
        import datetime
        return datetime.datetime.now().isoformat()

    def _generate_allocation_summary(self, enhanced_result):
        """Generate summary statistics for allocation explanation."""
        summary = {
            "total_nodes_evaluated": len(enhanced_result.get('node_decisions', [])),
            "allocation_possible": False,
            "primary_barriers": [],
            "recommendation": ""
        }

        # Determine if allocation is possible
        if enhanced_result.get('current_allocation', {}).get('allocated'):
            summary['allocation_possible'] = True
            summary['recommendation'] = "Shard is successfully allocated"
        else:
            # Check if any node can accept the shard
            node_decisions = enhanced_result.get('node_decisions', [])
            can_allocate_nodes = [n for n in node_decisions if n.get('node_decision') in ['yes', 'throttle']]

            if can_allocate_nodes:
                summary['allocation_possible'] = True
                summary['recommendation'] = f"Allocation possible on {len(can_allocate_nodes)} node(s)"
            else:
                summary['allocation_possible'] = False

                # Identify primary barriers
                all_deciders = []
                for node in node_decisions:
                    for decider in node.get('deciders', []):
                        if decider.get('decision') == 'no':
                            all_deciders.append(decider.get('decider'))

                # Count barrier frequency
                from collections import Counter
                barrier_counts = Counter(all_deciders)
                summary['primary_barriers'] = [
                    {"barrier": barrier, "affected_nodes": count}
                    for barrier, count in barrier_counts.most_common(3)
                ]

                if summary['primary_barriers']:
                    top_barrier = summary['primary_barriers'][0]['barrier']
                    summary['recommendation'] = f"Address '{top_barrier}' issue to enable allocation"
                else:
                    summary['recommendation'] = "Check cluster allocation settings"

        return summary

    def print_allocation_explain_results(self, explain_result):
        """
        Display allocation explanation results with enhanced Rich formatting.

        Args:
            explain_result (dict): Results from get_enhanced_allocation_explain
        """
        from rich.panel import Panel
        from rich.text import Text
        from rich.columns import Columns
        from rich.console import Console
        from rich.table import Table

        console = Console()

        # Handle error case
        if 'error' in explain_result:
            error_panel = Panel(
                Text(f"❌ {explain_result['error']}", style="bold red", justify="center"),
                title="[bold red]⚠️ Allocation Explain Error[/bold red]",
                border_style="red",
                padding=(1, 2)
            )
            print()
            console.print(error_panel)
            print()
            return

        # Extract key information
        index_name = explain_result.get('index_name', 'Unknown')
        shard_number = explain_result.get('shard_number', 0)
        shard_type = explain_result.get('shard_type', 'unknown').title()
        current_allocation = explain_result.get('current_allocation', {})
        summary = explain_result.get('summary', {})

        # Determine theme colors and icons based on allocation status
        if current_allocation.get('allocated', False):
            theme_color = "green"
            status_icon = "✅"
            status_text = "ALLOCATED"
        elif summary.get('allocation_possible', False):
            theme_color = "yellow"
            status_icon = "⚠️"
            status_text = "UNASSIGNED (Can Allocate)"
        else:
            theme_color = "red"
            status_icon = "❌"
            status_text = "UNASSIGNED (Blocked)"

        # Create title panel
        title_panel = Panel(
            Text(f"⚖️ Allocation Explanation", style=f"bold {theme_color}", justify="center"),
            subtitle=f"Index: {index_name} | Shard: {shard_number} ({shard_type}) | Status: {status_icon} {status_text}",
            border_style=theme_color,
            padding=(1, 2)
        )

        # Create current allocation panel
        if current_allocation.get('allocated', False):
            allocation_table = Table.grid(padding=(0, 3))
            allocation_table.add_column(style="bold white", no_wrap=True)
            allocation_table.add_column(style="bold green")

            node_name = current_allocation.get('node_name', 'Unknown')
            node_id = current_allocation.get('node_id', 'Unknown')
            weight_ranking = current_allocation.get('weight_ranking', 'N/A')

            allocation_table.add_row("🖥️ Allocated Node:", node_name)
            allocation_table.add_row("🆔 Node ID:", node_id)
            allocation_table.add_row("📊 Weight Ranking:", str(weight_ranking))
            allocation_table.add_row("✅ Status:", "Successfully Allocated")

            allocation_panel = Panel(
                allocation_table,
                title="[bold green]✅ Current Allocation[/bold green]",
                border_style="green",
                padding=(1, 2),
                width=50
            )
        else:
            # Unassigned details
            unassigned_details = explain_result.get('unassigned_details', {})
            allocation_table = Table.grid(padding=(0, 3))
            allocation_table.add_column(style="bold white", no_wrap=True)
            allocation_table.add_column(style="bold red")

            reason = unassigned_details.get('reason', 'Unknown')
            last_status = unassigned_details.get('last_allocation_status', 'Unknown')
            failed_attempts = unassigned_details.get('failed_attempts', 0)

            allocation_table.add_row("❌ Status:", "Unassigned")
            allocation_table.add_row("🔍 Reason:", reason)
            allocation_table.add_row("📝 Last Status:", last_status)
            allocation_table.add_row("🔄 Failed Attempts:", str(failed_attempts))

            allocation_panel = Panel(
                allocation_table,
                title="[bold red]❌ Allocation Status[/bold red]",
                border_style="red",
                padding=(1, 2),
                width=50
            )

        # Create summary panel
        summary_table = Table.grid(padding=(0, 3))
        summary_table.add_column(style="bold white", no_wrap=True)
        summary_table.add_column(style=f"bold {theme_color}")

        total_nodes = summary.get('total_nodes_evaluated', 0)
        allocation_possible = summary.get('allocation_possible', False)
        recommendation = summary.get('recommendation', 'No recommendation available')

        summary_table.add_row("🖥️ Nodes Evaluated:", str(total_nodes))
        summary_table.add_row("✅ Can Allocate:", "Yes" if allocation_possible else "No")
        summary_table.add_row("💡 Recommendation:", recommendation)

        # Add primary barriers if they exist
        barriers = summary.get('primary_barriers', [])
        if barriers:
            top_barrier = barriers[0]
            summary_table.add_row("🚫 Top Barrier:", f"{top_barrier['barrier']} ({top_barrier['affected_nodes']} nodes)")

        summary_panel = Panel(
            summary_table,
            title="[bold white]📊 Summary[/bold white]",
            border_style=theme_color,
            padding=(1, 2),
            width=45
        )

        # Create node decisions table
        node_decisions = explain_result.get('node_decisions', [])
        if node_decisions:
            decisions_table = Table(show_header=True, header_style="bold white", title="🖥️ Node Allocation Decisions", expand=True)
            decisions_table.add_column("🖥️ Node Name", style="cyan", no_wrap=True)
            decisions_table.add_column("📋 Decision", justify="center", width=12)
            decisions_table.add_column("📊 Weight", justify="center", width=8)
            decisions_table.add_column("🔍 Primary Reason", style="yellow")
            decisions_table.add_column("🌐 Address", style="dim cyan", no_wrap=True)

            # Sort by weight ranking (lower is better)
            sorted_decisions = sorted(node_decisions, key=lambda x: x.get('weight_ranking', 999))

            for decision in sorted_decisions:
                node_name = decision.get('node_name', 'Unknown')
                node_decision = decision.get('node_decision', 'unknown')
                weight_ranking = decision.get('weight_ranking', 0)
                transport_address = decision.get('transport_address', 'N/A')

                # Format decision with icons
                if node_decision == 'yes':
                    decision_display = "✅ Yes"
                    row_style = "green"
                elif node_decision == 'no':
                    decision_display = "❌ No"
                    row_style = "red"
                elif node_decision == 'throttle':
                    decision_display = "⏸️ Throttle"
                    row_style = "yellow"
                else:
                    decision_display = f"❓ {node_decision.title()}"
                    row_style = "white"

                # Get primary reason from deciders
                deciders = decision.get('deciders', [])
                blocking_deciders = [d for d in deciders if d.get('decision') == 'no']
                if blocking_deciders:
                    primary_reason = blocking_deciders[0].get('decider', 'Unknown')
                elif node_decision == 'yes':
                    primary_reason = "No barriers"
                else:
                    primary_reason = "See details"

                decisions_table.add_row(
                    node_name,
                    decision_display,
                    str(weight_ranking),
                    primary_reason,
                    transport_address,
                    style=row_style
                )

        # Create barriers breakdown if there are issues
        if barriers and len(barriers) > 1:
            barriers_table = Table(show_header=True, header_style="bold white", title="🚫 Allocation Barriers", expand=True)
            barriers_table.add_column("🚫 Barrier Type", style="bold red", no_wrap=True)
            barriers_table.add_column("🖥️ Affected Nodes", justify="center", width=15)
            barriers_table.add_column("📊 Impact", justify="center", width=12)

            for barrier in barriers:
                barrier_name = barrier.get('barrier', 'Unknown')
                affected_nodes = barrier.get('affected_nodes', 0)
                impact_percent = round((affected_nodes / total_nodes * 100), 1) if total_nodes > 0 else 0

                if impact_percent >= 75:
                    impact_display = "🔴 Critical"
                    row_style = "red"
                elif impact_percent >= 50:
                    impact_display = "🟡 High"
                    row_style = "yellow"
                else:
                    impact_display = "🟢 Medium"
                    row_style = "blue"

                barriers_table.add_row(
                    barrier_name,
                    f"{affected_nodes}/{total_nodes}",
                    impact_display,
                    style=row_style
                )

        # Create quick actions panel
        actions_table = Table.grid(padding=(0, 3))
        actions_table.add_column(style="bold magenta", no_wrap=True)
        actions_table.add_column(style="dim white")

        actions_table.add_row("View allocation:", "./escmd.py allocation display")
        actions_table.add_row("Check shards:", f"./escmd.py shards {index_name}")
        actions_table.add_row("Index details:", f"./escmd.py indice {index_name}")
        actions_table.add_row("JSON output:", f"./escmd.py allocation explain {index_name} --format json")

        actions_panel = Panel(
            actions_table,
            title="[bold white]🚀 Quick Actions[/bold white]",
            border_style="magenta",
            padding=(1, 1),
            width=45
        )

        # Display everything
        print()
        console.print(title_panel)
        print()
        console.print(Columns([allocation_panel, summary_panel], expand=True))

        if node_decisions:
            print()
            console.print(decisions_table)

        if barriers and len(barriers) > 1:
            print()
            console.print(barriers_table)

        print()
        console.print(actions_panel)
        print()

    def check_allocation_issues(self):
        """
        Check for allocation issues in the cluster.

        Returns:
            dict: Information about allocation issues found
        """
        try:
            # Get unassigned shards
            shards_data = self.get_shards_as_dict()
            unassigned_shards = [s for s in shards_data if s['state'] == 'UNASSIGNED']

            # Get cluster health for additional context
            health_data = self.es.cluster.health()

            # Calculate allocation statistics
            total_shards = len(shards_data)
            unassigned_count = len(unassigned_shards)
            assigned_count = total_shards - unassigned_count

            allocation_issues = {
                "has_issues": unassigned_count > 0,
                "total_shards": total_shards,
                "assigned_shards": assigned_count,
                "unassigned_shards": unassigned_count,
                "unassigned_percentage": round((unassigned_count / total_shards * 100), 1) if total_shards > 0 else 0,
                "active_shards_percent": health_data.get('active_shards_percent', 100),
                "cluster_status": health_data.get('status', 'unknown'),
                "sample_unassigned": unassigned_shards[:3] if unassigned_shards else []  # Sample for display
            }

            # Determine severity level
            if unassigned_count == 0:
                allocation_issues["severity"] = "none"
                allocation_issues["severity_text"] = "No Issues"
                allocation_issues["severity_icon"] = "✅"
                allocation_issues["theme_color"] = "green"
            elif unassigned_count <= 2:
                allocation_issues["severity"] = "low"
                allocation_issues["severity_text"] = "Minor Issues"
                allocation_issues["severity_icon"] = "⚠️"
                allocation_issues["theme_color"] = "yellow"
            elif unassigned_count <= 10:
                allocation_issues["severity"] = "medium"
                allocation_issues["severity_text"] = "Moderate Issues"
                allocation_issues["severity_icon"] = "🟠"
                allocation_issues["theme_color"] = "orange"
            else:
                allocation_issues["severity"] = "high"
                allocation_issues["severity_text"] = "Critical Issues"
                allocation_issues["severity_icon"] = "🔴"
                allocation_issues["theme_color"] = "red"

            return allocation_issues

        except Exception as e:
            # Return basic error info if check fails
            return {
                "has_issues": False,
                "error": f"Failed to check allocation issues: {str(e)}",
                "severity": "unknown",
                "severity_text": "Check Failed",
                "severity_icon": "❓",
                "theme_color": "dim"
            }

    def _create_allocation_issues_panel(self, allocation_issues):
        """Create allocation issues panel for health dashboard."""
        from rich.panel import Panel
        from rich.table import Table

        if not allocation_issues.get("has_issues", False):
            return None

        # Create inner table
        table = Table.grid(padding=(0, 3))
        table.add_column(style="bold white", no_wrap=True)
        table.add_column(style=f"bold {allocation_issues['theme_color']}")

        # Add allocation issue details
        severity_icon = allocation_issues.get("severity_icon", "⚠️")
        severity_text = allocation_issues.get("severity_text", "Issues Detected")
        unassigned_count = allocation_issues.get("unassigned_shards", 0)
        unassigned_percentage = allocation_issues.get("unassigned_percentage", 0)

        table.add_row("⚠️ Status:", f"{severity_icon} {severity_text}")
        table.add_row("📊 Unassigned Shards:", f"{unassigned_count:,}")
        table.add_row("📈 Impact:", f"{unassigned_percentage:.1f}% of total shards")
        table.add_row("🎯 Active Shards:", f"{allocation_issues.get('active_shards_percent', 0):.1f}%")

        # Add sample unassigned shards if available
        sample_unassigned = allocation_issues.get("sample_unassigned", [])
        if sample_unassigned:
            sample_index = sample_unassigned[0].get('index', 'Unknown')
            table.add_row("📝 Example Index:", sample_index[:30] + "..." if len(sample_index) > 30 else sample_index)

        # Add recommendation
        table.add_row("", "")  # spacing
        if unassigned_count == 1:
            recommend_text = f"./escmd.py allocation explain {sample_unassigned[0].get('index', '')}"
        else:
            recommend_text = "./escmd.py allocation display"
        table.add_row("💡 Quick Action:", recommend_text[:35] + "..." if len(recommend_text) > 35 else recommend_text)

        panel = Panel(
            table,
            title=f"[bold {allocation_issues['theme_color']}]⚠️ Allocation Issues[/bold {allocation_issues['theme_color']}]",
            border_style=allocation_issues['theme_color'],
            padding=(1, 2),
            width=50
        )

        return panel

    def get_index_info(self, index_name):
            try:
                # Get index settings
                settings = self.es.indices.get_settings(index=index_name)
                # Get index mappings
                mappings = self.es.indices.get_mapping(index=index_name)
                # Get index stats
                stats = self.es.indices.stats(index=index_name)
                # Get index health
                health = self.es.cluster.health(index=index_name)

                index_info = {
                    'settings': settings[index_name],
                    'mappings': mappings[index_name],
                    'stats': stats['indices'][index_name],
                    'health': health
                }

                self.print_index_info(index_info)
            except Exception as e:
                print(f"Error retrieving information for index '{index_name}': {e}")

    def get_index_info2(self, index_name):
        try:
            # Get index settings
            settings = self.es.indices.get_settings(index=index_name)
            # Get index stats
            stats = self.es.indices.stats(index=index_name)
            # Get index health
            index_status = self.es.indices.get(index=index_name, format='json')
            index_health = stats['indices'][index_name]['state']

            # Extract the required information
            number_of_replicas = settings[index_name]['settings']['index']['number_of_replicas']
            number_of_shards = settings[index_name]['settings']['index']['number_of_shards']
            disk_used = stats['indices'][index_name]['total']['store']['size_in_bytes']

            # Determine index health based on shard allocation
            shard_stats = stats['indices'][index_name]['shards']
            primary_shards = sum(1 for shard in shard_stats if shard['routing']['primary'])
            replica_shards = sum(1 for shard in shard_stats if not shard['routing']['primary'])
            unassigned_shards = sum(1 for shard in shard_stats if shard['routing']['state'] != 'STARTED')

            # Convert disk used to a more readable format (e.g., MB, GB)
            disk_used_gb = disk_used / (1024 * 1024 * 1024)

            # Create a Rich table
            table = Table(title="Index Information")

            table.add_column("Health", justify="right", style="white")
            table.add_column("Indice", justify="left", style="cyan", no_wrap=True)
            table.add_column("Allocation", justify="right", style="magenta")
            table.add_column("Disk Used (GB)", justify="right", style="yellow")

            # Add the row with the extracted data
            index_stats = f"{number_of_shards}/{number_of_replicas}"
            table.add_row(
                index_health,
                index_name,
                index_stats,
                f"{disk_used_gb:.2f} GB"
            )

            # Display the table
            console = Console()
            console.print(table)

        except Exception as e:
            print(f"Error retrieving index information: {str(e)}")

    def print_index_info(self, index_info):
        # Print detailed information about the index
        print("Index Information:")
        print("Settings:")
        print(index_info['settings'])
        print("Mappings:")
        print(index_info['mappings'])
        print("Stats:")
        print(index_info['stats'])
        print("Health:")
        print(index_info['health'])

    def build_es_url(self):
        # Determine the protocol based on use_ssl
        protocol = "https" if self.use_ssl else "http"

        # Build the URL string
        es_url = f"{protocol}://{self.host1}:{self.port}"

        return es_url

    def get_index_ilm_short(self, data):
        result = {}

        indices_data = data["indices"]

        for index_name, metadata in indices_data.items():

            phase = metadata.get('phase', None)
            age = metadata.get('age', 0)
            policy = metadata.get('policy', None)

            # Store in result dictionary with index_name as key
            result[index_name] = {
                'phase': phase,
                'age': age,
                'policy': policy
            }

        return result

    def get_index_ilms(self, short=False):
        """
        Retreive Indices with ILM status.

        :param short: Whether to return short version or not.

        Return:
        - Python Dictionary with ILM state.
        """

        self.short = short

        # Get ES URL
        ES_URL = self.build_es_url()

        # Step 1: Get list of all indice
        if self.elastic_authentication == True:
            indices_response = requests.get(
                f'{ES_URL}/_all/_ilm/explain',
                auth=HTTPBasicAuth(self.elastic_username, self.elastic_password),  # Basic Authentication
                verify=False  # Use None if SSL verification is not needed (e.g., self-signed certs)
            )
        else:
            indices_response = requests.get(
                f'{ES_URL}/_all/_ilm/explain',
                verify=False  # Use None if SSL verification is not needed (e.g., self-signed certs)
            )

        # Raise an exception if the response wasn't successful
        indices_response.raise_for_status()
        indices_response_text = indices_response.text
        indices_data = json.loads(indices_response_text)

        if self.short == True:
            return_data = self.get_index_ilm_short(indices_data)
        else:
            return_data = indices_data

        return return_data

    def get_indices_stats(self, pattern=None, status=None):

        self.pattern = pattern
        self.status = status

        # Get all indices
        if (self.pattern == None):
            indices = self.es.cat.indices(format='json')
        else:
            search_pattern = f"*{self.pattern}*"
            indices = self.es.cat.indices(format='json', index=search_pattern)

        # If Status passed we need to parse this down
        if self.status:
            indices_filtered = self.filter_indices_by_status(indices, self.status)
            return json.dumps(indices_filtered)
        else:
            return json.dumps(indices)

    def get_shards_stats(self, pattern=None):

        self.pattern = pattern

        # Get all shards
        if (self.pattern == None or self.pattern == '*'):
            shards = self.es.cat.shards(format='json')
        else:
            # Check if pattern contains shell-style wildcards
            if '*' in self.pattern or '?' in self.pattern:
                # Use pattern directly for Elasticsearch index matching
                search_pattern = self.pattern
            else:
                # For substring patterns, add wildcards for ES index matching
                search_pattern = f"*{self.pattern}*"
            
            try:
                shards = self.es.cat.shards(format='json', index=search_pattern)
            except Exception as e:
                # If ES index pattern fails, get all shards and filter manually
                all_shards = self.es.cat.shards(format='json')
                if '*' in self.pattern or '?' in self.pattern:
                    # Convert shell-style wildcards to regex for filtering
                    import re
                    escaped = re.escape(self.pattern)
                    escaped = escaped.replace(r'\*', '.*').replace(r'\?', '.')
                    regex = re.compile(f"^{escaped}$")
                    shards = [s for s in all_shards if regex.search(s.get('index', ''))]
                else:
                    # Substring matching
                    shards = [s for s in all_shards if self.pattern in s.get('index', '')]
                    
        return shards

    def list_indices_stats(self, pattern=None, status=None):

        self.pattern = pattern
        self.status = status

        # Get all indices
        indices = self.es.cat.indices(format='json')

        if self.pattern:
            # Escape special characters in pattern if necessary
            escaped_pattern = re.escape(self.pattern)
            # Construct the regex pattern (using ".*" to allow for partial matches)
            search_pattern = f".*{escaped_pattern}.*"
            # Compile the regex pattern
            pattern_regex = re.compile(search_pattern)
            # Manually filter the indices based on the regex pattern
            indices_filtered = [index for index in indices if pattern_regex.match(index['index'])]
        else:
            indices_filtered = indices

        indices_sorted = sorted(indices_filtered, key=lambda x: x['index'])

        # Filter indices by status if status is provided
        if self.status:
            indices_sorted = self.filter_indices_by_status(indices_sorted, self.status)

        return indices_sorted

    def filter_indices_by_status(self, indices, status):
        filtered_indices = []
        for index in indices:
            index_name = index['index']
            if index['health'] == status:
                filtered_indices.append(index)
        return filtered_indices

    def get_master_node(self):
        # Get the cluster stats
        master_node = self.es.cat.master(h="node").strip()
        return master_node

    def obtain_keys_values(self, data):
        keys = []
        values = {}

        if data:  # Ensure that data is not empty
            for entry in data:
                for key, value in entry.items():
                    if key not in keys:
                        keys.append(key)
                        values[key] = [value]
                    else:
                        values[key].append(value)

        return keys, [values[key] for key in keys]

    def flatten_json(self, json_obj, parent_key='', sep='.'):
        # Convert a JSON string to a dictionary if needed
        if isinstance(json_obj, str):
            try:
                json_obj = json.loads(json_obj)
            except json.JSONDecodeError:
                # Handle invalid JSON string
                return {}

        # Takes Json and returns it in DOT notation
        if not json_obj:
            return {}

        items = []
        for k, v in json_obj.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self.flatten_json(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    def get_recovery_status(self):
        """
        Get the recovery status of indices in Elasticsearch cluster.
        """
        recovery_status = {}
        try:
            recovery_info = self.es.cat.recovery(format='json')
            for entry in recovery_info:
                index = entry['index']
                if entry['stage'] != 'done':
                    if index not in recovery_status:
                        recovery_status[index] = []
                    recovery_status[index].append(entry)
        except Exception as e:
            print(f"An error occurred: {e}")
        return recovery_status

    def get_shards_as_dict(self):
        shards_info_list = []
        try:
            response = self.es.cat.shards(format="json")
            for shard_info in response:
                shard_dict = {
                    "index": shard_info.get("index", ""),
                    "shard": shard_info.get("shard", ""),
                    "prirep": shard_info.get("prirep", ""),
                    "state": shard_info.get("state", ""),
                    "docs": shard_info.get("docs", ""),
                    "store": shard_info.get("store", ""),
                    "size": self.size_to_bytes(shard_info.get("store", "0b")),
                    "node": shard_info.get("node", "")
                }
                shards_info_list.append(shard_dict)
        except Exception as e:
            print(f"An error occurred: {e}")

        # Sort shards_info_list by index_name
        sorted_shards_info_list = sorted(shards_info_list, key=lambda x: x["index"])

        return sorted_shards_info_list

    def analyze_shard_colocation(self, pattern=None):
        """
        Analyze shard distribution to find indices where primary and replica shards
        are located on the same host, which poses availability risks.

        Args:
            pattern (str, optional): Regex pattern to filter indices

        Returns:
            dict: Colocation analysis results
        """
        import re
        from collections import defaultdict

        # Get all shard information
        all_shards = self.get_shards_as_dict()

        # Filter by pattern if provided
        if pattern:
            try:
                regex = re.compile(f".*{re.escape(pattern)}.*", re.IGNORECASE)
                all_shards = [shard for shard in all_shards if regex.search(shard["index"])]
            except re.error:
                # If regex fails, use simple substring match
                all_shards = [shard for shard in all_shards if pattern.lower() in shard["index"].lower()]

        # Group shards by index and shard number
        index_shards = defaultdict(lambda: defaultdict(list))

        for shard in all_shards:
            if shard["state"] == "STARTED":  # Only consider started shards
                index_name = shard["index"]
                shard_number = shard["shard"]
                index_shards[index_name][shard_number].append(shard)

        # Analyze colocation
        colocated_indices = []
        total_indices = len(index_shards)
        total_shard_groups = 0
        problematic_shard_groups = 0

        for index_name, shards_by_number in index_shards.items():
            index_issues = []

            for shard_number, shard_list in shards_by_number.items():
                total_shard_groups += 1

                # Group by node
                nodes_for_shard = defaultdict(list)
                for shard in shard_list:
                    nodes_for_shard[shard["node"]].append(shard)

                # Check if any node has both primary and replica
                for node, node_shards in nodes_for_shard.items():
                    if len(node_shards) > 1:  # More than one shard (primary + replica(s))
                        has_primary = any(s["prirep"] == "p" for s in node_shards)
                        has_replica = any(s["prirep"] == "r" for s in node_shards)

                        if has_primary and has_replica:
                            problematic_shard_groups += 1
                            issue = {
                                "shard_number": shard_number,
                                "node": node,
                                "shards": node_shards,
                                "total_shards_on_node": len(node_shards),
                                "primary_count": sum(1 for s in node_shards if s["prirep"] == "p"),
                                "replica_count": sum(1 for s in node_shards if s["prirep"] == "r")
                            }
                            index_issues.append(issue)

            if index_issues:
                colocated_indices.append({
                    "index": index_name,
                    "issues": index_issues,
                    "affected_shard_groups": len(index_issues)
                })

        # Calculate summary statistics
        affected_indices = len(colocated_indices)
        risk_percentage = (affected_indices / total_indices * 100) if total_indices > 0 else 0

        return {
            "summary": {
                "total_indices_analyzed": total_indices,
                "affected_indices": affected_indices,
                "total_shard_groups": total_shard_groups,
                "problematic_shard_groups": problematic_shard_groups,
                "risk_percentage": round(risk_percentage, 2),
                "pattern_applied": pattern is not None,
                "filter_pattern": pattern
            },
            "colocated_indices": colocated_indices,
                         "risk_level": "high" if risk_percentage > 50 else "medium" if risk_percentage > 20 else "low"
         }

    def print_shard_colocation_results(self, colocation_results, use_pager=False):
        """
        Display shard colocation analysis results with enhanced Rich formatting.

        Args:
            colocation_results (dict): Results from analyze_shard_colocation
            use_pager (bool): Whether to use pager for large outputs
        """
        from rich.panel import Panel
        from rich.text import Text
        from rich.columns import Columns
        from rich.console import Console
        from rich.table import Table

        console = Console()
        summary = colocation_results["summary"]
        colocated_indices = colocation_results["colocated_indices"]
        risk_level = colocation_results["risk_level"]

        # Determine theme colors based on risk level
        if risk_level == "high":
            theme_color = "red"
            risk_icon = "🚨"
            risk_text = "HIGH RISK"
        elif risk_level == "medium":
            theme_color = "yellow"
            risk_icon = "⚠️"
            risk_text = "MEDIUM RISK"
        else:
            theme_color = "green"
            risk_icon = "✅"
            risk_text = "LOW RISK"

        # Create title panel with comprehensive statistics
        filter_info = f" | Pattern: {summary['filter_pattern']}" if summary['pattern_applied'] else ""
        comprehensive_subtitle = f"Risk: {risk_icon} {risk_text} | Analyzed: {summary['total_indices_analyzed']:,} indices | Affected: {summary['affected_indices']:,} | Shard Groups: {summary['total_shard_groups']:,} | Issues: {summary['problematic_shard_groups']:,}{filter_info}"

        title_panel = Panel(
            Text(f"⚠️  Shard Colocation Analysis", style=f"bold {theme_color}", justify="center"),
            subtitle=comprehensive_subtitle,
            border_style=theme_color,
            padding=(1, 2)
        )

        if summary['total_indices_analyzed'] == 0:
            # No indices found
            no_data_panel = Panel(
                Text("ℹ️  No indices found to analyze", style="dim white", justify="center"),
                title="[bold white]📊 No Data[/bold white]",
                border_style="dim white",
                padding=(1, 2)
            )

            print()
            console.print(title_panel)
            print()
            console.print(no_data_panel)
            print()
            return

        if not colocated_indices:
            # No colocation issues found - show success message in title panel
            success_title_panel = Panel(
                Text(f"⚠️  Shard Colocation Analysis\n\n🎉 Excellent Shard Distribution!\nNo shard colocation issues found. All primary and replica shards are properly distributed across different hosts.", style="bold green", justify="center"),
                subtitle=comprehensive_subtitle,
                border_style="green",
                padding=(1, 2)
            )

            print()
            console.print(success_title_panel)
            print()
            return



        # Create recommendation panel
        recommendations_table = Table.grid(padding=(0, 1))
        recommendations_table.add_column(style="bold cyan", no_wrap=True)
        recommendations_table.add_column(style="white")

        recommendations_table.add_row("🔧 Fix Issues:", "Use shard allocation exclude")
        recommendations_table.add_row("📋 Monitor:", "Check cluster balance regularly")
        recommendations_table.add_row("⚖️  Rebalance:", "Consider index rollover")
        recommendations_table.add_row("📚 Learn More:", "Elasticsearch shard allocation docs")

        recommendations_panel = Panel(
            recommendations_table,
            title="[bold white]💡 Recommendations[/bold white]",
            border_style="cyan",
            padding=(1, 2),
            width=40
        )

        # Create detailed issues table
        issues_table = Table(show_header=True, header_style="bold white", title="⚠️  Colocation Issues", expand=True)
        issues_table.add_column("📋 Index Name", style="yellow", no_wrap=True)
        issues_table.add_column("🔢 Shard", justify="center", width=8)
        issues_table.add_column("🖥️  Problem Node", style="red", no_wrap=True)
        issues_table.add_column("🔑 Primary", justify="center", width=10)
        issues_table.add_column("📋 Replicas", justify="center", width=10)
        issues_table.add_column("📦 Total", justify="center", width=8)
        issues_table.add_column("💾 Size", justify="right", width=10)

        for index_data in colocated_indices:
            index_name = index_data["index"]

            for issue in index_data["issues"]:
                shard_number = issue["shard_number"]
                node = issue["node"]
                primary_count = issue["primary_count"]
                replica_count = issue["replica_count"]
                total_shards = issue["total_shards_on_node"]

                # Calculate total size for this shard group on this node
                total_size = sum(s["size"] for s in issue["shards"])
                size_display = self.bytes_to_human_readable(total_size)

                issues_table.add_row(
                    index_name,
                    str(shard_number),
                    node,
                    str(primary_count),
                    str(replica_count),
                    str(total_shards),
                    size_display,
                    style="red" if primary_count > 0 and replica_count > 0 else "yellow"
                )

        # Check configuration to see if legend panels should be shown
        try:
            from configuration_manager import ConfigurationManager
            import os
            config_file = os.path.join(os.path.dirname(__file__), 'elastic_servers.yml')
            config_manager = ConfigurationManager(config_file, os.path.join(os.path.dirname(config_file), 'escmd.json'))
            show_legend_panels = config_manager.get_show_legend_panels()
        except Exception:
            # Fallback to default (disabled) if configuration fails
            show_legend_panels = False

        # Create legend panels only if enabled
        if show_legend_panels:
            legend_table = Table.grid(padding=(0, 2))
            legend_table.add_column(style="bold white", no_wrap=True)
            legend_table.add_column(style="white")
            legend_table.add_row("🔑 Primary:", "Main shard copy")
            legend_table.add_row("📋 Replicas:", "Backup shard copies")
            legend_table.add_row("🚨 Issue:", "Primary + replica on same host")
            legend_table.add_row("⚖️  Risk:", "Host failure = data loss")

            legend_panel = Panel(
                legend_table,
                title="[bold white]🔍 Legend[/bold white]",
                border_style="cyan",
                padding=(1, 1),
                width=50
            )

            # Quick actions panel
            actions_table = Table.grid(padding=(0, 1))
            actions_table.add_column(style="bold magenta", no_wrap=True)
            actions_table.add_column(style="dim white")
            actions_table.add_row("Filter indices:", "./escmd.py shard-colocation <pattern>")
            actions_table.add_row("JSON output:", "./escmd.py shard-colocation --format json")
            actions_table.add_row("Use pager:", "./escmd.py shard-colocation --pager")
            actions_table.add_row("Check specific:", "./escmd.py shard-colocation 'logs-.*'")

            actions_panel = Panel(
                actions_table,
                title="[bold white]🚀 Quick Actions[/bold white]",
                border_style="magenta",
                padding=(1, 1),
                width=45
            )

        # Check if we should use pager for large datasets
        try:
            config_file = os.path.join(os.path.dirname(__file__), 'elastic_servers.yml')
            config_manager = ConfigurationManager(config_file, os.path.join(os.path.dirname(config_file), 'escmd.json'))

            # Try to get paging settings with fallback to defaults
            paging_enabled = getattr(config_manager, 'get_paging_enabled', lambda: False)()
            paging_threshold = getattr(config_manager, 'get_paging_threshold', lambda: 50)()
        except Exception:
            # Fallback to safe defaults if configuration fails
            paging_enabled = False
            paging_threshold = 50

        should_use_pager = use_pager or (paging_enabled and len(colocated_indices) > paging_threshold)

        if should_use_pager:
            # Capture all output to pager
            with console.pager():
                print()
                console.print(title_panel)
                print()
                console.print(recommendations_panel)
                print()
                console.print(issues_table)
                if show_legend_panels:
                    print()
                    console.print(Columns([legend_panel, actions_panel], equal=False, expand=True))
                print()
        else:
            # Normal display
            print()
            console.print(title_panel)
            print()
            console.print(recommendations_panel)
            print()
            console.print(issues_table)
            if show_legend_panels:
                print()
                console.print(Columns([legend_panel, actions_panel], equal=False, expand=True))
            print()

    def parse_node_stats(self, node_stats):
        parsed_data = []
        for node_id, node_info in node_stats.get('nodes', {}).items():
            hostname = node_info.get('host', 'Unknown')
            name = node_info.get('name', 'Unknown')
            roles = node_info.get('roles', [])
            indices_count = node_info.get('indices', {}).get('docs', {}).get('count', 0)
            shards_count = node_info.get('indices', {}).get('shard_stats', {}).get('total_count', 0)
            parsed_data.append({
                'nodeid': node_id,
                'name': name,
                'hostname': hostname,
                'roles': roles,
                'indices': indices_count,
                'shards': shards_count
            })
        return parsed_data

    def ping(self):
        if (self.es.ping()):
            return True

    def print_table_allocation(self, title, data_dict):
        console = Console()

        table = Table(show_header=True, title=title, header_style="bold cyan", box=self.box_style)
        table.add_column("Storage Node")
        table.add_column("Shards", justify="center")
        table.add_column("Disk Percent", justify="center")
        table.add_column("Disk Used", justify="center")
        table.add_column("Disk Avail", justify="center")
        table.add_column("Disk Total", justify="center")

        for key, value in data_dict.items():
            storage_node = key
            storage_values = value
            storage_shards = storage_values['shards']
            storage_disk_percent = storage_values['disk.percent']
            storage_disk_used = self.format_bytes(storage_values['disk.used'])
            storage_disk_avail = self.format_bytes(storage_values['disk.avail'])
            storage_disk_total = self.format_bytes(storage_values['disk.total'])
            table.add_row(str(key), str(storage_shards), str(storage_disk_percent), str(storage_disk_used), str(storage_disk_avail), str(storage_disk_total))

        console.print(table)

    def print_enhanced_storage_table(self, data_dict):
        """Print enhanced storage allocation table with Rich formatting and statistics"""
        from rich.panel import Panel
        from rich.text import Text
        from rich.columns import Columns

        console = Console()

        if not data_dict:
            console.print("[red]❌ No storage data available[/red]")
            return

        # Calculate statistics
        total_nodes = len(data_dict)
        total_shards = sum(node_data['shards'] for node_data in data_dict.values())
        total_used_bytes = sum(node_data['disk.used'] for node_data in data_dict.values())
        total_avail_bytes = sum(node_data['disk.avail'] for node_data in data_dict.values())
        total_size_bytes = sum(node_data['disk.total'] for node_data in data_dict.values())

        # Calculate cluster-wide disk usage percentage
        if total_size_bytes > 0:
            cluster_used_percent = (total_used_bytes / total_size_bytes) * 100
        else:
            cluster_used_percent = 0

        # Find nodes with different disk usage levels
        critical_nodes = [node for node, data in data_dict.items() if float(data['disk.percent']) >= 90]
        high_usage_nodes = [node for node, data in data_dict.items() if 80 <= float(data['disk.percent']) < 90]
        elevated_nodes = [node for node, data in data_dict.items() if 70 <= float(data['disk.percent']) < 80]

        # Create title panel
        title_panel = Panel(
            Text(f"💾 Elasticsearch Storage Overview", style="bold cyan", justify="center"),
            subtitle=f"Nodes: {total_nodes} | Total Shards: {total_shards:,} | Cluster Usage: {cluster_used_percent:.1f}% | Elevated: {len(elevated_nodes)} | High: {len(high_usage_nodes)} | Critical: {len(critical_nodes)}",
            border_style="cyan",
            padding=(1, 2)
        )

        # Create enhanced storage table
        table = Table(show_header=True, header_style="bold white", title="💾 Node Storage Details", expand=True)
        table.add_column("🖥️ Node", no_wrap=True)
        table.add_column("🔄 Shards", justify="center", width=8)
        table.add_column("📊 Usage %", justify="center", width=10)
        table.add_column("💾 Used", justify="right", width=12)
        table.add_column("🆓 Available", justify="right", width=12)
        table.add_column("📦 Total", justify="right", width=12)
        table.add_column("🎯 Status", justify="center", width=8)

        # Sort nodes by disk usage percentage (highest first)
        sorted_nodes = sorted(data_dict.items(), key=lambda x: float(x[1]['disk.percent']), reverse=True)

        for node_name, node_data in sorted_nodes:
            shards = node_data['shards']
            disk_percent = float(node_data['disk.percent'])
            disk_used = self.format_bytes(node_data['disk.used'])
            disk_avail = self.format_bytes(node_data['disk.avail'])
            disk_total = self.format_bytes(node_data['disk.total'])

            # Determine row styling and status based on disk usage
            if disk_percent >= 90:
                row_style = "bright_red"
                status_icon = "🔴"
                status_text = "Critical"
            elif disk_percent >= 80:
                row_style = "red"
                status_icon = "⚠️"
                status_text = "High"
            elif disk_percent >= 70:
                row_style = "yellow"
                status_icon = "🟡"
                status_text = "Elevated"
            elif disk_percent >= 60:
                row_style = "white"
                status_icon = "📊"
                status_text = "Moderate"
            else:
                row_style = "green"
                status_icon = "✅"
                status_text = "Good"

            table.add_row(
                node_name,
                f"{shards:,}",
                f"{disk_percent:.1f}%",
                disk_used,
                disk_avail,
                disk_total,
                f"{status_icon} {status_text}",
                style=row_style
            )

        # Create summary statistics panel with aligned table
        summary_table = Table(show_header=False, box=None, padding=(0, 1))
        summary_table.add_column("Metric", style="bold", no_wrap=True)
        summary_table.add_column("Icon", justify="center", width=4)
        summary_table.add_column("Value", style="cyan")

        summary_table.add_row("Total Nodes:", "🖥️", f"{total_nodes}")
        summary_table.add_row("Total Shards:", "🔄", f"{total_shards:,}")
        summary_table.add_row("Cluster Used:", "💾", f"{self.format_bytes(total_used_bytes)}")
        summary_table.add_row("Cluster Available:", "🆓", f"{self.format_bytes(total_avail_bytes)}")
        summary_table.add_row("Cluster Total:", "📦", f"{self.format_bytes(total_size_bytes)}")
        summary_table.add_row("Average Usage:", "📊", f"{cluster_used_percent:.1f}%")

        summary_panel = Panel(
            summary_table,
            title="📈 Cluster Summary",
            border_style="cyan",
            padding=(1, 2)
        )

        # Create alerts panel if there are issues
        if critical_nodes or high_usage_nodes or elevated_nodes:
            alerts_content = ""
            if critical_nodes:
                alerts_content += f"[bold bright_red]🔴 Critical Nodes ({len(critical_nodes)}):[/bold bright_red]\n"
                for node in critical_nodes[:3]:  # Show first 3
                    usage = data_dict[node]['disk.percent']
                    alerts_content += f"  • {node}: {usage}%\n"
                if len(critical_nodes) > 3:
                    alerts_content += f"  • ... and {len(critical_nodes) - 3} more\n"
                alerts_content += "\n"

            if high_usage_nodes:
                alerts_content += f"[bold red]⚠️ High Usage Nodes ({len(high_usage_nodes)}):[/bold red]\n"
                for node in high_usage_nodes[:3]:  # Show first 3
                    usage = data_dict[node]['disk.percent']
                    alerts_content += f"  • {node}: {usage}%\n"
                if len(high_usage_nodes) > 3:
                    alerts_content += f"  • ... and {len(high_usage_nodes) - 3} more\n"
                alerts_content += "\n"

            if elevated_nodes:
                alerts_content += f"[bold yellow]🟡 Elevated Usage Nodes ({len(elevated_nodes)}):[/bold yellow]\n"
                for node in elevated_nodes[:3]:  # Show first 3
                    usage = data_dict[node]['disk.percent']
                    alerts_content += f"  • {node}: {usage}%\n"
                if len(elevated_nodes) > 3:
                    alerts_content += f"  • ... and {len(elevated_nodes) - 3} more\n"

            alerts_panel = Panel(
                alerts_content.rstrip(),
                title="⚠️ Storage Alerts",
                border_style="bright_red" if critical_nodes else ("red" if high_usage_nodes else "yellow"),
                padding=(1, 2)
            )

            # Display everything
            print()
            console.print(title_panel)
            print()
            console.print(Columns([summary_panel, alerts_panel], expand=True))
            print()
            console.print(table)
        else:
            # No alerts - just show summary
            print()
            console.print(title_panel)
            print()
            console.print(summary_panel)
            print()
            console.print(table)

    def print_enhanced_nodes_table(self, nodes, show_data_only=False):
        """Print enhanced nodes table with Rich formatting and statistics"""
        from rich.panel import Panel
        from rich.text import Text
        from rich.columns import Columns

        console = Console()

        if not nodes:
            console.print("[red]❌ No nodes data available[/red]")
            return

        # Calculate statistics
        total_nodes = len(nodes)
        node_roles = {}
        master_eligible = 0
        data_nodes = 0
        client_nodes = 0
        ingest_nodes = 0

        # Get current master node
        try:
            current_master = self.get_master_node()
        except:
            current_master = "Unknown"

        # Analyze node roles
        for node in nodes:
            roles = node.get('roles', [])

            # Count by primary roles
            if 'master' in roles:
                master_eligible += 1
            if any(role.startswith('data') for role in roles):
                data_nodes += 1
            if 'ingest' in roles:
                ingest_nodes += 1
            if not any(role.startswith('data') for role in roles) and 'master' not in roles:
                client_nodes += 1

            # Track role combinations
            role_key = ', '.join(sorted(roles)) if roles else 'none'
            node_roles[role_key] = node_roles.get(role_key, 0) + 1

        # Create title panel with version information
        filter_text = " (Data Nodes Only)" if show_data_only else ""
        
        # Get cluster version info
        try:
            health_data = self.get_cluster_health()
            cluster_name = health_data.get('cluster_name', 'Unknown')
            cluster_version = health_data.get('cluster_version', 'Unknown')
            mixed_versions = health_data.get('mixed_versions', False)
        except Exception:
            cluster_name = 'Unknown'
            cluster_version = 'Unknown'
            mixed_versions = False

        # Build enhanced title with version info
        if cluster_version != 'Unknown':
            if mixed_versions:
                nodes_title = f"🖥️  Elasticsearch Nodes: {cluster_name} (v{cluster_version} - Mixed Versions){filter_text}"
            else:
                nodes_title = f"🖥️  Elasticsearch Nodes: {cluster_name} (v{cluster_version}){filter_text}"
        else:
            nodes_title = f"🖥️  Elasticsearch Nodes: {cluster_name}{filter_text}"

        title_panel = Panel(
            Text(nodes_title, style="bold cyan", justify="center"),
            subtitle=f"Total: {total_nodes} | Master-eligible: {master_eligible} | Data: {data_nodes} | Ingest: {ingest_nodes} | Client: {client_nodes}",
            border_style="cyan",
            padding=(1, 2)
        )

        # Check if we have meaningful node IDs
        has_node_ids = any(node.get('nodeid', 'Unknown') != 'Unknown' for node in nodes)

        # Create enhanced nodes table
        table = Table(show_header=True, header_style="bold white", title="🖥️  Node Details", expand=True)
        table.add_column("📛 Node Name", no_wrap=True, width=25)
        if has_node_ids:
            table.add_column("🆔 Node ID", width=12, justify="center")
        table.add_column("🔧 ES Version", width=12, justify="center", no_wrap=True)
        table.add_column("📄 Indices", justify="center", width=8)
        table.add_column("👑 Master", justify="center", width=8)
        table.add_column("💾 Data", justify="center", width=6)
        table.add_column("🔄 Ingest", justify="center", width=8)
        table.add_column("🔗 Client", justify="center", width=8)
        table.add_column("🎯 Status", justify="center", width=10)

        # Sort nodes: master first, then data nodes, then others
        def node_sort_key(node):
            roles = node.get('roles', [])
            name = node.get('name', '')
            # Current master gets priority
            if name == current_master:
                return (0, name)
            # Master-eligible nodes next
            elif 'master' in roles:
                return (1, name)
            # Data nodes next
            elif any(role.startswith('data') for role in roles):
                return (2, name)
            # Others last
            else:
                return (3, name)

        sorted_nodes = sorted(nodes, key=node_sort_key)

        for node in sorted_nodes:
            name = node.get('name', 'Unknown')
            hostname = node.get('hostname', 'Unknown')
            node_id = node.get('nodeid', 'Unknown')[:12]  # Truncate for display
            roles = node.get('roles', [])
            
            # Get version information
            version = node.get('version', 'Unknown')
            build_hash = node.get('build_hash')
            indices_count = node.get('indices_count', 0)  # Get actual indices count
            
            # Format version display
            if version != 'Unknown':
                if build_hash:
                    version_display = f"v{version}"
                else:
                    version_display = f"v{version}"
            else:
                version_display = "Unknown"
            
            # Format node name with hostname in parentheses
            node_display_name = f"{name} ({hostname})"

            # Determine node type indicators
            is_master_eligible = 'master' in roles
            is_data = any(role.startswith('data') for role in roles)
            is_ingest = 'ingest' in roles
            is_client = not is_data and not is_master_eligible
            is_current_master = name == current_master

            # Set status and styling
            if is_current_master:
                row_style = "bold yellow"
                status_icon = "👑"
                status_text = "Master"
            elif is_master_eligible and is_data:
                row_style = "green"
                status_icon = "⚙️"
                status_text = "Master+Data"
            elif is_master_eligible:
                row_style = "blue"
                status_icon = "⚙️"
                status_text = " Master-only"
            elif is_data:
                row_style = "cyan"
                status_icon = "💾"
                status_text = "Data"
            elif is_client:
                row_style = "magenta"
                status_icon = "🔗"
                status_text = "Client"
            else:
                row_style = "white"
                status_icon = "❓"
                status_text = "Other"

            # Role indicators
            master_indicator = " ★ " if is_current_master else " ○ " if is_master_eligible else " - "
            data_indicator = " ● " if is_data else " - "
            ingest_indicator = " ● " if is_ingest else " - "
            client_indicator = " ● " if is_client else " - "

            # Build row data conditionally
            row_data = [node_display_name]  # Use the formatted name with hostname
            if has_node_ids:
                row_data.append(node_id)
            row_data.append(version_display)  # Add version column
            row_data.append(f"{indices_count:,}")  # Add indices count with comma formatting
            row_data.extend([
                master_indicator,
                data_indicator,
                ingest_indicator,
                client_indicator,
                f"{status_icon} {status_text}"
            ])

            table.add_row(*row_data, style=row_style)

        # Create summary statistics panel with aligned columns
        from rich.table import Table as InnerTable

        summary_table = InnerTable(show_header=False, box=None, padding=(0, 1))
        summary_table.add_column("Label", style="bold", no_wrap=True)
        summary_table.add_column("Icon", justify="left", width=3)
        summary_table.add_column("Value", no_wrap=True)

        summary_table.add_row("Total Nodes:", "🖥️", str(total_nodes))
        summary_table.add_row("Current Master:", "👑", current_master)
        summary_table.add_row("Master-eligible:", "⚙️", str(master_eligible))
        summary_table.add_row("Data Nodes:", "💾", str(data_nodes))
        summary_table.add_row("Ingest Nodes:", "🔄", str(ingest_nodes))
        summary_table.add_row("Client Nodes:", "🔗", str(client_nodes))

        summary_panel = Panel(
            summary_table,
            title="📊 Node Summary",
            border_style="cyan",
            padding=(1, 2)
        )

        # Create roles breakdown panel
        roles_content = ""
        for role_combo, count in sorted(node_roles.items(), key=lambda x: x[1], reverse=True):
            if role_combo == 'none':
                role_display = "No roles"
            else:
                role_display = role_combo
            roles_content += f"[bold]{role_display}:[/bold]  {count}\n"

        roles_panel = Panel(
            roles_content.rstrip(),
            title="🏷️  Role Distribution",
            border_style="green",
            padding=(1, 2)
        )

        # Display everything
        print()
        console.print(title_panel)
        print()
        console.print(Columns([summary_panel, roles_panel], expand=True))
        print()
        console.print(table)

    def print_table_shards(self, shards_info, use_pager=False):
        from rich.panel import Panel
        from rich.text import Text

        console = Console()
        cluster_all_settings = self.get_all_index_settings()

        # Calculate statistics
        total_shards = len(shards_info)
        state_counts = {'STARTED': 0, 'INITIALIZING': 0, 'RELOCATING': 0, 'UNASSIGNED': 0}
        type_counts = {'primary': 0, 'replica': 0}
        hot_count = 0
        frozen_count = 0

        for shard_info in shards_info:
            state_counts[shard_info['state']] = state_counts.get(shard_info['state'], 0) + 1
            if shard_info['prirep'] == 'p':
                type_counts['primary'] += 1
            else:
                type_counts['replica'] += 1

            if shard_info['index'] in self.cluster_indices_hot_indexes:
                hot_count += 1

            index_settings = cluster_all_settings.get(shard_info['index'], None)
            if index_settings:
                frozen_status = index_settings['settings']['index'].get('frozen', False)
                if frozen_status == "true":
                    frozen_count += 1

        # Create title panel
        title_panel = Panel(
            Text(f"📊 Elasticsearch Shards Overview", style="bold cyan", justify="center"),
            subtitle=f"Total: {total_shards} | Started: {state_counts.get('STARTED', 0)} | Initializing: {state_counts.get('INITIALIZING', 0)} | Unassigned: {state_counts.get('UNASSIGNED', 0)} | Primary: {type_counts['primary']} | Replica: {type_counts['replica']} | Hot: {hot_count} | Frozen: {frozen_count}",
            border_style="cyan",
            padding=(1, 2)
        )

        # Create enhanced shards table
        table = Table(show_header=True, header_style="bold white", title="📊 Elasticsearch Shards", expand=True)
        table.add_column("🔄 State", justify="center", width=12)
        table.add_column("⚖️ Type", justify="center", width=8)
        table.add_column("📋 Index Name", no_wrap=True)
        table.add_column("🔢 Shard", justify="center", width=8)
        table.add_column("📊 Documents", justify="right", width=12)
        table.add_column("💾 Store", justify="right", width=10)
        table.add_column("🖥️ Node", no_wrap=True)

        for shard_info in shards_info:
            # Determine row styling
            row_style = "white"  # Default
            index_name = shard_info["index"]

            # Check if hot and add flame indicator
            if index_name in self.cluster_indices_hot_indexes:
                index_name = f"{index_name} 🔥"
                row_style = "bright_red"

            # Check if frozen and add snowflake indicator
            index_settings = cluster_all_settings.get(shard_info['index'], None)
            if index_settings:
                frozen_status = index_settings['settings']['index'].get('frozen', False)
                if frozen_status == "true":
                    index_name = f"{index_name} ❄️"
                    if not index_name.endswith("🔥 ❄️"):  # Only set blue if not already red (hot)
                        row_style = "bright_blue"

            # Format shard type
            shard_type = "🔑 Primary" if shard_info["prirep"] == "p" else "📋 Replica"

            # Format state with icons
            state = shard_info["state"]
            if state == "STARTED":
                state_display = "✅ Started"
            elif state == "INITIALIZING":
                state_display = "🔄 Initializing"
            elif state == "RELOCATING":
                state_display = "🚚 Relocating"
            elif state == "UNASSIGNED":
                state_display = "❌ Unassigned"
            else:
                state_display = f"❓ {state}"

            # Format documents count
            docs_count = shard_info["docs"] if shard_info["docs"] is not None else "N/A"
            if docs_count != "N/A":
                try:
                    docs_count = f"{int(docs_count):,}"
                except:
                    pass

            table.add_row(
                state_display,
                shard_type,
                index_name,
                shard_info["shard"],
                docs_count,
                shard_info["store"] if shard_info["store"] is not None else "N/A",
                shard_info["node"] if shard_info["node"] is not None else "N/A",
                style=row_style
            )

        # Check if we should use pager for large datasets
        # Get paging configuration from config manager with safe defaults
        from configuration_manager import ConfigurationManager
        import os

        try:
            config_file = os.path.join(os.path.dirname(__file__), 'elastic_servers.yml')
            config_manager = ConfigurationManager(config_file, os.path.join(os.path.dirname(config_file), 'escmd.json'))

            # Try to get paging settings with fallback to defaults
            paging_enabled = getattr(config_manager, 'get_paging_enabled', lambda: False)()
            paging_threshold = getattr(config_manager, 'get_paging_threshold', lambda: 50)()
        except Exception:
            # Fallback to safe defaults if configuration fails
            paging_enabled = False
            paging_threshold = 50

        should_use_pager = use_pager or (paging_enabled and len(shards_info) > paging_threshold)

        if should_use_pager:
            # Capture all output to pager
            with console.pager():
                print()
                console.print(title_panel)
                print()
                console.print(table)
        else:
            # Normal display
            print()
            console.print(title_panel)
            print()
            console.print(table)

    def print_table_from_dict(self, title, data_dict):
        console = Console()

        # Enhance title with version information if available
        enhanced_title = title
        if 'cluster_version' in data_dict and 'cluster_name' in data_dict:
            cluster_name = data_dict['cluster_name']
            cluster_version = data_dict.get('cluster_version', 'Unknown')
            mixed_versions = data_dict.get('mixed_versions', False)
            
            if mixed_versions:
                version_display = f"v{cluster_version} (mixed)"
                enhanced_title = f"📋 Elasticsearch Cluster: {cluster_name} ({version_display})"
            elif cluster_version != 'Unknown':
                enhanced_title = f"📋 Elasticsearch Cluster: {cluster_name} (v{cluster_version})"
            else:
                enhanced_title = f"📋 Elasticsearch Cluster: {cluster_name}"

        table = Table(show_header=True, title=enhanced_title, header_style="bold cyan", box=self.box_style)
        table.add_column("Key")
        table.add_column("Value")

        for key, value in data_dict.items():
            # Skip version fields as they're now in the title
            if key in ['cluster_version', 'build_hash', 'build_date', 'mixed_versions', 'all_versions']:
                continue

            if key == "cluster_status":
                if value == "green":
                    value = "[green]green[/green]  ✅"
                    color = "green"
                elif value == "yellow":
                    value = "[yellow]yellow[/yellow] ⚠️"
                    color = "yellow"
                elif value == "red":
                    value = "[red]red[/red] ❌"
                    color = "red"

            elif key == "cluster_name" and 'cluster_version' in data_dict:
                # Enhance cluster name display with version details
                cluster_version = data_dict.get('cluster_version', 'Unknown')
                build_hash = data_dict.get('build_hash')
                
                if cluster_version != 'Unknown':
                    version_text = f"v{cluster_version}"
                    if build_hash:
                        version_text += f" (build: {build_hash})"
                    value = f"{value} | {version_text}"
                
                # Add mixed version warning if applicable
                if data_dict.get('mixed_versions', False):
                    value += " ⚠️ Mixed versions detected"

            elif key == "active_shards_percent":
                value = float(value)  # Ensure value is treated as a float
                progress_bar = self.text_progress_bar(value)
                value = f"[{color}]{progress_bar}[/{color}]"

            table.add_row(str(key), str(value))
        console.print(table)

    def print_table_indices(self, data_dict, use_pager=False):
        from rich.panel import Panel
        from rich.text import Text
        from rich.columns import Columns

        console = Console()
        cluster_all_settings = self.get_all_index_settings()

        # Get cluster health data for version info
        try:
            health_data = self.get_cluster_health()
            cluster_name = health_data.get('cluster_name', 'Unknown')
            cluster_version = health_data.get('cluster_version', 'Unknown')
        except Exception:
            cluster_name = 'Unknown'
            cluster_version = 'Unknown'

        # Create title panel
        total_indices = len(data_dict)
        health_counts = {'green': 0, 'yellow': 0, 'red': 0}
        status_counts = {'open': 0, 'close': 0}
        hot_count = 0
        frozen_count = 0

        # Count statistics
        for indice in data_dict:
            health_counts[indice['health']] = health_counts.get(indice['health'], 0) + 1
            status_counts[indice['status']] = status_counts.get(indice['status'], 0) + 1
            if indice['index'] in self.cluster_indices_hot_indexes:
                hot_count += 1

            index_settings = cluster_all_settings.get(indice['index'], None)
            if index_settings:
                frozen_status = index_settings['settings']['index'].get('frozen', False)
                if frozen_status == "true":
                    frozen_count += 1

        # Build enhanced title with version info
        if cluster_version != 'Unknown':
            indices_title = f"📊 Elasticsearch Indices: {cluster_name} (v{cluster_version})"
        else:
            indices_title = f"📊 Elasticsearch Indices: {cluster_name}"

        title_panel = Panel(
            Text(indices_title, style="bold cyan", justify="center"),
            subtitle=f"Total: {total_indices} | Green: {health_counts.get('green', 0)} | Yellow: {health_counts.get('yellow', 0)} | Red: {health_counts.get('red', 0)} | Hot: {hot_count} | Frozen: {frozen_count}",
            border_style="cyan",
            padding=(1, 2)
        )

        # Create enhanced indices table
        table = Table(show_header=True, header_style="bold white", title="📊 Elasticsearch Indices", expand=True)
        table.add_column("🟢 Health", justify="center", width=10)
        table.add_column("📄 Status", justify="center", width=8)
        table.add_column("📋 Index Name", no_wrap=True)
        table.add_column("📊 Documents", justify="right", width=12)
        table.add_column("⚖️  Shards", justify="center", width=8)
        table.add_column("💾 Primary", justify="right", width=10)
        table.add_column("📦 Total", justify="right", width=10)

        for indice in data_dict:
            # Health status with icons
            health = indice['health']
            if health == 'green':
                health_display = "✅ Green"
            elif health == 'yellow':
                health_display = "⚠️  Yellow"
            else:
                health_display = "❌ Red"

            # Status with icons
            status = indice['status']
            status_display = "📂 Open" if status == 'open' else "🔒 Closed"

            # Index name with hot/frozen indicators
            indice_name = indice['index']
            row_style = "white"  # Default to white for normal indices

            # Check if hot and add flame indicator
            if indice_name in self.cluster_indices_hot_indexes:
                indice_name = f"{indice_name} 🔥"
                row_style = "bright_red"

            # Check if frozen and add snowflake indicator
            index_settings = cluster_all_settings.get(indice['index'], None)
            if index_settings:
                frozen_status = index_settings['settings']['index'].get('frozen', False)
                if frozen_status == "true":
                    indice_name = f"{indice_name} ❄️"
                    if not indice_name.endswith("🔥 ❄️"):  # Only set blue if not already red (hot)
                        row_style = "bright_blue"

            # Format numbers with proper commas - handle None, empty, and dash values
            docs_count_raw = indice.get('docs.count')
            if docs_count_raw is None or docs_count_raw == '-' or docs_count_raw == '':
                docs_count = '-'
            else:
                try:
                    docs_count = f"{int(docs_count_raw):,}"
                except (ValueError, TypeError):
                    docs_count = str(docs_count_raw)

            # Shard information - handle None values
            pri = indice.get('pri', '-')
            rep = indice.get('rep', '-')
            pri_rep = f"{pri}|{rep}"

            # Handle potential None values for size fields
            pri_store_size = indice.get('pri.store.size')
            store_size = indice.get('store.size')

            pri_store_display = str(pri_store_size) if pri_store_size is not None else '-'
            store_display = str(store_size) if store_size is not None else '-'

            table.add_row(
                health_display,
                status_display,
                indice_name,
                docs_count,
                pri_rep,
                pri_store_display,
                store_display,
                style=row_style
            )

        # Display will be handled below based on pager settings

        # Check configuration to see if legend panels should be shown
        try:
            from configuration_manager import ConfigurationManager
            import os
            config_file = os.path.join(os.path.dirname(__file__), 'elastic_servers.yml')
            config_manager = ConfigurationManager(config_file, os.path.join(os.path.dirname(config_file), 'escmd.json'))
            show_legend_panels = config_manager.get_show_legend_panels()
        except Exception:
            # Fallback to default (disabled) if configuration fails
            show_legend_panels = False

        # Create bottom panels for legend and actions only if enabled
        if show_legend_panels:
            legend_table = Table.grid(padding=(0, 2))
            legend_table.add_column(style="bold white", no_wrap=True)
            legend_table.add_column(style="white")
            legend_table.add_row("🔥 Hot Index:", "Currently active for writes")
            legend_table.add_row("❄️  Frozen Index:", "Read-only, optimized storage")
            legend_table.add_row("⚖️  Shards:", "Primary|Replica shard count")

            legend_panel = Panel(
                legend_table,
                title="[bold white]🔍 Legend[/bold white]",
                border_style="cyan",
                padding=(1, 1),
                width=50
            )

            # Quick actions panel
            actions_table = Table.grid(padding=(0, 1))
            actions_table.add_column(style="bold magenta", no_wrap=True)
            actions_table.add_column(style="dim white")
            actions_table.add_row("Filter by regex:", "./escmd.py indices <pattern>")
            actions_table.add_row("Filter by status:", "./escmd.py indices --status yellow")
            actions_table.add_row("Show cold only:", "./escmd.py indices --cold")
            actions_table.add_row("JSON output:", "./escmd.py indices --format json")

            actions_panel = Panel(
                actions_table,
                title="[bold white]🚀 Quick Actions[/bold white]",
                border_style="magenta",
                padding=(1, 1),
                width=45
            )

        # Check if we should use pager for large datasets
        # Get paging configuration from config manager with safe defaults
        from configuration_manager import ConfigurationManager
        import os

        try:
            config_file = os.path.join(os.path.dirname(__file__), 'elastic_servers.yml')
            config_manager = ConfigurationManager(config_file, os.path.join(os.path.dirname(config_file), 'escmd.json'))

            # Try to get paging settings with fallback to defaults
            paging_enabled = getattr(config_manager, 'get_paging_enabled', lambda: False)()
            paging_threshold = getattr(config_manager, 'get_paging_threshold', lambda: 50)()
        except Exception:
            # Fallback to safe defaults if configuration fails
            paging_enabled = False
            paging_threshold = 50

        should_use_pager = use_pager or (paging_enabled and len(data_dict) > paging_threshold)

        if should_use_pager:
            # Capture all output to pager
            with console.pager():
                print()
                console.print(title_panel)
                print()
                console.print(table)
                if show_legend_panels:
                    print()
                    console.print(Columns([legend_panel, actions_panel], equal=False, expand=True))
                print()
        else:
            # Normal display
            print()
            console.print(title_panel)
            print()
            console.print(table)
            if show_legend_panels:
                print()
                console.print(Columns([legend_panel, actions_panel], equal=False, expand=True))
            print()

    def clean_index_name(self, index_name: str) -> str:
        """
        Clean Elasticsearch index names by removing '.ds-' prefix and date-related suffixes.

        Args:
            index_name (str): The original Elasticsearch index name
                             Example: '.ds-aex10-c01-logs-gwh-k8s-notifications-2025.01.06-000429'

        Returns:
            str: Cleaned index name without '.ds-' prefix and date suffix
                 Example: 'aex10-c01-logs-gwh-k8s-notifications'

        Raises:
            ValueError: If the input string is empty or None
            ValueError: If the input string doesn't match expected pattern
        """
        if not index_name:
            raise ValueError("Index name cannot be empty or None")

        # Remove '.ds-' prefix if it exists
        if index_name.startswith('.ds-'):
            index_name = index_name[4:]

        # Find and remove the date pattern and anything after it
        # Pattern matches: YYYY.MM.DD or YYYY.MM.D or YYYY.M.DD or YYYY.M.D
        pattern = r'-\d{4}\.\d{1,2}\.\d{1,2}.*$'
        cleaned_name = re.sub(pattern, '', index_name)

        # Verify we actually found and removed a date pattern
        if cleaned_name == index_name:
            raise ValueError("Input string doesn't match expected pattern with date suffix")

        return cleaned_name

    def rollover_index(self, index):
        """
        Rollover Elasticsearch Indice
        Parameters: Index (indice name)
        """
        response = self.es.indices.rollover(alias=index, body={}, dry_run=False)

        # Log the rollover result
        if response['rolled_over']:
            message = (
                f"Successfully rolled over index with alias {index}.\n"
                f"    Old index: {response['old_index']}\n"
                f"    New index: {response['new_index']}\n"
            )
        else:
            message = (
                f"Rollover conditions not met for alias {index}.\n "
                f"Conditions evaluated: {response['conditions']}\n"
            )
        return message

    def replace_roles(self, roles):
        role_mapping = {
            'data_cold': 'c',
            'data': 'd',
            'data_frozen': 'f',
            'data_hot': 'h',
            'ingest': 'i',
            'ml': 'l',
            'master': 'm',
            'remote_cluster_client': 'r',
            'data_content': 's',
            'transform': 't',
            'data_warm': 'w'
        }
        return ''.join(sorted(role_mapping.get(role, role) for role in roles))

    def change_shard_allocation(self, option):

        if option == "primary":

            settings = {
                "transient": {
                    "cluster.routing.allocation.enable": "primaries"
                }
            }
        elif option == "all":

            settings = {
                "transient": {
                    "cluster.routing.allocation.enable": None
                    #"cluster.routing.allocation.enable": "all"
                }
            }

        try:
            self.es.cluster.put_settings(body=settings)
            print("Cluster allocation change has completed successfully.")
            success = True

        except Exception as e:
            print(f"Error deleting transient settings: {e}")
            success = False

        return success

    def exclude_node_from_allocation(self, hostname=None):
        """
        Excludes a node from allocation using the cluster routing allocation exclude setting.
        Appends the hostname to any existing exclusions rather than replacing them.

        :param hostname: The hostname of the node to exclude from allocation
        :return: True if successful, False otherwise
        """
        if hostname is None:
            print("Error: Hostname parameter is required")
            return False
        try:
            # Get current cluster settings
            current_settings = self.es.cluster.get_settings(include_defaults=False)

            # Check if there are existing exclusions
            existing_exclusions = ""

            # Check transient settings first
            if 'transient' in current_settings and 'cluster' in current_settings['transient']:
                if 'routing' in current_settings['transient']['cluster']:
                    if 'allocation' in current_settings['transient']['cluster']['routing']:
                        if 'exclude' in current_settings['transient']['cluster']['routing']['allocation']:
                            if '_name' in current_settings['transient']['cluster']['routing']['allocation']['exclude']:
                                existing_exclusions = current_settings['transient']['cluster']['routing']['allocation']['exclude']['_name']

            # Check if there are existing exclusions, append the new hostname
            if existing_exclusions and existing_exclusions.strip():
                # Check if the hostname is already in the exclusion list
                exclusion_list = existing_exclusions.split(',')
                # Filter out any empty strings that might be in the list
                exclusion_list = [node for node in exclusion_list if node.strip()]
                if hostname not in exclusion_list:
                    new_exclusions = f"{','.join(exclusion_list)},{hostname}"
                else:
                    print(f"Node {hostname} is already in the exclusion list.")
                    return True
            else:
                new_exclusions = hostname

            # Update the settings with the new exclusion list
            settings = {
                "transient": {
                    "cluster.routing.allocation.exclude._name": new_exclusions
                }
            }

            response = self.es.cluster.put_settings(body=settings)
            if response.get('acknowledged', False):
                print(f"Node {hostname} has been added to allocation exclusions.")
                excluded_nodes = new_exclusions.split(',')
                # Filter out empty nodes for display
                valid_nodes = [node for node in excluded_nodes if node.strip()]
                print(f"Current exclusion list: {len(valid_nodes)} node(s)")
                if valid_nodes:
                    for node in valid_nodes:
                        print(f"  - {node}")
                else:
                    print("  No nodes are excluded")
                success = True
            else:
                print(f"Failed to update allocation exclusions. Response: {response}")
                success = False

        except Exception as e:
            print(f"Error excluding node from allocation: {e}")
            success = False

        return success

    def reset_node_allocation_exclusion(self):
        """
        Resets the node allocation exclusion setting by clearing the exclude._name parameter.
        This removes all hostnames from the exclusion list.

        :return: True if successful, False otherwise
        """
        settings = {
            "transient": {
                "cluster.routing.allocation.exclude._name": None
            }
        }

        try:
            # Get current settings before resetting
            current_settings = self.es.cluster.get_settings(include_defaults=False)
            existing_exclusions = None

            # Check if there are existing exclusions to report what's being cleared
            if 'transient' in current_settings and 'cluster' in current_settings['transient']:
                if 'routing' in current_settings['transient']['cluster']:
                    if 'allocation' in current_settings['transient']['cluster']['routing']:
                        if 'exclude' in current_settings['transient']['cluster']['routing']['allocation']:
                            if '_name' in current_settings['transient']['cluster']['routing']['allocation']['exclude']:
                                existing_exclusions = current_settings['transient']['cluster']['routing']['allocation']['exclude']['_name']

            response = self.es.cluster.put_settings(body=settings)

            if response.get('acknowledged', False):
                if existing_exclusions and existing_exclusions.strip():
                    print(f"Node allocation exclusions have been reset. Previously excluded: {existing_exclusions}")
                else:
                    print("Node allocation exclusions have been reset. No nodes were previously excluded.")
                success = True
            else:
                print(f"Failed to reset allocation exclusions. Response: {response}")
                success = False

        except Exception as e:
            print(f"Error resetting node allocation exclusion: {e}")
            success = False

        return success

    def rollover_datastream(self, datastream_name):

        # Get ES URL
        ES_URL = self.build_es_url()

        # Step 1: Get list of all indice
        if self.elastic_authentication == True:
            datastream_response = requests.post(
                f'{ES_URL}/{datastream_name}/_rollover',
                auth=HTTPBasicAuth(self.elastic_username, self.elastic_password),  # Basic Authentication
                verify=False  # Use None if SSL verification is not needed (e.g., self-signed certs)
            )
        else:
            datastream_response = requests.get(
                f'{ES_URL}/{datastream_name}/_rollover',
                verify=False  # Use None if SSL verification is not needed (e.g., self-signed certs)
            )

        # Raise an exception if the response wasn't successful
        datastream_response.raise_for_status()
        datastream_response_text = datastream_response.text
        datastream_data = json.loads(datastream_response_text)
        return datastream_data

    def list_datastreams(self):
        """
        List all datastreams in the cluster.

        :return: List of datastreams with their metadata
        """
        # Get ES URL
        ES_URL = self.build_es_url()

        if self.elastic_authentication == True:
            datastreams_response = requests.get(
                f'{ES_URL}/_data_stream',
                auth=HTTPBasicAuth(self.elastic_username, self.elastic_password),
                verify=False
            )
        else:
            datastreams_response = requests.get(
                f'{ES_URL}/_data_stream',
                verify=False
            )

        # Raise an exception if the response wasn't successful
        datastreams_response.raise_for_status()
        datastreams_data = json.loads(datastreams_response.text)
        return datastreams_data

    def get_datastream_details(self, datastream_name):
        """
        Get detailed information about a specific datastream.

        :param datastream_name: Name of the datastream
        :return: Dictionary containing datastream details
        """
        # Get ES URL
        ES_URL = self.build_es_url()

        if self.elastic_authentication == True:
            datastream_response = requests.get(
                f'{ES_URL}/_data_stream/{datastream_name}',
                auth=HTTPBasicAuth(self.elastic_username, self.elastic_password),
                verify=False
            )
        else:
            datastream_response = requests.get(
                f'{ES_URL}/_data_stream/{datastream_name}',
                verify=False
            )

        # Raise an exception if the response wasn't successful
        datastream_response.raise_for_status()
        datastream_data = json.loads(datastream_response.text)
        return datastream_data

    def delete_datastream(self, datastream_name):
        """
        Delete a specific datastream.

        :param datastream_name: Name of the datastream to delete
        :return: Dictionary containing deletion response
        """
        # Get ES URL
        ES_URL = self.build_es_url()

        if self.elastic_authentication == True:
            datastream_response = requests.delete(
                f'{ES_URL}/_data_stream/{datastream_name}',
                auth=HTTPBasicAuth(self.elastic_username, self.elastic_password),
                verify=False
            )
        else:
            datastream_response = requests.delete(
                f'{ES_URL}/_data_stream/{datastream_name}',
                verify=False
            )

        # Raise an exception if the response wasn't successful
        datastream_response.raise_for_status()
        datastream_data = json.loads(datastream_response.text)
        return datastream_data

    def show_cluster_settings(self):
        """
        Shows the current cluster settings with a focus on allocation settings.
        Highlights allocation exclusion settings if they exist.

        :return: A JSON string with the cluster settings
        """
        settings = self.es.cluster.get_settings(include_defaults=False)

        # Check for allocation exclusion settings
        exclusion_settings = None
        allocation_settings = None

        # Check in transient settings first
        if 'transient' in settings and 'cluster' in settings['transient']:
            if 'routing' in settings['transient']['cluster']:
                if 'allocation' in settings['transient']['cluster']['routing']:
                    allocation_settings = settings['transient']['cluster']['routing']['allocation']
                    if 'exclude' in allocation_settings and '_name' in allocation_settings['exclude']:
                        exclusion_settings = allocation_settings['exclude']['_name']

        # Display formatted output
        print("\n=== Current Cluster Settings ===")

        if allocation_settings:
            print("\nAllocation Settings:")
            for key, value in allocation_settings.items():
                if key == 'exclude' and '_name' in value:
                    # Handle empty string case
                    if not value['_name'] or value['_name'].strip() == '':
                        print(f"\n  Excluded Nodes (_name): 0 node(s)")
                        print("    No nodes are excluded")
                    else:
                        excluded_nodes = value['_name'].split(',')
                        # Filter out any empty strings
                        excluded_nodes = [node for node in excluded_nodes if node.strip()]
                        print(f"\n  Excluded Nodes (_name): {len(excluded_nodes)} node(s)")
                        if not excluded_nodes:
                            print("    No nodes are excluded")
                        else:
                            for node in excluded_nodes:
                                print(f"    - {node.strip()}")
                else:
                    print(f"  {key}: {value}")
        else:
            print("\nNo specific allocation settings found.")

        # Return the full JSON for reference
        return json.dumps(settings)

    def print_enhanced_allocation_settings(self):
        """
        Display allocation settings in enhanced multi-panel format following the 2.0+ style.
        """
        from rich.panel import Panel
        from rich.text import Text
        from rich.columns import Columns
        from rich.table import Table
        from rich.console import Console

        console = Console()

        try:
            # Get cluster settings
            settings = self.es.cluster.get_settings(include_defaults=False)
            health_data = self.get_cluster_health()

            # Parse allocation settings
            allocation_settings = None
            exclusion_settings = None
            excluded_nodes = []

            # Check in transient settings first
            if 'transient' in settings and 'cluster' in settings['transient']:
                if 'routing' in settings['transient']['cluster']:
                    if 'allocation' in settings['transient']['cluster']['routing']:
                        allocation_settings = settings['transient']['cluster']['routing']['allocation']
                        if 'exclude' in allocation_settings and '_name' in allocation_settings['exclude']:
                            exclusion_settings = allocation_settings['exclude']['_name']
                            if exclusion_settings and exclusion_settings.strip():
                                excluded_nodes = [node.strip() for node in exclusion_settings.split(',') if node.strip()]

            # Check if allocation is enabled by looking for enable setting
            allocation_enabled = True
            if allocation_settings and 'enable' in allocation_settings:
                if allocation_settings['enable'] == 'primaries':
                    allocation_enabled = False

            # Calculate statistics
            total_nodes = health_data.get('number_of_nodes', 0)
            data_nodes = health_data.get('number_of_data_nodes', 0)
            excluded_count = len(excluded_nodes)
            active_nodes = data_nodes - excluded_count

            # Create title panel
            if allocation_enabled:
                status_text = "✅ Enabled (All Shards)"
                status_color = "green"
            else:
                status_text = "⚠️ Disabled (Primaries Only)"
                status_color = "yellow"

            title_panel = Panel(
                Text(f"⚖️ Elasticsearch Allocation Settings Overview", style="bold cyan", justify="center"),
                subtitle=f"Status: {status_text} | Total Nodes: {total_nodes} | Data Nodes: {data_nodes} | Excluded: {excluded_count} | Active: {active_nodes}",
                border_style="cyan",
                padding=(1, 2)
            )

            # Create allocation status panel
            from rich.table import Table as InnerTable

            status_table = InnerTable(show_header=False, box=None, padding=(0, 1))
            status_table.add_column("Label", style="bold", no_wrap=True)
            status_table.add_column("Icon", justify="left", width=3)
            status_table.add_column("Value", no_wrap=True)

            if allocation_enabled:
                status_table.add_row("Allocation Status:", "✅", "Enabled (All Shards)")
                status_table.add_row("Shard Movement:", "🔄", "Primary & Replica")
            else:
                status_table.add_row("Allocation Status:", "⚠️", "Disabled (Primaries Only)")
                status_table.add_row("Shard Movement:", "🔒", "Primaries Only")

            status_table.add_row("Total Nodes:", "🖥️", str(total_nodes))
            status_table.add_row("Data Nodes:", "💾", str(data_nodes))
            status_table.add_row("Excluded Nodes:", "❌", str(excluded_count))
            status_table.add_row("Active Nodes:", "✅", str(active_nodes))

            status_panel = Panel(
                status_table,
                title="📊 Allocation Status",
                border_style=status_color,
                padding=(1, 2)
            )

            # Create exclusions panel
            if excluded_nodes:
                exclusion_content = ""
                for i, node in enumerate(excluded_nodes, 1):
                    exclusion_content += f"[bold red]{i}.[/bold red] [red]{node}[/red]\n"
                exclusion_content = exclusion_content.rstrip()

                exclusions_panel = Panel(
                    exclusion_content,
                    title="❌ Excluded Nodes",
                    border_style="red",
                    padding=(1, 2)
                )
            else:
                exclusions_panel = Panel(
                    Text("✅ No nodes are currently excluded from allocation", style="bold green", justify="center"),
                    title="❌ Excluded Nodes",
                    border_style="green",
                    padding=(1, 2)
                )

            # Create configuration details panel
            config_table = InnerTable(show_header=False, box=None, padding=(0, 1))
            config_table.add_column("Setting", style="bold", no_wrap=True)
            config_table.add_column("Icon", justify="left", width=3)
            config_table.add_column("Value", no_wrap=True)

            if allocation_settings:
                for key, value in allocation_settings.items():
                    if key == 'exclude':
                        continue  # Skip - handled in exclusions panel
                    elif key == 'enable':
                        icon = "✅" if value == 'all' else "⚠️" if value == 'primaries' else "❌"
                        display_value = "All Shards" if value == 'all' else "Primaries Only" if value == 'primaries' else "Disabled"
                        config_table.add_row("Enable Setting:", icon, display_value)
                    else:
                        config_table.add_row(f"{key.title()}:", "⚙️", str(value))
            else:
                config_table.add_row("Configuration:", "📋", "Default Settings (No Custom Config)")

            config_panel = Panel(
                config_table,
                title="⚙️ Configuration Details",
                border_style="blue",
                padding=(1, 2)
            )

            # Create quick actions panel
            actions_table = InnerTable(show_header=False, box=None, padding=(0, 1))
            actions_table.add_column("Action", style="bold magenta", no_wrap=True)
            actions_table.add_column("Command", style="dim white")

            actions_table.add_row("Enable allocation:", "./escmd.py allocation enable")
            actions_table.add_row("Disable allocation:", "./escmd.py allocation disable")
            actions_table.add_row("Exclude node:", "./escmd.py allocation exclude add <hostname>")
            actions_table.add_row("Remove exclusion:", "./escmd.py allocation exclude remove <hostname>")
            actions_table.add_row("Reset exclusions:", "./escmd.py allocation exclude reset")

            actions_panel = Panel(
                actions_table,
                title="🚀 Quick Actions",
                border_style="magenta",
                padding=(1, 2)
            )

            # Display everything with enhanced layout
            print()
            console.print(title_panel)
            print()

            # Create two-column layout for main panels
            console.print(Columns([status_panel, config_panel], expand=True))
            print()

            # Create two-column layout for bottom panels
            console.print(Columns([exclusions_panel, actions_panel], expand=True))
            print()

        except Exception as e:
            console.print(f"[red]❌ Error retrieving allocation settings: {str(e)}[/red]")

        # Return the full JSON for reference
        return json.dumps(settings)

    def show_progress_static(self, completion, bar_width=20):
        """
        Displays a static progress bar with the given completion percentage and specified width.
        The bar is yellow until it reaches 100%, at which point it turns green.

        :param completion: Completion percentage (0 to 100)
        :param bar_width: Width of the progress bar
        """
        console = Console()

        # Determine the color based on completion
        bar_color = "yellow" if completion < 100 else "green"
        unfinished_color = "white"

        # Create the progress bar components with a custom width and color
        progress = Progress(
            TextColumn(""),
            BarColumn(bar_width=bar_width, style=unfinished_color, complete_style=bar_color),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        )

        # Manually set up the progress bar without starting it
        task = progress.add_task("", total=100, completed=completion)

        # Render the static progress bar
        return progress

    def get_settings(self):

        settings = self.es.cluster.get_settings()
        return json.dumps(settings)

    def print_enhanced_cluster_settings(self):
        """
        Display cluster settings in enhanced multi-panel format following the 2.0+ style.
        """
        from rich.panel import Panel
        from rich.text import Text
        from rich.columns import Columns
        from rich.table import Table
        from rich.console import Console

        console = Console()

        try:
            # Get comprehensive cluster data
            settings = self.es.cluster.get_settings(include_defaults=False)
            default_settings = self.es.cluster.get_settings(include_defaults=True)
            health_data = self.get_cluster_health()

            # Extract different setting categories
            transient_settings = settings.get('transient', {})
            persistent_settings = settings.get('persistent', {})

            # Parse allocation settings
            allocation_settings = None
            excluded_nodes = []
            allocation_enabled = True

            if 'cluster' in transient_settings and 'routing' in transient_settings['cluster']:
                if 'allocation' in transient_settings['cluster']['routing']:
                    allocation_settings = transient_settings['cluster']['routing']['allocation']
                    if 'exclude' in allocation_settings and '_name' in allocation_settings['exclude']:
                        exclusion_settings = allocation_settings['exclude']['_name']
                        if exclusion_settings and exclusion_settings.strip():
                            excluded_nodes = [node.strip() for node in exclusion_settings.split(',') if node.strip()]
                    if 'enable' in allocation_settings:
                        if allocation_settings['enable'] == 'primaries':
                            allocation_enabled = False

            # Count total settings
            total_transient = self._count_nested_settings(transient_settings)
            total_persistent = self._count_nested_settings(persistent_settings)
            total_custom = total_transient + total_persistent

            # Calculate statistics
            cluster_name = health_data.get('cluster_name', 'Unknown')
            total_nodes = health_data.get('number_of_nodes', 0)
            data_nodes = health_data.get('number_of_data_nodes', 0)

            # Create title panel
            title_panel = Panel(
                Text(f"⚙️ Elasticsearch Cluster Settings Overview", style="bold cyan", justify="center"),
                subtitle=f"Cluster: {cluster_name} | Nodes: {total_nodes} | Custom Settings: {total_custom} | Transient: {total_transient} | Persistent: {total_persistent}",
                border_style="cyan",
                padding=(1, 2)
            )

            # Create cluster overview panel
            from rich.table import Table as InnerTable

            overview_table = InnerTable(show_header=False, box=None, padding=(0, 1))
            overview_table.add_column("Label", style="bold", no_wrap=True)
            overview_table.add_column("Icon", justify="left", width=3)
            overview_table.add_column("Value", no_wrap=True)

            cluster_status = health_data.get('cluster_status', 'unknown')
            status_icon = "🟢" if cluster_status == 'green' else "🟡" if cluster_status == 'yellow' else "🔴"

            overview_table.add_row("Cluster Name:", "🏢", cluster_name)
            overview_table.add_row("Cluster Status:", status_icon, cluster_status.title())
            overview_table.add_row("Total Nodes:", "🖥️", str(total_nodes))
            overview_table.add_row("Data Nodes:", "💾", str(data_nodes))
            overview_table.add_row("Custom Settings:", "⚙️", str(total_custom))

            overview_panel = Panel(
                overview_table,
                title="📊 Cluster Overview",
                border_style="blue",
                padding=(1, 2)
            )

            # Create allocation settings panel
            allocation_table = InnerTable(show_header=False, box=None, padding=(0, 1))
            allocation_table.add_column("Setting", style="bold", no_wrap=True)
            allocation_table.add_column("Icon", justify="left", width=3)
            allocation_table.add_column("Value", no_wrap=True)

            if allocation_enabled:
                allocation_table.add_row("Allocation Status:", "✅", "Enabled (All Shards)")
                allocation_table.add_row("Shard Movement:", "🔄", "Primary & Replica")
            else:
                allocation_table.add_row("Allocation Status:", "⚠️", "Disabled (Primaries Only)")
                allocation_table.add_row("Shard Movement:", "🔒", "Primaries Only")

            allocation_table.add_row("Excluded Nodes:", "❌", str(len(excluded_nodes)) if excluded_nodes else "None")

            # Add other routing settings if they exist
            if allocation_settings:
                for key, value in allocation_settings.items():
                    if key not in ['enable', 'exclude']:
                        allocation_table.add_row(f"{key.title()}:", "⚙️", str(value))

            allocation_panel = Panel(
                allocation_table,
                title="⚖️ Allocation Settings",
                border_style="green",
                padding=(1, 2)
            )

            # Create security & configuration panel
            config_table = InnerTable(show_header=False, box=None, padding=(0, 1))
            config_table.add_column("Category", style="bold", no_wrap=True)
            config_table.add_column("Status", no_wrap=True)

            # SSL/TLS status
            ssl_status = "Enabled 🔒" if self.use_ssl else "Disabled 🔓"
            config_table.add_row("SSL/TLS:", ssl_status)

            # Authentication status
            auth_status = "Enabled 🔐" if self.elastic_authentication else "Disabled 🚪"
            config_table.add_row("Authentication:", auth_status)

            # Cert verification
            if self.use_ssl:
                cert_status = "Verified ✅" if self.verify_certs else "Unverified ⚠️"
                config_table.add_row("Certificate Verify:", cert_status)

            # Check for other important settings
            if transient_settings or persistent_settings:
                config_table.add_row("Custom Config:", "Present ⚙️")
            else:
                config_table.add_row("Custom Config:", "Default Settings 📋")

            config_panel = Panel(
                config_table,
                title="🔐 Security & Configuration",
                border_style="yellow",
                padding=(1, 2)
            )

            # Create settings breakdown panel
            settings_breakdown = InnerTable(show_header=False, box=None, padding=(0, 1))
            settings_breakdown.add_column("Type", style="bold", no_wrap=True)
            settings_breakdown.add_column("Icon", justify="left", width=3)
            settings_breakdown.add_column("Count", no_wrap=True)

            settings_breakdown.add_row("Transient Settings:", "⏰", str(total_transient))
            settings_breakdown.add_row("Persistent Settings:", "💾", str(total_persistent))

            # Show key setting categories if they exist
            if 'cluster' in transient_settings:
                cluster_settings = self._count_nested_settings(transient_settings['cluster'])
                settings_breakdown.add_row("Cluster Settings:", "🏢", str(cluster_settings))

            if 'indices' in transient_settings or 'indices' in persistent_settings:
                indices_settings = (self._count_nested_settings(transient_settings.get('indices', {})) +
                                  self._count_nested_settings(persistent_settings.get('indices', {})))
                settings_breakdown.add_row("Index Settings:", "📊", str(indices_settings))

            breakdown_panel = Panel(
                settings_breakdown,
                title="📈 Settings Breakdown",
                border_style="magenta",
                padding=(1, 2)
            )

            # Create quick actions panel
            actions_table = InnerTable(show_header=False, box=None, padding=(0, 1))
            actions_table.add_column("Action", style="bold cyan", no_wrap=True)
            actions_table.add_column("Command", style="dim white")

            actions_table.add_row("View settings JSON:", "./escmd.py settings --format json")
            actions_table.add_row("View allocation:", "./escmd.py allocation display")
            actions_table.add_row("Check cluster health:", "./escmd.py health")
            actions_table.add_row("View nodes:", "./escmd.py nodes")
            actions_table.add_row("Monitor recovery:", "./escmd.py recovery")

            actions_panel = Panel(
                actions_table,
                title="🚀 Quick Actions",
                border_style="cyan",
                padding=(1, 2)
            )

            # Create ILM overview panel
            ilm_panel = self._create_ilm_overview_panel()

            # Create detailed settings table
            detailed_settings_table = self._create_detailed_settings_table(settings, transient_settings, persistent_settings)

            # Display everything with enhanced layout
            print()
            console.print(title_panel)
            print()

            # Create two-column layout for main panels
            console.print(Columns([overview_panel, allocation_panel], expand=True))
            print()

            # Create three-column layout for bottom panels (now includes ILM)
            console.print(Columns([config_panel, breakdown_panel, ilm_panel], expand=True))
            print()

            # Show detailed settings table if there are any settings
            if detailed_settings_table:
                console.print(detailed_settings_table)
                print()

            # Actions panel spans full width
            console.print(actions_panel)
            print()

        except Exception as e:
            console.print(f"[red]❌ Error retrieving cluster settings: {str(e)}[/red]")

    def _count_nested_settings(self, settings_dict):
        """Helper method to count nested settings recursively."""
        if not isinstance(settings_dict, dict):
            return 1

        count = 0
        for value in settings_dict.values():
            if isinstance(value, dict):
                count += self._count_nested_settings(value)
            else:
                count += 1
        return count

    def _get_ilm_status(self):
        """Get ILM status and basic statistics."""
        try:
            # Get ILM status
            ilm_status = self.es.ilm.get_status()

            # Get ILM policies
            policies = self.es.ilm.get_lifecycle()

            # Get ILM explain for all indices to understand phase distribution
            ilm_explain = self.es.ilm.explain_lifecycle(index="_all")

            # Process phase distribution
            phase_counts = {'hot': 0, 'warm': 0, 'cold': 0, 'frozen': 0, 'delete': 0, 'unmanaged': 0, 'error': 0}

            for index_name, index_info in ilm_explain.get('indices', {}).items():
                if 'managed' in index_info and index_info['managed']:
                    phase = index_info.get('phase', 'unknown')
                    if phase in phase_counts:
                        phase_counts[phase] += 1

                    # Check for errors
                    if 'step_info' in index_info and 'error' in index_info.get('step_info', {}):
                        phase_counts['error'] += 1
                else:
                    phase_counts['unmanaged'] += 1

            return {
                'operation_mode': ilm_status.get('operation_mode', 'UNKNOWN'),
                'policy_count': len(policies),
                'phase_counts': phase_counts,
                'total_managed': sum(phase_counts[p] for p in ['hot', 'warm', 'cold', 'frozen', 'delete']),
                'has_errors': phase_counts['error'] > 0
            }

        except Exception as e:
            return {
                'operation_mode': 'ERROR',
                'error': str(e),
                'policy_count': 0,
                'phase_counts': {'hot': 0, 'warm': 0, 'cold': 0, 'frozen': 0, 'delete': 0, 'unmanaged': 0, 'error': 0},
                'total_managed': 0,
                'has_errors': False
            }

    def _create_ilm_overview_panel(self):
        """Create ILM overview panel for settings display."""
        from rich.table import Table as InnerTable
        from rich.panel import Panel
        from rich.text import Text

        ilm_data = self._get_ilm_status()

        ilm_table = InnerTable(show_header=False, box=None, padding=(0, 1))
        ilm_table.add_column("Metric", style="bold", no_wrap=True)
        ilm_table.add_column("Value", no_wrap=True)

        # ILM Status
        if ilm_data['operation_mode'] == 'RUNNING':
            status_display = "Running ✅"
        elif ilm_data['operation_mode'] == 'STOPPED':
            status_display = "Stopped ⚠️"
        elif ilm_data['operation_mode'] == 'ERROR':
            status_display = f"Error ❌"
        else:
            status_display = f"{ilm_data['operation_mode']} ❓"

        ilm_table.add_row("ILM Status:", status_display)
        ilm_table.add_row("Policies:", f"{ilm_data['policy_count']} 📋")
        ilm_table.add_row("Managed Indices:", f"{ilm_data['total_managed']} 📊")

        # Phase breakdown (show only non-zero counts to save space)
        phase_icons = {'hot': '🔥', 'warm': '🟡', 'cold': '🧊', 'frozen': '❄️', 'delete': '🗑️'}
        for phase, count in ilm_data['phase_counts'].items():
            if count > 0 and phase in phase_icons:
                ilm_table.add_row(f"{phase.title()}:", f"{count} {phase_icons[phase]}")

        # Show unmanaged if any
        if ilm_data['phase_counts']['unmanaged'] > 0:
            ilm_table.add_row("Unmanaged:", f"{ilm_data['phase_counts']['unmanaged']} ⚪")

        # Show errors if any
        if ilm_data['has_errors']:
            ilm_table.add_row("Errors:", f"{ilm_data['phase_counts']['error']} ⚠️")

        # Error handling
        if 'error' in ilm_data:
            ilm_table.add_row("Error:", "API Access ❌")

        return Panel(
            ilm_table,
            title="📋 ILM Overview",
            border_style="blue",
            padding=(1, 2)
        )

    def get_ilm_policies(self):
        """Get all ILM policies."""
        try:
            return self.es.ilm.get_lifecycle()
        except Exception as e:
            return {"error": str(e)}

    def get_ilm_policy_detail(self, policy_name):
        """Get detailed information for a specific ILM policy."""
        try:
            # Get the specific policy
            policy_data = self.es.ilm.get_lifecycle(policy=policy_name)

            if policy_name not in policy_data:
                return {"error": f"Policy '{policy_name}' not found"}

            policy_info = policy_data[policy_name]

            # Get indices using this policy
            try:
                all_explain = self.es.ilm.explain_lifecycle(index="_all")
                using_indices = []

                for index_name, index_info in all_explain.get('indices', {}).items():
                    if index_info.get('policy') == policy_name:
                        using_indices.append({
                            'name': index_name,
                            'phase': index_info.get('phase', 'N/A'),
                            'action': index_info.get('action', 'N/A'),
                            'managed': index_info.get('managed', False)
                        })

                policy_info['using_indices'] = using_indices
            except:
                policy_info['using_indices'] = []

            return {policy_name: policy_info}

        except Exception as e:
            return {"error": str(e)}

    def get_ilm_explain(self, index_name):
        """Get ILM explain for specific index."""
        try:
            return self.es.ilm.explain_lifecycle(index=index_name)
        except Exception as e:
            error_msg = str(e)
            # Check if this might be a policy name instead of index name
            if "index_not_found_exception" in error_msg:
                # Get list of policies to check if the user provided a policy name
                try:
                    policies = self.get_ilm_policies()
                    if not isinstance(policies, dict) or 'error' in policies:
                        return {"error": f"Index not found: {error_msg}"}

                    if index_name in policies:
                        return {"error": f"'{index_name}' is an ILM policy name, not an index name. Use 'ilm explain <index-name>' with an actual index name, not a policy name."}
                except:
                    pass

                return {"error": f"Index '{index_name}' not found. Make sure you're using an index name (not a policy name). Use './escmd.py list' to see available indices."}

            return {"error": error_msg}

    def get_ilm_errors(self):
        """Get indices with ILM errors."""
        try:
            ilm_explain = self.es.ilm.explain_lifecycle(index="_all")
            errors = {}

            for index_name, index_info in ilm_explain.get('indices', {}).items():
                if 'step_info' in index_info and 'error' in index_info.get('step_info', {}):
                    errors[index_name] = index_info

            return errors
        except Exception as e:
            return {"error": str(e)}

    def print_enhanced_ilm_status(self):
        """Display comprehensive ILM status in multi-panel format."""
        from rich.panel import Panel
        from rich.text import Text
        from rich.columns import Columns
        from rich.table import Table
        from rich.console import Console

        console = Console()

        try:
            ilm_data = self._get_ilm_status()

            # Create title panel
            title_panel = Panel(
                Text(f"📋 Index Lifecycle Management (ILM) Status", style="bold cyan", justify="center"),
                subtitle=f"Operation Mode: {ilm_data['operation_mode']} | Policies: {ilm_data['policy_count']} | Managed: {ilm_data['total_managed']}",
                border_style="cyan",
                padding=(1, 2)
            )

            # Create status overview panel
            from rich.table import Table as InnerTable

            status_table = InnerTable(show_header=False, box=None, padding=(0, 1))
            status_table.add_column("Label", style="bold", no_wrap=True)
            status_table.add_column("Icon", justify="left", width=3)
            status_table.add_column("Value", no_wrap=True)

            # ILM Status
            if ilm_data['operation_mode'] == 'RUNNING':
                status_table.add_row("Operation Mode:", "✅", "Running")
            elif ilm_data['operation_mode'] == 'STOPPED':
                status_table.add_row("Operation Mode:", "⚠️", "Stopped")
            else:
                status_table.add_row("Operation Mode:", "❌", ilm_data['operation_mode'])

            status_table.add_row("Total Policies:", "📋", str(ilm_data['policy_count']))
            status_table.add_row("Managed Indices:", "📊", str(ilm_data['total_managed']))
            status_table.add_row("Unmanaged Indices:", "⚪", str(ilm_data['phase_counts']['unmanaged']))

            if ilm_data['has_errors']:
                status_table.add_row("Error Count:", "⚠️", str(ilm_data['phase_counts']['error']))

            status_panel = Panel(
                status_table,
                title="📊 ILM Status",
                border_style="green",
                padding=(1, 2)
            )

            # Create phase distribution panel
            phase_table = InnerTable(show_header=False, box=None, padding=(0, 1))
            phase_table.add_column("Phase", style="bold", no_wrap=True)
            phase_table.add_column("Icon", justify="left", width=3)
            phase_table.add_column("Count", no_wrap=True)

            phase_icons = {'hot': '🔥', 'warm': '🟡', 'cold': '🧊', 'frozen': '❄️', 'delete': '🗑️'}
            phase_colors = {'hot': 'red', 'warm': 'yellow', 'cold': 'blue', 'frozen': 'cyan', 'delete': 'magenta'}

            for phase, count in ilm_data['phase_counts'].items():
                if count > 0 and phase in phase_icons:
                    phase_table.add_row(
                        f"{phase.title()}:",
                        phase_icons[phase],
                        f"{count:,}"
                    )

            phase_panel = Panel(
                phase_table,
                title="🔄 Phase Distribution",
                border_style="blue",
                padding=(1, 2)
            )

            # Create quick actions panel
            actions_table = InnerTable(show_header=False, box=None, padding=(0, 1))
            actions_table.add_column("Action", style="bold cyan", no_wrap=True)
            actions_table.add_column("Command", style="dim white")

            actions_table.add_row("List policies:", "./escmd.py ilm policies")
            actions_table.add_row("Policy details:", "./escmd.py ilm policy <name>")
            actions_table.add_row("Check errors:", "./escmd.py ilm errors")
            actions_table.add_row("Explain index:", "./escmd.py ilm explain <index>")
            actions_table.add_row("JSON output:", "./escmd.py ilm status --format json")

            actions_panel = Panel(
                actions_table,
                title="🚀 Quick Actions",
                border_style="magenta",
                padding=(1, 2)
            )

            # Display everything
            print()
            console.print(title_panel)
            print()
            console.print(Columns([status_panel, phase_panel], expand=True))
            print()
            console.print(actions_panel)
            print()

        except Exception as e:
            console.print(f"[red]❌ Error retrieving ILM status: {str(e)}[/red]")

    def print_enhanced_ilm_policies(self):
        """Display ILM policies in enhanced format."""
        from rich.panel import Panel
        from rich.table import Table
        from rich.console import Console

        console = Console()
        policies = self.get_ilm_policies()

        if 'error' in policies:
            console.print(f"[red]❌ Error retrieving ILM policies: {policies['error']}[/red]")
            return

        # Get cluster name and version for context
        health_data = self.get_cluster_health()
        cluster_name = health_data.get('cluster_name', 'Unknown')
        cluster_version = health_data.get('cluster_version', 'Unknown')

        # Create title panel with version info
        if cluster_version != 'Unknown':
            cluster_info = f"Cluster: {cluster_name} (v{cluster_version})"
        else:
            cluster_info = f"Cluster: {cluster_name}"
            
        title_panel = Panel(
            Text(f"📋 ILM Policies Overview", style="bold cyan", justify="center"),
            subtitle=f"{cluster_info} | Total Policies: {len(policies)}",
            border_style="cyan",
            padding=(1, 2)
        )

        # Create policies table
        table = Table(show_header=True, header_style="bold white", expand=True)
        table.add_column("📋 Policy Name", style="cyan", no_wrap=True)
        table.add_column("🔥 Hot", justify="center", width=8)
        table.add_column("🟡 Warm", justify="center", width=8)
        table.add_column("🧊 Cold", justify="center", width=8)
        table.add_column("❄️ Frozen", justify="center", width=8)
        table.add_column("🗑️ Delete", justify="center", width=8)

        for policy_name, policy_data in policies.items():
            policy_def = policy_data.get('policy', {})
            phases = policy_def.get('phases', {})

            hot = "✅" if 'hot' in phases else "❌"
            warm = "✅" if 'warm' in phases else "❌"
            cold = "✅" if 'cold' in phases else "❌"
            frozen = "✅" if 'frozen' in phases else "❌"
            delete = "✅" if 'delete' in phases else "❌"

            table.add_row(policy_name, hot, warm, cold, frozen, delete)

        print()
        console.print(title_panel)
        print()
        console.print(table)
        print()

    def print_enhanced_ilm_policy_detail(self, policy_name, show_all_indices=False):
        """Display detailed information for a specific ILM policy with improved readability."""
        from rich.panel import Panel
        from rich.table import Table
        from rich.console import Console
        from rich.text import Text
        from rich.columns import Columns

        console = Console()
        policy_data = self.get_ilm_policy_detail(policy_name)

        if 'error' in policy_data:
            console.print(f"[red]❌ Error retrieving policy '{policy_name}': {policy_data['error']}[/red]")
            return

        # Get cluster name and version for context
        health_data = self.get_cluster_health()
        cluster_name = health_data.get('cluster_name', 'Unknown')
        cluster_version = health_data.get('cluster_version', 'Unknown')

        policy_info = policy_data[policy_name]
        policy_def = policy_info.get('policy', {})
        phases = policy_def.get('phases', {})
        using_indices = policy_info.get('using_indices', [])

        # Analyze phases and indices for summary
        active_phases = list(phases.keys())
        phase_stats = {}
        for index in using_indices:
            phase = index.get('phase', 'unknown')
            phase_stats[phase] = phase_stats.get(phase, 0) + 1

        # Create title panel with enhanced summary including version
        active_phases_str = " → ".join([f"{phase.title()} {self._get_phase_icon(phase)}" for phase in ['hot', 'warm', 'cold', 'frozen', 'delete'] if phase in phases])
        if not active_phases_str:
            active_phases_str = "No phases configured"

        # Build subtitle with cluster info and version
        if cluster_version != 'Unknown':
            cluster_info = f"Cluster: {cluster_name} (v{cluster_version})"
        else:
            cluster_info = f"Cluster: {cluster_name}"
            
        title_panel = Panel(
            Text(f"📋 ILM Policy: {policy_name}", style="bold cyan", justify="center"),
            subtitle=f"{cluster_info} | Version: {policy_info.get('version', 'N/A')} | Lifecycle: {active_phases_str} | Managing {len(using_indices)} indices",
            border_style="cyan",
            padding=(1, 2)
        )

        # Create individual phase cards instead of a single table
        phase_panels = []
        phase_order = ['hot', 'warm', 'cold', 'frozen', 'delete']
        
        for phase_name in phase_order:
            if phase_name in phases:
                phase_config = phases[phase_name]
                
                # Create phase details table
                phase_table = Table(show_header=False, box=None, padding=(0, 1))
                phase_table.add_column("Detail", style="bold", no_wrap=True, width=12)
                phase_table.add_column("Value", style="white")

                # Get actions with better formatting
                actions = []
                if 'actions' in phase_config:
                    for action_name, action_config in phase_config['actions'].items():
                        action_display = action_name.replace('_', ' ').title()
                        if isinstance(action_config, dict) and action_config:
                            # Show key configuration details
                            config_items = []
                            for key, value in action_config.items():
                                config_items.append(f"{key}: {value}")
                            if config_items:
                                action_display += f" ({', '.join(config_items)})"
                        actions.append(action_display)

                # Add phase information
                phase_table.add_row("Status:", f"✅ Active {self._get_phase_icon(phase_name)}")
                
                if 'min_age' in phase_config:
                    phase_table.add_row("Trigger:", f"After {phase_config['min_age']}")
                else:
                    phase_table.add_row("Trigger:", "Immediate")
                
                if actions:
                    phase_table.add_row("Actions:", f"{len(actions)} configured")
                    for i, action in enumerate(actions, 1):
                        phase_table.add_row(f"  └─ Action {i}:", action)
                else:
                    phase_table.add_row("Actions:", "None")

                # Add index count in this phase
                indices_in_phase = phase_stats.get(phase_name, 0)
                if indices_in_phase > 0:
                    phase_table.add_row("Indices:", f"{indices_in_phase} currently in this phase")

                # Create phase panel with appropriate color
                phase_colors = {
                    'hot': 'red',
                    'warm': 'yellow', 
                    'cold': 'blue',
                    'frozen': 'cyan',
                    'delete': 'magenta'
                }
                
                phase_panel = Panel(
                    phase_table,
                    title=f"[bold]{self._get_phase_icon(phase_name)} {phase_name.title()} Phase",
                    border_style=phase_colors.get(phase_name, 'white'),
                    padding=(1, 1)
                )
                phase_panels.append(phase_panel)

        # Create lifecycle flow visualization
        if phase_panels:
            # Group phase panels in rows of 2 for better readability
            flow_content = "📋 **Policy Lifecycle Flow**\n\n"
            configured_phases = [p for p in phase_order if p in phases]
            
            for i, phase in enumerate(configured_phases):
                arrow = " → " if i < len(configured_phases) - 1 else ""
                flow_content += f"{self._get_phase_icon(phase)} **{phase.title()}**{arrow}"
            
            flow_panel = Panel(
                Text(flow_content, style="bold white"),
                title="🔄 Lifecycle Overview",
                border_style="green",
                padding=(1, 2)
            )

        # Create enhanced indices display with better organization
        if using_indices:
            # Group indices by phase for better readability
            indices_by_phase = {}
            for index in using_indices:
                phase = index.get('phase', 'unknown')
                if phase not in indices_by_phase:
                    indices_by_phase[phase] = []
                indices_by_phase[phase].append(index)

            # Create summary stats
            summary_table = Table(show_header=False, box=None, padding=(0, 1))
            summary_table.add_column("Phase", style="bold", width=12)
            summary_table.add_column("Count", justify="center", width=8)
            summary_table.add_column("Icon", justify="center", width=6)

            for phase in phase_order:
                if phase in indices_by_phase:
                    count = len(indices_by_phase[phase])
                    summary_table.add_row(
                        f"{phase.title()}:",
                        f"{count}",
                        self._get_phase_icon(phase)
                    )

            summary_panel = Panel(
                summary_table,
                title="� Indices Distribution by Phase",
                border_style="blue",
                padding=(1, 1)
            )

            # Create detailed indices table
            indices_table = Table(show_header=True, header_style="bold white", expand=True)
            indices_table.add_column("📁 Index Name", style="cyan", no_wrap=True)
            indices_table.add_column("🔄 Phase", justify="center", width=12)
            indices_table.add_column("⚙️ Action", style="dim", width=20)
            indices_table.add_column("📊 Status", justify="center", width=10)

            # Sort indices by phase, then by name
            sorted_indices = sorted(using_indices, key=lambda x: (
                phase_order.index(x.get('phase', 'unknown')) if x.get('phase', 'unknown') in phase_order else 999,
                x.get('name', '')
            ))

            # Determine how many indices to show
            indices_to_show = sorted_indices if show_all_indices else sorted_indices[:15]  # Increased from 10

            current_phase = None
            for index in indices_to_show:
                phase = index.get('phase', 'unknown')
                
                # Add phase separator for better visual grouping
                if phase != current_phase and len(indices_to_show) > 5:  # Only show separators for larger lists
                    if current_phase is not None:  # Not the first phase
                        indices_table.add_row("", "", "", "")  # Empty separator row
                    current_phase = phase

                phase_display = f"{self._get_phase_icon(phase)} {phase.title()}"
                managed_display = "✅ Managed" if index.get('managed', False) else "⚠️ Unmanaged"
                
                indices_table.add_row(
                    index.get('name', 'Unknown'),
                    phase_display,
                    index.get('action', 'N/A'),
                    managed_display
                )

            # Add "more" indicator with better styling
            if not show_all_indices and len(using_indices) > 15:
                indices_table.add_row(
                    "...", 
                    f"[dim]+{len(using_indices) - 15} more[/dim]", 
                    "[dim]Use --show-all to see all[/dim]", 
                    ""
                )

            # Create enhanced indices panel
            if show_all_indices or len(using_indices) <= 15:
                indices_title = f"📁 All Indices Using This Policy ({len(using_indices)} total)"
            else:
                indices_title = f"📁 Indices Using This Policy (showing 15 of {len(using_indices)})"

            indices_panel = Panel(
                indices_table,
                title=indices_title,
                border_style="green",
                padding=(1, 1)
            )
        else:
            # No indices using this policy
            summary_panel = Panel(
                Text("ℹ️  This policy is not currently being used by any indices.\n\nTo apply this policy to an index template or data stream, update your index template configuration.", 
                     style="dim white", justify="center"),
                title="� Policy Usage",
                border_style="yellow",
                padding=(2, 2)
            )
            indices_panel = None

        # Create quick actions with more relevant commands
        actions_table = Table(show_header=False, box=None, padding=(0, 1))
        actions_table.add_column("Action", style="bold magenta", no_wrap=True)
        actions_table.add_column("Command", style="cyan")

        actions_table.add_row("📋 All policies:", "./escmd.py ilm policies")
        actions_table.add_row("📊 ILM status:", "./escmd.py ilm status")
        actions_table.add_row("⚠️  Check errors:", "./escmd.py ilm errors")
        
        if using_indices:
            # Pick a representative index from the largest phase
            largest_phase = max(phase_stats.items(), key=lambda x: x[1])[0] if phase_stats else None
            sample_index = next((idx for idx in using_indices if idx.get('phase') == largest_phase), using_indices[0])
            actions_table.add_row("🔍 Explain index:", f"./escmd.py ilm explain {sample_index['name']}")
            
            if not show_all_indices and len(using_indices) > 15:
                actions_table.add_row("📋 Show all indices:", f"./escmd.py ilm policy {policy_name} --show-all")
        
        actions_table.add_row("📄 JSON format:", f"./escmd.py ilm policy {policy_name} --format json")

        actions_panel = Panel(
            actions_table,
            title="🚀 Quick Actions",
            border_style="magenta",
            padding=(1, 1)
        )

        # Display everything with improved layout
        print()
        console.print(title_panel)
        print()

        # Show lifecycle flow if phases exist
        if phase_panels:
            console.print(flow_panel)
            print()

            # Display phase panels in a more readable layout
            if len(phase_panels) <= 2:
                # Show side by side for 1-2 phases
                console.print(Columns(phase_panels, expand=True))
            elif len(phase_panels) <= 4:
                # Show in 2x2 grid for 3-4 phases
                for i in range(0, len(phase_panels), 2):
                    row_panels = phase_panels[i:i+2]
                    console.print(Columns(row_panels, expand=True))
                    if i + 2 < len(phase_panels):  # Add spacing between rows
                        print()
            else:
                # Stack vertically for many phases
                for panel in phase_panels:
                    console.print(panel)
            print()

        # Show indices information
        if using_indices:
            console.print(summary_panel)
            print()
            if indices_panel:
                console.print(indices_panel)
                print()
        else:
            console.print(summary_panel)
            print()

        # Actions panel spans full width
        console.print(actions_panel)
        print()

    def print_enhanced_ilm_explain(self, index_name):
        """Display ILM explain for specific index."""
        from rich.panel import Panel
        from rich.table import Table
        from rich.console import Console
        from rich.text import Text

        console = Console()
        explain_data = self.get_ilm_explain(index_name)

        if 'error' in explain_data:
            console.print(f"[red]❌ Error explaining ILM for index '{index_name}': {explain_data['error']}[/red]")
            return

        # Check if index exists in the response
        if 'indices' not in explain_data:
            console.print(f"[red]❌ No ILM data found for index '{index_name}'[/red]")
            return

        index_info = explain_data.get('indices', {}).get(index_name, {})

        if not index_info:
            console.print(f"[red]❌ Index '{index_name}' not found in ILM explain response[/red]")
            return

        # Create title panel
        title_panel = Panel(
            Text(f"📋 ILM Explain: {index_name}", style="bold cyan", justify="center"),
            border_style="cyan",
            padding=(1, 2)
        )

        # Create details table
        details_table = Table(show_header=False, box=None, padding=(0, 1))
        details_table.add_column("Property", style="bold", no_wrap=True)
        details_table.add_column("Value", no_wrap=True)

        managed = index_info.get('managed', False)
        details_table.add_row("Managed:", "✅ Yes" if managed else "❌ No")

        if managed:
            details_table.add_row("Policy:", index_info.get('policy', 'N/A'))
            details_table.add_row("Current Phase:", f"{index_info.get('phase', 'N/A')} {self._get_phase_icon(index_info.get('phase', ''))}")
            details_table.add_row("Current Action:", index_info.get('action', 'N/A'))
            details_table.add_row("Current Step:", index_info.get('step', 'N/A'))

            # Check for errors
            if 'step_info' in index_info and 'error' in index_info.get('step_info', {}):
                error_info = index_info['step_info']['error']
                details_table.add_row("Error:", f"❌ {error_info.get('type', 'Unknown')}")
                details_table.add_row("Error Reason:", error_info.get('reason', 'N/A'))

        details_panel = Panel(
            details_table,
            title="📊 ILM Details",
            border_style="blue",
            padding=(1, 2)
        )

        print()
        console.print(title_panel)
        print()
        console.print(details_panel)
        print()

    def print_enhanced_ilm_errors(self):
        """Display indices with ILM errors."""
        from rich.panel import Panel
        from rich.table import Table
        from rich.console import Console
        from rich.text import Text

        console = Console()
        errors = self.get_ilm_errors()

        if 'error' in errors:
            console.print(f"[red]❌ Error retrieving ILM errors: {errors['error']}[/red]")
            return

        # Create title panel
        title_panel = Panel(
            Text(f"⚠️ ILM Errors Report", style="bold red", justify="center"),
            subtitle=f"Indices with errors: {len(errors)}",
            border_style="red",
            padding=(1, 2)
        )

        if not errors:
            console.print(title_panel)
            console.print()
            console.print(Panel(
                Text("✅ No ILM errors found!", style="bold green", justify="center"),
                border_style="green",
                padding=(1, 2)
            ))
            print()
            return

        # Create errors table
        table = Table(show_header=True, header_style="bold white", expand=True)
        table.add_column("📋 Index Name", style="cyan", no_wrap=False)
        table.add_column("📋 Policy", style="yellow", width=15)
        table.add_column("🔥 Phase", style="magenta", width=10)
        table.add_column("❌ Error Type", style="red", width=20)
        table.add_column("📝 Error Reason", style="white", no_wrap=False)

        for index_name, index_info in errors.items():
            policy = index_info.get('policy', 'N/A')
            phase = index_info.get('phase', 'N/A')

            error_info = index_info.get('step_info', {}).get('error', {})
            error_type = error_info.get('type', 'Unknown')
            error_reason = error_info.get('reason', 'N/A')

            # Truncate long error reasons
            if len(error_reason) > 50:
                error_reason = f"{error_reason[:47]}..."

            table.add_row(index_name, policy, phase, error_type, error_reason)

        print()
        console.print(title_panel)
        print()
        console.print(table)
        print()

    def _get_phase_icon(self, phase):
        """Get icon for ILM phase."""
        phase_icons = {
            'hot': '🔥',
            'warm': '🟡',
            'cold': '🧊',
            'frozen': '❄️',
            'delete': '🗑️'
        }
        return phase_icons.get(phase, '❓')

    def _create_detailed_settings_table(self, settings, transient_settings, persistent_settings):
        """Create a detailed table showing all cluster settings."""
        from rich.table import Table
        from rich.panel import Panel

        # Flatten the settings for display
        all_settings = {}

        # Add transient settings with prefix
        transient_flat = self.flatten_json(transient_settings)
        for key, value in transient_flat.items():
            all_settings[f"transient.{key}"] = value

        # Add persistent settings with prefix
        persistent_flat = self.flatten_json(persistent_settings)
        for key, value in persistent_flat.items():
            all_settings[f"persistent.{key}"] = value

        # If no custom settings, return None
        if not all_settings:
            return None

        # Create enhanced table
        table = Table(show_header=True, header_style="bold white", expand=True)
        table.add_column("⚙️ Setting Path", style="cyan", no_wrap=False, min_width=50)
        table.add_column("📊 Value", style="yellow", no_wrap=False)

        # Sort settings for better organization
        sorted_settings = sorted(all_settings.items())

        for setting_path, value in sorted_settings:
            # Format the value appropriately
            if isinstance(value, bool):
                display_value = "✅ True" if value else "❌ False"
            elif isinstance(value, (int, float)):
                display_value = f"{value:,}" if isinstance(value, int) and value > 1000 else str(value)
            elif isinstance(value, str) and len(value) > 50:
                display_value = f"{value[:47]}..."
            else:
                display_value = str(value)

            table.add_row(setting_path, display_value)

        # Wrap table in a panel
        settings_panel = Panel(
            table,
            title=f"[bold white]📋 Detailed Cluster Settings ({len(all_settings)} total)[/bold white]",
            subtitle="Current custom transient and persistent settings",
            border_style="white",
            padding=(1, 1)
        )

        return settings_panel

    def show_message_box(self, title, message, message_style="bold white", panel_style="white", border_style=None, width=None):
        """
        Display a message in a formatted box using rich.
        
        Args:
            title (str): The title of the message box
            message (str): The message to display
            message_style (str): The style for the message text
            panel_style (str): The style for the panel background (for compatibility)
            border_style (str): The border style/color (overrides panel_style if provided)
            width (int): Panel width (auto-sizing if None)
        """
        # Handle backward compatibility: convert panel_style to border_style if needed
        if border_style is None:
            if panel_style in ["red", "green", "blue", "yellow", "magenta", "cyan", "white"]:
                border_style = panel_style
            elif panel_style == "white on blue":
                border_style = "blue"
            else:
                border_style = panel_style
        
        message_text = Text(f"{message}", style=message_style, justify="center")
        panel_kwargs = {
            "title": title,
            "border_style": border_style,
            "padding": (1, 2)
        }
        
        if width:
            panel_kwargs["width"] = width
        
        panel = Panel(message_text, **panel_kwargs)
        self.console.print("\n")
        self.console.print(panel, markup=True)
        self.console.print("\n")

    def find_matching_index(self, indices_data, indice):
        """
        Check if a given index exists in the provided indices data.
        
        Args:
            indices_data (list or str): List of dictionaries or JSON string containing index data
            indice (str): The index name to search for
            
        Returns:
            bool: True if the index is found, False otherwise
        """
        # Ensure indices_data is a list of dictionaries, not a JSON string
        if isinstance(indices_data, str):
            try:
                indices_data = json.loads(indices_data)  # Convert JSON string to Python object
            except json.JSONDecodeError:
                print("Error: Provided data is not valid JSON.")
                return False

        for data in indices_data:
            if isinstance(data, dict) and data.get("index") == indice:
                return True
        return False  # Return False if no match is found

    def find_matching_node(self, json_data, indice, server):
        """
        Find the first node name in json_data where 'index' equals `indice`
        and 'node' matches the regex `server`.

        Args:
            json_data (list): List of dictionaries.
            indice (str): Index name to match exactly.
            server (str): Regex pattern to match node name.

        Returns:
            str or None: Node name that matches, or None if not found.
        """
        import re
        pattern_server = rf".*{server}.*"
        pattern = re.compile(pattern_server)
        for entry in json_data:
            if entry.get("index") == indice and pattern.search(entry.get("node", "")):
                return entry["node"]
        return None

    def print_json_as_table(self, json_data):
        """
        Prints a JSON object as a pretty table using the rich module.

        Args:
            json_data (dict): Dictionary representing JSON key-value pairs.
        """
        from rich.table import Table
        table = Table(title="JSON Data", show_header=True, header_style="bold magenta")

        table.add_column("Key", style="cyan", justify="left")
        table.add_column("Value", style="green", justify="left")

        for key, value in json_data.items():
            table.add_row(str(key), str(value))

        self.console.print(table)

    def text_progress_bar(self, percent, width=10):
        multiply_percent = int(percent)
        filled_width = int(width * multiply_percent / 100)
        bar = '█' * filled_width + '-' * (width - filled_width)
        return f"[{bar}] {percent:.2f}%"

    def freeze_index(self, index_name):
        """
        Freeze an index to make it read-only.

        Args:
            index_name (str): The name of the index to freeze.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            # First check if the index exists
            if not self.es.indices.exists(index=index_name):
                print(f"Index {index_name} does not exist.")
                return False

            # Freeze the index
            self.es.indices.freeze(index=index_name)
            return True
        except Exception as e:
            print(f"Error freezing index {index_name}: {str(e)}")
            return False

    def unfreeze_index(self, index_name):
        """
        Unfreeze an index to make it writable again.

        Args:
            index_name (str): The name of the index to unfreeze.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            # First check if the index exists
            if not self.es.indices.exists(index=index_name):
                print(f"Index {index_name} does not exist.")
                return False

            # Unfreeze the index
            self.es.indices.unfreeze(index=index_name)
            return True
        except Exception as e:
            print(f"Error unfreezing index {index_name}: {str(e)}")
            return False

    def get_snapshot_stats_fast(self, repository_name):
        """
        Get basic snapshot statistics from a repository (ultra-fast version for dashboard).
        Uses minimal API calls and processing.
        
        Args:
            repository_name (str): The name of the snapshot repository.
            
        Returns:
            dict: Basic snapshot statistics, or None if error.
        """
        try:
            # Skip repository existence check for speed - let the snapshot call handle it
            # Get snapshots with minimal information
            response = self.es.snapshot.get(
                repository=repository_name, 
                snapshot="_all",
                verbose=False,  # Reduce response size
                ignore_unavailable=True
            )

            if 'snapshots' not in response:
                return {'total': 0, 'successful': 0, 'failed': 0, 'in_progress': 0, 'partial': 0}

            # Fast counting - only look at state field
            stats = {'total': 0, 'successful': 0, 'failed': 0, 'in_progress': 0, 'partial': 0}
            
            for snapshot in response['snapshots']:
                stats['total'] += 1
                state = snapshot.get('state', '').upper()
                if state == 'SUCCESS':
                    stats['successful'] += 1
                elif state == 'FAILED':
                    stats['failed'] += 1
                elif state == 'IN_PROGRESS':
                    stats['in_progress'] += 1
                elif state == 'PARTIAL':
                    stats['partial'] += 1

            return stats

        except Exception:
            # Silently return empty stats on any error for dashboard speed
            return {'total': 0, 'successful': 0, 'failed': 0, 'in_progress': 0, 'partial': 0}

    def get_snapshot_stats(self, repository_name):
        """
        Get basic snapshot statistics from a repository (fast version for dashboard).
        
        Args:
            repository_name (str): The name of the snapshot repository.
            
        Returns:
            dict: Basic snapshot statistics, or None if error.
        """
        try:
            # First check if the repository exists
            try:
                self._call_with_version_compatibility(
                    self.es.snapshot.get_repository,
                    primary_kwargs={'repository': repository_name},
                    fallback_kwargs={'name': repository_name}
                )
            except NotFoundError:
                return None
            except Exception:
                return None

            # Get all snapshots from the repository (but don't process them extensively)
            response = self.es.snapshot.get(repository=repository_name, snapshot="_all")

            if 'snapshots' not in response:
                return {'total': 0, 'successful': 0, 'failed': 0, 'in_progress': 0, 'partial': 0}

            # Just count the states - no expensive processing
            stats = {'total': 0, 'successful': 0, 'failed': 0, 'in_progress': 0, 'partial': 0}
            
            for snapshot in response['snapshots']:
                stats['total'] += 1
                state = snapshot.get('state', 'UNKNOWN').upper()
                if state == 'SUCCESS':
                    stats['successful'] += 1
                elif state == 'FAILED':
                    stats['failed'] += 1
                elif state == 'IN_PROGRESS':
                    stats['in_progress'] += 1
                elif state == 'PARTIAL':
                    stats['partial'] += 1

            return stats

        except Exception:
            return None

    def list_snapshots(self, repository_name):
        """
        List all snapshots from a specific repository.

        Args:
            repository_name (str): The name of the snapshot repository.

        Returns:
            list: List of snapshot dictionaries, or empty list if error.
        """
        try:
            # First check if the repository exists
            try:
                # Use version compatibility helper to handle parameter differences
                self._call_with_version_compatibility(
                    self.es.snapshot.get_repository,
                    primary_kwargs={'repository': repository_name},  # Newer API
                    fallback_kwargs={'name': repository_name}        # Older API
                )
            except NotFoundError:
                print(f"Repository '{repository_name}' does not exist.")
                return []
            except Exception as e:
                print(f"Error checking repository '{repository_name}': {str(e)}")
                return []

            # Get all snapshots from the repository
            response = self.es.snapshot.get(repository=repository_name, snapshot="_all")

            if 'snapshots' not in response:
                return []

            snapshots = []
            for snapshot in response['snapshots']:
                snapshot_info = {
                    'repository': repository_name,
                    'snapshot': snapshot['snapshot'],
                    'state': snapshot['state'],
                    'start_time': snapshot.get('start_time', 'N/A'),
                    'end_time': snapshot.get('end_time', 'N/A'),
                    'duration_in_millis': snapshot.get('duration_in_millis', 0),
                    'indices': snapshot.get('indices', []),
                    'include_global_state': snapshot.get('include_global_state', False),
                    'failures': snapshot.get('failures', [])
                }

                # Calculate duration in human readable format
                if snapshot_info['duration_in_millis'] > 0:
                    duration_seconds = snapshot_info['duration_in_millis'] / 1000
                    if duration_seconds >= 3600:
                        snapshot_info['duration'] = f"{duration_seconds/3600:.1f}h"
                    elif duration_seconds >= 60:
                        snapshot_info['duration'] = f"{duration_seconds/60:.1f}m"
                    else:
                        snapshot_info['duration'] = f"{duration_seconds:.1f}s"
                else:
                    snapshot_info['duration'] = 'N/A'

                # Format timestamps
                if snapshot_info['start_time'] != 'N/A':
                    try:
                        start_dt = datetime.fromisoformat(snapshot_info['start_time'].replace('Z', '+00:00'))
                        snapshot_info['start_time_formatted'] = start_dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        snapshot_info['start_time_formatted'] = snapshot_info['start_time']
                else:
                    snapshot_info['start_time_formatted'] = 'N/A'

                if snapshot_info['end_time'] != 'N/A':
                    try:
                        end_dt = datetime.fromisoformat(snapshot_info['end_time'].replace('Z', '+00:00'))
                        snapshot_info['end_time_formatted'] = end_dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        snapshot_info['end_time_formatted'] = snapshot_info['end_time']
                else:
                    snapshot_info['end_time_formatted'] = 'N/A'

                snapshot_info['indices_count'] = len(snapshot_info['indices'])

                snapshots.append(snapshot_info)

            # Sort snapshots by start time (newest first)
            snapshots.sort(key=lambda x: x['start_time'], reverse=True)
            return snapshots

        except Exception as e:
            print(f"Error listing snapshots from repository '{repository_name}': {str(e)}")
            return []

    def get_snapshot_status(self, repository_name, snapshot_name):
        """
        Get detailed status information for a specific snapshot.

        Args:
            repository_name (str): The name of the snapshot repository.
            snapshot_name (str): The name of the snapshot to check status for.

        Returns:
            dict: Snapshot status information, or None if not found/error.
        """
        try:
            # First check if the repository exists
            try:
                self._call_with_version_compatibility(
                    self.es.snapshot.get_repository,
                    primary_kwargs={'repository': repository_name},  # Newer API
                    fallback_kwargs={'name': repository_name}        # Older API
                )
            except NotFoundError:
                print(f"Repository '{repository_name}' does not exist.")
                return None
            except Exception as e:
                print(f"Error checking repository '{repository_name}': {str(e)}")
                return None

            # Get the specific snapshot
            try:
                response = self.es.snapshot.get(repository=repository_name, snapshot=snapshot_name)
            except NotFoundError:
                return None
            except Exception as e:
                print(f"Error getting snapshot '{snapshot_name}': {str(e)}")
                return None

            if 'snapshots' not in response or len(response['snapshots']) == 0:
                return None

            snapshot = response['snapshots'][0]

            # Get current snapshot status (for in-progress snapshots)
            status_response = None
            try:
                status_response = self.es.snapshot.status(repository=repository_name, snapshot=snapshot_name)
            except Exception:
                # Status API might not be available or snapshot might be completed
                pass

            # Build comprehensive status information
            status_info = {
                'repository': repository_name,
                'snapshot': snapshot['snapshot'],
                'state': snapshot['state'],
                'start_time': snapshot.get('start_time', 'N/A'),
                'end_time': snapshot.get('end_time', 'N/A'),
                'duration_in_millis': snapshot.get('duration_in_millis', 0),
                'indices': snapshot.get('indices', []),
                'include_global_state': snapshot.get('include_global_state', False),
                'failures': snapshot.get('failures', []),
                'metadata': snapshot.get('metadata', {}),
                'version': snapshot.get('version', 'N/A'),
                'version_id': snapshot.get('version_id', 'N/A'),
                'successful_shards': snapshot.get('shards', {}).get('successful', 0),
                'failed_shards': snapshot.get('shards', {}).get('failed', 0),
                'total_shards': snapshot.get('shards', {}).get('total', 0)
            }

            # Add current status info if available (for in-progress snapshots)
            if status_response and 'snapshots' in status_response:
                current_status = status_response['snapshots'][0]
                status_info['current_status'] = {
                    'state': current_status.get('state', 'N/A'),
                    'stats': current_status.get('stats', {}),
                    'shards_stats': current_status.get('shards_stats', {}),
                    'indices_stats': current_status.get('indices', {})
                }

            # Calculate and format duration
            if status_info['duration_in_millis'] > 0:
                duration_seconds = status_info['duration_in_millis'] / 1000
                if duration_seconds >= 3600:
                    status_info['duration'] = f"{duration_seconds/3600:.1f}h"
                elif duration_seconds >= 60:
                    status_info['duration'] = f"{duration_seconds/60:.1f}m"
                else:
                    status_info['duration'] = f"{duration_seconds:.1f}s"
            else:
                status_info['duration'] = 'N/A'

            # Format timestamps
            if status_info['start_time'] != 'N/A':
                try:
                    from datetime import datetime
                    start_dt = datetime.fromisoformat(status_info['start_time'].replace('Z', '+00:00'))
                    status_info['start_time_formatted'] = start_dt.strftime('%Y-%m-%d %H:%M:%S UTC')
                except:
                    status_info['start_time_formatted'] = status_info['start_time']
            else:
                status_info['start_time_formatted'] = 'N/A'

            if status_info['end_time'] != 'N/A':
                try:
                    from datetime import datetime
                    end_dt = datetime.fromisoformat(status_info['end_time'].replace('Z', '+00:00'))
                    status_info['end_time_formatted'] = end_dt.strftime('%Y-%m-%d %H:%M:%S UTC')
                except:
                    status_info['end_time_formatted'] = status_info['end_time']
            else:
                status_info['end_time_formatted'] = 'N/A'

            # Calculate additional metrics
            status_info['indices_count'] = len(status_info['indices'])
            status_info['failures_count'] = len(status_info['failures'])

            return status_info

        except Exception as e:
            print(f"Error getting snapshot status for '{snapshot_name}' from repository '{repository_name}': {str(e)}")
            return None

    def display_snapshot_status(self, status_info, repository_name):
        """
        Display detailed snapshot status information in a formatted text box.

        Args:
            status_info (dict): Snapshot status information from get_snapshot_status()
            repository_name (str): Name of the snapshot repository
        """
        from rich.panel import Panel
        from rich.text import Text
        from rich.table import Table
        from rich.columns import Columns

        # Determine state styling and icon
        state = status_info.get('state', 'UNKNOWN')
        if state == 'SUCCESS':
            state_text = Text("✅ SUCCESS", style="bold green")
            panel_style = "green"
        elif state == 'IN_PROGRESS':
            state_text = Text("⏳ IN PROGRESS", style="bold yellow")
            panel_style = "yellow"
        elif state == 'FAILED':
            state_text = Text("❌ FAILED", style="bold red")
            panel_style = "red"
        elif state == 'PARTIAL':
            state_text = Text("⚠️ PARTIAL", style="bold orange3")
            panel_style = "orange3"
        else:
            state_text = Text(f"❓ {state}", style="bold white")
            panel_style = "white"

        # Create main status table
        status_table = Table.grid(padding=(0, 1))
        status_table.add_column(style="bold white", no_wrap=True)
        status_table.add_column(style="bold cyan")

        # Basic information
        status_table.add_row("📦 Repository:", repository_name)
        status_table.add_row("📸 Snapshot:", status_info.get('snapshot', 'N/A'))
        status_table.add_row("🏷️  State:", state_text)

        # Timing information
        status_table.add_row("🕐 Start Time:", status_info.get('start_time_formatted', 'N/A'))
        status_table.add_row("🕑 End Time:", status_info.get('end_time_formatted', 'N/A'))
        status_table.add_row("⏱️  Duration:", status_info.get('duration', 'N/A'))

        # Version information
        if status_info.get('version') != 'N/A':
            status_table.add_row("🔖 ES Version:", status_info.get('version', 'N/A'))

        # Global state
        global_state = "✅ Yes" if status_info.get('include_global_state') else "❌ No"
        status_table.add_row("🌐 Global State:", global_state)

        # Create statistics table
        stats_table = Table.grid(padding=(0, 1))
        stats_table.add_column(style="bold white", no_wrap=True)
        stats_table.add_column(style="bold cyan")

        stats_table.add_row("📊 Total Indices:", str(status_info.get('indices_count', 0)))
        stats_table.add_row("✅ Total Shards:", str(status_info.get('total_shards', 0)))
        stats_table.add_row("🎯 Successful Shards:", str(status_info.get('successful_shards', 0)))

        failed_shards = status_info.get('failed_shards', 0)
        failed_style = "bold red" if failed_shards > 0 else "bold green"
        stats_table.add_row("❌ Failed Shards:", Text(str(failed_shards), style=failed_style))

        failures_count = status_info.get('failures_count', 0)
        failures_style = "bold red" if failures_count > 0 else "bold green"
        stats_table.add_row("⚠️  Failures:", Text(str(failures_count), style=failures_style))

        # Create panels
        main_panel = Panel(
            status_table,
            title="[bold cyan]📸 Snapshot Information[/bold cyan]",
            border_style=panel_style,
            padding=(1, 2)
        )

        stats_panel = Panel(
            stats_table,
            title="[bold cyan]📊 Statistics[/bold cyan]",
            border_style=panel_style,
            padding=(1, 2)
        )

        # Display main panels side by side
        print()
        columns = Columns([main_panel, stats_panel], equal=True, expand=True)
        print(columns)

        # Show current status for in-progress snapshots
        if state == 'IN_PROGRESS' and 'current_status' in status_info:
            current = status_info['current_status']

            progress_table = Table.grid(padding=(0, 1))
            progress_table.add_column(style="bold white", no_wrap=True)
            progress_table.add_column(style="bold yellow")

            # Show current statistics if available
            shards_stats = current.get('shards_stats', {})
            if shards_stats:
                progress_table.add_row("⏳ Current State:", current.get('state', 'N/A'))
                progress_table.add_row("📊 Total Shards:", str(shards_stats.get('total', 0)))
                progress_table.add_row("✅ Started:", str(shards_stats.get('started', 0)))
                progress_table.add_row("🎯 Finalizing:", str(shards_stats.get('finalizing', 0)))
                progress_table.add_row("✅ Done:", str(shards_stats.get('done', 0)))
                progress_table.add_row("❌ Failed:", str(shards_stats.get('failed', 0)))

            progress_panel = Panel(
                progress_table,
                title="[bold yellow]⏳ Current Progress[/bold yellow]",
                border_style="yellow",
                padding=(1, 2)
            )
            print(progress_panel)

        # Show indices list if not too many
        indices = status_info.get('indices', [])
        if indices:
            if len(indices) <= 10:
                indices_text = Text("\n".join(f"• {idx}" for idx in indices))
            else:
                indices_text = Text(f"Total: {len(indices)} indices\n")
                indices_text.append("First 10:\n", style="dim")
                indices_text.append("\n".join(f"• {idx}" for idx in indices[:10]))
                indices_text.append(f"\n... and {len(indices) - 10} more", style="dim")

            indices_panel = Panel(
                indices_text,
                title="[bold cyan]🗂️  Included Indices[/bold cyan]",
                border_style=panel_style,
                padding=(1, 2)
            )
            print(indices_panel)

        # Show failures if any
        failures = status_info.get('failures', [])
        if failures:
            failures_text = Text()
            for i, failure in enumerate(failures):
                if i > 0:
                    failures_text.append("\n")
                failures_text.append(f"• Index: {failure.get('index', 'Unknown')}\n", style="bold white")
                failures_text.append(f"  Shard: {failure.get('shard_id', 'Unknown')}\n", style="white")
                failures_text.append(f"  Reason: {failure.get('reason', 'No details')}\n", style="red")

            failures_panel = Panel(
                failures_text,
                title="[bold red]❌ Failures Details[/bold red]",
                border_style="red",
                padding=(1, 2)
            )
            print(failures_panel)

        print()

    def get_matching_indices(self, pattern):
        """
        Get all indices matching regex pattern with their current ILM status.

        Args:
            pattern (str): Regex pattern to match index names

        Returns:
            list: List of matching index dictionaries with current ILM status
        """
        import re
        from elasticsearch.exceptions import NotFoundError

        try:
            # Get all indices
            indices_response = self.es.cat.indices(format='json', h='index,health,status')

            # Compile regex pattern
            compiled_pattern = re.compile(pattern, re.IGNORECASE)

            matching_indices = []
            for index_info in indices_response:
                index_name = index_info['index']
                if compiled_pattern.search(index_name):
                    # Get current ILM status for this index
                    current_policy = None
                    try:
                        ilm_response = self.es.ilm.explain_lifecycle(index=index_name)
                        if 'indices' in ilm_response and index_name in ilm_response['indices']:
                            current_policy = ilm_response['indices'][index_name].get('policy')
                    except (NotFoundError, Exception):
                        # Index might not have ILM or API might not be available
                        current_policy = None

                    matching_indices.append({
                        'name': index_name,
                        'current_policy': current_policy,
                        'health': index_info.get('health', 'unknown'),
                        'status': index_info.get('status', 'unknown')
                    })

            return matching_indices

        except Exception as e:
            print(f"Error getting matching indices for pattern '{pattern}': {str(e)}")
            return []

    def validate_ilm_policy_exists(self, policy_name):
        """
        Validate that an ILM policy exists.

        Args:
            policy_name (str): Name of the ILM policy to validate

        Returns:
            bool: True if policy exists, False otherwise
        """
        try:
            self.es.ilm.get_lifecycle(policy=policy_name)
            return True
        except Exception:
            return False

    def remove_ilm_policy_from_indices(self, indices, dry_run=False, max_concurrent=5, continue_on_error=False):
        """
        Remove ILM policy from multiple indices with concurrent processing.

        Args:
            indices (list): List of index dictionaries
            dry_run (bool): If True, only simulate the operation
            max_concurrent (int): Maximum number of concurrent operations
            continue_on_error (bool): Whether to continue on individual failures

        Returns:
            dict: Results with successful, failed, and skipped operations
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from rich.progress import Progress, TaskID
        import time

        results = {
            'successful': [],
            'failed': [],
            'skipped': [],
            'total_processed': 0,
            'start_time': time.time()
        }

        def remove_policy_single(index_info):
            index_name = index_info['name']

            if not index_info['current_policy']:
                return {'index': index_name, 'status': 'skipped', 'reason': 'No ILM policy assigned'}

            if dry_run:
                return {'index': index_name, 'status': 'would_remove', 'policy': index_info['current_policy']}

            try:
                # Remove ILM policy
                self.es.ilm.remove_policy(index=index_name)
                return {'index': index_name, 'status': 'success', 'removed_policy': index_info['current_policy']}
            except Exception as e:
                return {'index': index_name, 'status': 'failed', 'error': str(e), 'policy': index_info['current_policy']}

        # Process with progress tracking
        with Progress() as progress:
            operation_name = "Simulating policy removal..." if dry_run else "Removing ILM policies..."
            task = progress.add_task(operation_name, total=len(indices))

            with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
                futures = {executor.submit(remove_policy_single, idx): idx for idx in indices}

                for future in as_completed(futures):
                    result = future.result()
                    results['total_processed'] += 1

                    if result['status'] in ['success', 'would_remove']:
                        results['successful'].append(result)
                    elif result['status'] == 'failed':
                        results['failed'].append(result)
                        if not continue_on_error and not dry_run:
                            # Cancel remaining operations
                            for remaining_future in futures:
                                remaining_future.cancel()
                            break
                    else:
                        results['skipped'].append(result)

                    progress.advance(task)

        results['end_time'] = time.time()
        results['duration'] = results['end_time'] - results['start_time']
        return results

    def set_ilm_policy_for_indices(self, indices, policy_name, dry_run=False, max_concurrent=5, continue_on_error=False):
        """
        Set ILM policy for multiple indices with concurrent processing.

        Args:
            indices (list): List of index dictionaries
            policy_name (str): Name of the ILM policy to set
            dry_run (bool): If True, only simulate the operation
            max_concurrent (int): Maximum number of concurrent operations
            continue_on_error (bool): Whether to continue on individual failures

        Returns:
            dict: Results with successful, failed, and skipped operations
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from rich.progress import Progress, TaskID
        import time

        results = {
            'successful': [],
            'failed': [],
            'skipped': [],
            'total_processed': 0,
            'start_time': time.time()
        }

        def set_policy_single(index_info):
            index_name = index_info['name']
            current_policy = index_info['current_policy']

            if current_policy == policy_name:
                return {'index': index_name, 'status': 'skipped', 'reason': f'Already has policy {policy_name}'}

            if dry_run:
                return {
                    'index': index_name,
                    'status': 'would_set',
                    'new_policy': policy_name,
                    'current_policy': current_policy
                }

            try:
                # Set ILM policy using index settings API
                self.es.indices.put_settings(
                    index=index_name,
                    body={
                        "index.lifecycle.name": policy_name
                    }
                )
                return {
                    'index': index_name,
                    'status': 'success',
                    'new_policy': policy_name,
                    'previous_policy': current_policy
                }
            except Exception as e:
                return {
                    'index': index_name,
                    'status': 'failed',
                    'error': str(e),
                    'target_policy': policy_name,
                    'current_policy': current_policy
                }

        # Process with progress tracking
        with Progress() as progress:
            operation_name = f"Simulating policy assignment ({policy_name})..." if dry_run else f"Setting ILM policy ({policy_name})..."
            task = progress.add_task(operation_name, total=len(indices))

            with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
                futures = {executor.submit(set_policy_single, idx): idx for idx in indices}

                for future in as_completed(futures):
                    result = future.result()
                    results['total_processed'] += 1

                    if result['status'] in ['success', 'would_set']:
                        results['successful'].append(result)
                    elif result['status'] == 'failed':
                        results['failed'].append(result)
                        if not continue_on_error and not dry_run:
                            # Cancel remaining operations
                            for remaining_future in futures:
                                remaining_future.cancel()
                            break
                    else:
                        results['skipped'].append(result)

                    progress.advance(task)

        results['end_time'] = time.time()
        results['duration'] = results['end_time'] - results['start_time']
        return results

    def display_ilm_bulk_operation_results(self, results, operation_type):
        """
        Display results of bulk ILM operations in formatted panels.

        Args:
            results (dict): Results from bulk ILM operation
            operation_type (str): Type of operation performed
        """
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text
        from rich.columns import Columns

        # Determine if this was a dry run
        is_dry_run = any(item.get('status', '').startswith('would_') for item in results['successful'])

        # Create summary statistics
        total = results['total_processed']
        successful = len(results['successful'])
        failed = len(results['failed'])
        skipped = len(results['skipped'])
        duration = results.get('duration', 0)

        # Create summary table
        summary_table = Table.grid(padding=(0, 1))
        summary_table.add_column(style="bold white", no_wrap=True)
        summary_table.add_column(style="bold cyan")

        operation_display = f"🔍 {operation_type} (DRY RUN)" if is_dry_run else f"✅ {operation_type}"
        summary_table.add_row("🚀 Operation:", operation_display)
        summary_table.add_row("📊 Total Processed:", str(total))
        summary_table.add_row("✅ Successful:", str(successful))
        summary_table.add_row("❌ Failed:", str(failed))
        summary_table.add_row("⏭️  Skipped:", str(skipped))
        summary_table.add_row("⏱️  Duration:", f"{duration:.2f}s")

        # Create results details table if there are results to show
        details_table = Table(show_header=True, header_style="bold magenta")
        details_table.add_column("Index", style="cyan", no_wrap=True)
        details_table.add_column("Status", style="green")
        details_table.add_column("Details", style="yellow")

        # Add successful operations (first 10)
        for item in results['successful'][:10]:
            status_icon = "🔍" if item['status'].startswith('would_') else "✅"
            status_text = f"{status_icon} {item['status'].replace('_', ' ').title()}"

            details = ""
            if 'removed_policy' in item:
                details = f"Removed: {item['removed_policy']}"
            elif 'new_policy' in item:
                details = f"Set: {item['new_policy']}"
                if item.get('previous_policy'):
                    details += f" (was: {item['previous_policy']})"
            elif 'policy' in item:
                details = f"Would remove: {item['policy']}"

            details_table.add_row(item['index'], status_text, details)

        # Add failed operations
        for item in results['failed']:
            details_table.add_row(
                item['index'],
                "❌ Failed",
                item.get('error', 'Unknown error')[:50] + "..." if len(item.get('error', '')) > 50 else item.get('error', 'Unknown error')
            )

        # Add some skipped operations
        for item in results['skipped'][:5]:
            details_table.add_row(item['index'], "⏭️  Skipped", item.get('reason', 'Unknown reason'))

        # Show indication if there are more results
        total_shown = min(10, len(results['successful'])) + len(results['failed']) + min(5, len(results['skipped']))
        total_available = len(results['successful']) + len(results['failed']) + len(results['skipped'])

        if total_shown < total_available:
            details_table.add_row("...", f"[dim]({total_available - total_shown} more entries)[/dim]", "...")

        # Create panels
        summary_panel = Panel(
            summary_table,
            title="[bold cyan]📊 Operation Summary[/bold cyan]",
            border_style="green" if failed == 0 else "yellow" if failed < successful else "red",
            padding=(1, 2)
        )

        details_panel = Panel(
            details_table,
            title="[bold cyan]📋 Operation Details[/bold cyan]",
            border_style="cyan",
            padding=(1, 2)
        )

        # Display results
        print()
        print(summary_panel)

        if total_available > 0:
            print(details_panel)

        # Show warnings or errors
        if failed > 0 and not is_dry_run:
            warning_text = Text()
            warning_text.append("⚠️  Some operations failed. ", style="bold yellow")
            warning_text.append("Use --continue-on-error to process all indices even when some fail.", style="dim")

            warning_panel = Panel(
                warning_text,
                title="[bold yellow]⚠️  Warning[/bold yellow]",
                border_style="yellow",
                padding=(1, 2)
            )
            print(warning_panel)

        print()

    def print_stylish_health_dashboard(self, health_data):
        """
        Display cluster health in a stylish dashboard format with panels and visual elements.

        Args:
            health_data: Dictionary containing cluster health data and pre-gathered additional data:
                - Standard cluster health fields (cluster_name, cluster_status, etc.)
                - _recovery_status: Pre-gathered recovery status data
                - _allocation_issues: Pre-gathered allocation issues data
                - _nodes: Pre-gathered node information
                - _master_node: Pre-gathered master node information
                - _snapshots: Pre-gathered snapshot information
        """
        from rich.layout import Layout
        from rich.align import Align
        from rich.progress import BarColumn, Progress, TextColumn
        from rich.columns import Columns
        from rich.text import Text
        import time

        console = Console()

        # Get cluster status and set theme colors
        status = health_data.get('cluster_status', 'unknown')
        if status == 'green':
            status_color = "bright_green"
            status_icon = "🟢"
            theme_color = "green"
        elif status == 'yellow':
            status_color = "bright_yellow"
            status_icon = "🟡"
            theme_color = "yellow"
        elif status == 'red':
            status_color = "bright_red"
            status_icon = "🔴"
            theme_color = "red"
        else:
            status_color = "dim"
            status_icon = "⚪"
            theme_color = "white"

        # Use pre-gathered data (should always be available from _handle_health_dashboard)
        recovery_status = health_data.get('_recovery_status', [])
        allocation_issues = health_data.get('_allocation_issues', [])

        # Create the main title with cluster name and status
        cluster_name = health_data.get('cluster_name', 'Unknown')
        cluster_version = health_data.get('cluster_version', 'Unknown')
        
        title_text = Text()
        title_text.append("🔍 ", style="bold cyan")
        title_text.append("Elasticsearch Cluster Health", style="bold white")

        # Status header with large status indicator and version
        status_header = Text()
        status_header.append(f"{status_icon} ", style=f"bold {status_color}")
        status_header.append(f"Cluster: ", style="bold white")
        status_header.append(f"{cluster_name}", style=f"bold {theme_color}")
        
        # Add version information if available
        if cluster_version != 'Unknown':
            status_header.append(f" (v{cluster_version})", style=f"bold cyan")
            
        status_header.append(f" • Status: ", style="bold white")
        status_header.append(f"{status.upper()}", style=f"bold {status_color}")

        # Create main panels
        cluster_panel = self._create_cluster_overview_panel(health_data, theme_color)
        nodes_panel = self._create_nodes_panel(health_data, theme_color)
        shards_panel = self._create_shards_panel(health_data, theme_color)
        performance_panel = self._create_performance_panel(health_data, theme_color, recovery_status)

        # Create snapshot panel if configured
        snapshot_repo = getattr(self, 'snapshot_repo', None)
        snapshots_data = health_data.get('_snapshots', [])
        snapshots_panel = self._create_snapshots_panel(theme_color, snapshot_repo, snapshots_data)

        # Create allocation issues panel if there are issues
        allocation_panel = self._create_allocation_issues_panel(allocation_issues)

        # Create the panel grid first to measure its actual width
        from rich.table import Table

        # Create main layout table for panels only (2x3 grid)
        grid = Table.grid(padding=0)  # Reduced padding from 1 to 0
        grid.add_column(justify="left", ratio=1)
        grid.add_column(justify="left", ratio=1)

        # Add the panel rows
        grid.add_row(cluster_panel, nodes_panel)
        grid.add_row("", "")  # Minimal spacing
        grid.add_row(shards_panel, performance_panel)
        grid.add_row("", "")  # Minimal spacing

        # Add allocation issues panel next to snapshots if there are issues
        if allocation_panel:
            grid.add_row(snapshots_panel, allocation_panel)
        else:
            grid.add_row(snapshots_panel, "")

        # Calculate actual grid width for better centering
        # Each panel has title borders + content + padding. Let's measure more precisely:
        # Left panel: roughly 52 chars, Right panel: roughly 42 chars = 94 total
        actual_grid_width = 94

        # Create a header table that matches the actual grid width
        header_table = Table.grid()
        header_table.add_column(justify="center", width=actual_grid_width)
        header_table.add_row("")  # top spacing for cleaner look
        header_table.add_row(title_text)
        header_table.add_row(status_header)
        header_table.add_row("")  # minimal spacing

        # Print header then grid
        console.print(header_table)
        console.print(grid)
        console.print()

    def print_multi_cluster_health_comparison(self, config_file, group_name, output_format='table'):
        """
        Display health comparison for all clusters in a group.
        
        Args:
            config_file (str): Path to configuration file
            group_name (str): Name of cluster group to display
            output_format (str): Output format - 'table' or 'json'
        """
        try:
            from rich.console import Console
            from rich.table import Table
            from rich.panel import Panel
            
            console = Console()
            
            # Load configuration to get group members
            from configuration_manager import ConfigurationManager
            import os
            
            # Get the state file path (same as in escmd.py)
            script_directory = os.path.dirname(config_file)
            state_file = os.path.join(script_directory, 'escmd.json')
            
            config_manager = ConfigurationManager(config_file, state_file)
            all_config = config_manager.config
            cluster_groups = all_config.get('cluster_groups', {})
            
            if group_name not in cluster_groups:
                print(f"❌ Group '{group_name}' not found in configuration.")
                return
            
            group_members = cluster_groups[group_name]
            if not group_members:
                print(f"❌ Group '{group_name}' has no members.")
                return
            
            # Collect health data for all clusters
            clusters_health_data = []
            
            if output_format == 'table':
                print(f"\n🔍 Checking health for {len(group_members)} clusters in group '{group_name}'...\n")
            
            for cluster_name in group_members:
                cluster_data = {
                    'cluster_name': cluster_name,
                    'status': 'ERROR',
                    'version': 'N/A',
                    'nodes': 0,
                    'data_nodes': 0,
                    'primary_shards': 0,
                    'active_shards': 0,
                    'unassigned_shards': 0,
                    'shard_health_percent': 0.0,
                    'error': None
                }
                
                try:
                    # Get cluster configuration directly
                    cluster_config = config_manager.get_server_config_by_location(cluster_name)
                    
                    if not cluster_config:
                        cluster_data.update({
                            'status': 'NOT_FOUND',
                            'error': 'Configuration not found'
                        })
                        clusters_health_data.append(cluster_data)
                        continue
                    
                    # Create ES client for this cluster
                    temp_client = ElasticsearchClient(
                        host1=cluster_config['elastic_host'],
                        host2=cluster_config.get('elastic_host2', cluster_config['elastic_host']),
                        port=cluster_config['elastic_port'],
                        use_ssl=cluster_config.get('use_ssl', False),
                        verify_certs=cluster_config.get('verify_certs', False),
                        elastic_username=cluster_config.get('elastic_username'),
                        elastic_password=cluster_config.get('elastic_password'),
                        elastic_authentication=cluster_config.get('elastic_authentication', False)
                    )
                    
                    # Test connection first
                    if not temp_client.ping():
                        cluster_data.update({
                            'status': 'OFFLINE',
                            'error': 'Connection failed'
                        })
                        clusters_health_data.append(cluster_data)
                        continue
                    
                    # Get health data
                    health_data = temp_client.get_cluster_health()
                    
                    # Extract and format the data
                    display_name = health_data.get('cluster_name', cluster_name)
                    status = health_data.get('cluster_status', 'unknown').upper()
                    
                    # Format version
                    version = health_data.get('cluster_version', 'Unknown')
                    if isinstance(version, dict):
                        version = version.get('number', 'Unknown')
                    
                    # Update cluster data with real values
                    cluster_data.update({
                        'cluster_name': display_name,
                        'status': status,
                        'version': version,
                        'nodes': health_data.get('number_of_nodes', 0),
                        'data_nodes': health_data.get('number_of_data_nodes', 0),
                        'primary_shards': health_data.get('active_primary_shards', 0),
                        'active_shards': health_data.get('active_shards', 0),
                        'unassigned_shards': health_data.get('unassigned_shards', 0),
                        'shard_health_percent': health_data.get('active_shards_percent', 100.0),
                        'error': None
                    })
                    
                except Exception as e:
                    cluster_data.update({
                        'status': 'ERROR',
                        'error': str(e)
                    })
                
                clusters_health_data.append(cluster_data)
            
            # Output the data in the requested format
            if output_format == 'json':
                # JSON output
                json_output = {
                    'group_name': group_name,
                    'cluster_count': len(group_members),
                    'clusters': clusters_health_data
                }
                self.pretty_print_json(json_output)
            else:
                # Table output (default)
                # Create table for group health comparison
                table = Table(title=f"🏥 Health Status for Group: {group_name.upper()}")
                table.add_column("Cluster", style="bold cyan", no_wrap=True)
                table.add_column("Status", justify="center")
                table.add_column("Version", style="dim", no_wrap=True)
                table.add_column("Nodes", justify="right")
                table.add_column("Data Nodes", justify="right") 
                table.add_column("Primary", justify="right")
                table.add_column("Total Shards", justify="right")
                table.add_column("Unassigned", justify="right")
                table.add_column("Health %", justify="right")
                
                for cluster_data in clusters_health_data:
                    if cluster_data['status'] in ['NOT_FOUND', 'OFFLINE', 'ERROR']:
                        status_display = {
                            'NOT_FOUND': "❌ NOT FOUND",
                            'OFFLINE': "🔴 OFFLINE", 
                            'ERROR': "❌ ERROR"
                        }.get(cluster_data['status'], "❌ ERROR")
                        
                        table.add_row(
                            cluster_data['cluster_name'],
                            status_display,
                            "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A"
                        )
                    else:
                        status = cluster_data['status']
                        status_icon = "🟢" if status == 'GREEN' else "🟡" if status == 'YELLOW' else "🔴" if status == 'RED' else "⚪"
                        
                        version = cluster_data['version']
                        if version != 'Unknown' and not str(version).startswith('v'):
                            version = f"v{version}"
                        
                        table.add_row(
                            cluster_data['cluster_name'],
                            f"{status_icon} {status}",
                            version,
                            str(cluster_data['nodes']),
                            str(cluster_data['data_nodes']),
                            f"{cluster_data['primary_shards']:,}",
                            f"{cluster_data['active_shards']:,}",
                            str(cluster_data['unassigned_shards']),
                            f"{cluster_data['shard_health_percent']:.1f}%"
                        )
                
                console.print(table)
                print()
            
        except Exception as e:
            print(f"❌ Error displaying group health: {str(e)}")

    def print_cluster_health_comparison(self, config_file, cluster1, cluster2):
        """
        Display side-by-side health comparison between two clusters.
        
        Args:
            config_file (str): Path to configuration file
            cluster1 (str): First cluster name
            cluster2 (str): Second cluster name
        """
        try:
            from rich.console import Console
            from rich.table import Table
            from rich.columns import Columns
            
            console = Console()
            
            print(f"\n🔍 Comparing health between '{cluster1}' and '{cluster2}'...\n")
            
            # Create comparison table
            table = Table(title=f"🏥 Health Comparison: {cluster1} vs {cluster2}")
            table.add_column("Metric", style="bold white", no_wrap=True)
            table.add_column(cluster1, style="bold cyan")
            table.add_column(cluster2, style="bold magenta")
            
            try:
                # Get health for current cluster (cluster1)
                health1 = self.get_cluster_health()
                
                # Get health for comparison cluster (cluster2)
                from configuration_manager import ConfigurationManager
                import os
                
                # Get the state file path (same as in escmd.py)
                script_directory = os.path.dirname(config_file)
                state_file = os.path.join(script_directory, 'escmd.json')
                
                config_manager = ConfigurationManager(config_file, state_file)
                cluster2_config = config_manager.get_server_config_by_location(cluster2)
                
                temp_client = ElasticsearchClient(
                    cluster2_config['elastic_host'],
                    cluster2_config['elastic_port'],
                    use_ssl=cluster2_config.get('use_ssl', False),
                    verify_certs=cluster2_config.get('verify_certs', False),
                    elastic_username=cluster2_config.get('elastic_username'),
                    elastic_password=cluster2_config.get('elastic_password'),
                    elastic_authentication=cluster2_config.get('elastic_authentication', False)
                )
                
                health2 = temp_client.get_cluster_health()
                
                # Add comparison rows
                status1 = health1.get('cluster_status', 'unknown').upper()
                status2 = health2.get('cluster_status', 'unknown').upper()
                icon1 = "🟢" if status1 == 'GREEN' else "🟡" if status1 == 'YELLOW' else "🔴"
                icon2 = "🟢" if status2 == 'GREEN' else "🟡" if status2 == 'YELLOW' else "🔴"
                
                table.add_row("Status", f"{icon1} {status1}", f"{icon2} {status2}")
                table.add_row("Total Nodes", str(health1.get('number_of_nodes', 0)), str(health2.get('number_of_nodes', 0)))
                table.add_row("Data Nodes", str(health1.get('number_of_data_nodes', 0)), str(health2.get('number_of_data_nodes', 0)))
                table.add_row("Active Shards", f"{health1.get('active_shards', 0):,}", f"{health2.get('active_shards', 0):,}")
                table.add_row("Primary Shards", f"{health1.get('active_primary_shards', 0):,}", f"{health2.get('active_primary_shards', 0):,}")
                table.add_row("Unassigned", str(health1.get('unassigned_shards', 0)), str(health2.get('unassigned_shards', 0)))
                table.add_row("Pending Tasks", str(health1.get('number_of_pending_tasks', 0)), str(health2.get('number_of_pending_tasks', 0)))
                
                console.print(table)
                print()
                
            except Exception as e:
                print(f"❌ Error getting health data for comparison: {str(e)}")
                
        except Exception as e:
            print(f"❌ Error displaying cluster comparison: {str(e)}")

    def _create_cluster_overview_panel(self, health_data, theme_color):
        """Create cluster overview panel with key metrics."""
        from rich.table import Table

        # Create inner table for clean label-value pairs
        table = Table.grid(padding=(0, 1))
        table.add_column(style="bold white", no_wrap=True)
        table.add_column(style=f"bold {theme_color}")

        # Add cluster info rows
        table.add_row("🏢 Cluster Name:", health_data.get('cluster_name', 'Unknown'))
        
        # Add version information if available
        cluster_version = health_data.get('cluster_version', 'Unknown')
        build_hash = health_data.get('build_hash')
        if cluster_version != 'Unknown':
            version_text = f"v{cluster_version}"
            if build_hash:
                version_text += f" (build: {build_hash})"
            table.add_row("🔧 ES Version:", version_text)
            
            # Add mixed version warning if applicable
            if health_data.get('mixed_versions', False):
                table.add_row("⚠️  Version:", "Mixed versions detected!")

        # Get current master node - use pre-gathered data
        master_node = health_data.get('_master_node', 'Unknown')
        if master_node != 'Unknown':
            # Remove "-master" suffix from the display name
            display_name = master_node[:-7] if master_node.endswith('-master') else master_node
            table.add_row("👑 Master Node:", display_name)
        else:
            table.add_row("👑 Master Node:", "Unknown")

        table.add_row("🖥️  Total Nodes:", str(health_data.get('number_of_nodes', 0)))
        table.add_row("💾 Data Nodes:", str(health_data.get('number_of_data_nodes', 0)))

        # Create progress bar for shard health
        active_percent = float(health_data.get('active_shards_percent', 0))
        width = 12
        filled = int((active_percent / 100) * width)
        empty = width - filled

        if active_percent >= 95:
            bar_char = "🟢"
        elif active_percent >= 80:
            bar_char = "🟡"
        else:
            bar_char = "🔴"

        progress_bar = bar_char * filled + "⚪" * empty
        shard_health = f"{progress_bar} {active_percent:.1f}%"

        table.add_row("📊 Shard Health:", shard_health)

        return Panel(
            table,
            title="[bold cyan]📋 Cluster Overview[/bold cyan]",
            border_style=theme_color,
            padding=(1, 2)
        )

    def _create_nodes_panel(self, health_data, theme_color):
        """Create nodes information panel."""
        from rich.table import Table
        from rich.text import Text

        # Create inner table for clean label-value pairs
        table = Table.grid(padding=(0, 1))
        table.add_column(style="bold white", no_wrap=True)
        table.add_column()

        # Calculate node info
        total_nodes = health_data.get('number_of_nodes', 0)
        data_nodes = health_data.get('number_of_data_nodes', 0)

        # Get detailed node counts - use pre-gathered data if available
        nodes = health_data.get('_nodes')
        if nodes is not None:
            try:
                # Count different node types based on roles
                master_only_nodes = len([node for node in nodes if 'master' in node['roles'] and not any(role.startswith('data') for role in node['roles'])])
                # Client nodes are coordinating nodes (no data roles, no master role)
                client_nodes = len([node for node in nodes if 'master' not in node['roles'] and not any(role.startswith('data') for role in node['roles'])])
                # Other nodes are master-only nodes (since client nodes are shown separately)
                other_nodes = master_only_nodes
            except Exception:
                # Fallback if we can't process detailed node info
                client_nodes = 0
                other_nodes = total_nodes - data_nodes
        else:
            # Use simple calculation if detailed node data is not available
            client_nodes = 0
            other_nodes = total_nodes - data_nodes

        # Add node info rows
        table.add_row("🖥️  Total Nodes:", Text(str(total_nodes), style="bold white"))
        table.add_row("📚 Data Nodes:", Text(str(data_nodes), style="bold green"))
        if other_nodes > 0:
            table.add_row("⚙️  Master Nodes:", Text(str(other_nodes), style="bold yellow"))
        if client_nodes > 0:
            table.add_row("🔗 Client Nodes:", Text(str(client_nodes), style="bold cyan"))

        # Create data node ratio with progress bar
        if total_nodes > 0:
            data_ratio = (data_nodes / total_nodes) * 100
            width = 15
            filled = int((data_ratio / 100) * width)
            empty = width - filled

            # Create ratio text with progress bar
            ratio_text = Text()
            ratio_text.append("█" * filled, style="green")
            ratio_text.append("░" * empty, style="dim")
            ratio_text.append(f" {data_ratio:.0f}%", style="bold green")

            table.add_row("📈 Data Ratio:", ratio_text)

        return Panel(
            table,
            title="[bold green]🖥️  Node Information[/bold green]",
            border_style=theme_color,
            padding=(1, 2)
        )

    def _create_shards_panel(self, health_data, theme_color):
        """Create shards information panel."""
        from rich.table import Table
        from rich.text import Text

        # Create inner table for clean label-value pairs
        table = Table.grid(padding=(0, 1))
        table.add_column(style="bold white", no_wrap=True)
        table.add_column()

        # Shard metrics
        active_primary = health_data.get('active_primary_shards', 0)
        active_total = health_data.get('active_shards', 0)
        unassigned = health_data.get('unassigned_shards', 0)
        replicas = active_total - active_primary

        # Add shard info rows
        table.add_row("🟢 Primary:", Text(f"{active_primary:,}", style="bold green"))
        table.add_row("🔵 Total Active:", Text(f"{active_total:,}", style="bold blue"))
        table.add_row("🔄 Replicas:", Text(f"{replicas:,}", style="bold cyan"))

        # Calculate shards per data node (only data nodes hold shards)
        data_nodes = health_data.get('number_of_data_nodes', 1)  # Avoid division by zero
        if data_nodes > 0:
            shards_per_node = active_total / data_nodes
            table.add_row("⚖️  Shards/Node:", Text(f"{shards_per_node:.1f}", style="bold magenta"))

        # Unassigned shards status
        if unassigned > 0:
            table.add_row("🔴 Unassigned:", Text(f"{unassigned:,}", style="bold red"))
        else:
            table.add_row("✅ Status:", Text("All assigned!", style="bold green"))

        return Panel(
            table,
            title="[bold blue]🔄 Shard Status[/bold blue]",
            border_style=theme_color,
            padding=(1, 2)
        )

    def _create_performance_panel(self, health_data, theme_color, recovery_status=None):
        """Create performance metrics panel."""
        from rich.table import Table
        from rich.text import Text

        # Create inner table with 3 columns: Label, Value, Status
        table = Table.grid(padding=(0, 1))
        table.add_column(style="bold white", no_wrap=True)  # Label
        table.add_column(style="bold cyan", justify="right", width=16)  # Value
        table.add_column(style="", no_wrap=True)  # Status icon

        pending_tasks = health_data.get('number_of_pending_tasks', 0)
        in_flight = health_data.get('number_of_in_flight_fetch', 0)
        delayed_unassigned = health_data.get('delayed_unassigned_shards', 0)

        # Pending tasks
        if pending_tasks == 0:
            pending_status = Text("✅", style="bold green")
        else:
            pending_status = Text("⚠️", style="bold yellow")
        table.add_row("⏳ Pending Tasks:", str(pending_tasks), pending_status)

        # In-flight fetches
        if in_flight == 0:
            inflight_status = Text("✅", style="bold green")
        elif in_flight < 5:
            inflight_status = Text("📊", style="bold blue")
        else:
            inflight_status = Text("⚠️", style="bold yellow")
        table.add_row("🔄 In-Flight:", str(in_flight), inflight_status)

        # Recovery jobs
        if recovery_status:
            recovery_count = len(recovery_status)
            total_shards = sum(len(shards) for shards in recovery_status.values())
            recovery_value = f"{recovery_count}i, {total_shards}s"
            recovery_status_icon = Text("⚡", style="bold orange")
        else:
            recovery_value = "0"
            recovery_status_icon = Text("✅", style="bold green")
        table.add_row("🔧 Recovery Jobs:", recovery_value, recovery_status_icon)

        # Delayed unassigned shards
        if delayed_unassigned == 0:
            delayed_status = Text("✅", style="bold green")
        else:
            delayed_status = Text("⚠️", style="bold yellow")
        table.add_row("⏰ Delayed:", str(delayed_unassigned), delayed_status)

        # Overall performance indicator
        has_recovery = recovery_status and len(recovery_status) > 0
        if pending_tasks == 0 and delayed_unassigned == 0 and not has_recovery:
            status_text = "OPTIMAL"
            status_icon = Text("✨", style="bold green")
        elif pending_tasks < 10 and delayed_unassigned < 5 and (not has_recovery or len(recovery_status) < 3):
            status_text = "GOOD"
            status_icon = Text("👍", style="bold yellow")
        else:
            status_text = "NEEDS ATTENTION"
            status_icon = Text("⚠️", style="bold red")

        # Add overall status
        table.add_row("🎯 Overall:", status_text, status_icon)

        return Panel(
            table,
            title="[bold yellow]⚡ Performance[/bold yellow]",
            border_style=theme_color,
            padding=(1, 2),
            width=50
        )

    def _create_visual_progress_bar(self, percent, color, width=15):
        """Create a visual progress bar with emojis and colors."""
        filled = int((percent / 100) * width)
        empty = width - filled

        if percent >= 95:
            bar_char = "🟢"
        elif percent >= 80:
            bar_char = "🟡"
        else:
            bar_char = "🔴"

        bar = bar_char * filled + "⚪" * empty
        return f"[{bar}]"

    def _create_simple_bar(self, percent, width, color):
        """Create a simple colored progress bar."""
        filled = int((percent / 100) * width)
        empty = width - filled
        bar = "█" * filled + "░" * empty
        return f"[{color}]{bar}[/{color}]"

    def print_side_by_side_health(self, cluster1_name, cluster1_data, cluster1_status, cluster2_name, cluster2_data, cluster2_status):
        """Print health comparison for two clusters side by side."""
        from rich.table import Table
        from rich.columns import Columns
        from rich.panel import Panel
        from rich.text import Text

        console = Console()

        # Create individual health tables for each cluster
        cluster1_table = self._create_health_table(cluster1_name, cluster1_data, cluster1_status)
        cluster2_table = self._create_health_table(cluster2_name, cluster2_data, cluster2_status)

        # Display side by side with minimal spacing
        print()
        console.print(Columns([cluster1_table, cluster2_table], equal=True, expand=False, padding=(0, 0)))
        print()

    def print_group_health(self, group_name, cluster_health_data):
        """Print health status for all clusters in a group."""
        from rich.columns import Columns
        from rich.console import Console

        console = Console()

        # Create health tables for all clusters
        health_tables = []
        for cluster_info in cluster_health_data:
            health_table = self._create_health_table(
                cluster_info['name'],
                cluster_info['data'],
                cluster_info['status']
            )
            health_tables.append(health_table)

        # Display clusters in a grid layout (2 columns)
        if len(health_tables) == 1:
            # Single cluster - display normally
            console.print(health_tables[0])
        elif len(health_tables) == 2:
            # Two clusters - side by side
            console.print(Columns(health_tables, equal=True, expand=False, padding=(0, 0)))
        else:
            # Multiple clusters - display in pairs
            for i in range(0, len(health_tables), 2):
                if i + 1 < len(health_tables):
                    # Pair of clusters
                    console.print(Columns([health_tables[i], health_tables[i + 1]], equal=True, expand=False, padding=(0, 0)))
                else:
                    # Single remaining cluster
                    console.print(health_tables[i])
                print()  # Add spacing between rows

    def _create_health_table(self, cluster_name, health_data, status):
        """Create a health table for a single cluster."""
        from rich.table import Table
        from rich.panel import Panel
        from rich.text import Text

        # Determine cluster status color
        if "error" in health_data:
            title_color = "red"
            border_color = "red"
        else:
            # Health data uses 'cluster_status' not 'status'
            cluster_status = health_data.get('cluster_status', health_data.get('status', 'unknown')).upper()
            if cluster_status == 'GREEN':
                title_color = "green"
                border_color = "green"
            elif cluster_status == 'YELLOW':
                title_color = "yellow"
                border_color = "yellow"
            else:
                title_color = "red"
                border_color = "red"

        # Create table with health metrics
        table = Table.grid(padding=(0, 1))
        table.add_column(style="bold white", no_wrap=True)
        table.add_column(style=f"bold {title_color}")

        if "error" in health_data:
            table.add_row("❌ Status:", "ERROR")
            table.add_row("🔗 Connection:", "Failed")
            table.add_row("📄 Error:", str(health_data["error"])[:30] + "...")
        else:
            # Add health metrics
            cluster_status = health_data.get('cluster_status', health_data.get('status', 'unknown')).upper()
            table.add_row("📊 Status:", cluster_status)

            # Add master node information if available
            master_node = health_data.get('_master_node', 'Unknown')
            if master_node != 'Unknown':
                # Remove "-master" suffix from the display name
                display_name = master_node[:-7] if master_node.endswith('-master') else master_node
                table.add_row("👑 Master Node:", display_name)
            else:
                table.add_row("👑 Master Node:", "Unknown")

            table.add_row("🖥️  Nodes:", str(health_data.get('number_of_nodes', 0)))
            table.add_row("💾 Data Nodes:", str(health_data.get('number_of_data_nodes', 0)))
            table.add_row("🟢 Active Shards:", f"{health_data.get('active_shards', 0):,}")
            table.add_row("🔴 Unassigned:", str(health_data.get('unassigned_shards', 0)))
            table.add_row("⏳ Pending Tasks:", str(health_data.get('number_of_pending_tasks', 0)))
            table.add_row("🔄 In Flight:", str(health_data.get('number_of_in_flight_fetch', 0)))
            table.add_row("⏰ Delayed:", str(health_data.get('delayed_unassigned_shards', 0)))

            # Calculate shards per node
            data_nodes = health_data.get('number_of_data_nodes', 1)
            if data_nodes > 0:
                shards_per_node = health_data.get('active_shards', 0) / data_nodes
                table.add_row("⚖️  Shards/Node:", f"{shards_per_node:.1f}")

            # Add active shards percent with progress bar at the bottom
            active_percent = health_data.get('active_shards_percent', 0)
            progress_bar = self.text_progress_bar(active_percent, 10)
            table.add_row("📈 Shard Health:", progress_bar)

        return Panel(
            table,
            title=f"[bold {title_color}]{status} {cluster_name}[/bold {title_color}]",
            border_style=border_color,
            padding=(1, 2),
            width=60  # Set a reasonable fixed width instead of full terminal width
        )

    def _create_snapshots_panel(self, theme_color, snapshot_repo=None, snapshots=None):
        """Create snapshots information panel."""
        from rich.table import Table
        from rich.text import Text

        # Create inner table with 3 columns: Label, Value, Status
        table = Table.grid(padding=(0, 1))
        table.add_column(style="bold white", no_wrap=True)  # Label
        table.add_column(style="bold cyan", justify="left", width=15)  # Value - wider for repo names
        table.add_column(style="", no_wrap=True)  # Status icon

        if not snapshot_repo:
            # No snapshot repository configured
            table.add_row("📦 Repository:", "None", Text("⚠️", style="bold yellow"))
            table.add_row("📸 Total:", "N/A", Text("", style=""))
            table.add_row("✅ Successful:", "N/A", Text("", style=""))
            table.add_row("❌ Failed:", "N/A", Text("", style=""))
            table.add_row("🎯 Status:", "NOT CONFIGURED", Text("⚠️", style="bold yellow"))
        else:
            # Check if we have stats dict (fast method) or list of snapshots (old method)
            if isinstance(snapshots, dict) and 'total' in snapshots:
                # New fast stats format
                stats = snapshots
                total_snapshots = stats.get('total', 0)
                successful = stats.get('successful', 0)
                failed = stats.get('failed', 0)
                in_progress = stats.get('in_progress', 0)
                partial = stats.get('partial', 0)
            else:
                # Old format - list of snapshots or empty list
                if snapshots is None:
                    snapshots = []

                total_snapshots = len(snapshots)
                
                # Count successful and failed snapshots
                successful = sum(1 for s in snapshots if s.get('state') == 'SUCCESS')
                failed = sum(1 for s in snapshots if s.get('state') == 'FAILED')
                in_progress = sum(1 for s in snapshots if s.get('state') == 'IN_PROGRESS')
                partial = sum(1 for s in snapshots if s.get('state') == 'PARTIAL')

            # Repository status
            table.add_row("📦 Repository:", snapshot_repo, Text("✅", style="bold green"))

            # Total snapshots
            if total_snapshots == 0:
                total_status = Text("⚠️", style="bold yellow")
            else:
                total_status = Text("📊", style="bold blue")
            table.add_row("📸 Total:", str(total_snapshots), total_status)

            # Successful snapshots
            if successful > 0:
                success_status = Text("✅", style="bold green")
            else:
                success_status = Text("", style="")
            table.add_row("✅ Successful:", str(successful), success_status)

            # Failed snapshots
            if failed > 0:
                failed_status = Text("❌", style="bold red")
            else:
                failed_status = Text("✅", style="bold green")
            table.add_row("❌ Failed:", str(failed), failed_status)

            # In progress snapshots
            if in_progress > 0:
                table.add_row("⏳ In Progress:", str(in_progress), Text("⚡", style="bold orange"))
                
            # Partial snapshots
            if partial > 0:
                table.add_row("⚠️ Partial:", str(partial), Text("⚠️", style="bold yellow"))

            # Overall status
            if failed > 0:
                status_text = "FAILURES DETECTED"
                status_icon = Text("❌", style="bold red")
            elif in_progress > 0:
                status_text = "ACTIVE"
                status_icon = Text("⚡", style="bold orange")
            elif successful > 0:
                status_text = "HEALTHY"
                status_icon = Text("✅", style="bold green")
            else:
                status_text = "NO SNAPSHOTS"
                status_icon = Text("⚠️", style="bold yellow")

            table.add_row("🎯 Status:", status_text, status_icon)

        return Panel(
            table,
            title="[bold magenta]📦 Snapshots[/bold magenta]",
            border_style=theme_color,
            padding=(1, 2)
        )

    def print_enhanced_current_master(self, master_node_id):
        """Print enhanced current master information with Rich formatting"""
        from rich.panel import Panel
        from rich.text import Text
        from rich.columns import Columns
        from rich.table import Table as InnerTable

        console = Console()

        try:
            # Get detailed node information
            nodes = self.get_nodes()
            master_node = None

            # Find the master node details
            for node in nodes:
                if node.get('name') == master_node_id:
                    master_node = node
                    break

            if not master_node:
                # Fallback if we can't find detailed info
                simple_panel = Panel(
                    Text(f"👑  {master_node_id}", style="bold yellow", justify="center"),
                    title="👑 Current Cluster Master",
                    border_style="yellow",
                    padding=(1, 2)
                )
                print()
                console.print(simple_panel)
                return

            # Create title panel
            title_panel = Panel(
                Text(f"👑 Current Cluster Master", style="bold yellow", justify="center"),
                subtitle=f"Active master node: {master_node_id}",
                border_style="yellow",
                padding=(1, 2)
            )

            # Master node details panel
            master_table = InnerTable(show_header=False, box=None, padding=(0, 1))
            master_table.add_column("Label", style="bold", no_wrap=True)
            master_table.add_column("Icon", justify="left", width=3)
            master_table.add_column("Value", no_wrap=True)

            # Basic information
            name = master_node.get('name', 'Unknown')
            hostname = master_node.get('hostname', 'Unknown')
            node_id = master_node.get('node', 'Unknown')
            roles = master_node.get('roles', [])

            master_table.add_row("Node Name:", "📛", name)
            master_table.add_row("Hostname:", "🌐", hostname)
            if node_id != 'Unknown':
                master_table.add_row("Node ID:", "🆔", node_id[:16] + "..." if len(node_id) > 16 else node_id)

            # Role information
            master_table.add_row("Master Role:", "👑", "✅ Active Master")

            # Check if it has other roles
            other_roles = []
            if any(role.startswith('data') for role in roles):
                other_roles.append("💾 Data")
            if 'ingest' in roles:
                other_roles.append("🔄 Ingest")

            if other_roles:
                master_table.add_row("Additional Roles:", "⚙️", " + ".join(other_roles))
            else:
                master_table.add_row("Node Type:", "🔧", "Dedicated Master")

            master_details_panel = Panel(
                master_table,
                title="📋 Master Node Details",
                border_style="yellow",
                padding=(1, 2)
            )

            # Cluster status panel
            try:
                health_data = self.get_cluster_health()
                status = health_data.get('cluster_status', 'unknown').upper()

                if status == 'GREEN':
                    status_icon = "🟢"
                    status_color = "green"
                elif status == 'YELLOW':
                    status_icon = "🟡"
                    status_color = "yellow"
                elif status == 'RED':
                    status_icon = "🔴"
                    status_color = "red"
                else:
                    status_icon = "⚪"
                    status_color = "white"

                cluster_name = health_data.get('cluster_name', 'Unknown')
                total_nodes = health_data.get('number_of_nodes', 0)
                data_nodes = health_data.get('number_of_data_nodes', 0)

                status_table = InnerTable(show_header=False, box=None, padding=(0, 1))
                status_table.add_column("Label", style="bold", no_wrap=True)
                status_table.add_column("Icon", justify="left", width=3)
                status_table.add_column("Value", no_wrap=True)

                status_table.add_row("Cluster Name:", "🏢", cluster_name)
                status_table.add_row("Cluster Status:", status_icon, status)
                status_table.add_row("Total Nodes:", "🖥️", str(total_nodes))
                status_table.add_row("Data Nodes:", "💾", str(data_nodes))

                cluster_status_panel = Panel(
                    status_table,
                    title="📊 Cluster Status",
                    border_style=status_color,
                    padding=(1, 2)
                )

                # Display everything
                print()
                console.print(title_panel)
                print()
                console.print(Columns([master_details_panel, cluster_status_panel], expand=True))

            except Exception:
                # If we can't get cluster status, just show master details
                print()
                console.print(title_panel)
                print()
                console.print(master_details_panel)

        except Exception as e:
            console.print(f"[red]❌ Error retrieving master node details: {str(e)}[/red]")

    def print_enhanced_masters_info(self, master_nodes):
        """Print enhanced master nodes information with Rich formatting"""
        from rich.panel import Panel
        from rich.text import Text
        from rich.columns import Columns
        from rich.table import Table as InnerTable

        console = Console()

        if not master_nodes:
            no_masters_panel = Panel(
                Text("⚠️ No master-eligible nodes found", style="bold red", justify="center"),
                title="👑 Master Nodes",
                border_style="red",
                padding=(2, 4)
            )
            print()
            console.print(no_masters_panel)
            return

        # Get current master for identification
        try:
            current_master = self.get_master_node()
        except:
            current_master = None

        # Calculate master statistics
        total_masters = len(master_nodes)
        active_master_count = 1 if current_master else 0
        standby_masters = total_masters - active_master_count

        # Analyze master node types
        dedicated_masters = 0
        mixed_role_masters = 0

        for node in master_nodes:
            roles = node.get('roles', [])
            if len(roles) == 1 and 'master' in roles:
                dedicated_masters += 1
            else:
                mixed_role_masters += 1

        # Create title panel
        title_panel = Panel(
            Text("👑 Master-Eligible Nodes", style="bold yellow", justify="center"),
            subtitle=f"Total: {total_masters} nodes ({active_master_count} active, {standby_masters} standby)",
            border_style="yellow",
            padding=(1, 2)
        )

        # Master summary panel
        summary_table = InnerTable(show_header=False, box=None, padding=(0, 1))
        summary_table.add_column("Label", style="bold", no_wrap=True)
        summary_table.add_column("Icon", justify="left", width=3)
        summary_table.add_column("Value", no_wrap=True)

        summary_table.add_row("Total Masters:", "👑", str(total_masters))
        summary_table.add_row("Active Master:", "🌟", current_master if current_master else "Unknown")
        summary_table.add_row("Standby Masters:", "⭐", str(standby_masters))
        summary_table.add_row("Dedicated Masters:", "🔧", str(dedicated_masters))
        summary_table.add_row("Mixed Role Masters:", "⚙️", str(mixed_role_masters))

        # Add cluster health status
        try:
            health_data = self.get_cluster_health()
            status = health_data.get('cluster_status', 'unknown').upper()

            if status == 'GREEN':
                status_icon = "🟢"
            elif status == 'YELLOW':
                status_icon = "🟡"
            elif status == 'RED':
                status_icon = "🔴"
            else:
                status_icon = "⚪"

            summary_table.add_row("Cluster Status:", status_icon, status)
        except:
            pass

        summary_panel = Panel(
            summary_table,
            title="📊 Master Overview",
            border_style="yellow",
            padding=(1, 2)
        )

        # Master quorum panel
        quorum_table = InnerTable(show_header=False, box=None, padding=(0, 1))
        quorum_table.add_column("Metric", style="bold", no_wrap=True)
        quorum_table.add_column("Icon", justify="left", width=3)
        quorum_table.add_column("Value", no_wrap=True)

        # Calculate quorum information
        quorum_size = (total_masters // 2) + 1
        quorum_table.add_row("Quorum Required:", "🗳️", str(quorum_size))
        quorum_table.add_row("Available Masters:", "✅", str(total_masters))

        if total_masters >= quorum_size:
            quorum_status = "Healthy"
            quorum_color = "green"
        else:
            quorum_status = "At Risk"
            quorum_color = "red"

        quorum_table.add_row("Quorum Status:", "🛡️", quorum_status)

        quorum_panel = Panel(
            quorum_table,
            title="🗳️ Master Quorum",
            border_style=quorum_color,
            padding=(1, 2)
        )

        # Check if any node has a known node ID
        has_known_node_ids = any(node.get('node', 'Unknown') != 'Unknown' for node in master_nodes)

        # Detailed masters table
        masters_table = Table(show_header=True, header_style="bold white", expand=True)
        masters_table.add_column("📛 Node Name", no_wrap=True)
        masters_table.add_column("🌐 Hostname", no_wrap=True)
        if has_known_node_ids:
            masters_table.add_column("🆔 Node ID", no_wrap=True, max_width=20)
        masters_table.add_column("👑 Status", justify="center", width=15)
        masters_table.add_column("⚙️ Roles", no_wrap=True)

        for node in master_nodes:
            name = node.get('name', 'Unknown')
            hostname = node.get('hostname', 'Unknown')
            node_id = node.get('node', 'Unknown')
            roles = node.get('roles', [])

            # Determine master status and styling
            if current_master and name == current_master:
                status = "🌟 Active"
                row_style = "yellow"
            else:
                status = "⭐ Standby"
                row_style = "cyan"

            # Format node ID (truncate if too long) - only if we're showing the column
            if has_known_node_ids:
                if node_id != 'Unknown' and len(node_id) > 16:
                    node_id_display = node_id[:16] + "..."
                else:
                    node_id_display = node_id

            # Format roles with icons
            role_icons = {
                'master': '👑',
                'data': '💾',
                'data_content': '💾',
                'data_hot': '🔥',
                'data_warm': '🌡️',
                'data_cold': '🧊',
                'data_frozen': '❄️',
                'ingest': '🔄',
                'ml': '🤖',
                'remote_cluster_client': '🌐',
                'transform': '🔄'
            }

            role_display = []
            for role in roles:
                icon = role_icons.get(role, '⚙️')
                role_display.append(f"{icon} {role}")

            roles_text = " | ".join(role_display) if role_display else "Unknown"

            # Add row with or without node ID column
            if has_known_node_ids:
                masters_table.add_row(
                    name,
                    hostname,
                    node_id_display,
                    status,
                    roles_text,
                    style=row_style
                )
            else:
                masters_table.add_row(
                    name,
                    hostname,
                    status,
                    roles_text,
                    style=row_style
                )

        # Display everything
        print()
        console.print(title_panel)
        print()
        console.print(Columns([summary_panel, quorum_panel], expand=True))
        print()
        console.print(Panel(
            masters_table,
            title="👑 Master Node Details",
            border_style="yellow",
            padding=(1, 2)
        ))

    def print_detailed_indice_info(self, indice_name):
        """Print detailed information about a specific index with Rich formatting"""
        from rich.panel import Panel
        from rich.text import Text
        from rich.columns import Columns
        from rich.table import Table
        from rich.layout import Layout
        from rich.console import Console

        console = Console()

        try:
            # Get comprehensive index data
            indices_data = self.filter_indices(pattern=None, status=None)
            shards_data = self.get_shards_as_dict()
            cluster_all_settings = self.get_all_index_settings()

            # Find the specific index
            index_info = None
            for index in indices_data:
                if index['index'] == indice_name:
                    index_info = index
                    break

            if not index_info:
                self.show_message_box("❌ Index Not Found", f"Index '{indice_name}' not found", message_style="bold white", panel_style="red")
                return

            # Get index settings
            index_settings = cluster_all_settings.get(indice_name, {})
            settings = index_settings.get('settings', {}).get('index', {})

            # Filter shards for this index
            index_shards = [shard for shard in shards_data if shard['index'] == indice_name]

            # Determine index type and styling
            is_hot = indice_name in self.cluster_indices_hot_indexes
            is_frozen = settings.get('frozen', 'false') == 'true'

            # Set theme colors
            if is_hot:
                theme_color = "bright_red"
                type_indicator = "🔥 Hot Index"
            elif is_frozen:
                theme_color = "bright_blue"
                type_indicator = "❄️ Frozen Index"
            else:
                theme_color = "bright_cyan"
                type_indicator = "📋 Standard Index"

            # Create title panel
            title_text = Text(f"📊 Index Details: {indice_name}", style=f"bold {theme_color}", justify="center")
            title_panel = Panel(
                title_text,
                subtitle=type_indicator,
                border_style=theme_color,
                padding=(1, 2)
            )

            # Index Overview Panel - Create table for aligned columns
            from rich.table import Table as InnerTable

            health_icon = "🟢" if index_info['health'] == 'green' else "🟡" if index_info['health'] == 'yellow' else "🔴"
            status_icon = "📂" if index_info['status'] == 'open' else "🔒"
            docs_count = f"{int(index_info['docs.count']):,}" if index_info['docs.count'] != '-' else 'N/A'

            overview_table = InnerTable(show_header=False, box=None, padding=(0, 1))
            overview_table.add_column("Label", style="bold", no_wrap=True)
            overview_table.add_column("Icon", justify="left", width=3)
            overview_table.add_column("Value", no_wrap=True)

            overview_table.add_row("Health:", health_icon, index_info['health'].title())
            overview_table.add_row("Status:", status_icon, index_info['status'].title())
            overview_table.add_row("Documents:", "📊", docs_count)
            overview_table.add_row("Primary Shards:", "⚖️", index_info['pri'])
            overview_table.add_row("Replica Shards:", "📋", index_info['rep'])
            overview_table.add_row("Primary Size:", "💾", index_info['pri.store.size'])
            overview_table.add_row("Total Size:", "📦", index_info['store.size'])

            overview_panel = Panel(
                overview_table,
                title="📋 Overview",
                border_style=theme_color,
                padding=(1, 2)
            )

            # Index Settings Panel
            creation_date = settings.get('creation_date', 'Unknown')
            if creation_date != 'Unknown':
                try:
                    import datetime
                    creation_date = datetime.datetime.fromtimestamp(int(creation_date) / 1000).strftime('%Y-%m-%d %H:%M:%S')
                except:
                    pass

            uuid = settings.get('uuid', 'Unknown')
            version = settings.get('version', {}).get('created', 'Unknown')
            number_of_shards = settings.get('number_of_shards', 'Unknown')
            number_of_replicas = settings.get('number_of_replicas', 'Unknown')

            # Get ILM policy information
            ilm_policy = settings.get('lifecycle', {}).get('name', 'None')
            ilm_icon = "📋" if ilm_policy != 'None' else "❌"

            # Get ILM phase if available
            ilm_phase = 'Unknown'
            ilm_phase_icon = ''
            if ilm_policy != 'None':
                try:
                    # Try to get ILM explain info for this index
                    ilm_explain = self.es.ilm.explain_lifecycle(index=indice_name)
                    if indice_name in ilm_explain['indices']:
                        index_ilm = ilm_explain['indices'][indice_name]
                        phase_name = index_ilm.get('phase', 'Unknown')
                        # Add phase icon
                        phase_icons = {
                            'hot': '🔥',
                            'warm': '🟡',
                            'cold': '🧊',
                            'frozen': '❄️',
                            'delete': '🗑️'
                        }
                        ilm_phase_icon = phase_icons.get(phase_name, '❓')
                        ilm_phase = phase_name.title()
                except:
                    pass

            # Index Settings Panel - Create table for aligned columns
            settings_table = InnerTable(show_header=False, box=None, padding=(0, 1))
            settings_table.add_column("Label", style="bold", no_wrap=True)
            settings_table.add_column("Icon", justify="left", width=3)
            settings_table.add_column("Value", no_wrap=True)

            settings_table.add_row("UUID:", "🆔", uuid)
            settings_table.add_row("Created:", "📅", creation_date)
            settings_table.add_row("Version:", "⚙️", version)
            settings_table.add_row("ILM Policy:", ilm_icon, ilm_policy)
            settings_table.add_row("ILM Phase:", ilm_phase_icon, ilm_phase)
            settings_table.add_row("Configured Shards:", "⚖️", number_of_shards)
            settings_table.add_row("Configured Replicas:", "📋", number_of_replicas)

            settings_panel = Panel(
                settings_table,
                title="⚙️ Settings",
                border_style=theme_color,
                padding=(1, 2)
            )

            # Shards Distribution Panel - Create 3 separate tables
            shard_states = {}
            shard_types = {'primary': 0, 'replica': 0}
            nodes_distribution = {}

            for shard in index_shards:
                # Count states
                state = shard['state']
                shard_states[state] = shard_states.get(state, 0) + 1

                # Count types
                if shard['prirep'] == 'p':
                    shard_types['primary'] += 1
                else:
                    shard_types['replica'] += 1

                # Count node distribution
                node = shard.get('node', 'unassigned')
                nodes_distribution[node] = nodes_distribution.get(node, 0) + 1

            # Create Shard Totals Table
            totals_table = Table.grid(padding=(0, 3))
            totals_table.add_column(style="bold cyan", min_width=16)
            totals_table.add_column(style="white")
            totals_table.add_row("Total Shards:", f"📊 {len(index_shards)}")
            totals_table.add_row("Primary:", f"🔑 {shard_types['primary']}")
            totals_table.add_row("Replica:", f"📋 {shard_types['replica']}")

            totals_panel = Panel(
                totals_table,
                title="📊 Shard Totals",
                border_style=theme_color,
                padding=(1, 1)
            )

            # Create States Table
            states_table = Table.grid(padding=(0, 3))
            states_table.add_column(style="bold cyan", min_width=16)
            states_table.add_column(style="white")
            for state, count in shard_states.items():
                icon = "✅" if state == "STARTED" else "🔄" if state == "INITIALIZING" else "❌"
                states_table.add_row(f"{state}:", f"{icon} {count}")

            states_panel = Panel(
                states_table,
                title="🔄 Shard States",
                border_style=theme_color,
                padding=(1, 1)
            )

            # Create Nodes Table
            nodes_table = Table.grid(padding=(0, 3))
            nodes_table.add_column(style="bold cyan", min_width=16)
            nodes_table.add_column(style="white")
            top_nodes = sorted(nodes_distribution.items(), key=lambda x: x[1], reverse=True)[:5]
            for node, count in top_nodes:
                if node != 'unassigned':
                    nodes_table.add_row(f"{node}:", f"🖥️  {count}")
                else:
                    nodes_table.add_row("None:", f"�️  {count}")

            nodes_panel = Panel(
                nodes_table,
                title="�️ Node Distribution",
                border_style=theme_color,
                padding=(1, 1)
            )

            # Create detailed shards table
            shards_table = Table(
                show_header=True,
                header_style="bold white",
                title="📊 Detailed Shards Information",
                expand=True
            )
            shards_table.add_column("🔄 State", justify="center", width=12)
            shards_table.add_column("⚖️ Type", justify="center", width=10)
            shards_table.add_column("🔢 Shard", justify="center", width=8)
            shards_table.add_column("📊 Documents", justify="right", width=12)
            shards_table.add_column("💾 Store", justify="right", width=10)
            shards_table.add_column("🖥️ Node", no_wrap=True)

            # Sort shards by shard number and type
            sorted_shards = sorted(index_shards, key=lambda x: (int(x['shard']), x['prirep']))

            for shard in sorted_shards:
                # Format state
                state = shard['state']
                if state == "STARTED":
                    state_display = "✅ Started"
                    row_style = "green"
                elif state == "INITIALIZING":
                    state_display = "🔄 Initializing"
                    row_style = "yellow"
                elif state == "RELOCATING":
                    state_display = "🚚 Relocating"
                    row_style = "blue"
                elif state == "UNASSIGNED":
                    state_display = "❌ Unassigned"
                    row_style = "red"
                else:
                    state_display = f"❓ {state}"
                    row_style = "white"

                # Format type
                shard_type = "🔑 Primary" if shard['prirep'] == 'p' else "📋 Replica"

                # Format documents
                docs = shard.get('docs', 'N/A')
                if docs != 'N/A' and docs is not None:
                    try:
                        docs = f"{int(docs):,}"
                    except:
                        pass

                shards_table.add_row(
                    state_display,
                    shard_type,
                    shard['shard'],
                    str(docs),
                    shard.get('store', 'N/A'),
                    shard.get('node', 'unassigned'),
                    style=row_style
                )

            # Display everything
            print()
            console.print(title_panel)
            print()

            # Create layout for top panels - two columns
            top_panels = Columns([overview_panel, settings_panel], expand=True)
            console.print(top_panels)
            print()

            # Shards distribution in three columns
            shards_distribution_panels = Columns([totals_panel, states_panel, nodes_panel], expand=True)
            console.print(shards_distribution_panels)
            print()

            console.print(shards_table)

        except Exception as e:
            console.print(f"[red]❌ Error retrieving index details: {str(e)}[/red]")

    def check_ilm_errors(self):
        """
        Check for ILM errors by calling the ILM explain API and looking for STEP = error.
        Returns a list of indices with ILM errors.
        """
        import requests
        from requests.auth import HTTPBasicAuth

        try:
            ES_URL = self.build_es_url()
            if ES_URL is None:
                return []

            # Call ILM explain API with filter to get detailed error information
            explain_url = f'{ES_URL}/_all/_ilm/explain?pretty&filter_path=indices.*,indices.*.policy,indices.*.step,indices.*.step_info,indices.*.failed_step,indices.*.phase,indices.*.action,indices.*.step_time,indices.*.is_auto_retryable_error,indices.*.failed_step_retry_count'

            if self.elastic_authentication == True:
                response = requests.get(
                    explain_url,
                    auth=HTTPBasicAuth(self.elastic_username, self.elastic_password),
                    verify=False,
                    timeout=self.timeout
                )
            else:
                response = requests.get(explain_url, verify=False, timeout=self.timeout)

            response.raise_for_status()

            data = response.json()
            error_indices = []
            no_policy_indices = []
            managed_indices_count = 0

            if 'indices' in data:
                for index_name, index_data in data['indices'].items():
                    # Check if index has any ILM policy
                    if not index_data.get('policy') or index_data.get('policy') == '':
                        no_policy_indices.append({
                            'index': index_name,
                            'reason': 'No ILM policy attached'
                        })
                    elif 'step' in index_data and index_data['step'] == 'ERROR':
                        # Index has policy but is in error state
                        error_info = {
                            'index': index_name,
                            'policy': index_data.get('policy', 'Unknown'),
                            'step': index_data.get('step'),
                            'phase': index_data.get('phase', 'Unknown'),
                            'action': index_data.get('action', 'Unknown'),
                            'step_time': index_data.get('step_time', 'Unknown'),
                            'failed_step': index_data.get('failed_step', 'Unknown'),
                            'step_info': index_data.get('step_info', {}),
                            'phase_time': index_data.get('phase_time', 'Unknown'),
                            'action_time': index_data.get('action_time', 'Unknown'),
                            'step_time_millis': index_data.get('step_time_millis', 'Unknown'),
                            'is_auto_retryable_error': index_data.get('is_auto_retryable_error', False),
                            'failed_step_retry_count': index_data.get('failed_step_retry_count', 0)
                        }
                        error_indices.append(error_info)
                    else:
                        # Index has policy and is working correctly
                        managed_indices_count += 1

            # Return comprehensive ILM status
            return {
                'errors': error_indices,
                'no_policy': no_policy_indices,
                'managed_count': managed_indices_count,
                'total_indices': len(data.get('indices', {}))
            }

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 405:
                # ILM not supported on this cluster
                return {'not_supported': True, 'reason': 'ILM API not available on this cluster (older ES version or ILM disabled)'}
            else:
                print(f"Error checking ILM status: {str(e)}")
                return []
        except Exception as e:
            print(f"Error checking ILM status: {str(e)}")
            return []

    def check_no_replica_indices(self):
        """
        Check for indices that have no replicas (number_of_replicas = 0).
        Returns a list of indices with no replicas.
        """
        import requests
        from requests.auth import HTTPBasicAuth

        try:
            ES_URL = self.build_es_url()
            if ES_URL is None:
                return []

            # Get index settings for all indices
            settings_url = f'{ES_URL}/_all/_settings'

            if self.elastic_authentication == True:
                response = requests.get(
                    settings_url,
                    auth=HTTPBasicAuth(self.elastic_username, self.elastic_password),
                    verify=False,
                    timeout=self.timeout
                )
            else:
                response = requests.get(settings_url, verify=False, timeout=self.timeout)

            response.raise_for_status()

            data = response.json()
            no_replica_indices = []

            for index_name, index_data in data.items():
                if 'settings' in index_data:
                    settings = index_data['settings']
                    index_settings = settings.get('index', {})

                    # Check number_of_replicas
                    replicas = index_settings.get('number_of_replicas', '1')

                    # Convert to int for comparison
                    try:
                        replica_count = int(replicas)
                        if replica_count == 0:
                            no_replica_indices.append({
                                'index': index_name,
                                'replicas': replica_count,
                                'shards': index_settings.get('number_of_shards', 'Unknown'),
                                'creation_date': index_settings.get('creation_date', 'Unknown')
                            })
                    except (ValueError, TypeError):
                        # Skip if replica count cannot be determined
                        continue

            return no_replica_indices

        except Exception as e:
            print(f"Error checking replica settings: {str(e)}")
            return []

    def check_large_shards(self, max_size_gb=50):
        """
        Check for shards larger than the specified size in GB.
        Returns a list of large shards.
        """
        import requests
        from requests.auth import HTTPBasicAuth

        try:
            ES_URL = self.build_es_url()
            if ES_URL is None:
                return []

            # Get detailed shard information
            shards_url = f'{ES_URL}/_cat/shards?v&h=index,shard,prirep,store,node&bytes=b&s=store:desc'

            if self.elastic_authentication == True:
                response = requests.get(
                    shards_url,
                    auth=HTTPBasicAuth(self.elastic_username, self.elastic_password),
                    verify=False,
                    timeout=self.timeout
                )
            else:
                response = requests.get(shards_url, verify=False, timeout=self.timeout)

            response.raise_for_status()

            lines = response.text.strip().split('\n')
            large_shards = []
            max_size_bytes = max_size_gb * 1024 * 1024 * 1024  # Convert GB to bytes

            # Skip header line
            for line in lines[1:]:
                parts = line.split()
                if len(parts) >= 5:
                    index_name = parts[0]
                    shard_id = parts[1]
                    shard_type = parts[2]  # 'p' for primary, 'r' for replica
                    store_size = parts[3]
                    node_name = parts[4] if len(parts) > 4 else 'unassigned'

                    try:
                        # Convert store size to bytes
                        if store_size and store_size != '-':
                            size_bytes = int(store_size)
                            if size_bytes > max_size_bytes:
                                size_gb = size_bytes / (1024 * 1024 * 1024)
                                large_shards.append({
                                    'index': index_name,
                                    'shard': shard_id,
                                    'type': 'Primary' if shard_type == 'p' else 'Replica',
                                    'size_bytes': size_bytes,
                                    'size_gb': round(size_gb, 2),
                                    'node': node_name
                                })
                    except (ValueError, TypeError):
                        # Skip if size cannot be determined
                        continue

            return large_shards

        except Exception as e:
            print(f"Error checking shard sizes: {str(e)}")
            return []

    def perform_cluster_health_checks(self, max_shard_size_gb=50, skip_ilm=False):
        """
        Perform all cluster health checks and return results as a dictionary.
        Used for JSON output format.
        """
        from datetime import datetime

        # Get cluster name from health data
        try:
            cluster_name = self.get_cluster_health().get('cluster_name', 'Unknown')
        except:
            cluster_name = 'Unknown'

        # Perform ILM check unless skipped
        if skip_ilm:
            ilm_errors = {'skipped': True, 'reason': 'ILM checks skipped via --skip-ilm flag'}
        else:
            ilm_errors = self.check_ilm_errors()

        return {
            'cluster_name': cluster_name,
            'timestamp': str(datetime.now()),
            'checks': {
                'ilm_results': ilm_errors,  # This now contains the comprehensive ILM analysis
                'no_replica_indices': self.check_no_replica_indices(),
                'large_shards': self.check_large_shards(max_shard_size_gb)
            },
            'parameters': {
                'max_shard_size_gb': max_shard_size_gb,
                'skip_ilm': skip_ilm
            }
        }

    def display_cluster_health_report(self, check_results):
        """
        Display a comprehensive cluster health report using Rich formatting.
        """
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        from rich.columns import Columns
        from rich.text import Text
        from rich import box
        from datetime import datetime

        console = Console()

        # Extract results
        ilm_results = check_results.get('ilm_errors', check_results.get('ilm_results', []))
        no_replica_indices = check_results.get('no_replica_indices', [])
        large_shards = check_results.get('large_shards', [])
        max_shard_size = check_results.get('max_shard_size', 50)
        show_details = check_results.get('show_details', False)

        # Handle both old format (list) and new format (dict) for backward compatibility
        if isinstance(ilm_results, dict):
            ilm_errors = ilm_results.get('errors', [])
            ilm_no_policy = ilm_results.get('no_policy', [])
            ilm_managed_count = ilm_results.get('managed_count', 0)
            ilm_total_count = ilm_results.get('total_indices', 0)
        else:
            # Old format - treat as error list only
            ilm_errors = ilm_results
            ilm_no_policy = []
            ilm_managed_count = 0
            ilm_total_count = len(ilm_errors)

        # Create title panel
        try:
            cluster_name = self.get_cluster_health().get('cluster_name', 'Unknown')
        except:
            cluster_name = 'Unknown'

        title_text = f"🏥 Cluster Health Check Report"
        subtitle_text = f"Cluster: {cluster_name} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        title_panel = Panel(
            Text(title_text, style="bold cyan", justify="center"),
            subtitle=subtitle_text,
            border_style="cyan",
            padding=(1, 2)
        )

        # Create summary panel
        summary_table = Table.grid(padding=(0, 1))
        summary_table.add_column(style="bold white", no_wrap=True)
        summary_table.add_column(style="bold cyan")

        # Add summary with status indicators
        if isinstance(ilm_results, dict) and ilm_results.get('not_supported'):
            ilm_status = "ℹ️  Not supported on this cluster"
        elif isinstance(ilm_results, dict) and ilm_results.get('skipped'):
            ilm_status = "⏭️  Skipped"
        else:
            error_count = len(ilm_errors)
            no_policy_count = len(ilm_no_policy)

            if error_count == 0 and no_policy_count == 0:
                ilm_status = "✅ All indices managed"
            elif error_count > 0 and no_policy_count > 0:
                ilm_status = f"❌ {error_count} errors, ⚠️  {no_policy_count} unmanaged"
            elif error_count > 0:
                ilm_status = f"❌ {error_count} errors found"
            else:
                ilm_status = f"⚠️  {no_policy_count} indices unmanaged"

        replica_status = "✅ All have replicas" if len(no_replica_indices) == 0 else f"⚠️  {len(no_replica_indices)} without replicas"
        shard_status = "✅ All within limits" if len(large_shards) == 0 else f"⚠️  {len(large_shards)} oversized shards"

        summary_table.add_row("🔍 ILM Status:", ilm_status)
        summary_table.add_row("📊 Replica Status:", replica_status)
        summary_table.add_row(f"📏 Shard Size (>{max_shard_size}GB):", shard_status)

        # Determine border color based on issues found
        has_ilm_errors = len(ilm_errors) > 0
        has_ilm_unmanaged = len(ilm_no_policy) > 0
        has_issues = has_ilm_errors or has_ilm_unmanaged or len(no_replica_indices) > 0 or len(large_shards) > 0

        summary_panel = Panel(
            summary_table,
            title="📋 Summary",
            border_style="green" if not has_issues else "yellow",
            padding=(1, 2)
        )

        # Display header
        print()
        console.print(title_panel)
        print()
        console.print(summary_panel)
        print()

        # ILM Info Messages
        if isinstance(ilm_results, dict) and (ilm_results.get('not_supported') or ilm_results.get('skipped')):
            if ilm_results.get('not_supported'):
                info_text = f"ℹ️  {ilm_results.get('reason', 'ILM API not available')}\n\nThis is normal for Elasticsearch versions < 6.6 or clusters with ILM disabled."
                title = "📋 ILM Information"
            else:  # skipped
                info_text = f"⏭️  {ilm_results.get('reason', 'ILM checks were skipped')}\n\nUse the command without --skip-ilm to include ILM checks."
                title = "📋 ILM Skipped"

            ilm_info_panel = Panel(
                info_text,
                title=title,
                border_style="blue",
                padding=(1, 2)
            )
            console.print(ilm_info_panel)
            print()

        # ILM Overview (if we have comprehensive data)
        elif isinstance(ilm_results, dict) and ilm_total_count > 0:
            overview_text = f"📊 Total indices analyzed: {ilm_total_count}\n"
            overview_text += f"✅ Successfully managed: {ilm_managed_count}\n"
            overview_text += f"❌ In error state: {len(ilm_errors)}\n"
            overview_text += f"⚠️  Without ILM policy: {len(ilm_no_policy)}"

            overview_panel = Panel(
                overview_text,
                title="📋 ILM Coverage Overview",
                border_style="blue",
                padding=(1, 2)
            )
            console.print(overview_panel)
            print()

        # ILM Errors Details
        if isinstance(ilm_errors, list) and ilm_errors:
            ilm_table = Table(title="❌ Indices with ILM Errors", box=box.ROUNDED, expand=True)
            ilm_table.add_column("Index", style="bold red", ratio=6)
            ilm_table.add_column("Policy", style="cyan", ratio=2)
            ilm_table.add_column("Phase", style="yellow", ratio=0.8)
            ilm_table.add_column("Action", style="magenta", ratio=1)
            ilm_table.add_column("Error Reason", style="red", ratio=3)
            if show_details:
                ilm_table.add_column("Step Time", style="dim")
                ilm_table.add_column("Failed Step", style="dim")

            for error in ilm_errors:
                # Extract error reason from step_info with comprehensive fallbacks
                error_reason = "Unknown error"

                if 'step_info' in error and error['step_info']:
                    step_info = error['step_info']

                    # Try different fields for error information
                    if isinstance(step_info, dict):
                        if 'reason' in step_info:
                            error_reason = step_info['reason']
                        elif 'message' in step_info:
                            error_reason = step_info['message']
                        elif 'error' in step_info:
                            if isinstance(step_info['error'], dict):
                                error_reason = step_info['error'].get('reason', str(step_info['error']))
                            else:
                                error_reason = str(step_info['error'])
                        elif 'type' in step_info:
                            # Sometimes Elasticsearch errors have 'type' field
                            error_reason = f"{step_info['type']}: {step_info.get('reason', 'No details')}"
                        else:
                            # If step_info exists but no clear reason, show formatted content
                            error_reason = str(step_info)
                    else:
                        error_reason = str(step_info)

                # Fallback to failed_step if no useful step_info
                if error_reason == "Unknown error" and error.get('failed_step') and error['failed_step'] != 'Unknown':
                    error_reason = f"Failed at step: {error['failed_step']}"

                # Add retry information if available (this is very important!)
                retry_count = error.get('failed_step_retry_count', 0)
                if retry_count > 0:
                    if retry_count > 1000:
                        error_reason += f" (retried {retry_count:,} times!)"
                    else:
                        error_reason += f" (retried {retry_count} times)"

                # For table display, keep error messages at reasonable length but preserve key info
                if len(error_reason) > 100:
                    # Try to find a good break point to preserve the most important part
                    if " for index [" in error_reason and len(error_reason) > 120:
                        # Try to preserve the main error message before the index name
                        parts = error_reason.split(" for index [", 1)
                        if len(parts[0]) < 90:
                            error_reason = parts[0] + " for index [...]" + error_reason[error_reason.rfind("("):]
                        else:
                            error_reason = error_reason[:97] + "..."
                    else:
                        error_reason = error_reason[:97] + "..."

                if show_details:
                    ilm_table.add_row(
                        error['index'],
                        error['policy'],
                        error['phase'],
                        error['action'],
                        error_reason,
                        error['step_time'],
                        error['failed_step']
                    )
                else:
                    ilm_table.add_row(
                        error['index'],
                        error['policy'],
                        error['phase'],
                        error['action'],
                        error_reason
                    )

            console.print(Panel(ilm_table, border_style="red", padding=(1, 2)))
            print()

        # Indices without ILM policies
        if ilm_no_policy:
            no_policy_table = Table(title="⚠️  Indices without ILM Policies", box=box.ROUNDED, expand=True)
            no_policy_table.add_column("Index", style="bold yellow", no_wrap=True, ratio=4)
            no_policy_table.add_column("Status", style="yellow", ratio=2)

            for index_info in ilm_no_policy:
                no_policy_table.add_row(
                    index_info['index'],
                    index_info['reason']
                )

            console.print(Panel(no_policy_table, border_style="yellow", padding=(1, 2)))
            print()

        # No Replica Indices Details
        if no_replica_indices:
            replica_table = Table(title="⚠️  Indices with No Replicas", box=box.ROUNDED)
            replica_table.add_column("Index", style="bold yellow", no_wrap=True)
            replica_table.add_column("Shards", style="cyan")
            replica_table.add_column("Replicas", style="red")
            if show_details:
                replica_table.add_column("Creation Date", style="dim")

            for index in no_replica_indices:
                if show_details:
                    creation_date = index['creation_date']
                    if creation_date != 'Unknown' and creation_date.isdigit():
                        try:
                            creation_date = datetime.fromtimestamp(int(creation_date) / 1000).strftime('%Y-%m-%d %H:%M')
                        except:
                            pass

                    replica_table.add_row(
                        index['index'],
                        str(index['shards']),
                        str(index['replicas']),
                        creation_date
                    )
                else:
                    replica_table.add_row(
                        index['index'],
                        str(index['shards']),
                        str(index['replicas'])
                    )

            console.print(Panel(replica_table, border_style="yellow", padding=(1, 2)))
            print()

        # Large Shards Details
        if large_shards:
            shard_table = Table(title=f"📏 Shards Larger Than {max_shard_size}GB", box=box.ROUNDED)
            shard_table.add_column("Index", style="bold orange1", no_wrap=True)
            shard_table.add_column("Shard", style="cyan")
            shard_table.add_column("Type", style="yellow")
            shard_table.add_column("Size (GB)", style="red", justify="right")
            if show_details:
                shard_table.add_column("Node", style="dim")

            for shard in large_shards:
                if show_details:
                    shard_table.add_row(
                        shard['index'],
                        str(shard['shard']),
                        shard['type'],
                        str(shard['size_gb']),
                        shard['node']
                    )
                else:
                    shard_table.add_row(
                        shard['index'],
                        str(shard['shard']),
                        shard['type'],
                        str(shard['size_gb'])
                    )

            console.print(Panel(shard_table, border_style="orange1", padding=(1, 2)))
            print()

        # Final recommendations
        has_actual_ilm_errors = len(ilm_errors) > 0
        has_unmanaged_indices = len(ilm_no_policy) > 0
        if has_actual_ilm_errors or has_unmanaged_indices or no_replica_indices or large_shards:
            recommendations = []

            if has_actual_ilm_errors:
                recommendations.append("🔧 Review ILM policies and fix configuration errors")

            if has_unmanaged_indices:
                recommendations.append("📋 Consider adding ILM policies to unmanaged indices for automated lifecycle management")

            if no_replica_indices:
                recommendations.append("🔄 Consider adding replicas for data redundancy")

            if large_shards:
                recommendations.append(f"📏 Consider reindexing or using rollover for shards > {max_shard_size}GB")

            if recommendations:
                rec_text = "\n".join([f"• {rec}" for rec in recommendations])
                rec_panel = Panel(
                    rec_text,
                    title="💡 Recommendations",
                    border_style="blue",
                    padding=(1, 2)
                )
                console.print(rec_panel)
                print()

    def init_replica_manager(self):
        """Initialize the replica manager for this ES client."""
        if not hasattr(self, 'replica_manager'):
            self.replica_manager = ReplicaManager(self)


class ReplicaManager:
    """Manages replica count operations for Elasticsearch indices."""

    def __init__(self, es_client):
        """Initialize replica manager with ES client reference."""
        self.es_client = es_client

    def plan_replica_updates(self, target_count, indices=None, pattern=None, no_replicas_only=False):
        """
        Plan replica count updates without executing them.

        Args:
            target_count (int): Target replica count
            indices (list): Specific indices to update
            pattern (str): Pattern to match indices (e.g., "logs-*")
            no_replicas_only (bool): Only update indices with 0 replicas

        Returns:
            dict: Plan results with indices to update and metadata
        """
        import requests
        import fnmatch
        from requests.auth import HTTPBasicAuth

        try:
            # Get current cluster state
            ES_URL = self.es_client.build_es_url()
            if ES_URL is None:
                raise Exception("Could not build Elasticsearch URL")

            # Get all indices and their settings
            settings_url = f'{ES_URL}/_all/_settings?filter_path=*.settings.index.number_of_replicas'

            if self.es_client.elastic_authentication:
                response = requests.get(
                    settings_url,
                    auth=HTTPBasicAuth(self.es_client.elastic_username, self.es_client.elastic_password),
                    verify=False,
                    timeout=self.es_client.timeout
                )
            else:
                response = requests.get(settings_url, verify=False, timeout=self.es_client.timeout)

            response.raise_for_status()
            settings_data = response.json()

            # Build list of candidate indices
            candidate_indices = []

            if indices:
                # Use specific indices provided
                for index_name in indices:
                    if index_name in settings_data:
                        candidate_indices.append(index_name)
                    else:
                        print(f"Warning: Index '{index_name}' not found in cluster")
            elif pattern:
                # Use pattern matching
                for index_name in settings_data.keys():
                    if fnmatch.fnmatch(index_name, pattern):
                        candidate_indices.append(index_name)
            else:
                # Use all indices
                candidate_indices = list(settings_data.keys())

            # Filter indices that need updates
            indices_to_update = []
            skipped_indices = []

            for index_name in candidate_indices:
                if index_name not in settings_data:
                    continue

                current_replicas = settings_data[index_name].get('settings', {}).get('index', {}).get('number_of_replicas')

                if current_replicas is None:
                    skipped_indices.append({
                        'index': index_name,
                        'reason': 'Could not determine current replica count'
                    })
                    continue

                current_replicas = int(current_replicas)

                # Apply no_replicas_only filter
                if no_replicas_only and current_replicas != 0:
                    skipped_indices.append({
                        'index': index_name,
                        'reason': f'Has {current_replicas} replicas (--no-replicas-only specified)'
                    })
                    continue

                # Check if update is needed
                if current_replicas != target_count:
                    indices_to_update.append({
                        'index': index_name,
                        'current_replicas': current_replicas,
                        'target_replicas': target_count
                    })
                else:
                    skipped_indices.append({
                        'index': index_name,
                        'reason': f'Already has {target_count} replicas'
                    })

            return {
                'indices_to_update': indices_to_update,
                'skipped_indices': skipped_indices,
                'target_count': target_count,
                'total_candidates': len(candidate_indices),
                'total_updates_needed': len(indices_to_update),
                'pattern': pattern,
                'no_replicas_only': no_replicas_only
            }

        except Exception as e:
            raise Exception(f"Failed to plan replica updates: {str(e)}")

    def execute_replica_updates(self, indices_to_update, target_count, progress=None, task_id=None):
        """
        Execute the planned replica count updates.

        Args:
            indices_to_update (list): List of indices to update from plan_replica_updates
            target_count (int): Target replica count
            progress (Progress): Optional Rich progress bar
            task_id: Optional task ID for progress tracking

        Returns:
            dict: Execution results
        """
        import requests
        import time
        from requests.auth import HTTPBasicAuth

        try:
            ES_URL = self.es_client.build_es_url()
            if ES_URL is None:
                raise Exception("Could not build Elasticsearch URL")

            successful_updates = []
            failed_updates = []

            for index_info in indices_to_update:
                index_name = index_info['index']

                try:
                    # Update replica count
                    settings_url = f'{ES_URL}/{index_name}/_settings'
                    update_payload = {
                        "index": {
                            "number_of_replicas": target_count
                        }
                    }

                    if self.es_client.elastic_authentication:
                        response = requests.put(
                            settings_url,
                            json=update_payload,
                            auth=HTTPBasicAuth(self.es_client.elastic_username, self.es_client.elastic_password),
                            verify=False,
                            timeout=self.es_client.timeout
                        )
                    else:
                        response = requests.put(settings_url, json=update_payload, verify=False, timeout=self.es_client.timeout)

                    response.raise_for_status()

                    successful_updates.append({
                        'index': index_name,
                        'previous_replicas': index_info['current_replicas'],
                        'new_replicas': target_count,
                        'timestamp': time.time()
                    })

                except Exception as e:
                    failed_updates.append({
                        'index': index_name,
                        'error': str(e),
                        'previous_replicas': index_info.get('current_replicas', 'unknown')
                    })

                # Update progress if provided
                if progress and task_id:
                    progress.advance(task_id)
                    time.sleep(0.1)  # Small delay to show progress

            return {
                'successful_updates': successful_updates,
                'failed_updates': failed_updates,
                'target_count': target_count,
                'total_attempted': len(indices_to_update),
                'success_count': len(successful_updates),
                'failure_count': len(failed_updates)
            }

        except Exception as e:
            raise Exception(f"Failed to execute replica updates: {str(e)}")

    def display_update_plan(self, plan_result, dry_run=False):
        """Display the replica update plan in a formatted table."""
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        from rich import box

        console = Console()

        # Summary information
        summary_info = [
            f"📊 Total indices analyzed: {plan_result['total_candidates']}",
            f"🔧 Indices requiring updates: {plan_result['total_updates_needed']}",
            f"⏭️  Indices to skip: {len(plan_result['skipped_indices'])}",
            f"🎯 Target replica count: {plan_result['target_count']}"
        ]

        if plan_result.get('pattern'):
            summary_info.append(f"🔍 Pattern filter: {plan_result['pattern']}")
        if plan_result.get('no_replicas_only'):
            summary_info.append("📋 Mode: No-replicas-only")

        summary_text = "\n".join(summary_info)
        summary_panel = Panel(
            summary_text,
            title="📋 Replica Update Plan Summary",
            border_style="blue",
            padding=(1, 2)
        )
        console.print(summary_panel)
        print()

        # Show indices to update
        if plan_result['indices_to_update']:
            update_table = Table(title="🔧 Indices to Update", box=box.ROUNDED, expand=True)
            update_table.add_column("Index", style="bold cyan", ratio=4)
            update_table.add_column("Current Replicas", style="red", ratio=1)
            update_table.add_column("Target Replicas", style="green", ratio=1)
            update_table.add_column("Status", style="yellow", ratio=2)

            for index_info in plan_result['indices_to_update']:
                status = "🔄 Ready for update" if not dry_run else "📋 Dry run (no changes)"
                update_table.add_row(
                    index_info['index'],
                    str(index_info['current_replicas']),
                    str(index_info['target_replicas']),
                    status
                )

            console.print(Panel(update_table, border_style="green", padding=(1, 2)))
            print()

        # Show skipped indices (first 10)
        if plan_result['skipped_indices']:
            skipped_table = Table(title="⏭️  Skipped Indices (First 10)", box=box.ROUNDED, expand=True)
            skipped_table.add_column("Index", style="bold yellow", ratio=3)
            skipped_table.add_column("Reason", style="dim", ratio=3)

            for index_info in plan_result['skipped_indices'][:10]:
                skipped_table.add_row(
                    index_info['index'],
                    index_info['reason']
                )

            if len(plan_result['skipped_indices']) > 10:
                skipped_table.add_row("...", f"and {len(plan_result['skipped_indices']) - 10} more")

            console.print(Panel(skipped_table, border_style="yellow", padding=(1, 2)))
            print()

    def display_update_results(self, result):
        """Display the results of replica updates."""
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        from rich import box

        console = Console()

        # Summary
        summary_info = [
            f"✅ Successful updates: {result['success_count']}/{result['total_attempted']}",
            f"❌ Failed updates: {result['failure_count']}/{result['total_attempted']}",
            f"🎯 Target replica count: {result['target_count']}"
        ]

        summary_text = "\n".join(summary_info)
        border_style = "green" if result['failure_count'] == 0 else "red"
        summary_panel = Panel(
            summary_text,
            title="📊 Replica Update Results",
            border_style=border_style,
            padding=(1, 2)
        )
        console.print(summary_panel)
        print()

        # Show successful updates
        if result['successful_updates']:
            success_table = Table(title="✅ Successful Updates", box=box.ROUNDED, expand=True)
            success_table.add_column("Index", style="bold green", ratio=4)
            success_table.add_column("Previous", style="red", ratio=1)
            success_table.add_column("New", style="green", ratio=1)
            success_table.add_column("Status", style="bright_green", ratio=2)

            for update_info in result['successful_updates']:
                success_table.add_row(
                    update_info['index'],
                    str(update_info['previous_replicas']),
                    str(update_info['new_replicas']),
                    "✅ Updated successfully"
                )

            console.print(Panel(success_table, border_style="green", padding=(1, 2)))
            print()

        # Show failed updates
        if result['failed_updates']:
            failure_table = Table(title="❌ Failed Updates", box=box.ROUNDED, expand=True)
            failure_table.add_column("Index", style="bold red", ratio=3)
            failure_table.add_column("Previous", style="yellow", ratio=1)
            failure_table.add_column("Error", style="red", ratio=4)

            for failure_info in result['failed_updates']:
                failure_table.add_row(
                    failure_info['index'],
                    str(failure_info['previous_replicas']),
                    failure_info['error']
                )

            console.print(Panel(failure_table, border_style="red", padding=(1, 2)))
            print()


# ---- End of Class Library above.
