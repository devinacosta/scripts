#!/usr/bin/env python3
'''
Script to manage snapshots
ie: Purge old Snapshots no longer needed.
v. 1.0.0 - Devin Acosta (09/08/2023)
'''

import argparse
import configparser
from datetime import datetime
from elasticsearch import Elasticsearch
import logging
import os
import re
import requests
import urllib3
import warnings
import yaml

# Suppress the UserWarning
warnings.filterwarnings("ignore", category=UserWarning, module="elasticsearch")

# Read Data from YAML
def read_retention_data_from_yaml(file_path):
    # Open YAML and read into array: data
    with open(file_path, 'r') as file:
        data = yaml.safe_load(file)

    # Loop through data and return dict.
    _retentions = {}
    for pattern in data['retention']:
        ret_pattern = pattern['pattern']
        ret_max_days = pattern['max_days']
        _retentions[ret_pattern] = ret_max_days

    return _retentions


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


# Function to actually create the snapshot
def delete_elasticsearch_snapshot(es_client, snapshot_name, repository_name='lab-minio-backup-repos'):
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
        # Start the snapshot process
        response = es_client.snapshot.delete(repository=repository_name, snapshot=snapshot_name)
        return True, response

    except Exception as e:
        logging.warning(f"Error creating snapshot: {e}")
        return None, None


def delete_snapshots(snapshot_purge_list, es, repos_name):
    # Purge All Snapshots on list
    for snap_to_delete in snapshot_purge_list:
        snap_deleted = delete_elasticsearch_snapshot(es, snap_to_delete, repos_name)
        logging.info(f"Deleted snapshot: {snap_to_delete}")


# Extract date from filename
def extract_date_from_filename(filename):
    # Define the regex pattern to capture the date in YYYY.mm.dd format
    date_pattern = r'\d{4}\.\d{2}\.\d{2}'

    # Use re.search() to find the first match of the date pattern in the filename
    match = re.search(date_pattern, filename)

    # Check if a match was found
    if match:
        # Extract the matched date from the regex match object
        extracted_date_str = match.group()
        extracted_date = datetime.strptime(extracted_date_str, '%Y.%m.%d')
        return extracted_date
    else:
        return None


# Return difference in date in the number of days.
def date_difference(date1):
    # Get Today's date
    today = datetime.today()

    # Calculate the time difference
    time_difference = today - date1

    return time_difference.days


# Function to get a list of all snapshots
# Returns: ['snapshost_.ds-ams02-c01-logs-avp-main-2023.07.05-000064', 'snapshost_.ds-ams02-c01-logs-avp-main-2023.07.08-000065', 'snapshost_.ds-ams02-c01-logs-jwl-stat-api-2023.07.09-000085']
def get_all_snapshots():
    snapshots = []
    cat_snapshots = es.cat.snapshots(format="json")
    
    for snapshot_info in cat_snapshots:
        snapshots.append(snapshot_info['id'])
    
    return snapshots


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


# Function to process filename and then return retention days based upon retention.yml
def get_value_based_on_regex(filename, regex_dict):
    for regex_pattern, value in regex_dict.items():
        if re.match(regex_pattern, filename):
            return value
    return None  # Return a default value if no match is found


def process_snapshots(snapshots, delete_days, regex_pattern, retention_file):
    # Loop through each snapshot obtain date/age of each and add to an array

    # We need to obtain the delete_days based upon retention policy.
    _retentions = read_retention_data_from_yaml(retention_file)
    logging.info(f"Retention: {_retentions}")

    _snapshots = {}
    for snapshot in snapshots:
        snap_date = extract_date_from_filename(snapshot)
        snap_date_difference = date_difference(snap_date)
        snapshot_name_minus = snapshot.strip('snapshot_')
        _ret_data = retention_delete_days = get_value_based_on_regex(snapshot_name_minus, _retentions)
        if _ret_data == None:
            retention_delete_days = delete_days

        if int(snap_date_difference) >= retention_delete_days:
            # Check to see if pattern patches to allow limiting which indices to process
            if pattern_matches(snapshot, regex_pattern):
                _snapshots[snapshot] = snap_date_difference
        #print("Current Snap", snapshot, snap_date, snap_date_difference)

    return _snapshots


# Main Program
if __name__ == "__main__":

    # Get the path to the currently executing script
    script_directory = os.path.dirname(os.path.abspath(__file__))

    # Load INI 
    config_file = os.path.join(script_directory,'elastic_settings.ini')
    retention_file = os.path.join(script_directory, 'elastic_retention.yml')
    log_file = os.path.join(script_directory, 'logs/elastic-snapshot-manager.log')
    settings = read_settings(config_file)
    elastic_host = settings.get('elastic_host', 'localhost')
    elastic_port = settings.get('elastic_port', '9201')
    elastic_use_ssl = settings.getboolean('elastic_use_ssl', False)
    elastic_repository = settings.get('elastic_repository')
    default_retention_maxdays = settings.get('default_retention_maxdays')
    elastic_ca_certs =  "/path/to/your/ca.crt.pem"  # Path to the CA certificate

    # Logging Settings
    logging.basicConfig(level=logging.INFO, filename=log_file, format='%(asctime)s - %(levelname)s - %(funcName)s - %(message)s')

    # Set up a custom logger for Elasticsearch requests
    elasticsearch_logger = logging.getLogger("elasticsearch")
    elasticsearch_logger.setLevel(logging.WARNING)

    # Setup ES Connection settings to Elasticsearch
    es = Elasticsearch([elastic_host], port=elastic_port, use_ssl=elastic_use_ssl, verify_certs=False, cacerts=elastic_ca_certs, logger=elasticsearch_logger)
    if not es.ping():
        print(f"Elasticsearch cluster is not available with settings: {elastic_host}:{elastic_port}")
        exit(1)
        
    # Parse Arguments and setup variables
    parser = argparse.ArgumentParser()
    parser.add_argument("-debug","--debug", action="store_true", help="Debug information")
    parser.add_argument("-days", help="Number of days to delete indices old than this value", type=int, default=default_retention_maxdays)
    parser.add_argument("-pattern",help="Limit Snapshots to pattern specified", type=str, default='.*')
    parser.add_argument("-noaction", help="Stop before performing snapshots", default=False, action="store_true")
    parser.add_argument("-repository", "-repo", help="S3 Repository name", default=False)

    logging.info("Starting Snapshot Manager...")

    args = parser.parse_args()
    delete_days = args.days
    args_regex_pattern = args.pattern
    args_noaction = args.noaction
    args_repository = args.repository
    logging.info(f"Snapshot [Default] max retention days: {delete_days}")

    # Get All Snapshots and store in var: snapshots
    snapshots = get_all_snapshots()

    # Process the snapshot list, return array of indice and date.
    snapshots_to_delete = process_snapshots(snapshots, delete_days, args_regex_pattern, retention_file)
    logging.info(f"Snapshots to delete: {snapshots_to_delete}")

    # Now Actually Purge Snapshots
    if args_noaction == True:
        logging.info(f"Parameter [noaction] detected, not performing actions.")
        #pass
    else:
        delete_snapshots(snapshots_to_delete, es, elastic_repository)

    # End Logging
    logging.info("Script has completed...")

