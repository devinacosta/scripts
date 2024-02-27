#!/usr/bin/env python3
"""
# Disk Cleanup Python Script
# Written by Devin Acosta
# Version 1.2.5 02/26/2024
# Repo: https://github.com/devinacosta/python/blob/master/scripts/diskcleanup/
"""

# Import Libraries
import arrow
import datetime
import glob
import logging
import json
import os
import re
import shutil
import yaml
from pathlib import Path

# Initial Variables
rc_files = {}
SCRIPTVER = "1.2.5"

"""
ABRT Functions
"""

def extract_date_from_directory_name(directory_name):
    # Replace colons with underscores to make the date format compatible with directory names
    directory_name = directory_name.replace(':', '_')

    # Split the directory name by non-digit characters
    date_parts = re.split(r'\D+', directory_name)

    # Attempt to parse date components (year, month, day, hour, minute, second)
    try:
        date_components = [int(part) for part in date_parts if part]
        if len(date_components) >= 6:
            return datetime.datetime(*date_components)
    except ValueError:
        pass

    return None

def delete_old_abrt_directories(dump_dir, days_threshold):
    try:
        # Calculate the threshold date (x days ago from today)
        threshold_date = datetime.datetime.now() - datetime.timedelta(days=days_threshold)

        # Iterate through the dump directory
        for root, dirs, _ in os.walk(dump_dir):
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)

                # Extract the date from the directory name
                dir_date = extract_date_from_directory_name(dir_name)

                if dir_date:
                    # Check if the directory is older than the threshold
                    if str(dir_date) < str(threshold_date):
                        # Remove the entire directory and its contents
                        shutil.rmtree(dir_path)
                        logging.info(f"[abrt][delete] : Removed directory: {dir_path}")

    except Exception as e:
        logging.error(f"Error deleting old ABRT directories: {e}")

def delete_old_abrt_files(dump_dir, days_threshold):
    try:
        # Calculate the threshold date (x days ago from today)
        threshold_date = datetime.datetime.now() - datetime.timedelta(days=days_threshold)

        # Iterate through the dump directory
        for root, _, files in os.walk(dump_dir):
            for file_name in files:
                file_path = os.path.join(root, file_name)

                # Get the file's modification timestamp
                file_timestamp = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))

                # Check if the file is older than the threshold
                if file_timestamp < threshold_date:
                    # Delete the file
                    os.remove(file_path)
                    logging.info(f"[abrt][delete] : Deleted: {file_path}")

            # Check if the directory is empty
            if not os.listdir(root):
                # Remove the empty directory
                os.rmdir(root)
                logging.info(f"[abrt][delete] : Removed empty directory: {root}")
    except Exception as e:
        logging.error(f"Error deleting old ABRT files: {e}")

def convert_size_threshold(size_threshold):
    # Regular expression to extract numeric value and unit (MB or GB)
    match = re.match(r'^(\d+(?:\.\d+)?)\s*(MB|GB)$', size_threshold, re.IGNORECASE)
    if match:
        value = float(match.group(1))
        unit = match.group(2).upper()
        if unit == "MB":
            return value * 1024**2
        elif unit == "GB":
            return value * 1024**3
    else:
        print("Invalid size format. Please use 'MB' or 'GB'.")
        exit(1)

def delete_abrt_directories_by_size(dump_dir, size_threshold):
    try:
        size_threshold_bytes = convert_size_threshold(size_threshold)

        # Iterate through the dump directory
        for root, dirs, _ in os.walk(dump_dir, topdown=False):
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)

                # Calculate the size of the directory
                dir_size = sum(os.path.getsize(os.path.join(dir_path, file)) for file in os.listdir(dir_path))

                # Check if the directory exceeds the size threshold
                if dir_size > size_threshold_bytes:
                    # Delete the directory and its contents
                    shutil.rmtree(dir_path)
                    logging.info(f"[abrt][delete] : Deleted directory over size limit: {dir_path}")

    except Exception as e:
        print(f"An error occurred: {e}")

"""
End of ABRT Functions
"""

def has_slashes(path):
    return '/' in path


"""
Function to Truncate Log File (keep our logs from taking over OS)
"""
def truncate_log_file(filename, file_size):
    # Convert human-readable size (e.g., 100M) to bytes
    size_multiplier = {'K': 1024, 'M': 1024**2, 'G': 1024**3, 'T': 1024**4}
    try:
        size_unit = file_size[-1].upper()
        size_value = int(file_size[:-1])
        bytes_to_compare = size_value * size_multiplier[size_unit]
    except (ValueError, KeyError):
        raise ValueError("Invalid file size format. Use a format like '100M'.")

    try:
        # Check file size
        actual_size = os.path.getsize(filename)

    except FileNotFoundError:
        actual_size = 0

    if actual_size > bytes_to_compare:
        # Truncate the file
        with open(filename, 'r+') as file:
            file.truncate(bytes_to_compare)

        print(f"File '{filename}' truncated to {file_size}.")
    else:
        pass

# Extract Date from Filename rather than file date/time
def extract_date_from_directory_name(directory_name):
    # Define a regular expression pattern to match the date part of the directory name
    pattern = r'\d{4}-\d{2}-\d{2}'

    # Search for the pattern in the directory name
    match = re.search(pattern, directory_name)

    if match:
        # Extract and return the matched date
        return match.group()
    else:
        # Return None if no date is found
        return None


# Find YML Configuration file
def find_yaml_config():

    # Get Script name, and look for YML that matches.
    current_directory = os.path.abspath(os.path.dirname(__file__))
    script_prefix = os.path.basename(__file__).split('.')[0]
    full_script_prefix = f"{current_directory}/{script_prefix}"


    # List of possible YAML filenames to check
    yaml_filenames = [f'{full_script_prefix}.yml', f'{full_script_prefix}.yaml']

    for filename in yaml_filenames:
        if os.path.isfile(filename):
            return filename

    # If no matching file is found, return None
    return None


# Check List of Files to see if any are actionable.
# ie: needing disk cleanup.
def check_files(files, files_main_settings):

    global rc_files

    # Loop through files and obtain file info to perform action against.
    for file in files:

        # Check if file has specific size limit if so use that instead of global value
        if (files[file] != {} ):
            max_filesize = int(convert_to_bytes(files[file]))
        else:
            max_filesize = int(convert_to_bytes(files_main_settings['max_filesize']))

        # Get Filesize
        fexist = os.path.exists(file)
        if (fexist == True):
            fsize = os.path.getsize(file)
            rc_files[file] = { "file_size": fsize, "file_maxsize": max_filesize }
            #print(file,fsize,max_filesize)
        else:
            rc_files[file] = { "file_size": 0, "file_maxsize": 0 }
            #print(f"{file} does not exist, not details to capture.")


    # Updates Global pydict [rc_files] with all the info needed.
    #print(rc_files)

# Truncate File Function, uses /dev/null to clear file size to not affect open file handles.
def truncate_file(filename):
    global logging

    cmd = "cat /dev/null > %s" % filename
    os.system(cmd)
    logging.info("truncate: File %s truncated to 0 bytes." % filename)


# Check if the filename matches any of the file extensions
def check_filename_pattern(filename):
    global file_extensions
    check_filename = str(filename)
    for extension in file_extensions:
        if re.search(extension, check_filename):
            return True
    return False


# New Function to cleanup Directory advanced
def advanced_cleanup_directory(directory, max_age_days, file_pattern):
    current_time = datetime.datetime.now()

    logging.info(f"[action][CHECK] : Performing Directory cleanup of directory: [{directory}], max_age_days: {max_age_days}")
    try:
        pattern = re.compile(file_pattern)
   
        for root, _, files in os.walk(directory):

            for filename in files:
                file_path = os.path.join(root, filename)
                file_age = current_time - datetime.datetime.fromtimestamp(os.path.getmtime(file_path))

                if pattern.search(filename) and file_age.days > max_age_days:
                    #logging.info(f"Found an old file: {file_path} (Age: {file_age.days} days)")
                    try:
                        os.remove(file_path)
                        logging.info(f"[action][REMOVE] : Removed old file {file_path} (Age: {file_age.days} days)")
                    except FileNotFoundError:
                        logging.info(f"[action][ENOENT] : File Not Found {file_path}")
                    except Exception as e:
                        logging.info(f"[action][ERROR] : An error occured: {e}")
                    
    except Exception as e:
        print(f"[action][ERROR] : An error occurred: {str(e)}")

# Function to Cleanup old files found in directory over XX days old. Reads
# from INI file default settings.
def directory_cleanup(directory):
    global max_fileage
    global file_extensions

    logging.info("[action][CHECK] : Starting Directory Cleanup scan of directory [%s], Max fileage: %s" % (directory,max_fileage))

    # Pickup max_fileage from INI file and get timestamp of that time ago.
    dir_max_fileage = int(f"-{max_fileage}")
    dir_max_fileage_tstamp = arrow.now().shift(hours=-7).shift(days=dir_max_fileage)

    # Loop through directory looking for files over XX age and remove.
    for item in Path(directory).glob('*'):
        if item.is_file():
            itemTime = arrow.get(item.stat().st_mtime)
            # If Filename is older than max_fileage, then remove
            if itemTime < dir_max_fileage_tstamp:
                # If Filename has the allowed extension then remove it ONLY
                if check_filename_pattern(item):
                    
                    try:
                        os.remove(item)
                        logging.info("[action][REMOVE] : Removing File %s, timestamp: %s" % (item,itemTime))
                    except PermissionError: 
                        logging.info("[action][DENIED] : Permission denied removing file %s" % (item))



# Loop through Files and cleanup what needs to be cleaned up.
def disk_cleanup():
    global rc_files
    global logging

    # Perform Disk Clean on Python Dictionary
    for file in rc_files:
        file_size = rc_files[file]['file_size']
        file_maxsize = rc_files[file]['file_maxsize']

        # If file over max_size go ahead and delete
        if ((file_size >= file_maxsize) and file_size != 0):
            logging.info("[action][CHECK] : File %s will be truncated because %s >= %s" % (file, file_size, file_maxsize))
            truncate_file(file)
        else:
            logging.info("[action][ENOENT] : Skip file %s" % file)


# Convert Disk Size (2 GiB to Bytes number for easier comparison)
def convert_to_bytes(size_str):
    '''
    Converts torrent sizes to a common count in bytes.
    '''
    size_data = size_str.split()

    multipliers = ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB']

    size_magnitude = float(size_data[0])
    multiplier_exp = multipliers.index(size_data[1])
    size_multiplier = 1024 ** multiplier_exp if multiplier_exp > 0 else 1

    return size_magnitude * size_multiplier


# Reads INI file and processes information in INI.
def readConfig(filename):

    # Parse YML configuration
    with open(filename, 'r') as yaml_file:
        config = yaml.safe_load(yaml_file)

    files_to_check = config['files']
    files_main_settings = config['main']
    directories_to_check = config['directories']
    
    # Ensure each directory has max_fileage, if missing add default value
    for directory, values in directories_to_check.items():
        try:
            values['max_fileage']
        except:
            directories_to_check[directory]['max_fileage'] = files_main_settings['max_fileage']
    

    return files_to_check, files_main_settings, directories_to_check


# Check if p1 and p2 are on the same partition, return True if they are, otherwise False
def same_partition(p1, p2):
    try:
        dev1 = os.stat(p1).st_dev
        dev2 = os.stat(p2).st_dev
        return dev1 == dev2
    except FileNotFoundError:
        return False


def disk_usage(file):
    try:
        total, used, free = shutil.disk_usage(file)
        percent = round(((total - free) / total * 100),1)
        return (total,used,free,percent)
    except FileNotFoundError:
        return None, None, None, None

# Check path and return percent used.
def partition_usage(path):

    # Get Disk Statistics
    total, used, free, percent = disk_usage(path)

    if total is None:
        return 0, 0, 0 

    # Return Values
    return total, used, percent

# Scan Directory for all Audit files and return filelist in array.
def audit_scan_files(audit_path,disk_percent):
    audit_files = []
    for filename in glob.glob(f"{audit_path}/audit.log.*"):
        audit_files.append(filename)

    sorted_audit_files = sorted(audit_files)

    # Do Loop while free space > 50% then delete a file
    # Once under 50% stop deleting and exit
    current_disk_usage = disk_percent
    while (current_disk_usage > 50):

        # Now delete a file and check disk percentage
        audit_last_file = sorted_audit_files.pop(-1)
        os.remove(audit_last_file)

        # Update Disk Usage Information
        total, used, free, percent = disk_usage(audit_path)
        current_disk_usage = percent
        logging.info("[action][REMOVE] : Removing File %s, disk_percent_after_delete: %s" % (audit_last_file,current_disk_usage))

    logging.info('AuditD : Disk Cleanup has been completed.')


# Main Function to do all /var/log/audit cleanup
def check_auditd(audit_percent=50):

    audit_path = '/var/log/audit'
    disk_total, disk_used, disk_percent = partition_usage(audit_path)
    logging.info("[action][CHECK] : Starting Directory Cleanup scan of directory [%s], Disk_Percent: %s, Disk_Purge_Percent: %s%%" % (audit_path,disk_percent,audit_percent))

    # If audit is not on different partition log about that
    if same_partition(audit_path,'/var/log') == True:
        logging.info("[action][SKIP] : /var/log/audit not on dedicated parition, skipping cleanup checks")

    # If /var/log/audit on different partition than /var/log, and disk space over 50% then purge.
    if same_partition(audit_path,'/var/log') == False and disk_percent > int(audit_percent):
        audit_scan_files(audit_path, disk_percent)


# Main Script
if __name__ == '__main__':

    myprog = 'diskcleanup'

    # Variable stuff
    script_name = os.path.basename(__file__)
    current_directory = os.path.abspath(os.path.dirname(__file__))

    # Init Config
    yml_config = find_yaml_config()
    files, files_main_settings, directories_to_check = readConfig(filename=yml_config)

    # Get Variables from INI
    dirtochk = files_main_settings["directories_to_check"]
    max_fileage = files_main_settings["max_fileage"]
    file_extensions = files_main_settings["file_extensions"]
    audit_percent = files_main_settings['audit_percent']
    abrt_maxage = files_main_settings['abrt_maxage']
    abrt_maxsize = files_main_settings['abrt_maxsize']
    abrt_directory = files_main_settings['abrt_directory']
    LOGFILE = files_main_settings['log_file']

    # Adjust Log File Path based upon if it's specific or not
    if has_slashes(LOGFILE):
        LOGFILE_PATH = LOGFILE
    else:
        LOGFILE_PATH = f"{current_directory}/{LOGFILE}"

    # Truncate log file if over 100M in size
    truncate_log_file(LOGFILE_PATH,'100M')

    # Initialize Logging
    logging.basicConfig(filename=LOGFILE_PATH, filemode='a', format='%(asctime)s|%(name)s|%(levelname)s| %(message)s', level=logging.INFO)
    logging.info(f"{script_name} [ verison: {SCRIPTVER} ] - Starting...")
    logging.info(f"{script_name} [ config_file: {yml_config} ]")
    logging.info("[settings][main]: %s" % files_main_settings)
    logging.info("[settings][directories]: %s" % directories_to_check)
    logging.info("[settings][files]: %s" % files)
    check_files(files,files_main_settings)

    # Loop through each directory and check for old files
    for dir in dirtochk:
        directory_cleanup(dir)

    # Do Disk Cleanup
    disk_cleanup()

    # Do Advanced Directory Cleanup
    for directory in directories_to_check:
        # Get Directory specific configurations
        max_fileage = directories_to_check[directory]['max_fileage']
        file_pattern = directories_to_check[directory]['file_pattern']

        # Scan Directory for files to delete and purge them
        advanced_cleanup_directory(directory, max_fileage, file_pattern)

    # AuditD Disk Cleanup
    check_auditd(audit_percent)

    # Perform ABRT Cleanups
    logging.info("[abrt][main] : Starting ABRT Cleanup...")
    logging.info(f"[abrt][settings]: Max Age: [{abrt_maxage}], Max Size: [{abrt_maxsize}]")
    logging.info(f"[abrt][age] : Checking Crash Dumps by Age")
    delete_old_abrt_directories(abrt_directory, abrt_maxage)
    logging.info(f"[abrt][size] : Checking Crash Dumps by Size")
    delete_abrt_directories_by_size(abrt_directory, abrt_maxsize)

    # Script Exit
    logging.info('Disk Cleanup has been completed.')