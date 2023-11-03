#!/usr/bin/env python3
'''
Restore Snapshot from S3 Minio
Written by Devin Acosta
v 0.0.2a (08/16/2023)
- Added elastic_servers.yml
- Added additional error handling.
- Cleanup script a bit, added _ilm/remove
'''

import argparse
from datetime import datetime
from elasticsearch import Elasticsearch, ElasticsearchWarning, exceptions
from collections import defaultdict
import yaml
import re
from tabulate import tabulate
import warnings

# Suppress the UserWarning
warnings.filterwarnings("ignore", category=UserWarning, module="elasticsearch")
warnings.filterwarnings("ignore", category=ElasticsearchWarning)


# Return Dictionary
def returnDict():
    return {}


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
Pretty Print Results to Screen and get acknowledgement to proceed
'''
def displayResults(tabdata,batched_final):

    if len(tabdata) == 0:
        print("\nThe Script found [- No results -] to restore!\n")
        exit()


    print("\nThe Script found the following snapshots to be restored:")
    print(tabulate(tabdata,tablefmt="heavy_grid",headers=["Cluster","Indice"]))

    proceed = validateProceed()
    if proceed == True:
        '''
        Proceed to unfreeze indices
        '''
        print("\n")
        restoreSnapshots(batched_final)
    else:
        print("You have aborted operations!")
        exit()


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

'''
Gets all the snapshots from cluster via the port specified
'''
def getSnapshots(location,es_port):

    try:
        # Convert to upper case so that it matches Variable SJC01/IAD01/etc...
        es_host = eval(location.upper())

    except Exception as e:
        print(f"Exception Occured: {e}, please ensure server is listed in elastic_servers.yml")
        exit(1)


    # Connect to Elastic Search
    es = Elasticsearch([{'host': es_host, 'port': es_port}])
    es_ping = es.ping()
    if (es_ping == False):
        return { location: {} }

    es_snapshots = defaultdict(returnDict)
    es_snapshots_list = []
    cat_snapshots = es.cat.snapshots(format="json")
    #print("snapshots:", cat_snapshots)

    # List Indices and return 
    for index in cat_snapshots:
      
        current_snapshot = index['id']
        current_snapshot_status = index['status']
       
        es_snapshots_list.append(index['id']) 
        es_snapshots[location][current_snapshot] = { 'location': location, 'port': es_port, 'status': current_snapshot_status}
    
    '''
    Now variables es_indices_list and mydict are populated with data 
    '''
    #print(location, es_indices)
    return es_snapshots


'''
Function: Restore Single Snapshot
'''
def restore_elasticsearch_snapshot(snapshot_name, repository_name, elastic_host, elastic_port):

    # Used to determine if snapshot restore was successful
    _snapshot_status = False

    # Establish a connection to the Elasticsearch cluster
    es = Elasticsearch([{'host': elastic_host, 'port': elastic_port}])
    
    # Define the restore settings
    restore_settings = {
        "indices": "",  # Specify the indices to restore, e.g., "index1,index2"
        "ignore_unavailable": True,
        "include_global_state": False
    }
    
    try:
        # Perform the restore operation
        response = es.snapshot.restore(repository=repository_name, snapshot=snapshot_name, body=restore_settings)
        
        # Check the response for success
        if response.get("accepted"):
            _snapshot_status = True
            print(f"Snapshot '{snapshot_name}' restore has been accepted and started.")
        else:
            print(f"Snapshot restore request for '{snapshot_name}' was not accepted.")
    
    except exceptions.TransportError as e:
        if e.error == "snapshot_restore_exception" and "an open index with same name already exists in the cluster" in e.info['error']['reason']:
            print(f"Error: An index with the same name already exists in the cluster. Close, delete, or restore with a different name.")
        else:
            print(f"An error occurred: {e}")
    
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    return _snapshot_status

'''
Function to remove ILM policy, so that when we restore it doesn't get deleted right away.
'''
def remove_ilm_policy(index_name, elastic_host, elastic_port):
    # Define the Elasticsearch client
    es = Elasticsearch([{'host': elastic_host, 'port': elastic_port}])  # Update with your Elasticsearch cluster details

    # Construct the URL for the _ilm/remove API
    url = f'/{index_name}/_ilm/remove'

    try:
        # Send a POST request to remove the ILM policy
        response = es.transport.perform_request('POST', url)
    
        if response['has_failures'] == False:
            print(f"Removed ILM policy from index '{index_name}'.")
        else:
            print(f"Failed to remove ILM policy from index '{index_name}'.")
    except exceptions.RequestError as e:
        print(f"Failed to remove ILM policy from index '{index_name}': {e}")



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

        restore_status = restore_elasticsearch_snapshot(snapshot, repository, snapshot_location, snapshot_port)

        # Batching All Successful Snapshots so we can remove ILM policy afterwards.
        if restore_status == True:
            _restore_batch[snapshot_name_minus] = { "location": snapshot_location, "port": snapshot_port}


    # Now Loop through successful snapshots and remove ILM policy
    for snapshot in _restore_batch:
  
        snapshot_location = _restore_batch[snapshot]["location"]
        snapshot_port = _restore_batch[snapshot]["port"]
        remove_ilm_policy(snapshot, snapshot_location, snapshot_port)


def tabData(data):

    tabulate_out = []
    for indice in data:
        snapshot_location = f"{data[indice]['location']}/{data[indice]['port']}"

        tab_data = [snapshot_location,indice]
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


def validateProceed():
    while True:
        answer = input("Would you like to restore these Snapshots? [y/n]: ").lower()
        if (answer == 'y' or answer == 'yes'):
            return True
            break
        elif (answer == 'n' or answer == 'no'):
            return False
            break
        else:
            print("Invalid Input, Please try again.")

# Main Script
if __name__ == "__main__":

    '''
    Load Variables from elastic_servers.yml
    Please Ensure All hostnames are CAPITAL in the elastic_servers.yml
    '''

    elastic_servers = read_servers_from_yaml('elastic_servers.yml')
    # Load Servers into memory for easy access.
    for key in elastic_servers:
        _value = elastic_servers[key]
        exec(f"{key} = '{_value}'")


    # Parse Arguments and setup variables
    parser = argparse.ArgumentParser()
    parser.add_argument("-debug","--debug", action="store_true", help="Debug information")
    parser.add_argument("-d","--date", help="Date of indice to restore ( Format: YYYY.mm.dd )", required=True)
    parser.add_argument("-c","--component", help="Component (i.e.: logs-XXX )", required=True)
    parser.add_argument("-l","--locations", help="Location ( defaults to localhost )", type=str, default='DEFAULT')
    parser.add_argument("-r","--repository", help="Snapshot repository to use", default="lab-minio-backup-repos")

    args = parser.parse_args()
    locations=args.locations.split(',')
    dt=args.date
    comp=args.component
    repository=args.repository

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
                port = merged_snapshots[indices]['port']
                batched_final[indices] = { "location": location, "port": port }

    # Now Display Tab Data to screen on what we plan to restore.
    tabdata = tabData(batched_final)
    displayResults(tabdata,batched_final)

    print("\n\nScript has completed!")
