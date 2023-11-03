#!/usr/bin/env python3
'''
Script to check if cold indices are snapshotted to S3, if not it will snapshot them so we have backups.
Written by Devin Acosta
Version: 1.0.0 (09/08/2023)
- Added some fixes to run out of cron.
- Added .tasks to exclude list.
- Made Repo a variable (not hard coded)
'''

from elasticsearch import Elasticsearch, RequestsHttpConnection
from elasticsearch.exceptions import ConnectionError, TransportError

import argparse
import configparser
import logging
import os
import re
import requests
import urllib3
import warnings

# Suppress the UserWarning
warnings.filterwarnings("ignore", category=UserWarning, module="elasticsearch")

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


# Function to take string and pattern and return true if match is found
def pattern_matches(data, regex_pattern):
    """
    Check if the given string matches the provided regex pattern.
    
    Args:
        string (str): The input string to be checked.
        pattern (str): The regex pattern to match against.
        
    Returns:
        bool: True if the string matches the pattern, False otherwise.
    """
    if re.match(regex_pattern, data):
        return True
    else:
        return False

# Function to check if the index name matches any of the regex patterns
def index_matches_patterns(index_name, regex_patterns):
    return any(re.search(pattern, index_name) for pattern in regex_patterns)

def has_matching_element(arr, regex_pattern):
    """
    Check if there is at least one element in the array that matches the regular expression pattern.

    Parameters:
        arr (list): An array of strings to be checked for matches.
        regex_pattern (str): The regular expression pattern to match against.pytho

    Returns:
        bool: True if there is a matching element, False otherwise.
    """
    for string in arr:
        if re.search(regex_pattern, string):
            return True
    return False

# Function to get a list of all snapshots
# Returns: ['snapshost_.ds-ams02-c01-logs-avp-main-2023.07.05-000064', 'snapshost_.ds-ams02-c01-logs-avp-main-2023.07.08-000065', 'snapshost_.ds-ams02-c01-logs-jwl-stat-api-2023.07.09-000085']
def get_all_snapshots():
    snapshots = []
    cat_snapshots = es.cat.snapshots(format="json")
    
    for snapshot_info in cat_snapshots:
        snapshots.append(snapshot_info['id'])
    
    return snapshots

# Function take list of snapshots and list of cold indices and return ones needing snapshot
# Return _snapshots (array of indices needing backedup)
def get_cold_indices_needing_backedup(cold_indices,snapshots,regex_pattern):
    _snapshots = []
    #print("snapshots", snapshots)

    for cold_index in cold_indices:
        _cisnap = f"snapshot_{cold_index}"

        result = has_matching_element(snapshots,_cisnap)

        if result == True:
            continue
        else:
            # Check Regex Pattern to see if we want to include it or not
            if pattern_matches(cold_index,regex_pattern):
                _snapshots.append(cold_index)
        

    return _snapshots

# Function to actually create the snapshot
def create_elasticsearch_snapshot(es_client, index_name, snapshot_name, repository_name):
    """
    Create a snapshot of an Elasticsearch index.

    Parameters:
        es_client (Elasticsearch): An instance of the Elasticsearch client.
        index_name (str): The name of the index to be snapshotted.
        snapshot_name (str): The name to be given to the snapshot.
        repository_name (str): The name of the snapshot repository.

    Returns:
        dict: The response from Elasticsearch containing information about the snapshot.
    """
    try:
        # Create the snapshot request
        snapshot_body = {
            "indices": index_name,
            "ignore_unavailable": True,
            "include_global_state": False
        }
        
        # Start the snapshot process
        response = es_client.snapshot.create(repository=repository_name, snapshot=snapshot_name, body=snapshot_body)
        return True, response

    except Exception as e:
        logging.warning(f"Error creating snapshot: {e}")
        return None, None

# Backup Cold Indices, array passed in of what needs to be snapshotted
def backup_cold_indices(cold_indices, elastic_repository):
    for cold_index in cold_indices:
        _backup_name = f"snapshot_{cold_index}"
        
        _snap_result, _snap_value = create_elasticsearch_snapshot(es,cold_index,_backup_name,elastic_repository)
        if _snap_result == True:
            logging.info(f"Snapshot accepted for {cold_index}.")
        else:
            logging.info(f"Snapshot failed for {cold_index}.")
        

# Get the list of indices and their respective ILM states
def get_index_ilms():
    index_ilms = {}
    cat_indices = es.cat.indices(format="json", expand_wildcards="open,closed", h=["index"])

    for index_info in cat_indices:
        index = index_info['index']
        ignored_indices = [ '.async-search','.kibana_task_manager','.kibana','.apm-custom-link', '.geoip_databases', '.ds-test-data-logs', '.apm-agent-configuration', '.tasks']

        if index_matches_patterns(index,ignored_indices):
            continue
        
        ilm_info = es.transport.perform_request("GET", f"/{index}/_ilm/explain")

        # Try to get the phase, if no phase then skip onto next item.
        try:
            ilm_state = ilm_info["indices"][index]["phase"]
        except:
            ilm_state = None
        index_ilms[index] = ilm_state

    return index_ilms

#
## Main Script
#
if __name__ == "__main__":

    # Suppress the InsecureRequestWarning
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning) 

    # Get Current working directory
    current_directory = os.getcwd()
    # Get the path to the currently executing script
    script_directory = os.path.dirname(os.path.abspath(__file__))

    # Setup log directory
    log_file = os.path.join(script_directory, 'logs/elastic-cold-snapshots.log')

    # Load INI 
    config_file = os.path.join(script_directory,'elastic_settings.ini')
    settings = read_settings(config_file)
    elastic_host = settings.get('elastic_host', 'localhost')
    elastic_port = settings.get('elastic_port', '9201')
    elastic_use_ssl = settings.getboolean('elastic_use_ssl', False)
    elastic_repository = settings.get('elastic_repository')
    elastic_ca_certs =  "/path/to/your/ca.crt.pem"  # Path to the CA certificate

    # Logging Settings
    logging.basicConfig(level=logging.INFO, filename=log_file, format='%(asctime)s - %(levelname)s - %(message)s')

    # Set up a custom logger for Elasticsearch requests
    elasticsearch_logger = logging.getLogger("elasticsearch")
    elasticsearch_logger.setLevel(logging.WARNING)

    # Connect to Elasticsearch
    # Setup ES Connection settings to Elasticsearch
    es = Elasticsearch([elastic_host], port=elastic_port, use_ssl=elastic_use_ssl, verify_certs=False, cacerts=elastic_ca_certs, logger=elasticsearch_logger)
    
    if not es.ping():
        print(f"Elasticsearch cluster is not available with settings: {elastic_host}:{elastic_port}")
        exit(1)

    # Initialize Argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-debug", "--debug", help="Show Debugging Information", action="store_true")
    parser.add_argument("-pattern", help="Limit Snapshots to pattern specified", type=str, default='.*')
    parser.add_argument("-noaction", help="Stop before performing snapshots", default=False, action="store_true")
    parser.add_argument("-repository", "-repos", help="Elastic S3 Repository to use")
    args = parser.parse_args()

    # Capture Arguments Passed in to Parser
    args_debug = args.debug
    args_regex_pattern = args.pattern
    args_noaction = args.noaction
    args_repository = args.repository

    if args_debug == True:
        print(f"Arguments: {args}")

    # Log Script Starting
    logging.info("Elastic-Snapshots Script starting...")
    logging.info(f"Config File: {config_file}")
    logging.info(f"Log File: {log_file}")


    # Handle Repository
    # If Repository passed as argument that wins
    if args_repository != None:
        elastic_repository = args_regex_pattern
    logging.info(f"Using Repository: {elastic_repository}")

    # Get All Snapshots and store in var: snapshots
    snapshots = get_all_snapshots()

    # Get All Indices store in var: index_ilms, cold stored in var: cold_indices
    index_ilms = get_index_ilms()
    cold_indices = [index for index, state in index_ilms.items() if state == "cold"]

    if args_debug == True:
        logging.info(f"Cold Indices: {cold_indices}")


    _cold_tobackup = get_cold_indices_needing_backedup(cold_indices,snapshots, args_regex_pattern)                    
    logging.info(f"Indices needing backedup: {_cold_tobackup}")

    # Snapshot indices.
    if args_noaction == True:
        pass
    else:
        backup_cold_indices(_cold_tobackup, elastic_repository)

    logging.info("Script Ending...")

