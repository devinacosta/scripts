#!/usr/bin/env python3
'''
Administration tool for Elastic Search, simplifies admin tasks.
Version: 1.0.5 (04/18/2024)
- Added Disk Storage
'''

# Import Modules
import argparse
import json
import os
import yaml
import requests
import warnings
import urllib3
from elasticsearch import Elasticsearch, ElasticsearchWarning, exceptions, helpers
from elasticsearch.exceptions import RequestError
from rich import print
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich import box

VERSION = '1.0.4'

# Suppress only the InsecureRequestWarning from urllib3 needed for Elasticsearch
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
requests.packages.urllib3.disable_warnings(DeprecationWarning)

# Suppress the UserWarning
warnings.filterwarnings("ignore", category=UserWarning, module="elasticsearch")
warnings.filterwarnings("ignore", category=ElasticsearchWarning)


class ElasticsearchClient:
    def __init__(self, host='localhost', port=9200, use_ssl=False, verify_certs=False, elastic_authentication=False, elastic_username=None, elastic_password=None, box_style=box.SIMPLE):
        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self.verify_certs = verify_certs
        self.box_style = box_style
        self.elastic_authentication = elastic_authentication
        self.elastic_username = elastic_username
        self.elastic_password = elastic_password
        self.elastic_host = host
        self.elastic_port = port

        # Set Authentication to True if Username/Password NOT None
        if (self.elastic_username != None and self.elastic_password != None):
            self.elastic_authentication = True

        if self.elastic_authentication == True:
            self.es = Elasticsearch([{'host': self.host, 'port': self.port, 'use_ssl': self.use_ssl, 'verify_certs': self.verify_certs, 'http_auth': (self.elastic_username, self.elastic_password)}])
        else:
            self.es = Elasticsearch([{'host': self.host, 'port': self.port, 'use_ssl': self.use_ssl, 'verify_certs': self.verify_certs}])

        if self.es.ping():
            pass
        else:
            attempted_settings = f"host:{self.host}, port:{self.port}, ssl:{self.use_ssl}, verify_certs:{self.verify_certs}"
            self.show_message_box("Connection Error", f"ERROR: There was a 'Connection Error' trying to connect to ES.\nSettings: {attempted_settings}", message_style="white on blue")
            exit(1)

    def display_recovery_table(self, recovery_status):
        """
        Display recovery status in a table using rich.
        """
        table = Table(title="Elasticsearch Recovery Status")

        if not recovery_status:
            self.show_message_box("Cluster Recovery", "No Recovery Jobs Found", message_style='bold white', panel_style='bold white')
            return

        table.add_column("Index", style="cyan")
        table.add_column("Shard", style="magenta")
        table.add_column("Stage", style="green")
        table.add_column("Source", style="blue")
        table.add_column("Target", style="yellow")
        table.add_column("Type", style="cyan")

        for index, shards in recovery_status.items():
            for shard in shards:
                shard_id = shard.get('shard', 'N/A')
                stage = shard.get('stage', 'N/A')
                source = shard.get('source', 'N/A')
                target = shard.get('target', 'N/A')
                shard_type = shard.get('type', 'N/A')
                table.add_row(index, shard_id, stage, source, target, shard_type)

        console.print(table)

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

    def get_template(self, name=None):
        if name:
            return self.es.indices.get_template(name)
        else:
            return self.es.indices.get_template()

    def get_nodes(self):
        stats = self.es.nodes.stats()
        node_stats = self.parse_node_stats(stats)
        nodes_sorted = sorted(node_stats, key=lambda x: x['name'])
        return nodes_sorted

    def get_all_nodes_stats(self):
        nodes_stats = self.es.nodes.stats()
        return nodes_stats['nodes']

    def get_cluster_health(self):

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
                'disk.percent': float(entry['disk.percent']),
                'disk.used': int(entry['disk.used']),
                'disk.avail': int(entry['disk.avail']),
                'disk.total': int(entry['disk.total'])
            }

        # Sort the dictionary by keys alphabetically
        sorted_allocation_dict = dict(sorted(allocation_dict.items()))
        
        return sorted_allocation_dict

    def get_indices_stats(self, pattern=None):
 
        self.pattern = pattern

        # Get all indices
        if (self.pattern == None):
            indices = self.es.cat.indices(format='json')
        else:
            search_pattern = f"*{self.pattern}*"
            indices = self.es.cat.indices(format='json', index=search_pattern)
        indices_json = json.dumps(indices)
        return indices_json


    def list_indices_stats(self, pattern=None):
 
        self.pattern = pattern

        # Get all indices
        if (self.pattern == None):
            indices = self.es.cat.indices(format='json')
            indices_sorted = sorted(indices, key=lambda x: x['index'])
        else:
            search_pattern = f"*{self.pattern}*"
            indices = self.es.cat.indices(format='json', index=search_pattern)
            indices_sorted = sorted(indices, key=lambda x: x['index'])

        self.print_table_indices(indices_sorted)


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

    def print_filtered_key_value_pairs(self, keys, values, display_keys):
     
        table = Table(show_header=True, show_lines=False, box=self.box_style)
        for key in display_keys:
            if key in keys:
                table.add_column(str(key), style="white")

         # Transpose the values so each inner list represents a row
        rows = list(zip(*values))

        for row in rows:
            display_values = []
            for key in display_keys:
                if key in keys:
                    key_index = keys.index(key)
                    value = row[key_index]

                    if key == 'name':
                        
                        # See if what current master is and display * next to it.
                        _current_master = self.get_master_node()
                        if str(value) == str(_current_master):
                            value += " [bold cyan]*[/bold cyan]"

                    if key == 'roles':
                        value = self.replace_roles(value)
                    display_values.append(str(value))
            table.add_row(*display_values)
 

        console = Console()
        console.print(table)


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

    def print_table_from_dict(self, title, data_dict):
        console = Console()

        table = Table(show_header=True, title=title, header_style="bold cyan", box=self.box_style)
        table.add_column("Key")
        table.add_column("Value")

        for key, value in data_dict.items():

            if (key == "cluster_status" and value == "green"):
                value="[green]green[/green]"
            if (key == "cluster_status" and value == "yellow"):
                value="[yellow]yellow[/yellow]"
            if (key == "cluster_status" and value == "red"):
                value="[red]red[/red]"
            if (key == "active_shards_percent" and value == 100.0):
                value="[green]100.0[/green]"
            if (key == "active_shards_percent" and value != 100.0):
                value=f"[yellow]{value}[/yellow]"

            table.add_row(str(key), str(value))

        console.print(table)

    def print_table_indices(self, data_dict):
        console = Console()

        table = Table(show_header=True, title='Indices', header_style="bold cyan", box=self.box_style)
        table.add_column("Health", justify="right")
        table.add_column("Satus", justify="right")
        table.add_column("Indice")
        table.add_column("UUID")
        table.add_column("Docs", justify="right")
        table.add_column("Pri/Rep", justify="center")
        table.add_column("Size Primary", justify="right")
        table.add_column("Size Total", justify="right")

        for indice in data_dict:


            indice_health = indice['health']
            indice_status = indice['status']
            indice_name = indice['index']
            indice_uuid = indice['uuid']
            indice_docs_count = indice['docs.count']
            indice_store_size = indice['store.size']
            indice_primary_store_size = indice['pri.store.size']
            indice_pri = indice['pri']
            indice_rep = indice['rep']
            pri_rep = f"{indice_pri}|{indice_rep}"
            indice_size = f"{indice_primary_store_size}|{indice_store_size}"

            table.add_row(str(indice_health), str(indice_status), str(indice_name), str(indice_uuid), str(indice_docs_count), str(pri_rep), str(indice_primary_store_size), str(indice_store_size))

        console.print(table)


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
                    "cluster.routing.allocation.enable": "all" 
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

    def show_cluster_settings(self):

        settings = self.es.cluster.get_settings()
        return (json.dumps(settings))


    def get_settings(self):

        settings = self.es.cluster.get_settings()
        return json.dumps(settings)


    def show_message_box(self, title, message, message_style="bold white", panel_style="white on blue"):
        self.title = title
        self.message_style = message_style
        self.panel_style = panel_style

        message = Text(f"{message}", style=self.message_style, justify="center")
        panel = Panel(message, style=self.panel_style, title=self.title, border_style="bold white", width=80)
        console.print("\n")
        console.print(panel)
        console.print("\n")


# ---- End of Class Library above.    


def show_message_box(title, message, message_style="bold white", panel_style="white on blue"):

    message = Text(f"{message}", style=message_style, justify="center")
    panel = Panel(message, style=panel_style, title=title, border_style="bold white", width=80)
    console.print("\n")
    console.print(panel)
    console.print("\n")        

def convert_dict_list_to_dict(dict_list):
    result_dict = {}
    for item in dict_list:
        name = item.pop('name').lower()
        result_dict[name] = item
    return result_dict

def read_config_server(file_path, locations):
    with open(file_path, 'r') as file:
        config = yaml.safe_load(file)
        servers = config.get('servers', [])
        default_config = config.get('default', {})
        
        for location in locations:
            for server in servers:
                if server['name'].lower() == locations.lower():
                    return {
                        'elastic_host': server.get('hostname', default_config.get('hostname', 'localhost')),
                        'elastic_port': server.get('port', default_config.get('port', 9200)),
                        'use_ssl': server.get('use_ssl', default_config.get('use_ssl', False)),
                        'elastic_authentication': server.get('elastic_authentication', default_settings.get('elastic_authentication', False)),
                        'elastic_username': server.get('elastic_username', default_settings.get('elastic_username', None)),
                        'elastic_password': server.get('elastic_password', default_settings.get('elastic_password', None)),
                        'repository': server.get('repository', default_config.get('repository', 'default-repo'))
                    }
        
        return None

# Read Data from YAML, store data automatically into Global Variables
def read_servers_from_yaml(file_path):
    # Open YAML and read into array: data
    with open(file_path, 'r') as file:
        data = yaml.safe_load(file)

    # Loop through data and return dict.
    # Convert hostname to 'lowercase' to normalize
    _servers = {}
    for server in data['servers']:
        ret_name = server['name'].upper()
        ret_hostname = server['hostname']
        _servers[ret_name] = ret_hostname

    return _servers

def read_yaml_file(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            return yaml.safe_load(file)
    else:
        return {}

def read_settings(file):
    try:
        with open(file, 'r') as file:
            settings = json.load(file)
    except FileNotFoundError:
        settings = {"current_cluster": "default"}
    return settings

def write_settings(settings):
    with open('escmd.json', 'w') as file:
        json.dump(settings, file, indent=4)

def set_cluster(file, value):
    settings = read_settings(file)
    settings["current_cluster"] = value
    write_settings(settings)
    print(f"Current cluster set to: {value}")



if __name__ == "__main__":

 
     # Start Status Console
    console = Console()

     # Run Main Function
    parser = argparse.ArgumentParser(description='Elasticsearch command-line tool')
    subparsers = parser.add_subparsers(dest='command', help='Sub-command help')

    # Parameters
    parser.add_argument("-l","--locations", help="Location ( defaults to localhost )", type=str, default=None)


    # Nodes command
    allocation_parser = subparsers.add_parser('allocation', help='Actions for ES Allocation')
    current_master_parser = subparsers.add_parser('current-master', help='List Current Master')
    health_parser = subparsers.add_parser('health', help='Show Cluster Health')
    indices_parser = subparsers.add_parser('indices', help='Indices')
    masters_parser = subparsers.add_parser('masters', help='List ES Master nodes')
    nodes_parser = subparsers.add_parser('nodes', help='List Elasticsearch nodes')
    ping_parser = subparsers.add_parser('ping', help='Check ES Connection')
    recovery_parser = subparsers.add_parser('recovery', help='List Recovery Jobs')
    settings_parser = subparsers.add_parser('settings', help='Actions for ES Allocation')
    storage_parser = subparsers.add_parser('storage', help='List ES Disk Usage')
    getdefault_parser = subparsers.add_parser('get-default', help='Show Default Cluster configured.')
    setdefault_parser = subparsers.add_parser('set-default', help='Set Default Cluster to use for commands.')
    version = subparsers.add_parser('version', help='Show Version Number')


    # Add Json Parameters
    allocation_parser.add_argument('allocation_cmd', choices=['enable', 'disable', 'display', 'show'], nargs='?', default='display', help='Enable/Disable Shard Allocation')
    current_master_parser.add_argument('format', choices=['json', 'table'], nargs='?', default='table', help='Ouptput format (json or table)')
    health_parser.add_argument('--format', choices=['json', 'table'], nargs='?', default='table', help='Output format (json or table)')
    indices_parser.add_argument('--format', choices=['json', 'table'], nargs='?', default='table', help='List indices')
    indices_parser.add_argument('regex', nargs='?', default=None, help='Regex')
    masters_parser.add_argument('--format', choices=['json', 'table'], nargs='?', default='table', help='Ouptput format (json or table)')
    nodes_parser.add_argument('--format', choices=['data','json', 'table'], nargs='?', default='table', help='Ouptput format (json or table)')
    recovery_parser.add_argument('--format', choices=['data','json', 'table'], nargs='?', default='table', help='Ouptput format (json or table)')
    settings_parser.add_argument('--format', choices=['table', 'json'], nargs='?', default='table', help='Output format (json or table)')
    settings_parser.add_argument('settings_cmd', choices=['display', 'show'], nargs='?', default='display', help='Show Settings')
    setdefault_parser.add_argument('defaultcluster_cmd', nargs='?', default='default')
    storage_parser.add_argument('--format', choices=['data','json', 'table'], nargs='?', default='table', help='Ouptput format (json or table)')

    args = parser.parse_args()


    # Variables
    script_directory = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(script_directory,'elastic_servers.yml')
    config = read_yaml_file(config_file)
    default_settings = config.get('settings', {})
    # Contains all the servers from YAML
    servers_settings = config.get('servers', [{"name": 'DEFAULT', "hostname": 'localhost', "port": 9200, "use_ssl": False}])
    servers_dict = convert_dict_list_to_dict(servers_settings)

    # Now we need to see what environment is defauled to by set-default
    state_file = f"{script_directory}/escmd.json"
    default_cluster_from_file = read_settings(state_file)['current_cluster']

    # Need to Place this here so that it bypasses a lot of the checks afterwards.
    if (args.command == 'set-default'):
        cmd_cluster_touse = args.defaultcluster_cmd
        set_cluster(state_file, cmd_cluster_touse)
        exit()

    if args.command == 'get-default':
        current_cluster = read_settings(state_file)
        message = [f"name: {default_cluster_from_file}"]
        try:
            for key,value in servers_dict[default_cluster_from_file].items():
                append_item = f"{key}: {value}"
                message.append(append_item)
                show_message = "\n".join(message)
        except KeyError: 
            show_message = "No Configuration Found"
        
        show_message_box(f"Default Cluster: {current_cluster['current_cluster']}", message=f"\n{show_message}\n")      
        exit()
   

    # Now we need to figure out if we use location or default from file.
    if args.locations == None:
        es_location = default_cluster_from_file
    else:
        es_location = args.locations

    # Read Configuration from YAML
    locations = es_location.lower()

    # Now we need to determine whether there is a location match in dict or return Error.
    if not locations in servers_dict:
        text = (f"Location: {locations} not found.\nPlease check your elastic_settings.yml config file.")
        console.print(Panel.fit(text, title="Configuration Error"))
        exit(1) 

    location_to_use_dict = servers_dict[locations]

    # Get Values that May or May Not Exist    
    elastic_host = location_to_use_dict.get('hostname', 'localhost')
    elastic_port = location_to_use_dict.get('port', 9200)
    elastic_use_ssl = location_to_use_dict.get('use_ssl', False)
    elastic_repository = location_to_use_dict.get('repository', None)
    #elastic_authentication = location_to_use_dict.get('elastic_authentication', False)
    elastic_username = location_to_use_dict.get('elastic_username', None)
    elastic_password = location_to_use_dict.get('elastic_password', None)
    elastic_authentication = location_to_use_dict.get('elastic_authentication', elastic_username is not None and elastic_password is not None)

    elastic_verify_certs = location_to_use_dict.get('verify_certs', False)

    # Need to Define the Box Style (have to do a bit of magic)
    box_style_string = default_settings.get('box_style', 'SQUARE_DOUBLE_HEAD')
    # Define a dictionary mapping strings to box styles
    box_styles = {
        "SIMPLE": box.SIMPLE,
        "ASCII": box.ASCII,
        "SQUARE": box.SQUARE,
        "ROUNDED": box.ROUNDED,
        "SQUARE_DOUBLE_HEAD": box.SQUARE_DOUBLE_HEAD
    }
    box_style = box_styles.get(box_style_string)


    #### Now to process arguments and do the work.

    # If no arguments passed, display help.
    if vars(args)['command'] == None:
        parser.print_help()
    else:

        # We want to ensure it doesn't try to connect to ES for the set-default command.
        if (args.command != 'set-default'):

            # Setup Elastic Search Connection
            es_client = ElasticsearchClient(host=elastic_host, port=elastic_port, use_ssl=elastic_use_ssl, verify_certs=elastic_verify_certs, elastic_authentication=elastic_authentication, elastic_username=elastic_username, elastic_password=elastic_password, box_style=box_style)

        if args.command == 'ping':
            # Setup Elastic Search Connection
            if es_client.ping():
                if (es_client.elastic_username != None and es_client.elastic_password != None):
                    cluster_connection_info = f"Cluster: {locations}\nhost: {elastic_host}\nport: {elastic_port}\nssl: {elastic_use_ssl}\nverify_certs: {elastic_verify_certs}\nelastic_username: {elastic_username}\nelastic_password: XXXXXXXXXXX\n"
                else:
                    cluster_connection_info = f"Cluster: {locations}\nhost: {elastic_host}\nport: {elastic_port}\nssl: {elastic_use_ssl}\nverify_certs: {elastic_verify_certs}\n"
                es_client.show_message_box("Connection Success", f"\n{cluster_connection_info}\nConnection was successful.\n", message_style="bold white")
                exit()


        if (args.command == 'allocation'):
            if (args.allocation_cmd == "display" or args.allocation_cmd == "show"):
                es_client.show_message_box("ES Allocation Info",f"Please pass additional keyword: disable, enable", message_style='bold white', panel_style='bold white')
                exit()

            elif (args.allocation_cmd == "disable"):
                success = es_client.change_shard_allocation('primary')
                if success == True:
                    print("Successfully changed allocation to primaries only.")
                    es_client.show_cluster_settings()

                else:
                    print("An ERROR occurred trying to change allocation")
                    exit(1)
            elif (args.allocation_cmd == "enable"):
                success = es_client.change_shard_allocation('all')
                if success == True:
                    print("Successfully re-enabled all shards allocation.")
                    es_client.show_cluster_settings()
                else:
                    print("An ERROR occurred trying to change allocation")
                    exit(1)            
    

        if (args.command == 'current-master'):
            
            master_node_id = es_client.get_master_node()
            
            if args.format=='json':
                print(json.dumps(master_node_id))
            else:
                print(f"Current Master is: [cyan]{master_node_id}[/cyan]")

        if (args.command == 'nodes'):
            nodes = es_client.get_nodes()

            if args.format=='json':
                json_dump = json.dumps(nodes)
                print(json_dump)
            elif args.format=='data':
                data_nodes = es_client.filter_nodes_by_role(nodes,'data')
                keys, values = es_client.obtain_keys_values(data_nodes)
                display_keys = ["name", "hostname", "node", "roles"]
                es_client.print_filtered_key_value_pairs(keys,values, display_keys)            
            else:
                keys, values = es_client.obtain_keys_values(nodes)
                display_keys = ["name", "hostname", "node", "roles"]
                es_client.print_filtered_key_value_pairs(keys,values, display_keys)

        if (args.command == 'masters'):
            nodes = es_client.get_nodes()
            master_node_id = es_client.get_master_node()
            master_nodes = es_client.filter_nodes_by_role(nodes, 'master')
            if args.format=='json':
                print(json.dumps(master_nodes))
            else:
                master_nodes = es_client.filter_nodes_by_role(nodes, 'master')
                keys, values = es_client.obtain_keys_values(master_nodes)
                display_keys = ["name", "hostname", "node", "roles"]
                es_client.print_filtered_key_value_pairs(keys,values, display_keys)            

        if (args.command == 'health'):
            health_data = es_client.get_cluster_health()
            if args.format=='json':
                json_dump = json.dumps(health_data)
                print(json_dump)
            else:
                print("")
                es_client.print_table_from_dict('Elastic Health Status', health_data)

        if (args.command == 'indices'):

            if (args.regex != None):
                if (args.format=='json'):
                    print(es_client.get_indices_stats(pattern=args.regex))
                    exit()
                else:
                    es_client.list_indices_stats(pattern=args.regex)
                    exit()
            if args.format=='json':
                print(es_client.get_indices_stats(pattern=args.regex))
            else:
                es_client.list_indices_stats(None)

        if (args.command == 'recovery'):
            if (args.format == "json"):
                es_recovery = es_client.get_recovery_status()
                print(json.dumps(es_recovery))
                exit()

            else:

                with console.status("Retrieving recovery data..."):
                    # Show ES Recovery Status
                    es_recovery = es_client.get_recovery_status()
                    es_client.display_recovery_table(es_recovery)
                exit()

        if (args.command == 'settings'):
            if (args.format == 'json'):
                print(es_client.show_cluster_settings())
                exit()
            else:
                cluster_settings = es_client.get_settings()
                cluster_flattened = es_client.flatten_json(cluster_settings)
                es_client.print_table_from_dict("Cluster Settings", cluster_flattened)
                exit()

        if (args.command == 'storage'):
            allocation_data = es_client.get_allocation_as_dict()
            es_client.print_table_allocation("Cluster Allocation", allocation_data)

        if (args.command == 'version'):
                es_client.show_message_box("Version Info",f"Utility: escmd.py\nVersion: {VERSION}", message_style='bold white', panel_style='bold white')
                exit()
        