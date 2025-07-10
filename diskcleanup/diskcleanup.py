#!/usr/bin/python3
"""
# Disk Cleanup Python Script
# Written by Devin Acosta
# Version 1.3.2 07/10/2025
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
import subprocess
import yaml
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List

# Initial Variables
rc_files: Dict[str, Dict[str, int]] = {}
SCRIPTVER = "1.3.2"

"""
ABRT Functions
"""

def extract_date_from_directory_name(directory_name: str) -> Optional[datetime.datetime]:
    """
    Extracts a datetime object from a directory name using a pattern like YYYY-MM-DD-HH-MM-SS.
    Returns None if no date is found.

    Args:
        directory_name (str): The name of the directory.

    Returns:
        Optional[datetime.datetime]: The extracted datetime object, or None if not found.
    """
    pattern = r'(\d{4})[-_](\d{2})[-_](\d{2})[-_](\d{2})[-_](\d{2})[-_](\d{2})'
    match = re.search(pattern, directory_name)
    if match:
        try:
            return datetime.datetime(*map(int, match.groups()))
        except Exception:
            return None
    return None

def delete_old_abrt_directories(dump_dir: str, days_threshold: int) -> None:
    """
    Deletes ABRT directories older than a specified number of days.

    Args:
        dump_dir (str): The directory containing ABRT dumps.
        days_threshold (int): The age threshold in days.
    """
    try:
        threshold_date = datetime.datetime.now() - datetime.timedelta(days=days_threshold)
        for root, dirs, _ in os.walk(dump_dir):
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                dir_date = extract_date_from_directory_name(dir_name)
                if dir_date and dir_date < threshold_date:
                    shutil.rmtree(dir_path)
                    logging.info(f"[abrt][delete] : Removed directory: {dir_path}")
    except Exception as e:
        logging.error(f"Error deleting old ABRT directories: {e}")

def delete_old_abrt_files(dump_dir: str, days_threshold: int) -> None:
    """
    Deletes ABRT files older than a specified number of days and removes empty directories.

    Args:
        dump_dir (str): The directory containing ABRT dumps.
        days_threshold (int): The age threshold in days.
    """
    try:
        threshold_date = datetime.datetime.now() - datetime.timedelta(days=days_threshold)
        for root, _, files in os.walk(dump_dir):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                file_timestamp = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                if file_timestamp < threshold_date:
                    os.remove(file_path)
                    logging.info(f"[abrt][delete] : Deleted: {file_path}")
            if not os.listdir(root):
                os.rmdir(root)
                logging.info(f"[abrt][delete] : Removed empty directory: {root}")
    except Exception as e:
        logging.error(f"Error deleting old ABRT files: {e}")

def convert_size_to_bytes(size_str: str) -> int:
    """
    Converts a human-readable size string (e.g., '100M', '2 GiB', '1GB') to bytes.

    Args:
        size_str (str): The size string to convert.

    Returns:
        int: The size in bytes.

    Raises:
        ValueError: If the size string format is invalid.
    """
    size_str = size_str.strip().replace(' ', '')
    match = re.match(r'^(\d+(?:\.\d+)?)([KMGTP]?i?B?)$', size_str, re.IGNORECASE)
    if not match:
        logging.error("Invalid size format. Use formats like '100M', '2GiB', '1GB'.")
        raise ValueError("Invalid size format.")
    value, unit = match.groups()
    value = float(value)
    unit = unit.upper()
    multipliers = {
        'B': 1,
        'K': 1024, 'KB': 1024, 'KIB': 1024,
        'M': 1024**2, 'MB': 1024**2, 'MIB': 1024**2,
        'G': 1024**3, 'GB': 1024**3, 'GIB': 1024**3,
        'T': 1024**4, 'TB': 1024**4, 'TIB': 1024**4,
        'P': 1024**5, 'PB': 1024**5, 'PIB': 1024**5,
    }
    return int(value * multipliers.get(unit, 1))

def get_directory_size(path: str) -> int:
    """
    Recursively calculates the total size of a directory.

    Args:
        path (str): The directory path.

    Returns:
        int: The total size in bytes.
    """
    total_size = 0
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            try:
                total_size += os.path.getsize(fp)
            except OSError:
                continue
    return total_size

def delete_abrt_directories_by_size(dump_dir: str, size_threshold: str) -> None:
    """
    Deletes ABRT directories that exceed a specified size threshold.

    Args:
        dump_dir (str): The directory containing ABRT dumps.
        size_threshold (str): The size threshold (e.g., '100M').
    """
    try:
        size_threshold_bytes = convert_size_to_bytes(size_threshold)
        for root, dirs, _ in os.walk(dump_dir, topdown=False):
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                dir_size = get_directory_size(dir_path)
                if dir_size > size_threshold_bytes:
                    shutil.rmtree(dir_path)
                    logging.info(f"[abrt][delete] : Deleted directory over size limit: {dir_path}")
    except Exception as e:
        logging.error(f"An error occurred: {e}")

def has_slashes(path: str) -> bool:
    """
    Checks if a path contains slashes.

    Args:
        path (str): The path to check.

    Returns:
        bool: True if the path contains slashes, False otherwise.
    """
    return '/' in path

def truncate_log_file(filename: str, file_size: str) -> None:
    """
    Truncates a log file if it exceeds a specified size.

    Args:
        filename (str): The log file path.
        file_size (str): The maximum allowed file size (e.g., '100M').
    """
    try:
        bytes_to_compare = convert_size_to_bytes(file_size)
        actual_size = os.path.getsize(filename)
    except FileNotFoundError:
        actual_size = 0
    if actual_size > bytes_to_compare:
        with open(filename, 'r+') as file:
            file.truncate(bytes_to_compare)
        logging.info(f"File '{filename}' truncated to {file_size}.")

def find_yaml_config() -> Optional[str]:
    """
    Finds a YAML configuration file matching the script name in the current directory.

    Returns:
        Optional[str]: The path to the YAML config file, or None if not found.
    """
    current_directory = os.path.abspath(os.path.dirname(__file__))
    script_prefix = os.path.basename(__file__).split('.')[0]
    full_script_prefix = f"{current_directory}/{script_prefix}"
    yaml_filenames = [f'{full_script_prefix}.yml', f'{full_script_prefix}.yaml']
    for filename in yaml_filenames:
        if os.path.isfile(filename):
            return filename
    return None

def check_files(files: Dict[str, Any], files_main_settings: Dict[str, Any]) -> None:
    """
    Checks files for cleanup based on size limits and updates the global rc_files dictionary.

    Args:
        files (Dict[str, Any]): Dictionary of files to check.
        files_main_settings (Dict[str, Any]): Main settings for files.
    """
    global rc_files
    for file in files:
        if (files[file] != {} ):
            max_filesize = int(convert_size_to_bytes(files[file]))
        else:
            max_filesize = int(convert_size_to_bytes(files_main_settings['max_filesize']))
        fexist = os.path.exists(file)
        fsize = os.path.getsize(file) if fexist else 0
        rc_files[file] = {"file_size": fsize, "file_maxsize": max_filesize}

def truncate_file(filename: str) -> None:
    """
    Truncates a file to zero bytes using /dev/null.

    Args:
        filename (str): The file to truncate.
    """
    os.system(f"cat /dev/null > {filename}")
    logging.info(f"truncate: File {filename} truncated to 0 bytes.")

def check_filename_pattern(filename: str, file_extensions: List[str]) -> bool:
    """
    Checks if the filename matches any of the provided file extensions.

    Args:
        filename (str): The filename to check.
        file_extensions (List[str]): List of file extension patterns.

    Returns:
        bool: True if a match is found, False otherwise.
    """
    check_filename = str(filename)
    for extension in file_extensions:
        if re.search(extension, check_filename):
            return True
    return False

def advanced_cleanup_directory(directory: str, max_age_days: int, file_pattern: str) -> None:
    """
    Cleans up files in a directory matching a pattern and older than a specified age.

    Args:
        directory (str): The directory to clean.
        max_age_days (int): Maximum allowed file age in days.
        file_pattern (str): Regex pattern for files to match.
    """
    current_time = datetime.datetime.now()
    logging.info(f"[action][CHECK] : Performing Directory cleanup of directory: [{directory}], max_age_days: {max_age_days}")
    pattern = re.compile(file_pattern)
    for root, _, files in os.walk(directory):
        for filename in files:
            file_path = os.path.join(root, filename)
            try:
                file_age = current_time - datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                if pattern.search(filename) and file_age.days > max_age_days:
                    try:
                        os.remove(file_path)
                        logging.info(f"[action][REMOVE] : Removed old file {file_path} (Age: {file_age.days} days)")
                    except FileNotFoundError:
                        logging.info(f"[action][ENOENT] : File Not Found {file_path}")
                        continue
                    except Exception as e:
                        logging.info(f"[action][ERROR] : An error occured: {e}")
            except  FileNotFoundError:
                logging.info(f"[action][ERROR] : File Not Found {file_path}")
                continue

def directory_cleanup(directory: str, max_fileage: int, file_extensions: List[str]) -> None:
    """
    Cleans up files in a directory older than a specified age and matching given extensions.

    Args:
        directory (str): The directory to clean.
        max_fileage (int): Maximum allowed file age in days.
        file_extensions (List[str]): List of file extension patterns.
    """
    logging.info(f"[action][CHECK] : Starting Directory Cleanup scan of directory [{directory}], Max fileage: {max_fileage}")
    dir_max_fileage = int(f"-{max_fileage}")
    dir_max_fileage_tstamp = arrow.now().shift(hours=-7).shift(days=dir_max_fileage)
    for item in Path(directory).glob('*'):
        if item.is_file():
            itemTime = arrow.get(item.stat().st_mtime)
            if itemTime < dir_max_fileage_tstamp:
                if check_filename_pattern(item, file_extensions):
                    try:
                        os.remove(item)
                        logging.info(f"[action][REMOVE] : Removing File {item}, timestamp: {itemTime}")
                    except PermissionError:
                        logging.info(f"[action][DENIED] : Permission denied removing file {item}")

def disk_cleanup() -> None:
    """
    Performs disk cleanup by truncating files that exceed their maximum allowed size.
    """
    global rc_files
    for file in rc_files:
        file_size = rc_files[file]['file_size']
        file_maxsize = rc_files[file]['file_maxsize']
        if ((file_size >= file_maxsize) and file_size != 0):
            logging.info(f"[action][CHECK] : File {file} will be truncated because {file_size} >= {file_maxsize}")
            truncate_file(file)
        else:
            logging.info(f"[action][ENOENT] : Skip file {file}")

def readConfig(filename: str) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """
    Reads the YAML configuration file and returns its components.

    Args:
        filename (str): Path to the YAML configuration file.

    Returns:
        Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]: Files, main settings, and directories configs.
    """
    with open(filename, 'r') as yaml_file:
        config = yaml.safe_load(yaml_file)
    files_to_check = config['files']
    files_main_settings = config['main']
    directories_to_check = config['directories']
    for directory, values in directories_to_check.items():
        if 'max_fileage' not in values:
            directories_to_check[directory]['max_fileage'] = files_main_settings['max_fileage']
    return files_to_check, files_main_settings, directories_to_check

def same_partition(p1, p2):
    """
    Checks if two paths are on the same partition.

    Args:
        p1 (str): First path.
        p2 (str): Second path.

    Returns:
        bool: True if both paths are on the same partition, False otherwise.
    """
    try:
        dev1 = os.stat(p1).st_dev
        dev2 = os.stat(p2).st_dev
        return dev1 == dev2
    except FileNotFoundError:
        return False

def disk_usage(file):
    """
    Returns disk usage statistics for a given path.

    Args:
        file (str): Path to check.

    Returns:
        tuple: (total, used, free, percent) or (None, None, None, None) if not found.
    """
    try:
        total, used, free = shutil.disk_usage(file)
        percent = round(((total - free) / total * 100),1)
        return (total,used,free,percent)
    except FileNotFoundError:
        return None, None, None, None

def partition_usage(path):
    """
    Returns disk usage statistics for a partition.

    Args:
        path (str): Path to check.

    Returns:
        tuple: (total, used, percent) or (0, 0, 0) if not found.
    """
    total, used, free, percent = disk_usage(path)
    if total is None:
        return 0, 0, 0
    return total, used, percent

def audit_scan_files(audit_path, disk_percent):
    """
    Scans and deletes audit log files until disk usage drops below 50%.

    Args:
        audit_path (str): Path to audit logs.
        disk_percent (float): Current disk usage percent.
    """
    audit_files = []
    for filename in glob.glob(f"{audit_path}/audit.log.*"):
        audit_files.append(filename)
    sorted_audit_files = sorted(audit_files)
    current_disk_usage = disk_percent
    while (current_disk_usage > 50):
        audit_last_file = sorted_audit_files.pop(-1)
        os.remove(audit_last_file)
        total, used, free, percent = disk_usage(audit_path)
        current_disk_usage = percent
        logging.info("[action][REMOVE] : Removing File %s, disk_percent_after_delete: %s" % (audit_last_file,current_disk_usage))
    logging.info('AuditD : Disk Cleanup has been completed.')

def check_auditd(audit_percent=50):
    """
    Checks and cleans up audit logs if disk usage exceeds a threshold.

    Args:
        audit_percent (int, optional): Disk usage percent threshold. Defaults to 50.
    """
    audit_path = '/var/log/audit'
    disk_total, disk_used, disk_percent = partition_usage(audit_path)
    logging.info("[action][CHECK] : Starting Directory Cleanup scan of directory [%s], Disk_Percent: %s, Disk_Purge_Percent: %s%%" % (audit_path,disk_percent,audit_percent))
    if same_partition(audit_path,'/var/log') == True:
        logging.info("[action][SKIP] : /var/log/audit not on dedicated parition, skipping cleanup checks")
    if same_partition(audit_path,'/var/log') == False and disk_percent > int(audit_percent):
        audit_scan_files(audit_path, disk_percent)

def run_check_services(services):
    """
    Checks each service for open deleted file handles and restarts if needed.

    Args:
        services (list): List of service names to check.
    """
    for service in services:
        logging.info(f"[services][check] : {service}, looking for open handles. ")
        service_count = count_deleted_files_procfs(service)
        logging.info(f"[services][{service}] : {service_count} deleted open file handles.")
        if service_count > 0:
            restart_service(service)

def count_deleted_files_procfs(program_name: str) -> int:
    """
    Counts deleted files by checking the /proc filesystem for a specific program name.

    Args:
        program_name (str): Name of the program to check.

    Returns:
        int: Number of deleted files found.
    """
    deleted_count = 0
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            with open(f"/proc/{pid}/comm", "r") as comm_file:
                comm_name = comm_file.read().strip()
            if comm_name != program_name:
                continue
            fd_path = f"/proc/{pid}/fd"
            for fd in os.listdir(fd_path):
                fd_target = os.readlink(os.path.join(fd_path, fd))
                if "(deleted)" in fd_target:
                    deleted_count += 1
        except (FileNotFoundError, PermissionError):
            continue
    return deleted_count

def restart_service(service_name: str):
    """
    Restarts a systemd service using systemctl.

    Args:
        service_name (str): The name of the service to restart.
    """
    try:
        subprocess.run(["systemctl", "restart", service_name], check=True)
        logging.info(f"[service][restart] : Service '{service_name}' restarted successfully.")
    except subprocess.CalledProcessError as e:
        logging.error(f"[service][restart] : Failed to restart service '{service_name}': {e}")


# Main Script
if __name__ == '__main__':

    myprog = 'diskcleanup'

    # Variable stuff
    script_name = os.path.basename(__file__)
    current_directory = os.path.abspath(os.path.dirname(__file__))

    # Init Config
    yml_config = find_yaml_config()
    if yml_config is None:
        logging.error("No YAML configuration file found. Exiting.")
        print("No YAML configuration file found. Exiting.")
        exit(1)

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
    check_services = files_main_settings.get('check_services', [])

    # Adjust Log File Path based upon if it's specific or not
    if has_slashes(LOGFILE):
        LOGFILE_PATH = LOGFILE
    else:
        LOGFILE_PATH = f"{current_directory}/{LOGFILE}"

    # Truncate log file if over 100M in size
    truncate_log_file(LOGFILE_PATH,'100M')

    # Initialize Logging
    logging.basicConfig(filename=LOGFILE_PATH, filemode='a', format='%(asctime)s|%(name)s|%(levelname)s| %(message)s', level=logging.INFO)
    logging.info(f"{script_name} [ version: {SCRIPTVER} ] - Starting...")
    logging.info(f"{script_name} [ config_file: {yml_config} ]")
    logging.info("[settings][main]: %s" % files_main_settings)
    logging.info("[settings][directories]: %s" % directories_to_check)
    logging.info("[settings][files]: %s" % files)
    check_files(files, files_main_settings)

    # Loop through each directory and check for old files
    for dir in dirtochk:
        directory_cleanup(dir, max_fileage, file_extensions)

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
    logging.info("[abrt][age] : Checking Crash Dumps by Age")
    delete_old_abrt_directories(abrt_directory, abrt_maxage)
    logging.info("[abrt][size] : Checking Crash Dumps by Size")
    delete_abrt_directories_by_size(abrt_directory, abrt_maxsize)

    # Check Services
    if len(check_services) > 0:
        logging.info("[services][main] : Checking for open file handles.")
        run_check_services(check_services)

    # Script Exit
    logging.info('Disk Cleanup has been completed.')
