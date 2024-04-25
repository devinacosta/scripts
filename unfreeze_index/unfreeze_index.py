#!/usr/bin/env python3
'''
 Index Opener (DataStream) version.
 Written by Devin Acosta
'''
VERSION = "1.1.1"
DATE = "04/25/2024"

import re
import requests
import argparse, subprocess
from elasticsearch import Elasticsearch, ConnectionTimeout
from collections import defaultdict
import datetime
from rich import print
from rich.console import Console
from rich.layout import Layout
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.progress import Progress, Spinner
from rich.syntax import Syntax
from rich.text import Text
from rich import box
from rich.box import Box
import pickle
import time


def Merge(dict1, dict2):
    res = dict1 | dict2
    return res


def returnDict():
    return {}


def find_most_likely_file(filenames, date):

    closest_date_diff = float('inf')
    most_likely_file = None
    date_obj = datetime.strptime(date, '%Y.%m.%d')  # Assuming the date is in YYYY-MM-DD format

    print(closest_date_diff, date_obj)

    for filename in filenames:
        date_str = filename.split('-')[-2]
        file_date_obj = datetime.strptime(date_str, '%Y.%m.%d')
        date_diff = abs((date_obj - file_date_obj).days)

        print(filename, date_str, file_date_obj, date_diff, closest_date_diff)

        if date_diff < closest_date_diff:
            closest_date_diff = date_diff
            most_likely_file = filename

    return most_likely_file


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


def uniquePatterns(filenames):
    ret_filenames = []
    for filename in filenames:
        match = re.search(r'logs-(.*?)-\d{4}\.\d{2}\.\d{2}', filename)

        if match:
            result = f"logs-{match.group(1)}"
            ret_filenames.append(result)

    ret_filenames = list(set(ret_filenames))
    return ret_filenames


def getIndices(location,es_port):

    # Convert to upper case so that it matches Variable SJC01/IAD01/etc...
    es_host = eval(location.upper())

    try:
        # Connect to Elastic Search
        es = Elasticsearch([{'host': es_host, 'port': es_port}], timeout=60)
        es_ping = es.ping()

        if (es_ping == False):
            return { location: {} }

    except ConnectionTimeout:
            print("Made it connection Timeout")
            return { location: {} }

    es_indices = defaultdict(returnDict)
    es_indices_list = []
    cat_indices = es.cat.indices(format="json")

    # List Indices and return
    for index in cat_indices:

        current_index = index['index']
        current_index_status = index['status']

        es_indices_list.append(index['index'])
        es_indices[location][current_index] = { 'location': location, 'port': es_port, 'status': current_index_status}

    '''
    Now variables es_indices_list and mydict are populated with data
    '''
    #print(location, es_indices)
    return es_indices


'''
Expects input to be a key=>value pair
'''
def processResults(indices, patterns):
    matching_keys = []
    regex_patterns = [re.compile(f".*{pattern}.*") for pattern in patterns]

    # Loop through indices and find matches
    for key in indices.keys():
        if any(regex_pattern.match(key) for regex_pattern in regex_patterns):
            matching_keys.append(key)

    return matching_keys


'''
Same as processResults but is simple list.
'''
def matchingIndices(indices,pattern):

    matching_keys = []
    search_pattern = f".*{pattern}.*"
    regex_pattern = re.compile(search_pattern)

    # Loop through indices and find matches
    for key in indices:

        if regex_pattern.match(key):
            matching_keys.append(key)

    return matching_keys


'''
Get the Frozen Status of an indice
returns False or True
Need to pass in data (contains location/port info), and indice in question.
'''
def get_frozenStatus(data, indice):

    host = eval(data[indice]['location'].upper())
    port = data[indice]['port']

    url = f"http://{host}:{port}/_cat/indices/{indice}?h=i,sth"
    response = requests.get(url)
    res_data = response.text.strip().split(" ")[1]

    #print(url,response.text, res_data)
    # Convert false/true to Python Style [False/True]
    if res_data == "false":
        return False
    elif res_data == "true":
        return True
    else:
        return None


'''
Function: Unfreeze single indice
'''
def action_unFreezeIndice(host,port,indice):
    current_host = host.upper()
    es_host = eval(current_host)
    url = f"http://{es_host}:{port}/{indice}/_unfreeze"
    response = requests.post(url)
    resp_data = response.text
    return response, resp_data


'''
Function: Get matching indices and actually unfreeze them
'''
def unFreezeIndices(batched_final):
    for indice in batched_final:
        indice_data = batched_final[indice]
        indice_location = indice_data['location']
        indice_port = indice_data['port']
        indice_freeze = indice_data['frozen_status']

        if (indice_freeze == True):

            with console.status("Unfreezing Indices...") as status:
                status.update(f"Action: Unfreezing Indice {indice}")
                ufs_response, ufs_data = action_unFreezeIndice(indice_location,indice_port,indice)
                #print(ufs_response,ufs_data)
                if (ufs_response.status_code == 200):
                    console.log(f"Indice (unfrozen): {indice}")

        elif (indice_freeze == False):
            # Not going to log anything.
            pass


# Create tables
def create_table(title, data):
    table = Table(title=title, width=115)
    table.add_column("Cluster")
    table.add_column("Index")
    table.add_column("Frozen Status")
    if len(data) == 0:
        table.add_row("N/A", "No results found", "N/A")
    else:
        for index, row_data in data.items():
            index_cluster = f"{row_data['location']}/{row_data['port']}"
            index_frozen_status = f"{row_data['frozen_status']}"
            table.add_row(index_cluster, index, index_frozen_status)
    return table

'''
Display Results to Screen
'''
def displayResults(frozen_final, unfrozen_final, batched_final):

    global console

    print("\n")

    # Create the Tables
    frozen_table = create_table("Frozen Indices (action)", frozen_final)
    unfrozen_table = create_table("Unfrozen Indices (noaction)", unfrozen_final)

    console.print(frozen_table)
    console.print(unfrozen_table)


    # Determine if there are any indices to open or not
    any_true = any(item['frozen_status'] for item in batched_final.values())
    if any_true == False:
        console.log(f"There are no FROZEN indices to open, exiting...\n\n")
        exit()
    else:
        proceed = validateProceed()
        if proceed == True:
            '''
            Proceed to unfreeze indices
            '''
            print("\n")
            unFreezeIndices(batched_final)
        else:
            print("You have aborted operations!")
            exit()


def tabData(data):

    tabulate_out = []
    for indice in data:
        indice_location = f"{data[indice]['location']}/{data[indice]['port']}"
        indice_frozen_status = data[indice]['frozen_status']

        tab_data = [indice_location,indice,indice_frozen_status]
        tabulate_out.append(tab_data)

    return tabulate_out


def validateProceed():
    while True:
        answer = input("Would you like to open these Indices? [y/n]: ").lower()
        if (answer == 'y' or answer == 'yes'):
            return True
            break
        elif (answer == 'n' or answer == 'no'):
            return False
            break
        else:
            print("Invalid Input, Please try again.")


'''
Function to update the status bar with latest data.
'''
def status_bar_update(message):
    global console

    with console.status(f"[bold green]{message}") as status:
        time.sleep(0.5)
        console.log(message)


def show_message_box(title, message, message_style="bold white", panel_style="white on blue"):

    message = Text(f"{message}", style=message_style, justify="center")
    panel = Panel(message, style=panel_style, title=title, border_style="bold white", width=80)
    console.print("\n")
    console.print(panel)
    console.print("\n")

'''
Main Function starts here.
'''
if __name__ == "__main__":

    # Start Rich Console...
    console = Console()
    print("")
    
    '''
    Load Variables from unfreeze_servers.txt
    Please Ensure All hostnames are CAPITAL in the unfreeze_servers.txt
    '''
    with open('unfreeze_servers.txt') as f:
        variables = f.read()
        exec(variables, globals())

    # Parser Stuff
    parser = argparse.ArgumentParser()
    # Locations(split by ,) where indexes need to be opened
    parser.add_argument("-l", "--locations", required=True)
    # date
    parser.add_argument("-d", "--date", required=True)
    # component
    parser.add_argument("-c", "--component", required=True)
    args = parser.parse_args()
    locations=args.locations.split(',')
    dt=args.date
    comp=args.component.split(',')
    indx2openList=[]

    # Print to Console script starting... then progress bar.
    status_bar_update(f"UNFREEZE Index Script [white](v{VERSION}  {DATE})[/white]")
    status_bar_update(f"Query: DATE: [{dt}], COMPONENT: [bold green]{comp}[/bold green], LOCATIONS {locations}")
    batched_final = defaultdict(dict)

    time.sleep(1)
    with console.status("Collecting data...") as status:

        for location in locations:
            status.update(f"Collecting data from cluster: {location}")

            # Get Indices (from all ports for the Instance)
            rc_indices_1 = getIndices(location,9201)
            rc_indices_2 = getIndices(location,9202)
            rc_indices_3 = getIndices(location,9203)
            rc_indices_4 = getIndices(location,9200)

            # Create new dictionary and append results of last step.
            merged_indices = {}
            merged_indices.update(rc_indices_1[location])
            merged_indices.update(rc_indices_2[location])
            merged_indices.update(rc_indices_3[location])
            merged_indices.update(rc_indices_4[location])


            # Look for matches of indices
            matching_indices = processResults(merged_indices,comp)
            unique_indices_patterns = uniquePatterns(matching_indices)

            # Loop through each unique pattern and get that match
            final_matching_indices = []
            for match in unique_indices_patterns:
                _matches = matchingIndices(matching_indices, match)
                most_likely_match = find_closest_file(_matches, dt)
                # Only Append if there is something to append
                if most_likely_match != None:
                    final_matching_indices.append(most_likely_match)

            '''
            Create (batched_final) and append all indices so we can open those at the end.
            '''
            if (len(final_matching_indices) > 0 ):
                for indices in final_matching_indices:
                    port = merged_indices[indices]['port']
                    batched_final[indices] = { "location": location, "port": port }

            matches = len(final_matching_indices)

            # Loop Through Batched_Final to get Frozen Status
            for indice in batched_final:
                _indice_frozen_status = get_frozenStatus(batched_final,indice)
                if _indice_frozen_status == True:
                    batched_final[indice]['frozen_status'] = _indice_frozen_status
                elif _indice_frozen_status == False:
                    batched_final[indice]['frozen_status'] = _indice_frozen_status
                else:
                    batched_final[indice]['frozen_status'] = None
    
            console.log(f"Search Results: Cluster {location} : {matches:02} matches found.")

    # Break Dictionaries into what we need to action and not action on.
    frozen_final = {}
    unfrozen_final = {}

    for indice, data in batched_final.items():
        # Determine the target dictionary based on the 'frozen_status' value
        target_dict = frozen_final if data['frozen_status'] else unfrozen_final
        target_dict[indice] = data

    tabdata = tabData(batched_final)
    # Exit if Nothing to Process
    if len(tabdata) == 0:
        show_message_box("No Results Found", "The Script found no frozen indices to open!")
        exit()
    displayResults(frozen_final, unfrozen_final,batched_final)
    print("\n")
