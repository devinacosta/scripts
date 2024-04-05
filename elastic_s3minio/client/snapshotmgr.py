#!/usr/bin/env python3
"""
Elastic Snaphot Utility
Written by Devin Acosta
Version: 1.2.2a (3/12/2024)
"""

import argparse
import configparser
import os
import re
import requests
import warnings
import yaml
from requests.auth import HTTPBasicAuth
from urllib3.exceptions import InsecureRequestWarning
from datetime import datetime
from elasticsearch import Elasticsearch, ElasticsearchWarning
from rich.console import Console
from rich.table import Table
from rich import print
from rich.text import Text
from rich.panel import Panel
from rich.syntax import Syntax
from rich.style import Style



warnings.filterwarnings("ignore", category=DeprecationWarning, module="elasticsearch")
warnings.filterwarnings("ignore", category=ElasticsearchWarning)


def read_yaml_file(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)


def read_config_server(file_path, locations):
    with open(file_path, 'r') as file:
        config = yaml.safe_load(file)
        servers = config.get('servers', [])
        default_config = config.get('default', {})
        
        for location in locations:
            for server in servers:
                if server['name'].lower() == location.lower():
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


def fetch_snapshot_size(snapshot_name):
        
        # Get Indice Size
        if elastic_use_ssl == False:
            es_url = f"http://{elastic_host}:{elastic_port}"
        else:
            es_url = f"https://{elastic_host}:{elastic_port}"
            
        snapshot_size = get_snapshot_size(es_url, elastic_repository, snapshot_name)
        return snapshot_size

def get_snapshot_size(elasticsearch_url, repository_name, snapshot_name):
    
    global elastic_authentication
    global elastic_username
    global elastic_password
    

    # Construct the URL for the snapshot status API
    url = f"{elasticsearch_url}/_snapshot/{repository_name}/{snapshot_name}/_status?pretty"

    try:
        # Send a GET request to the Elasticsearch snapshot status API
        if elastic_authentication == True:
            auth = HTTPBasicAuth(elastic_username, elastic_password)
            response = requests.get(url, verify=False, auth=HTTPBasicAuth(elastic_username, elastic_password))
        else:
            response = requests.get(url, verify=False)
        response.raise_for_status()  # Raise an exception for HTTP errors
        #print(f"Response: {response}")

        # Parse the response as JSON
        snapshot_status = response.json()

        # Extract the snapshot size in bytes
        snapshot_size_bytes = snapshot_status['snapshots'][0]['stats']['total']['size_in_bytes']

        # Convert bytes to a human-readable format
        snapshot_size_human_readable = format_bytes(snapshot_size_bytes)

        return snapshot_size_human_readable

    except requests.exceptions.RequestException as e:
        print(f"Error retrieving snapshot status: {e}")
        return None

def format_bytes(size_in_bytes):
    # Function to convert bytes to a human-readable format
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024.0


def get_snapshots_info(repository_name, optional_regex, elastic_host, elastic_port, elastic_use_ssl):

    global elastic_authentication
    global elastic_username
    global elastic_password

    # Elasticsearch endpoint for Cat Snapshots API
    endpoint = '/_cat/snapshots/{repository_name}?v&s=id'

    # Build the URL for the Cat Snapshots API
    if elastic_use_ssl == False:
        url = f'http://{elastic_host}:{elastic_port}{endpoint.format(repository_name=repository_name)}'
    if elastic_use_ssl == True:
        url = f'https://{elastic_host}:{elastic_port}{endpoint.format(repository_name=repository_name)}'

    # Add HTTP authentication if needed
    if elastic_authentication:
        auth = (elastic_username, elastic_password)
    else:
        auth = None

    try:
        # Make a GET request to the Elasticsearch endpoint
        response = requests.get(url, auth=auth, verify=False)

        # Check if the request was successful (status code 200)
        if response.status_code == 200:

            # Parse the response content and create a list of dictionaries
            snapshots_data = parse_snapshots_response(response.text, optional_regex)

            # Use tabulate to print the data in a pretty table with left-aligned columns
            return snapshots_data
        else:
            text = (f"Status code: {response.status_code}\nUnable to retrieve snapshots.")
            console.print(Panel.fit(text, title="Connection Error"))
            exit(1)      
    except Exception as e:
        text = (f"Error: {e}")
        console.print(Panel.fit(text, title="Connection Error"))
        exit(1)

def parse_snapshots_response(response_text, optional_regex):

    # Split the response text into lines
    lines = response_text.strip().split('\n')

    # Get the header line (contains field names)
    header_line = lines.pop(0).split()

    # Initialize an empty list to store dictionaries
    snapshots_data = []

    # Define the fields to include in the output
    desired_fields = ['id', 'status', 'end_epoch', 'duration', 'total_shards']

    # Iterate over the remaining lines
    for line in lines:
        # Split each line into values
        values = line.split()

        # Convert epoch time to human-readable format
        end_epoch = int(values[header_line.index('end_epoch')])
        end_time = datetime.utcfromtimestamp(end_epoch).strftime('%Y-%m-%d %H:%M:%S')


        # Create a dictionary using the desired fields as keys and corresponding values
        snapshot_info = {
            'id': values[header_line.index('id')],
            'status': values[header_line.index('status')],
            'end_time': end_time,
            'duration': values[header_line.index('duration')],
            'total_shards': values[header_line.index('total_shards')]
        }

        if optional_regex is not None:
            # Add Regex to limit response
            re_pattern = f'.*{re.escape(optional_regex)}.*'
            re_match = re.search(re_pattern, snapshot_info['id'])

            if re_match:
                # Append the dictionary to the list
                snapshots_data.append(snapshot_info)
        else:
            # Append the dictionary to the list
            snapshots_data.append(snapshot_info)

    return snapshots_data


# Read INI file and load settings.
def read_settings(file_path):
    """
    Read settings from an INI file.

    Args:
        file_path (str): The path to the INI file.

    Returns:
        dict: A dictionary containing the settings.
    """
    config = configparser.ConfigParser()
    config.read(file_path)

    settings = {}
    if 'settings' in config:
        settings = config['settings']

    return settings

def elastic_restoredsnapshosts_search_and_print(index_name):

    global es

    # Define the search query (match all in this case)
    query = {
        "query": {
            "match_all": {}
        }
    }

    # Perform the search
    result = es.search(index=index_name, body=query)

    # Extract relevant information from the search result
    hits = result["hits"]["hits"]

    # Prepare data for table
    data = []
    for hit in hits:
        source = hit["_source"]
        data.append(source)

    # Pretty print using rich
    if data:
        console = Console()
        table = Table(show_header=True, header_style="bold white")
        for key in data[0].keys():
            table.add_column(key)
        for item in data:
            table.add_row(*[str(item[column]) for column in data[0].keys()])
        console.print(table)
    else:
        print("No results found.")


def update_snapshot_data(snapshots_data):
    for snapshot in snapshots_data:
        current_snapshot = snapshot["id"]
        current_snapshot_size = fetch_snapshot_size(current_snapshot)
        snapshot['snapshot_size'] = current_snapshot_size


def print_snapshot_table(snapshots_data):
    console = Console()
    table = Table(show_header=True, header_style="bold white")
    for key in snapshots_data[0].keys():
        table.add_column(key)
    for snapshot in snapshots_data:
        table.add_row(*[str(snapshot[column]) for column in snapshots_data[0].keys()])
    console.print(table)

    snapshot_count_total = len(snapshots_data)
    console.print(f"Total Snapshots in database: {snapshot_count_total}")

def elastic_history_list():
    '''
    Shows History from Elastic Search History
    '''

    global es
    global elastic_history_indice

    # Search for the last 50 rows
    res = es.search(
        index=elastic_history_indice,
        body={
            "size": 50,
            "sort": [{"datetime": {"order": "asc"}}]
        }
    )

    # Create a rich table to display the data
    console = Console()
    table = Table(show_header=True, show_lines=True, header_style="bold magenta")
    table.grid_style = "double"
    table.add_column("Datetime")
    table.add_column("Username")
    table.add_column("Status")
    table.add_column("Message")

    for hit in res["hits"]["hits"]:
        source = hit["_source"]
        table.add_row(str(source["datetime"]), source["username"], source["status"], source["message"])

    console.print(table)


def elastic_clear_staged():

    global es
    global elastic_restored_indice
    status = 'init'

    # Search for documents with the specified status
    res = es.search(
        index=elastic_restored_indice,
        body={
            "query": {
                "match": {
                    "status": status
                }
            }
        }
    )

    # Delete the matching documents
    for hit in res["hits"]["hits"]:
        es.delete(index=elastic_restored_indice, id=hit["_id"])
    print("Cleared all staged indices...")


def elastic_ping():
    
    global elastic_host
    global elastic_username
    global elastic_password
    global elastic_port
    global elastic_use_ssl
    global elastic_ca_certs
    global elastic_authentication


    # Setup ES Connection settings to Elasticsearch
    if elastic_authentication == True:
        es = Elasticsearch([elastic_host], http_auth=(elastic_username, elastic_password), port=elastic_port, use_ssl=elastic_use_ssl, verify_certs=False, cacerts=elastic_ca_certs)
    else:
        es = Elasticsearch([elastic_host], port=elastic_port, use_ssl=elastic_use_ssl, verify_certs=False, cacerts=elastic_ca_certs)
    
    # Capture if ES Ping Fails
    if es.ping():
        text = (f" Successfully connected to Elastic Search\n Settings: {elastic_host}:{elastic_port} ssl:{elastic_use_ssl}, Auth: {elastic_authentication}")
        console.print(Panel.fit(text, title="Success"))
        exit(0)

    if not es.ping():     
        text = (f"Elasticsearch cluster is not available with settings: {elastic_host}:{elastic_port} ssl:{elastic_use_ssl}, cacerts={elastic_ca_certs}")
        console.print(Panel.fit(text, title="Connection Error"))
        exit(1)


# Main Script
if __name__ == "__main__":

    # Suppress only the InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    requests.packages.urllib3.disable_warnings(UserWarning)
    requests.packages.urllib3.disable_warnings(DeprecationWarning)


     # Read YAML config files
    script_directory = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(script_directory,'elastic_servers.yml')
    config = read_yaml_file(config_file)
    elastic_servers = read_servers_from_yaml(config_file)

    # Read Configuration Sections
    default_settings = config.get('settings', {})
    server_settings = config.get('servers', [])

    # Set default settings if they aren't set
    elastic_default_timeout = default_settings.get('elastic_default_timeout', 60)
    elastic_restored_indice = default_settings.get('elastic_restored_indice', 'rc_snapshots')
    elastic_history_indice = default_settings.get('elastic_history_indice','rc_snapshots_history')
    elastic_max_shards_per_node = int(default_settings.get('elastic_max_shards_per_node', 1000))
    elastic_restore_batch_size = default_settings.get('elastic_restore_batch_size', 3)
    elastic_ca_certs = default_settings.get('elastic_ca_certs', '/etc/elasticsearch-1/cert.p12')

    # Parse Arguments and setup variables
    parser = argparse.ArgumentParser(prog='snapshotmgr', description='manages snapshots in elasticsearch', epilog='Elastic Snapshot Manager')
    # Adding a positional argument
    parser.add_argument('command', help='Command to run: list, etc.')
    parser.add_argument('optional', nargs='?', help='Regex of pattern to search for')
    parser.add_argument("-debug","--debug", action="store_true", help="Debug Information")
    parser.add_argument("-size", "--size", action="store_true", help="Show Snapshot Size")
    parser.add_argument("-l","--locations", help="Location ( defaults to localhost )", type=str, default='DEFAULT')

    # Arguments
    args = parser.parse_args()
    optional = args.optional
    args_size = args.size
    locations=args.locations.split(',')

    # Create a console object
    console = Console()

    # Capture Elastic Server Settings
    server_config = read_config_server(config_file, locations)
    
    #print(f"Server: {server_config}")
    if (server_config) == None:
        text = (f"Location: {locations} not found.")
        console.print(Panel.fit(text, title="Configuration Error"))
        exit(1)      
    
    # Now Check to see if we passfed Creds via Server config
    elastic_host = server_config['elastic_host']
    elastic_port = server_config['elastic_port']
    elastic_use_ssl = server_config['use_ssl']
    elastic_repository = server_config['repository']
    elastic_authentication = server_config['elastic_authentication']
    elastic_username = server_config['elastic_username']
    elastic_password = server_config['elastic_password']

    # Catch if no arguments are passed.
    valid_commands = ['list', 'list-history', 'list-restored', 'clear-staged', 'show-config', 'help', 'ping']
    if args.command not in valid_commands:
        text = (f"Invalid Command, must be one of: {valid_commands}")
        console.print(Panel.fit(text, title="Command Error"))
        exit(1)      

    # Need to put this first cause no need for ES connection to display help screen.
    if args.command == 'help':
        print('\n')
        table = Table(show_header=True)
        table.add_column('Command')
        table.add_column('Description')
        table.add_row('list', 'List all Snapshots backed up into S3 Database')
        table.add_row('list-history', 'Show history database.')
        table.add_row('list-restored', 'List All Restored Indices.')
        table.add_row('clear-staged', 'Clear all pending restores (in INIT status)')
        table.add_row('show-config', 'Show Configuration File to Screen')
        table.add_row('ping', 'Validate Connection Settings to Elastic Search')
        table.add_row('help', 'This help page!')

        panel = Panel.fit(table, title='\[snapshotmgr.py] - Command Options')
        console.print(panel)
        print('\n')
        exit()

    if args.command == "show-config":

        # Display the YAML data using Syntax
        with open("elastic_servers.yml", "r") as file:
            content = file.read()

        console.print(Syntax(content, "yaml", theme="ansi_dark"))
        exit()


    if args.command == 'ping':
        elastic_ping()


     # Setup ES Connection settings to Elasticsearch
    if elastic_authentication == True:
        es = Elasticsearch([elastic_host], http_auth=(elastic_username, elastic_password), port=elastic_port, use_ssl=elastic_use_ssl, verify_certs=False, cacerts=elastic_ca_certs)
    else:
        es = Elasticsearch([elastic_host], port=elastic_port, use_ssl=elastic_use_ssl, verify_certs=False, cacerts=elastic_ca_certs)
    
    # Capture if ES Ping Fails
    if not es.ping():     
        text = (f"Elasticsearch cluster is not available with settings: {elastic_host}:{elastic_port} ssl:{elastic_use_ssl}, cacerts={elastic_ca_certs}")
        console.print(Panel.fit(text, title="Connection Error"))
        exit(1)

    # Process commands
    if args.command == 'list':

        # Gather Snapshot Data
        snapshots_data = get_snapshots_info(elastic_repository, optional, elastic_host, elastic_port, elastic_use_ssl)

        if args.size == True:
            update_snapshot_data(snapshots_data)
        print_snapshot_table(snapshots_data)

    if (args.command == 'list-restored' or args.command == 'list-status'):
        elastic_restoredsnapshosts_search_and_print(elastic_restored_indice)

 # Process commands
    if args.command == 'list-csv':

        # Gather Snapshot Data
        snapshots_data = get_snapshots_info(elastic_repository, optional, elastic_host, elastic_port)

        if args_size == True:

            # Fetch Snapshot size
            for snapshot in snapshots_data:
                _current_snapshot = snapshot["id"]
                _current_snapshot_size = fetch_snapshot_size(_current_snapshot)

                # Now update the array with the data
                snapshot['snapshot_size'] = _current_snapshot_size

        for snapshot in snapshots_data:
            _snapshot_id = snapshot['id']
            _snapshot_endtime = snapshot['end_time']
            _snapshot_duration = snapshot['duration']
            try:
                _snapshot_size = snapshot['snapshot_size']
            except KeyError:
                _snapshot_size = 0
            print(f"{_snapshot_id},{_snapshot_endtime},{_snapshot_duration},{_snapshot_size}")


    if args.command == 'list-history':
        elastic_history_list()

    if args.command == 'clear-staged':
        elastic_clear_staged()
