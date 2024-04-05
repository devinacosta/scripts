#!/usr/bin/env python3
'''
Script to manage restored snapshots
ie: Purge older restored indices to keep cluster clean.
v. 1.0.1 - Devin Acosta (01/26/2024)
'''

import argparse
import configparser
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch
import logging
import os
import re
import requests
import urllib3
import warnings
import yaml
import urllib3

# Suppress the UserWarning
warnings.filterwarnings("ignore", category=UserWarning, module="elasticsearch")
# Suppress only the InsecureRequestWarning from urllib3 needed for Elasticsearch
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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

'''
Function to take date and compare difference in days.
'''
def days_difference(date_str):
    # Convert the input date string to a datetime object
    input_date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S.%fZ')

    # Get today's date
    today_date = datetime.now()

    # Calculate the difference in days
    difference = today_date - input_date

    # Extract the days component from the timedelta object
    days_difference = difference.days

    return str(days_difference)


def delete_document_by_field_value(field_name, field_value, es):
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

    global elastic_index_name

    try:
        # Search for the document
        query = {"query": {"match": {field_name: field_value}}}
        result = es.search(index=elastic_index_name, body=query)

        # Check if any documents were found
        if result["hits"]["total"]["value"] > 0:
            # Extract document ID
            doc_id = result["hits"]["hits"][0]["_id"]

            # Delete the document
            es.delete(index=elastic_index_name, id=doc_id)
            print(f"Document with {field_name}='{field_value}' deleted successfully.")

            return True
        else:
            print(f"No document found with {field_name}='{field_value}'.")
            return False
    except Exception as e:

        print(f"An error occurred: {e}")
        return False


'''
Function to delete an elasticsearch indice
'''
def delete_elasticsearch_index(es, document_name):
    """
    Deletes an Elasticsearch index.

    Parameters:
    - es: ElasticSearch connection handler.
    - index_name: The name of the index to be deleted.


    Returns:
    - True if the index is successfully deleted, False otherwise.
    """

    global elastic_index_name


    try:
        if es.indices.exists(index=document_name):
            es.indices.delete(document_name)
            delete_document_by_field_value('index_name', document_name, es)
            logging.info(f"[deleted] Index '{document_name}' deleted successfully.")
            return True
        else:
            logging.info(f"[notexist] '{document_name}' does not exist.")
            delete_document_by_field_value('index_name', document_name, es)
            logging.info(f"[deleted] Deleted {document_name} from Restored Database")
            return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return False

'''
Function to take indice data and see if it needs automatic purging.
'''
def elastic_purge_indice_cleaner(indice, restore_date, elastic_restored_maxdays):

    days_diff = days_difference(restore_date)

    if days_diff >= elastic_restored_maxdays:
        logging.info(f"[delete] indice {indice} :  {days_diff} days old.")
        delete_elasticsearch_index(es, indice)
    else:
        logging.info(f"[noaction] indice {indice} : {days_diff} days old.")



'''
Function to loop over elastic_restored indice and determine if any indices need to be deleted.
'''
def elastic_restored_cleaner(es, elastic_index_name, elastic_restored_maxdays):

    # Check for existing documents with the same index_name
    query = {
        "query": {
            "match_all": {}
        }
    }
    existing_docs = es.search(index=elastic_index_name, body=query, scroll='2m', size=1000)
    hits = existing_docs['hits']['hits']

    for doc in hits:
        data = doc['_source']
        _index_name = data['index_name']
        _restore_date = data['restore_date']
        _status = data['status']

        logging.info(f"Processing: indice: {_index_name}, restore_date: {_restore_date}")
        # Now Check date to see if we need to manually purge this index.
        elastic_purge_indice_cleaner(_index_name, _restore_date, elastic_restored_maxdays)

'''
Function to delete an indice from Elastic Search
'''

'''
The Main Program
'''
if __name__ == "__main__":

    # Get the path to the currently executing script
    script_directory = os.path.dirname(os.path.abspath(__file__))

    # Load INI 
    config_file = os.path.join(script_directory,'elastic_settings.ini')
    retention_file = os.path.join(script_directory, 'elastic_retention.yml')
    log_file = os.path.join(script_directory, 'logs/elastic-restored-indice-manager.log')
    settings = read_settings(config_file)
    elastic_host = settings.get('elastic_host', 'localhost')
    elastic_port = settings.get('elastic_port', '9201')
    elastic_use_ssl = settings.getboolean('elastic_use_ssl', False)
    elastic_repository = settings.get('elastic_repository')
    default_retention_maxdays = settings.get('default_retention_maxdays')
    elastic_ca_certs =  "/path/to/your/ca.crt.pem"  # Path to the CA certificate
    elastic_index_name = settings.get('elastic_restored_indice')
    elastic_restored_maxdays = settings.get('elastic_restored_maxdays')

    # Logging Settings
    logging.basicConfig(level=logging.INFO, filename=log_file, format='%(asctime)s - %(levelname)s - %(funcName)s - %(message)s')

    # Set up a custom logger for Elasticsearch requests
    elasticsearch_logger = logging.getLogger("elasticsearch")
    elasticsearch_logger.setLevel(logging.WARNING)
    
    logging.info("Starting Restored Indice Manager...")
    logging.info(f"[config] Elastic Indice: {elastic_index_name}")
    logging.info(f"[config] Restored [Default] max days: {elastic_restored_maxdays}")

    print(f"Restored Max Days: {elastic_restored_maxdays}")
    print(f"Elastic_Indice: {elastic_index_name}")

    # Connect to ElasticSearch
    es = Elasticsearch([elastic_host], port=elastic_port, use_ssl=elastic_use_ssl, verify_certs=False)

    # Now Check the Indice
    elastic_restored_cleaner(es, elastic_index_name, elastic_restored_maxdays)

    # Close Logging
    logging.info(f"Script has completed...")
