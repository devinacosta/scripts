#!/usr/bin/env python3

"""
  yum-updates-summary.py
  Captures packages to be upgraded and currently installed versions of those packages
  Version: 1.0.0, Written by Devin Acosta
"""

import argparse
import json
import re
import subprocess
from tabulate import tabulate

VER = '1.0.0'

def run_yumlist(pkg_name):
    
    cmd = f'yum list {pkg_name} -C'
    output = subprocess.check_output(cmd, shell=True, universal_newlines=True)
    return output

def run_linux_command(command):
    try:
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        status_code = process.returncode
        return status_code, stdout, stderr
    except Exception as e:
        return -1, None, str(e)

def parse_version(version_str):
    # Split the version string into numeric and non-numeric parts
    version_parts = re.split(r'[^0-9]+', version_str)
    
    # Convert numeric parts to integers
    version_parts = [int(part) if part.isdigit() else part for part in version_parts]
    
    return version_parts

def compare_versions(version1, version2):
    # Compare version tuples component by component
    for part1, part2 in zip(version1, version2):
        if part1 == part2:
            continue
        if part1 < part2:
            return -1
        else:
            return 1
    return 0

def get_package_info_with_highest_available_version(package_name):

    stdout = run_yumlist(package_name)

    # Split the output into lines
    lines = stdout.splitlines()

    # Initialize variables
    package_data = {
        "installed": [],
        "available": []
    }
    status = None
    available_versions = []

    for line in lines:
        if "Installed Packages" in line:
            status = "installed"
        elif "Available Packages" in line:
            status = "available"
        elif status and "Last metadata expiration check" not in line:
            parts = line.split()
            if len(parts) >= 3:
                package_name = parts[0]
                version = parts[1]
                repository = parts[2].strip()
                if package_name != status.capitalize():
                    if status == "available":
                        available_versions.append({
                            "package_name": package_name,
                            "version": version,
                            "repository": repository
                        })
                    else:
                        package_data[status].append({
                            "package_name": package_name,
                            "version": version,
                            "repository": repository
                        })


    # Find the highest available version
    if available_versions:
        highest_available_version = max(available_versions, key=lambda x: parse_version(x['version']))
        package_data["highest_available_version"] = highest_available_version["version"]
    else:
        package_data["highest_available_version"] = None

    #print(package_name, package_data)

    return json.dumps(package_data, indent=4)


def run_yum_check_update():

    # Run 'yum check-update' and capture the output
    #output = subprocess.check_output(['yum', 'check-update'], stderr=subprocess.STDOUT)
    completed_process = subprocess.run(['yum', 'check-update'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, check=False)
    completed_output = completed_process.stdout

    # Initialize a dictionary to store package information
    package_info = {}

    # Parse the 'yum check-update' output
    lines = completed_output.strip().split('\n')
    packages_count = len(lines)
    
    for line in lines:
        if line.startswith("Excluding"):
            continue
        if line.startswith("Load"):
            continue
        if line.startswith("Last"):
           continue
        if line.startswith("Security"):
            continue
        if line.startswith(" * "):
            continue
        package_data = line.split(None, 2)

        #print("Package_Data: ", package_data)
        if len(package_data) == 3:
            package_name, update_version, repos = package_data

            # Strip Package Name
            package_name = package_name.split(".")[0]

            # Capture package data
            package_data = json.loads(get_package_info_with_highest_available_version(package_name))

            #print(f"{package_name} => {package_data}")
            current_version = package_data['installed'][0]['version']
            update_version = package_data['highest_available_version']

            package_info[package_name] = {
                'current_version': current_version,
                'update_version': update_version,
                'repos': repos.strip()
            }

    # Loop through and get Currently installed package information
    return json.dumps(package_info, indent=4)

def save_update_data(json):
    f = open("yum-updates-summary.json", "w")
    f.write(json)
    f.close()

def json_to_dict(data):
    return json.loads(data)

def dict_to_tabulate_array(result_data):
    # Pretty Print the Data
    table_data = []
    pkg_count = 0
    for key in result_data:
        pkg_count += 1
        key_data = result_data[key]

        key_current = key_data['current_version']
        key_update = key_data["update_version"]
        table_data.append([key, key_current, key_update])

    return table_data

def show_pretty_output():
    """
    Shows Pretty Output format of JSON data
    """
    f = open('yum-updates-summary.json', 'r')
    json_data = json.load(f)
    f.close()

    table_data = dict_to_tabulate_array(json_data)
    show_table(table_data)

    total = len(json_data)

    print(f"\nTotal of {total} packages being upgraded.")


def show_table(table_data):
    headers = [ "package", "current_version", "update_version"]
    print(tabulate(table_data, headers, tablefmt="rounded_outline"))

"""
Main Script
"""
if __name__ == "__main__":

    # Get Arguments
    parser = argparse.ArgumentParser(description='Obtains currently installed verisons of packages to be updated by YUM.')
    parser.add_argument('-p', '--pretty', dest='pretty', help='Show Pretty output from JSON file', action='store_true')
    parser.add_argument('-v', '--version', dest='version', help='Show Version Number', action='store_true')
    args = parser.parse_args()
 
    # Process Arguments if passed
    if args.pretty == True:
        show_pretty_output()
        exit()
    if args.version == True:
        print(f"Version: {VER}")
        exit()

    # Print Starting Script
    print(f"Please wait, checking for updates...")

    # Ensure Yum Cache is present
    status_code, stdout, stderr = run_linux_command('yum makecache')

    # Get Packages to be upgraded
    yum_update_data = run_yum_check_update()
    result_data = json_to_dict(yum_update_data)

    # Save Data to Local Disk
    save_update_data(yum_update_data)
   
    # If Result Data is empty display that to screen
    if len(result_data) == 0:
        print(f"\nOperating system is fully patched, no updates found.\n")
        exit()
   
    table_data = dict_to_tabulate_array(result_data)
    show_table(table_data)