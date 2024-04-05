#!/usr/bin/env python3
'''
Restore Snapshot from S3/Minio
Written by Devin Acosta
v 1.2.5 (3/20/2024)
'''

import argparse
from datetime import datetime
from elasticsearch import Elasticsearch, ElasticsearchWarning, exceptions, helpers
from collections import defaultdict
import getpass
import yaml
import re
import warnings
import os
import configparser
import requests
from requests.auth import HTTPBasicAuth
from rich.console import Console
from rich.table import Table
from rich import print
from rich.text import Text
from rich.panel import Panel
import time
import urllib3


# Suppress the UserWarning
warnings.filterwarnings("ignore", category=UserWarning, module="elasticsearch")
warnings.filterwarnings("ignore", category=ElasticsearchWarning)

# Suppress only the InsecureRequestWarning from urllib3 needed for Elasticsearch
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
requests.packages.urllib3.disable_warnings(DeprecationWarning)


# Return Dictionary
def returnDict():
    return {}


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


'''
Function: Take in batched_final (loop through to see if anything to action)
'''
def action_tabdata_anything(batched_final):

    allowed_batched = {}

    for key, values in batched_final.items():
        _action_incluster = values['active_incluster']

        if _action_incluster == False:
            _tmp = { key: values }
            allowed_batched.update(_tmp)
        else:
            pass
        
    # Only Return Indices not already restored
    return allowed_batched
    

'''
Function: Obtain Elasticsearch Cluster status.
'''
def get_elasticsearch_cluster_status():
   
    global es

    # Get cluster health
    cluster_health = es.cluster.health()

    # Extract the cluster status color
    cluster_status = cluster_health['status']

    if cluster_status == "green":
        return cluster_status, f"[green]{cluster_status}[/green]"
    if cluster_status == "yellow":
        return cluster_status, f"[yellow]{cluster_status}[/yellow]"
    if cluster_status == "red":
        return cluster_status, f"[red]{cluster_status}[/red]"


'''
Function: Take in Cluster node data and return cluster total space/free space.
'''
def get_cluster_total_dict(data):

    total_bytes = 0
    available_bytes = 0

    for instance, instance_data in data.items():
        total_bytes += instance_data['total']['total_in_bytes']
        available_bytes += instance_data['total']['available_in_bytes']

    return total_bytes, available_bytes


def get_data_nodes_dict():

    global es

    data_nodes_info = get_data_nodes_info()   

    es_datanodes_data = {}

    for es_data_node in data_nodes_info:

        data_hostname = es_data_node['name']
        data_total = es_data_node['fs']

        es_datanodes_data[data_hostname] = data_total

    return es_datanodes_data


def get_data_nodes_info(allowed_roles=('data_content', 'data_hot', 'data_warm')):
    """
    Retrieve information about data nodes with specific roles.

    Args:
    - es: Elasticsearch instance
    - allowed_roles: Roles to filter data nodes (default includes 'data_content', 'data_hot', 'data_warm')

    Returns:
    - List of data nodes with specified roles
    """
    global es

    # Retrieve information about all nodes
    nodes_info = es.nodes.stats(metric=['fs'])
    
    # Filter data nodes based on allowed roles
    data_nodes_info = [node_info for node_id, node_info in nodes_info['nodes'].items() if any(role in node_info.get('roles', []) for role in allowed_roles)]
    
    return data_nodes_info


'''
Expects input to be a key=>value pair
'''
def processResults(indices,pattern):

    matching_keys = []
    search_pattern = f".*{pattern}.*"
    regex_pattern = re.compile(search_pattern)
    
    # Loop through indices and find matches
    for key in indices.keys():

        if regex_pattern.match(key):
            matching_keys.append(key)

    return matching_keys


def find_closest_file(filenames, date):
    # Convert the date string to a datetime object

    date = datetime.datetime.strptime(date, '%Y.%m.%d')

    
    closest_file = None
    closest_delta = None

    for filename in filenames:

        file_date_str = filename.split("-")[-2]
        file_date = datetime.datetime.strptime(file_date_str, '%Y.%m.%d')

        if file_date > date:
            continue
        
        # Calculate the time delta between the target date and the file date
        delta = date - file_date if date >= file_date else file_date - date
        
        # Update the closest file if necessary
        if closest_file is None or delta < closest_delta:
            closest_file = filename
            closest_delta = delta
    
    return closest_file


# Find records that matches data date passed.
def find_closest_records(name_list, target_date):
    closest_records = []
    closest_date = None

    target_datetime = datetime.strptime(target_date, "%Y.%m.%d")

    for name in name_list:
        match = re.search(r'(\d{4}\.\d{2}\.\d{2})', name)
        if match:
            record_date_str = match.group(1)
            record_datetime = datetime.strptime(record_date_str, "%Y.%m.%d")

            if record_datetime <= target_datetime and (closest_date is None or record_datetime > closest_date):
                closest_date = record_datetime
                closest_records = [name]
            elif record_datetime == closest_date:
                closest_records.append(name)

    return closest_records


def filter_indices_by_date(index_names, target_date):
    matching_indices = []
    try:
        target_date_obj = datetime.strptime(target_date, "%Y.%m.%d")
        target_date_str = target_date_obj.strftime("%Y.%m.%d")
        for index_name in index_names:
            index_parts = index_name.split('.')
            if len(index_parts) == 5:
                index_year = int(index_parts[4])
                index_month = int(index_parts[3])
                index_day = int(index_parts[2])
                index_date_str = f"{index_year:04d}.{index_month:02d}.{index_day:02d}"
                if index_date_str == target_date_str:
                    matching_indices.append(index_name)
    except ValueError:
        print("Invalid target date format. Please use YYYY.MM.DD format.")
    return matching_indices


def get_active_shards_per_node():
    '''
    Function to Return dictionary with hostname: {shards_per_node}
    example: {'aex20-c01-ess16-1': 770, 'aex20-c01-ess11-1': 769 }
    '''

    global es

    try:
        # Use the _cat/shards API to get information about shards
        shards_info = es.cat.shards(format='json', h=['node', 'shard'])

        # Extract data nodes and their active shards count
        active_shards_per_node = {}
        for shard_info in shards_info:
            node_id = shard_info['node']
            shard = shard_info['shard']
            if node_id not in active_shards_per_node:
                active_shards_per_node[node_id] = 1
            else:
                active_shards_per_node[node_id] += 1

        return active_shards_per_node

    except Exception as e:
        print(f"Error: {e}")
        return {}


## Snapshot Functions below
def fetch_snapshot_size(snapshot_name):

        global elastic_host
        global elastic_port
        global elastic_use_ssl
        global elastic_repository
        
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
            response = requests.get(url, verify=False, auth=HTTPBasicAuth(elastic_username, elastic_password))
        else:
            response = requests.get(url, verify=False)
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Parse the response as JSON
        snapshot_status = response.json()

        # Extract the snapshot size in bytes
        snapshot_size_bytes = snapshot_status['snapshots'][0]['stats']['total']['size_in_bytes']

        # Convert bytes to a human-readable format
        snapshot_size_human_readable = format_bytes(snapshot_size_bytes)


        return snapshot_size_bytes

    except requests.exceptions.RequestException as e:
        print(f"Error retrieving snapshot status: {e}")
        return None


def format_bytes(size_in_bytes):
    # Function to convert bytes to a human-readable format
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024.0


def get_datanode_memory_map(node_data):
    """
    Function to take Elasticsearch Node Data and return special Map 
    Map reduces avaialble space by 20% to ensure we never hit 80% used.
    """

    # Create dictionary to return
    datanode_memory_map = {}

    # Loop over Node Data and make memory map
    for item in node_data:
        _data_hostname = item['name']
        _data_total_bytes = int(item['fs']['total']['total_in_bytes'])
        _data_buffer_total = int(_data_total_bytes * .20)
        _data_available_bytes = int(item['fs']['total']['available_in_bytes'])
        # We are going to take available_bytes and minus the .20% to ensure node never hits 80% with restores.
        _data_free = int(_data_available_bytes - _data_buffer_total)
        _node_data = { _data_hostname: { 'total_bytes': _data_total_bytes, 'available_bytes': _data_free }}
        datanode_memory_map.update(_node_data)

    # Return the Mapß
    return datanode_memory_map


def get_active_shards_per_node():

    global es

    try:
        # Use the _cat/shards API to get information about shards
        shards_info = es.cat.shards(format='json', h=['node', 'shard'])

        # Extract data nodes and their active shards count
        active_shards_per_node = {}
        for shard_info in shards_info:
            node_id = shard_info['node']
            shard = shard_info['shard']
            if node_id not in active_shards_per_node:
                active_shards_per_node[node_id] = 1
            else:
                active_shards_per_node[node_id] += 1

        return active_shards_per_node

    except Exception as e:
        print(f"Error: {e}")
        return {}

'''
Gets all the snapshots from cluster via the port specified
'''
def getSnapshots(location,es_port):

    global es

    try:
        # Convert to upper case so that it matches Variable SJC01/IAD01/etc...
        es_host = eval(location.upper())

    except Exception as e:
        print(f"Exception Occured: {e}, please ensure server is listed in elastic_servers.yml")
        exit(1)


    # Connect to Elastic Search
    es_ping = es.ping()
    if (es_ping == False):
        return { location: {} }

    es_snapshots = defaultdict(returnDict)
    es_snapshots_list = []
    cat_snapshots = es.cat.snapshots(format="json")

    # List Indices and return 
    for index in cat_snapshots:
      
        current_snapshot = index['id']
        current_snapshot_totalshards = index['total_shards']
        current_snapshot_status = index['status']
       
        es_snapshots_list.append(index['id']) 
        es_snapshots[location][current_snapshot] = { 'location': location, 'port': es_port, 'status': current_snapshot_status, 'total_shards': current_snapshot_totalshards }
    
    '''
    Now variables es_indices_list and mydict are populated with data 
    '''
    return es_snapshots


'''
Function: Restore Single Snapshot
'''
def restore_elasticsearch_snapshot(snapshot_name):

    global es, elastic_repository

    # Used to determine if snapshot restore was successful
    _snapshot_status = False

    # Establish a connection to the Elasticsearch cluster
    #es = Elasticsearch([{'host': elastic_host, 'port': elastic_port}])
    
    # Define the restore settings
    restore_settings = {
        "indices": "_all",  # Specify the indices to restore, e.g., "index1,index2"
        "ignore_unavailable": True,
        "include_global_state": False
    }
    
    try:
        # Perform the restore operation
        response = es.snapshot.restore(repository=elastic_repository, snapshot=snapshot_name, body=restore_settings)
        
        # Check the response for success
        if response.get("accepted"):
            _snapshot_msg = (f"Snapshot '{snapshot_name}' restore has been accepted and started.")
        else:
            _snapshot_msg = (f"Snapshot restore request for '{snapshot_name}' was not accepted.")
    
    except exceptions.TransportError as e:
        if e.error == "snapshot_restore_exception" and "an open index with same name already exists in the cluster" in e.info['error']['reason']:
            _snapshot_msg = (f"Error: An index with the same name already exists in the cluster. Close, delete, or restore with a different name.")
        else:
            _snapshot_msg = (f"An error occurred: {e}")
    
    except Exception as e:
        _snapshot_msg = (f"An unexpected error occurred: {e}")

    return _snapshot_msg

'''
Function to remove ILM policy, so that when we restore it doesn't get deleted right away.
'''
def remove_ilm_policy(index_name, elastic_host, elastic_port):

    global es
    # Define the Elasticsearch client
    #es = Elasticsearch([{'host': elastic_host, 'port': elastic_port}], use_ssl=elastic_use_ssl, verify_certs=False)  # Update with your Elasticsearch cluster details

    # Construct the URL for the _ilm/remove API
    url = f'/{index_name}/_ilm/remove'

    try:
        # Send a POST request to remove the ILM policy
        response = es.transport.perform_request('POST', url)
    
        if response['has_failures'] == False:
            return (f"Removed ILM policy from index '{index_name}'.")
        else:
            return(f"Failed to remove ILM policy from index '{index_name}'.")
    except exceptions.RequestError as e:
        return(f"Failed to remove ILM policy from index '{index_name}': {e}")


'''
Function to remove Hidden Flag on indice
'''
def elastic_unhide_index(index_name, elastic_host, elastic_port):
    
    global es
    # Define the Elasticsearch client
    #es = Elasticsearch([{'host': elastic_host, 'port': elastic_port}], use_ssl=elastic_use_ssl, verify_certs=False)  # 

    # Explicitly set the 'index.hidden' property to False for the restored index
    update_settings = {
        'settings': {
            'index': {
                'hidden': False
            }
        }
    }

    es.indices.put_settings(index=index_name, body=update_settings)
    return(f"Set Elastic Indice Hidden Status to False")


'''
Elasticsearch functions to write/read from ES
'''

def create_es_document(index_name, os_username):
    today_date = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ')

    document = {
        'index_name': index_name,
        '_id': index_name,
        'osuser': os_username,
        'restore_date': today_date,
        'last_updated': today_date,
        'status': 'init'
    }

    return document


def es_write_and_validate_document(document):
    """
    Writes the document to Elasticsearch and validates its successful creation.

    Args:
        document: Dictionary containing the document data.

    Returns:
        True if writing succeeded, False otherwise.
    """

    global es
    global elastic_restored_indice

    response = helpers.bulk(es, [document], index=elastic_restored_indice)

    if response[0] == 1:
        return True
    else:
        print("Error: Failed to write document to index")
        return False


def index_document_unique(document):

    global es
    
    index_name_value = document['index_name']
    #print(f"Document name: {index_name_value}")

    # Check for existing documents with the same index_name
    query = {
        'query': {
            'term': {
                'index_name.keyword': index_name_value
            }
        }
    }
    existing_docs = es.search(index='rc_snapshots', body=query)['hits']['hits']

    if existing_docs:
        return(f"Document with index_name '{index_name_value}' already exists. Skipping indexing.")

    # Use update API with doc_as_upsert to ensure uniqueness
    es.update(
        index='rc_snapshots',
        id=index_name_value,  # Use index_name as the document ID for convenience
        body={
            'doc': document,
            'doc_as_upsert': True
        }
    )
    return(f"Document with index_name '{index_name_value}' indexed successfully.")


'''
Function to just create Elastic Document to record that we restored an indice.
'''
def elastic_record_index(index_name):


    os_username = getpass.getuser()
    _success = es_write_and_validate_document(create_es_document(index_name, os_username))
    if _success:
        return f"Recorded indice to Elasticsearch."
    else:
        return f"Failed to write indice to Elasticsearch."

    # Return Status
    return _status


def check_document_exists(document_id):

    global es
    global elastic_restored_indice

    # Check if document exists
    try:
        result = es.get(index=elastic_restored_indice, id=document_id)
        return True, result['_source']
    except:
        return False, None


def elastic_document_decide_action(doc_indice_name):
    
    # Check to see if document already exists
    _doc_exists, _doc_data = check_document_exists(doc_indice_name)
    #print(f"Document Exists?: {_doc_exists}, Data: {_doc_data}")
    if _doc_exists == True:
        # Now Get Source Data to Determine what to do next
        _result_status = _doc_data['status']
        if _result_status == "cancelled":
            # Update Doc with Status INIT
            elastic_update_index(doc_indice_name, 'init')
            return "Updated to INIT"
    elif _doc_exists == False:
        elastic_record_index(doc_indice_name)
        return "Inserted new Doc"


def delete_document_by_field_value(field_name, field_value):
    """
    Searches for a document in an Elasticsearch index by a specific field value and deletes it.

    Parameters:
    - index_name: The name of the Elasticsearch index.
    - field_name: The name of the field to search for.
    - field_value: The value to match in the specified field.
    - es: The Elasticsearch handle

    Returns:
    - True if the document is successfully deleted, False otherwise.
    """

    global es
    global elastic_restored_indice

    try:
        # Search for the document
        query = {"query": {"match": {field_name: field_value}}}
        result = es.search(index=elastic_restored_indice, body=query)

        # Check if any documents were found
        if result["hits"]["total"]["value"] > 0:
            # Extract document ID
            doc_id = result["hits"]["hits"][0]["_id"]

            # Delete the document
            es.delete(index=elastic_restored_indice, id=doc_id)

            return True
        else:
            return False
    except Exception as e:

        print(f"An error occurred: {e}")
        return False


def find_document_id(field, value):
    """
    Find the document ID based on a field value in Elasticsearch index.

    Parameters:
        - field: Field name to search for.
        - value: Value of the field to search for.
    """

    global elastic_restored_indice

    query = {
        "query": {
            "match": {
                field: value
            }
        }
    }

    print("Query: ", query)

    # Search for the document
    response = es.search(index=elastic_restored_indice, body=query)

    # Extract the document ID from the search response
    document_id = response['hits']['hits'][0]['_id']

    return document_id


def elastic_update_index(index_name, status):
    """
    Update a document in Elasticsearch index based on the hostname key.
    
    Parameters:
        - index_name: Name of Snapshot Index to update.
        - status : Status to set on the document.
    """
    global es
    global elastic_restored_indice
    
    today_date = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ')

    update_data = {
        "doc": {
            "last_updated": today_date,
            "status": status
        }
    }

    # Update the document in the index
    response = es.update(index=elastic_restored_indice, body=update_data, id=index_name)

    return response

'''
Function to set Indice to have no replicas for faster recovery.
'''
def set_index_settings(index_name):

    global es
    # Define the Elasticsearch client
    #es = Elasticsearch([{'host': elastic_host, 'port': elastic_port}])  # 

    settings = {
        "settings": {
            "number_of_replicas": 0
        }
    }

    try:
        # Update the index settings
        es.indices.put_settings(index=index_name, body=settings)
        return(f"Settings updated for index '{index_name}': 1 shard, 0 replicas.")
    except Exception as e:
        return(f"Error updating settings for index '{index_name}': {e}")


'''
Function: Process Batch of Snapshots
'''
def process_batch(batch):

    #print(f"[process_batch] Batch: {batch}")

    for key, values in batch.items():

        snapshot = f"snapshot_{key}"
        snapshot_location = str(values['location'])
        snapshot_port = values['port']
        snapshot_name_minus = key

        # Restore Snapshot
        status_bar_update(f"Restoring Snapshot: {snapshot} | {snapshot_location}:{snapshot_port}")
        _restore_status = restore_elasticsearch_snapshot(snapshot)
        status_bar_update(_restore_status)

        #Remove the ILM policy so it doesn't get deleted by ES.
        _rilm_status = remove_ilm_policy(snapshot_name_minus, snapshot_location, snapshot_port)
        status_bar_update(_rilm_status)       

        # Set Elastic Indice Settings
        _isettings_status = set_index_settings(snapshot_name_minus)
        status_bar_update(_isettings_status)
        
        # We need to unhide the Restored Indice to make available within ES
        _unhide_status = elastic_unhide_index(snapshot_name_minus, snapshot_location, snapshot_port)
        status_bar_update(_unhide_status)
        
        # Lets Record the Indice to the rc_snapshots indice to future monitoring.
        _record_status = elastic_record_index(snapshot_name_minus)
        status_bar_update(_record_status)

        # Set Status to restored, cause once ILM is removed it will complete the restoration process
        status_bar_update(f"[status] Updating Status for : {snapshot_name_minus}")
        _restored_status = elastic_update_index(snapshot_name_minus, 'restored')
        status_bar_update(f"[status] Update Response: {_restored_status}")

        elasticsearch_history_log("INFO", f"Restored Snapshot {snapshot}")


'''
Function: Restore Indice in Batches to not overwhelm cluster.
'''
def process_restore_in_batches(indices_to_restore, batch_size=None):

    if batch_size == None:
        global elastic_restore_batch_size
        batch_size = elastic_restore_batch_size


    keys_list = list(indices_to_restore.keys())

    status_bar_update(f"Using Batch Size: {batch_size}")

    for i in range(0, len(keys_list), batch_size):
        batch_keys = keys_list[i:i + batch_size]
        batch = {key: indices_to_restore[key] for key in batch_keys}
        

        status_bar_update(f"Processing Batch: {batch}")
        elasticsearch_history_log('INFO', f"Processing Batch: {batch}")

        # Now that we have the batch to process, let's get processing
        process_batch(batch)

        # Introduce a wait time between batches
        # Wait for all green before starting next batch.
        loop_check_indices_status(batch)


'''
Function: Restore Snapshots
'''
def restoreSnapshots(batched_final):

    _restore_batch = {}

    for snapshot in batched_final:
        snapshot_data = batched_final[snapshot]
        _tmp_location = snapshot_data['location'].upper()
        snapshot_location = eval(str(snapshot_data['location'].upper()))
        snapshot_port = snapshot_data['port']
        snapshot_name_minus = snapshot.strip("snapshot_")

        _restore_batch[snapshot_name_minus] = { "location": snapshot_location, "port": snapshot_port}

        #restore_status = restore_elasticsearch_snapshot(snapshot, repository, snapshot_location, snapshot_port)

        # Batching All Successful Snapshots so we can remove ILM policy afterwards.
        #if restore_status == True:
        #    _restore_batch[snapshot_name_minus] = { "location": snapshot_location, "port": snapshot_port}


    # Start Restore in Batches
    process_restore_in_batches(_restore_batch)

    ## Old Code use to be here.. was moved into step above.


def tabData(data):

    tabulate_out = []
    for indice in data:
        snapshot_location = f"{data[indice]['location']}/{data[indice]['port']}"
        indice_status = data[indice]['active_incluster']
        indice_totalshards = data[indice]['total_shards']
        _indice_size = format_bytes(data[indice]['size']).ljust(10)
        if 'GB' in _indice_size:
            _indice_size_text = f"[u]{_indice_size}[/u]"
        else:
            _indice_size_text = f"{_indice_size}"
        #indice_size = format_bytes(data[indice]['size']).ljust(10)

        tab_data = [snapshot_location,indice,indice_totalshards,_indice_size_text,indice_status]
        tabulate_out.append(tab_data)
     
    return tabulate_out


def uniquePatterns(filenames):
    ret_filenames = []
    for filename in filenames:
        #match = re.search(r'logs-(.*?)-\d{4}\.\d{2}\.\d{2}', filename)
        match = re.search(r'filebeat-(.*?)-\d{4}\.\d{2}\.\d{2}', filename)

        if match:
            result = f"logs-{match.group(1)}"
            ret_filenames.append(result)
    
    ret_filenames = list(set(ret_filenames))
    return ret_filenames


# Can Restore Snapshot
def validation_test_canrestoresnapshot_memorymap(snapshot_data):
    """
    Check if a given Elasticsearch snapshot can be safely restored into the cluster.

    Args:
    - snapshot_data: Snapshot data, including 'size'

    Returns:
    - True if the snapshot can be safely restored, False otherwise
    """

    global global_datanode_memory_map

    # Loop over memory map and find node with disk space
    for data_key, data_values in global_datanode_memory_map.items():

        total_node_storage = int(data_values['total_bytes'])
        available_node_storage = int(data_values['available_bytes'])

        # Check if there is enough free space on the node for the snapshot size
        if available_node_storage > snapshot_data['size']:

            # Subtract the disk space from available space.
            global_datanode_memory_map[data_key]['available_bytes'] -= snapshot_data['size']

            return True

    # If none of the data nodes have enough storage, return False
    return False


def validation_batched_final_storage(batched_final):
    '''
    Function takes the list of indices to restore and compares the indices to ensure each can be restored

    Returns 2 arrays: Passed, Failed
    '''
    
    # Create dictionary of passed indices
    indices_passed = []
    indices_failed = []
    global global_datanode_memory_map

    for indice, indice_values in batched_final.items():
        _indice_size = indice_values['size']
        _indice_dict = { 'size': _indice_size }
        _enough_storage = validation_test_canrestoresnapshot_memorymap(_indice_dict)

        if _enough_storage == True:
            indices_passed.append(indice)
        elif _enough_storage == False:
            indices_failed.append(indice)

    # Return array of Indices Passed/Indices Failed.
    return indices_passed, indices_failed
    

def validation_test_shards_free_in_cluster(shards_count_to_restore):
 
    global elastic_max_shards_per_node

    # Check if we have enough available shards free in cluster to restore so we don't overload cluster.
    # Loop over shards per node (ensure we are good there)
    _elastic_shards_per_node = get_active_shards_per_node()
    # Test Shards per node is under our limit (elastic_max_shards_per_node)
    _tf_results_max_shards_per_node = any(value >= elastic_max_shards_per_node for value in _elastic_shards_per_node.values())
    _results_count_shards_in_cluster = sum(_elastic_shards_per_node.values())
    _results_total_shards_in_cluster = len(_elastic_shards_per_node) * elastic_max_shards_per_node
    _results_left_shards_to_use = (_results_total_shards_in_cluster - _results_count_shards_in_cluster)

    #print(f"Total Shard that can exist in cluster is: {_results_total_shards_in_cluster}")
    #print(f"Total Shards left to keep cluster happy: {_results_left_shards_to_use}")
    #print(f"{_elastic_shards_per_node}, {_tf_results_max_shards_per_node}, {_results_count_shards_in_cluster}")

    # Return True if it Passed, safe to continue to next check
    if shards_count_to_restore < _results_left_shards_to_use:
        return True
    else:
        return False

def restore_validation_cluster_tests(batched_final, elastic_nodes_data_dict, shards_count_to_restore):
    '''
    Function: Validate of Cluster resources (shards available/disk space) for recovery
    '''

    global console

    green_checkmark = Text("✔", style="bold green")
    red_failed_icon = Text("✖", style="bold red")


    with console.status("[bold green] Validating Cluster to handle restores.."):
        
        # Validate that cluster has enough shards to handle restoration request.
        _validate_shards_in_cluster = validation_test_shards_free_in_cluster(shards_count_to_restore)

        # Set Validation Output
        if _validate_shards_in_cluster == True:
            _shards_validation_chk = True
        else:
            _shards_validation_chk = False

        #print(f"Results of Shards Test: {_validate_shards_in_cluster}")

        # Validate that we can restore Snapshot based upon size of indice.
        _indices_passed_storage_chk, _indices_failed_storage_chk = validation_batched_final_storage(batched_final)

        if len(_indices_failed_storage_chk) == 0:
            _indices_storage_chk = True
        else:
            _indices_storage_chk = False


    # Check if Cluster is Green
    cluster_status, cluster_text = get_elasticsearch_cluster_status()
    if cluster_status == "green":
        print(f"[green]{green_checkmark} Cluster Health Check: Passed ({cluster_text})[/green]")
        cluster_green_state = True
    elif cluster_status == "yellow":
        print(f"[yellow] Cluster is Yellow, please wait until Green.[/yellow]")
        exit(1)
    elif cluster_status == "red":
        print(f"[red] Cluster is RED, aborting...[/red]")
        exit(1)

    if _shards_validation_chk == True:
        print(f"[green]{green_checkmark} Shard Allocation Check: Passed[/green]")
    else:
        print(f"[red]{red_failed_icon} ALERT: Aborting Restore, Cluster Shard Check has FAILED!!![/red]")
        exit(1)

    if _indices_storage_chk == True:
        print(f"[green]{green_checkmark} Storage Allocation Checks: Passed[/green]")
    else:
        print(f"[red] Storage Checks have failed, exiting...[/red]")
        exit(1)


'''
Function to wait for all indices to go green and to return the time it took.
'''
def loop_check_indices_status(batched_indices):
    """
    Check the status of Elasticsearch indices and return the time it takes for all indices to reach 'green'.

    Parameters:
    - es : Elasticsearch handle
    - indices (list): List of Elasticsearch indices to be checked.

    Returns:
    - float: Time in seconds it took for all indices to reach 'green'.
    """

    global es

    start_time = time.time()

    # Dictionary to keep track of the status of each index
    index_statuses = {index: 'yellow' for index in batched_indices}

    # Check status of each index
    while any(status != 'green' for status in index_statuses.values()):

        # Show Status
        status_bar_update("Waiting for indices to go 'green'...")

        for index in batched_indices:

            # Check if the index status is 'green'
            if index_statuses[index] == 'green':
                continue

            try:
                # Get the index health
                index_health = es.cluster.health(index=index, wait_for_status='green', request_timeout=10)
                # Update the index status
                index_statuses[index] = index_health['status']
            except exceptions.ConnectionTimeout as e:
                pass
                # Log the error (optional)
                # Handle the error as needed, e.g., ignore or log
            except Exception as e:
                pass
                #print(f"Error while checking index {index}: {e}")
                # Handle the error if necessary

        # Wait for a short period before checking again
        time.sleep(10)

    end_time = time.time()
    elapsed_time = end_time - start_time

    return elapsed_time

'''
We need to convert from dictionary to array in order for the next function to work.
'''
def process_batch_waitforgreen(batched):
    
    global es

    print(f"Batched: {batched}")
    indices_to_watch = []
    for item in batched:
        _name_minus = item.strip("snapshot_")
        indices_to_watch.append(_name_minus)

    elapsed_time = loop_check_indices_status(es, indices_to_watch)
    print(f'Time taken for indices to reach "green" status: {elapsed_time:.2f} seconds')


'''
Function: Obtain all indices in cluster for use later to prevent restore errors.
'''
def get_all_indices():
    global es

    try:
        # Get all indices using the _cat indices API
        indices = es.cat.indices(h='index', format='json')
        return [index['index'] for index in indices]
    except Exception as e:
        print(f"Error: {e}")
        return []


def check_indice_active_incluster(indice):
    
    global elastic_all_active_indices

    if indice in elastic_all_active_indices:
        return True
    else:
        return False


'''
Function to update the status bar with latest data.
'''
def status_bar_update(message):
    global console

    with console.status(f"[bold green]{message}") as status:
        time.sleep(0.5)
        console.log(message)


def count_documents_with_status_init():
    '''
    Function to see if any staged indices are being ready for recovery.
    Returns count of docs with status=init.
    Used to prevent 2nd user from restoring into cluster at same time.
    '''
    global es
    global elastic_restored_indice

    # Query to count documents with status='init'
    query = {
        "query": {
            "match": {
                "status": "init"
            }
        }
    }

    # Execute the search
    response = es.search(index=elastic_restored_indice, body=query)

    # Get the count from the response
    count = response['hits']['total']['value']
    return count


def elasticsearch_history_log(status, message):

    global es
    global os_username
    global elastic_history_indice

    # Create a document to index
    document = {
        'datetime': datetime.now(),
        'username': os_username,
        'status': status,
        'message': message
    }

    # Index the document
    es.index(index=elastic_history_indice, body=document)


# Main Script
if __name__ == "__main__":

    '''
    Load Variables from elastic_servers.yml
    Please Ensure All hostnames are CAPITAL in the elastic_servers.yml
    '''

    # Start Status Console
    console = Console()

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


    # Parse Arguments and setup variables
    parser = argparse.ArgumentParser()
    parser.add_argument("-debug","--debug", action="store_true", help="Debug information")
    parser.add_argument("-d","--date", help="Date of indice to restore ( Format: YYYY.mm.dd )", required=True)
    parser.add_argument("-c","--component", help="Component (i.e.: logs-XXX )", required=True)
    parser.add_argument("-l","--locations", help="Location ( defaults to localhost )", type=str, default='DEFAULT')
    parser.add_argument("-r","--repository", help="Snapshot repository to use", default="aex20-repo")
    parser.add_argument("-t","--time", action="store_true", help="Time entire restore until all restored indices are Green")
    parser.add_argument("-b","--batch", type=int, default='3', help="Set Restore Batch Size to this value...")
    parser.add_argument("-m","--maxshards", type=int, default=None, help="Max Shards per node setting")
    parser.add_argument("-n","--dryrun", action="store_true", help="Perform Dry Run, do not execute.", default=False)

    # Capture Passed Arguments into variables
    args = parser.parse_args()
    locations=args.locations.split(',')
    dt=args.date
    comp=args.component
    repository=args.repository
    wait_until_finished=args.time
    dryrun=args.dryrun


    # Capture Elastic Server Settings from YAML
    server_config = read_config_server(config_file, locations)
    if (server_config) == None:
        text = (f"Location: {locations} not found.\nPlease check your elastic_settings.yml config file.")
        console.print(Panel.fit(text, title="Configuration Error"))
        exit(1)

    # Get Values that May or May Not Exist    
    elastic_host = server_config['elastic_host']
    elastic_port = server_config['elastic_port']
    elastic_use_ssl = server_config['use_ssl']
    elastic_repository = server_config['repository']
    elastic_authentication = server_config['elastic_authentication']
    elastic_username = server_config['elastic_username']
    elastic_password = server_config['elastic_password']

    # Determine if we are using Elasticsearch Authentication
    if ((elastic_username != None) and (elastic_password != None)):
        elastic_authentication = True
    else:
        elastic_authentication = False

    # Load Servers into memory for easy access.
    for key in elastic_servers:
        _value = elastic_servers[key]
        exec(f"{key} = '{_value}'")


    # Capture Current Username
    os_username = getpass.getuser()    

    # If maxshards passed by CLI, use it instead of default setting
    if args.maxshards != None:
        elastic_max_shards_per_node = args.maxshards


    try:
        # Define the Elasticsearch client
        if elastic_authentication == True:
            es = Elasticsearch([elastic_host], http_auth=(elastic_username, elastic_password), port=elastic_port, use_ssl=elastic_use_ssl, verify_certs=False, timeout=elastic_default_timeout)
        else:
            es = Elasticsearch([elastic_host], port=elastic_port, use_ssl=elastic_use_ssl, verify_certs=False, timeout=elastic_default_timeout)
        es_ping = es.ping()
  
        if es_ping == False:
            text = (f"Host: {server_settings[0]['hostname']}:{server_settings[0]['port']}, SSL: {server_settings[0]['use_ssl']}\nCannot talk to ElasticSearch Cluster, please check your connection.")
            console.print(Panel.fit(text, title="Connection Error"))
            exit(1)

    except ConnectionError: 
        print(f"ERROR: An error occurred trying to connect to the ElasticSearch Cluster.")
        exit(1)


    # Log Query to History
    elasticsearch_history_log('INFO', f"Query: Component: {comp}, Date: {dt}, Locations: {locations}")    

    # Get All Indices in Clsuter
    elastic_all_active_indices = get_all_indices()
    
    # Loop over all the servers now
    batched_final = defaultdict(dict)
    for location in locations:

        # Get Indices (from all ports for the Instance)
        rc_snapshots_1 = getSnapshots(location,9201)
        rc_snapshots_2 = getSnapshots(location,9202)
        rc_snapshots_3 = getSnapshots(location,9203)
        rc_snapshots_4 = getSnapshots(location,9200)
   
        # Create new dictionary and append results of last step.
        merged_snapshots = {}
        merged_snapshots.update(rc_snapshots_1[location])
        merged_snapshots.update(rc_snapshots_2[location])
        merged_snapshots.update(rc_snapshots_3[location])
        merged_snapshots.update(rc_snapshots_4[location])

        # Look for matches of snapshots from all merged (ports/server) combo
        name_matching_snapshots = processResults(merged_snapshots,comp)
        matching_snapshots = find_closest_records(name_matching_snapshots, dt)


        '''
        Create (batched_final) and append all indices so we can open those at the end.
        '''
        if (len(matching_snapshots) > 0 ):
            for indices in matching_snapshots:

                # Check to see if already restored to prevent restore error.
                _indice_minus = indices.strip("snapshot_")
                _already_restored = check_indice_active_incluster(_indice_minus)
                _indice_size = fetch_snapshot_size(indices)
                _indice_total_shards = merged_snapshots[indices]['total_shards']
                #print(f"Indice: {_indice_minus}, Restored: {_already_restored}")

                port = merged_snapshots[indices]['port']
                batched_final[indices] = { "location": location, "port": port, "active_incluster": _already_restored, "size": _indice_size, "total_shards": _indice_total_shards }

    #print(f"Batched Final: {batched_final}")

    # Now Display Tab Data to screen on what we plan to restore.
    tabdata = tabData(batched_final)
    # {'snapshot_.ds-aex20-c01-logs-gas-k8s-init-instrumentation-2023.12.05-000138': {'location': 'DEFAULT', 'port': 9200, 'active_incluster': True, 'size': 1066021, 'total_shards': '1'}, 'snapshot_.ds-aex20-c01-logs-gas-k8s-gas-healthcheck-2023.12.05-000173': {'location': 'DEFAULT', 'port': 9200, 'active_incluster': False, 'size': 869459448, 'total_shards': '1'}
 
    # Create Data Node Memory Map
    global_datanode_memory_map = get_datanode_memory_map(get_data_nodes_info())

    if len(tabdata) == 0:
        text = (f"[blue]No Snapshots Matching Query[/blue]\nDate: [blue]{dt}[/blue], Comp/RegEX: [blue]{comp}[/blue]")
        console.print(Panel.fit(text, title="Notice"))
        exit()   

    print("\n")

    elasticsearch_status, elasticsearch_status_text = get_elasticsearch_cluster_status()
    elasticsearch_shards_by_host = get_active_shards_per_node()
    elasticsearch_data_node_count = len(elasticsearch_shards_by_host)
    es_shards_avg_by_host = sum(elasticsearch_shards_by_host.values()) / elasticsearch_data_node_count if elasticsearch_data_node_count > 0 else 0
    # Calculate total size for entries with 'active_incluster' set to False
    total_size_inactive = sum(entry['size'] for entry in batched_final.values() if not entry['active_incluster'])
    total_shards_inactive = sum(int(entry['total_shards']) for entry in batched_final.values() if not entry['active_incluster'])
    # Count the number of items where 'active_incluster' is False
    num_inactive_items = sum(1 for entry in batched_final.values() if not entry['active_incluster'])
    # Cluster Total Disk Space / Available Space
    elastic_nodes_data_dict = get_data_nodes_dict()
    cluster_total_bytes, cluster_available_bytes = get_cluster_total_dict(elastic_nodes_data_dict)

    table_text = (f"[bold cyan]Restore Plan:[/bold cyan] [green]{num_inactive_items}[/green][bold cyan] indice(s)[/bold cyan], [green]{total_shards_inactive}[/green][bold cyan] shard(s), with total space of :[/bold cyan][green] {format_bytes(total_size_inactive)}[/green]")
    elasticsearch_history_log('INFO', table_text)

    # Display some Cluster info to screen
    cluster_text = (f"ES Cluster Health: {elasticsearch_status_text}, Data Nodes: {elasticsearch_data_node_count} ({int(es_shards_avg_by_host)}), Storage: avail: {format_bytes(cluster_available_bytes)} / Total: {format_bytes(cluster_total_bytes)}")

     # Create Rich Table
    table = Table(title="Snapshot matches", style="bold cyan", caption_style="cyan italic", caption=f"{table_text}\n{cluster_text}", header_style="white")
    # Add Columns
    table.add_column("Repository", style="cyan", justify="left")
    table.add_column("Snapshot Name", style="green", justify="left")
    table.add_column("Count", justify="right")
    table.add_column("Size", justify="right")
    table.add_column("Restored", style="magenta", justify="right")
    # Now Loop through Rows
    for row in tabdata:
        # Convert boolean value to string before adding to the table
        row[-1] = str(row[-1])
        table.add_row(*row)

    # Print -Table- to screen
    console.print(table)
    print("\n")

    if elasticsearch_status != "green":
        text = (f"ElasticSearch status is: [yellow]{elasticsearch_status}[/yellow], please retry when Green.")
        console.print(Panel.fit(text, title="Notice"))    
        exit()

    # Final_action_data: {'snapshot_.ds-aex20-c01-logs-gpn-k8s-access-2024.01.05-000051': {'location': 'DEFAULT', 'port': 9200, 'active_incluster': False, 'size': 443658873, 'total_shards': '1'}
    final_action_data = action_tabdata_anything(batched_final)

    # Exit restore if all indices have already been restored.
    if len(final_action_data) == 0:
        text = (f"All Snapshots have already been restored.")
        console.print(Panel(text, title="Script Exiting"), width=80)      
        exit()

    # Exit script is another user is restoring data
    docs_init_count = count_documents_with_status_init()
    if docs_init_count > 0:
        print(f"[red] ERROR:[/red] [white][underline]Another RESTORE job is running to restore snapshots[/underline], please wait for that to complete before trying again.[/white]")
        print(f"[white] Found [/white][blue] {docs_init_count} indice(s) [/blue][white] in PENDING RESTORE STATUS...[/white]\n")
        elasticsearch_history_log('ERROR', f"ERROR: Another RESTORE job is running... exiting script.")
        exit(1)

    # Validate that we have enough Shards / Storage in Cluster before proceeding
    restore_validation_cluster_tests(batched_final, elastic_nodes_data_dict, total_shards_inactive)

    # Only Log and continue if DRYRUN not selected.
    if dryrun == False:
        # Create INIT log entry for indice
        for key, values in final_action_data.items():
            _active_incluster = values['active_incluster']
            # We are only going to set INIT on indices not already restored in database.
            if _active_incluster == False:
                _indice_name = key.strip("snapshot_")
                # Write Record to DB as INIT.
                _eri_status = elastic_document_decide_action(_indice_name)
                #print(f"{key} {_eri_status}")
    else:
        # Going To Exit because Dry Run was specified.
        print("Detected Dry Run, exiting script now...")
        elasticsearch_history_log('INFO',f"Operations cancelled because of DRYRUN detected.")
        exit()

    try:
        while True:
            print("Only Indices with Restored status of [green]'False'[/green] will be restored.")
            answer = input("Would you like to restore these Snapshots? [y/n]: ").lower()
            if (answer == 'y' or answer == 'yes'):
                elasticsearch_history_log('INFO', f"User Accepted Restore, restore in progress...")
                restoreSnapshots(final_action_data)
                # Now Break out of this loop
                break
            elif (answer == 'n' or answer == 'no'):

                # Remove Instances from table as no longer going to restore.
                for key, values in final_action_data.items():
                    _active_incluster = values['active_incluster']
                    # We are only going to set INIT on indices not already restored in database.
                    if _active_incluster == False:
                        _indice_name = key.strip("snapshot_")
                        # Write Record to DB as INIT.
                        elastic_update_index(_indice_name, 'cancelled')

                elasticsearch_history_log('INFO', f"User cancelled restore operations!")
                print("\nYou have aborted operations!\n")
                exit()
            else:
                print("Invalid Input, Please try again.")
    except KeyboardInterrupt:
        # Remove Instances from table as no longer going to restore.
        for key, values in final_action_data.items():
            _active_incluster = values['active_incluster']
            # We are only going to set INIT on indices not already restored in database.
            if _active_incluster == False:
                _indice_name = key.strip("snapshot_")
                # Write Record to DB as INIT.
                elastic_update_index(_indice_name, 'cancelled')

        elasticsearch_history_log('INFO', f"User cancelled restore operations!")
        print("You have aborted operations!")
        exit()


    # If Asked to do timing process that now.
    if wait_until_finished == True:
        print(f"You have asked to show timings..")
        process_batch_waitforgreen(batched_final)

    elasticsearch_history_log('INFO', f"Script has completed successfully!")
    print("\n\nScript has completed!")