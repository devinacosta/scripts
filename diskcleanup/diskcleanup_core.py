#!/usr/bin/python3
"""
Disk Cleanup Utility - Core Functions Module

This module contains all the core business logic including:
- Configuration management and validation
- File and directory cleanup operations  
- ABRT crash dump management
- System health monitoring
- Service management
- Disk usage calculations

Author: Devin Acosta
Version: 2.0.4
Date: 2025-07-23
"""

import arrow
import datetime
import glob
import logging
import json
import os
import re
import shutil
import subprocess
import sys
import time
import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List, Union
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.align import Align

# Import from our logging module
from diskcleanup_logging import LogHelper, LogSampler, OperationMetrics

# Global instances - will be initialized by main script
logger = LogHelper()
log = None  # Will be set by main script
global_metrics = None  # Will be set by main script

# Global variables
rc_files: Dict[str, Dict[str, int]] = {}
SCRIPTVER = "2.0.4"

@dataclass
class CleanupConfig:
    """Configuration settings for disk cleanup operations."""
    # Main settings
    max_fileage: int
    max_filesize: str
    audit_percent: int
    abrt_maxage: int
    abrt_maxsize: str
    abrt_directory: str
    log_file: str
    directories_to_check: List[str]
    file_extensions: List[str]
    check_services: List[str]
    
    # Files to monitor
    files: Dict[str, Any]
    
    # Advanced directory settings
    directories: Dict[str, Dict[str, Any]]
    
    @classmethod
    def from_config_dict(cls, files: Dict[str, Any], main: Dict[str, Any], directories: Dict[str, Any]) -> 'CleanupConfig':
        """Create CleanupConfig from configuration dictionaries."""
        return cls(
            max_fileage=main['max_fileage'],
            max_filesize=main['max_filesize'],
            audit_percent=main['audit_percent'],
            abrt_maxage=main['abrt_maxage'],
            abrt_maxsize=main['abrt_maxsize'],
            abrt_directory=main['abrt_directory'],
            log_file=main['log_file'],
            directories_to_check=main['directories_to_check'],
            file_extensions=main['file_extensions'],
            check_services=main.get('check_services', []),
            files=files,
            directories=directories
        )

# Utility Functions
def format_size(size_bytes: int) -> str:
    """Format bytes into human readable format."""
    if size_bytes == 0:
        return "0 B"
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024.0 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.1f} {size_names[i]}"

def convert_size_to_bytes(size_str: str) -> int:
    """Convert human readable size to bytes."""
    size_str = size_str.strip()
    if not size_str:
        return 0
    
    # Extract number and unit
    match = re.match(r'^(\d+(?:\.\d+)?)\s*([KMGT]?i?B?)$', size_str, re.IGNORECASE)
    if not match:
        raise ValueError(f"Invalid size format: {size_str}")
    
    number = float(match.group(1))
    unit = match.group(2).upper()
    
    # Convert to bytes based on unit
    multipliers = {
        'B': 1,
        'KB': 1024, 'KIB': 1024,
        'MB': 1024**2, 'MIB': 1024**2,
        'GB': 1024**3, 'GIB': 1024**3,
        'TB': 1024**4, 'TIB': 1024**4
    }
    
    if unit in multipliers:
        return int(number * multipliers[unit])
    else:
        # Default to bytes if no unit specified
        return int(number)

def has_slashes(filename: str) -> bool:
    """Check if filename contains slashes (absolute path)."""
    return '/' in filename

# ABRT Functions
def extract_date_from_directory_name(directory_name: str) -> Optional[datetime.datetime]:
    """
    Extracts a datetime object from a directory name using a pattern like YYYY-MM-DD-HH-MM-SS.
    Returns None if no date is found.
    """
    pattern = r'(\d{4})[-_](\d{2})[-_](\d{2})[-_](\d{2})[-_](\d{2})[-_](\d{2})'
    match = re.search(pattern, directory_name)
    if match:
        try:
            return datetime.datetime(*map(int, match.groups()))
        except Exception:
            return None
    return None

def simulate_cleanup(directory: str) -> int:
    """Simulate cleanup and return estimated space freed."""
    total_size = 0
    try:
        for root, dirs, files in os.walk(directory):
            for file in files:
                filepath = os.path.join(root, file)
                try:
                    total_size += os.path.getsize(filepath)
                except (OSError, IOError):
                    continue
    except (OSError, IOError):
        pass
    return total_size

def delete_old_abrt_directories(abrt_directory: str, max_age_days: int, dry_run: bool = False) -> int:
    """
    Delete ABRT directories older than max_age_days.
    """
    if not os.path.exists(abrt_directory):
        log.warning(logger.system(f"ABRT directory does not exist: {abrt_directory}"))
        return 0
    
    space_freed = 0
    threshold_date = datetime.datetime.now() - datetime.timedelta(days=max_age_days)
    
    try:
        for dump_dir in os.listdir(abrt_directory):
            dir_path = os.path.join(abrt_directory, dump_dir)
            if os.path.isdir(dir_path):
                # Extract date from directory name
                dir_date = extract_date_from_directory_name(dump_dir)
                if dir_date and dir_date < threshold_date:
                    age_days = (datetime.datetime.now() - dir_date).days
                    if dry_run:
                        freed = simulate_cleanup(dir_path)
                        space_freed += freed
                        global_metrics.add_directory(freed)
                        log.info(logger.dry_run(f"remove directory {dir_path}", 
                                               size=format_size(freed), operation="age_cleanup"))
                    else:
                        freed = simulate_cleanup(dir_path)
                        space_freed += freed
                        shutil.rmtree(dir_path)
                        global_metrics.add_directory()
                        log.info(logger.action(f"removed directory {dir_path}", 
                                              size=format_size(freed), operation="age_cleanup"))
    except Exception as e:
        log.error(logger.error_with_context(abrt_directory, e))
        global_metrics.add_error()
    
    return space_freed

def cleanup_empty_abrt_directories(abrt_directory: str) -> None:
    """Clean up empty ABRT directories and old files."""
    try:
        for root, dirs, files in os.walk(abrt_directory, topdown=False):
            # Clean up old files first
            for file_name in files:
                file_path = os.path.join(root, file_name)
                try:
                    file_timestamp = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                    threshold_date = datetime.datetime.now() - datetime.timedelta(days=30)
                    
                    if file_timestamp < threshold_date:
                        os.remove(file_path)
                        log.info(logger.action(f"deleted file {file_path}"))
                        global_metrics.add_file()
                except Exception:
                    continue
            
            # Remove empty directories
            if not os.listdir(root):
                os.rmdir(root)
                log.info(logger.action(f"removed empty directory {root}"))
                global_metrics.add_directory()
    except Exception as e:
        log.error(logger.error_with_context(abrt_directory, e))
        global_metrics.add_error()

def delete_abrt_directories_by_size(abrt_directory: str, max_size: str, dry_run: bool = False) -> int:
    """Delete ABRT directories when total size exceeds max_size."""
    if not os.path.exists(abrt_directory):
        return 0
    
    size_threshold_bytes = convert_size_to_bytes(max_size)
    space_freed = 0
    
    try:
        directories_with_sizes = []
        for dump_dir in os.listdir(abrt_directory):
            dir_path = os.path.join(abrt_directory, dump_dir)
            if os.path.isdir(dir_path):
                try:
                    dir_size = sum(
                        os.path.getsize(os.path.join(dirpath, filename))
                        for dirpath, dirnames, filenames in os.walk(dir_path)
                        for filename in filenames
                    )
                    directories_with_sizes.append((dir_path, dir_size))
                except (OSError, IOError):
                    continue
        
        # Sort by size (largest first) and delete until under threshold
        directories_with_sizes.sort(key=lambda x: x[1], reverse=True)
        total_size = sum(size for _, size in directories_with_sizes)
        
        for dir_path, dir_size in directories_with_sizes:
            if total_size > size_threshold_bytes:
                if dry_run:
                    space_freed += dir_size
                    global_metrics.add_directory(dir_size)
                    log.info(logger.dry_run(f"remove directory over size limit {dir_path}", 
                                           size=format_size(dir_size), operation="size_cleanup"))
                else:
                    shutil.rmtree(dir_path)
                    space_freed += dir_size
                    global_metrics.add_directory()
                    log.info(logger.action(f"deleted directory over size limit {dir_path}", 
                                          size=format_size(dir_size)))
                total_size -= dir_size
    except Exception as e:
        log.error(logger.error_with_context(dump_dir, e))
        global_metrics.add_error()
    
    return space_freed

# File Operations
def truncate_log_file(filename: str, file_size: str) -> None:
    """
    Truncates a log file if it exceeds a specified size.
    """
    try:
        bytes_to_compare = convert_size_to_bytes(file_size)
        actual_size = os.path.getsize(filename)
    except FileNotFoundError:
        actual_size = 0
    if actual_size > bytes_to_compare:
        with open(filename, 'r+') as file:
            file.truncate(bytes_to_compare)
        # Only log if logging system is available
        if log is not None:
            log.info(logger.action(f"truncated file {filename}",
                                  target_size=file_size))

def find_yaml_config() -> Optional[str]:
    """Find YAML configuration file in current directory."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    possible_configs = [
        os.path.join(current_dir, 'diskcleanup.yaml'),
        os.path.join(current_dir, 'diskcleanup.yml'),
        os.path.join(current_dir, 'config.yaml'),
        os.path.join(current_dir, 'config.yml')
    ]
    
    for config_path in possible_configs:
        if os.path.exists(config_path):
            return config_path
    return None

def truncate_file(filename: str) -> None:
    """Truncate a file to 0 bytes."""
    try:
        with open(filename, 'w') as f:
            f.truncate(0)
        log.info(logger.action(f"truncated file {filename} to 0 bytes"))
        global_metrics.add_file()
    except (OSError, IOError) as e:
        log.error(logger.error_with_context(filename, e))
        global_metrics.add_error()

def check_filename_pattern(file_path: Path, file_extensions: List[str]) -> bool:
    """Check if a file matches any of the specified extensions."""
    filename = file_path.name
    for extension in file_extensions:
        # Support regex patterns
        if re.search(extension, filename):
            return True
    return False

# Directory Cleanup Functions
def advanced_cleanup_directory(directory: str, max_age_days: int, file_pattern: str, dry_run: bool = False) -> int:
    """
    Performs advanced cleanup of a directory based on file age and regex pattern.
    """
    if not os.path.exists(directory):
        log.warning(f"Directory does not exist: {directory}")
        return 0
    
    space_freed = 0
    current_time = datetime.datetime.now()
    threshold_date = current_time - datetime.timedelta(days=max_age_days)
    
    log.info(logger.system(f"starting directory cleanup for {directory}",
                          max_age=max_age_days, pattern=file_pattern))
    
    try:
        pattern = re.compile(file_pattern)
        directory_path = Path(directory)
        
        if not directory_path.exists():
            log.warning(f"Directory does not exist: {directory}")
            return 0
        
        # Use pathlib's rglob for more efficient recursive search with sampling
        sampler = LogSampler(50)  # Log every 50th file for large operations
        files_processed = 0
        
        for file_path in directory_path.rglob('*'):
            if file_path.is_file():
                files_processed += 1
                try:
                    if pattern.search(file_path.name):
                        file_mtime = datetime.datetime.fromtimestamp(file_path.stat().st_mtime)
                        if file_mtime < threshold_date:
                            file_size = file_path.stat().st_size
                            age_days = (current_time - file_mtime).days
                            
                            if dry_run:
                                space_freed += file_size
                                global_metrics.add_file(file_size)
                                if sampler.should_log():
                                    log.info(logger.dry_run(f"remove file {file_path}", 
                                                           age_days=age_days, size=format_size(file_size)))
                            else:
                                file_path.unlink()
                                space_freed += file_size
                                global_metrics.add_file(file_size)
                                if sampler.should_log():
                                    log.info(logger.action(f"removed old file {file_path}", 
                                                          age_days=age_days, size=format_size(file_size)))
                        # Progress logging for large operations
                        if files_processed % 1000 == 0:
                            log.debug(logger.progress(files_processed, files_processed + 1000,
                                                     directory=directory))
                except (OSError, FileNotFoundError) as e:
                    log.debug(logger.error_with_context(str(file_path), e))
                    global_metrics.add_error()
                    continue
                    
        log.info(logger.system(f"completed cleanup for {directory}", 
                              files_processed=files_processed, space_freed=format_size(space_freed)))
        
    except Exception as e:
        log.error(logger.error_with_context(directory, e))
        global_metrics.add_error()
    
    return space_freed

def directory_cleanup(directory: str, max_fileage: int, file_extensions: List[str], dry_run: bool = False) -> int:
    """
    Performs cleanup of files in a directory based on age and extensions.
    """
    space_freed = 0
    log.info(logger.system(f"starting cleanup for {directory}",
                          max_age=max_fileage, extensions=file_extensions))
    
    dir_max_fileage = int(f"-{max_fileage}")
    dir_max_fileage_tstamp = arrow.now().shift(hours=-7).shift(days=dir_max_fileage)
    
    sampler = LogSampler(25)  # Log every 25th file
    
    for item in Path(directory).glob('*'):
        if item.is_file():
            itemTime = arrow.get(item.stat().st_mtime)
            if itemTime < dir_max_fileage_tstamp:
                if check_filename_pattern(item, file_extensions):
                    try:
                        file_size = os.path.getsize(item)
                        age_days = (arrow.now() - itemTime).days
                        if dry_run:
                            space_freed += file_size
                            global_metrics.add_file(file_size)
                            if sampler.should_log():
                                log.info(logger.dry_run(f"remove file {item}", 
                                                       age_days=age_days, size=format_size(file_size)))
                        else:
                            os.remove(item)
                            space_freed += file_size
                            global_metrics.add_file(file_size)
                            if sampler.should_log():
                                log.info(logger.action(f"removed file {item}", 
                                                      age_days=age_days, size=format_size(file_size)))
                    except PermissionError:
                        log.warning(logger.system(f"permission denied removing file {item}"))
                        global_metrics.add_error()
    return space_freed

# Disk Operations
def disk_cleanup() -> int:
    """
    Performs disk cleanup by truncating files that exceed their maximum allowed size.
    """
    global rc_files
    space_freed = 0
    for file in rc_files:
        file_size = rc_files[file]['file_size']
        file_maxsize = rc_files[file]['file_maxsize']
        if ((file_size >= file_maxsize) and file_size != 0):
            log.info(logger.action(f"truncating file {file}", 
                                  current_size=format_size(file_size), 
                                  max_size=format_size(file_maxsize)))
            space_freed += file_size
            truncate_file(file)
        else:
            log.debug(logger.system(f"skipping file {file} (within size limit)", 
                                   current_size=format_size(file_size)))
    return space_freed

# Configuration Functions
def readConfig(filename: str) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    try:
        with open(filename, 'r') as yaml_file:
            config = yaml.safe_load(yaml_file)
            
        required_keys = ['files', 'main', 'directories']
        missing_keys = [key for key in required_keys if key not in config]
        if missing_keys:
            raise KeyError(f"Missing required configuration sections: {', '.join(missing_keys)}")
            
        return config['files'], config['main'], config['directories']
    except yaml.YAMLError as e:
        if log is not None:
            log.error(logger.config("failed to parse YAML configuration", error=str(e)))
        raise
    except Exception as e:
        if log is not None:
            log.error(logger.config("failed to read configuration file", error=str(e)))
        raise

def setup_rc_files(files: Dict[str, Any], max_filesize: str) -> None:
    """Set up the global rc_files dictionary."""
    global rc_files
    rc_files = {}
    
    for filename, file_config in files.items():
        try:
            file_size = os.path.getsize(filename) if os.path.exists(filename) else 0
            
            if isinstance(file_config, dict) and file_config:
                file_maxsize = convert_size_to_bytes(file_config.get('max_size', max_filesize))
            elif isinstance(file_config, str):
                file_maxsize = convert_size_to_bytes(file_config)
            else:
                file_maxsize = convert_size_to_bytes(max_filesize)
            
            rc_files[filename] = {
                'file_size': file_size,
                'file_maxsize': file_maxsize
            }
        except Exception as e:
            if log is not None:
                log.warning(logger.config(f"failed to process file {filename}", error=str(e)))

# System Health and Monitoring Functions
def check_system_health() -> Dict[str, Dict[str, Union[str, int, float]]]:
    """Check system health including disk usage for all mount points."""
    health_data = {}
    
    try:
        # Get all mount points
        result = subprocess.run(['df', '-h'], capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')[1:]  # Skip header
        
        for line in lines:
            parts = line.split()
            if len(parts) >= 6:
                filesystem = parts[0]
                size = parts[1]
                used = parts[2]
                available = parts[3]
                percent_used_str = parts[4].rstrip('%')
                mount_point = parts[5]
                
                # Skip special filesystems
                if mount_point.startswith(('/dev', '/sys', '/proc', '/run')) or filesystem.startswith('tmpfs'):
                    continue
                
                try:
                    percent_used = int(percent_used_str)
                except ValueError:
                    percent_used = 0
                
                health_data[mount_point] = {
                    'filesystem': filesystem,
                    'size': size,
                    'used': used,
                    'available': available,
                    'percent_used': percent_used,
                    'status': get_health_status(percent_used)
                }
    except subprocess.CalledProcessError as e:
        log.error(logger.error_with_context("df command", e))
    except Exception as e:
        log.error(logger.error_with_context("system health check", e))
    
    return health_data

def get_health_status(percent_used: int) -> str:
    """Get health status based on disk usage percentage."""
    if percent_used >= 95:
        return "Critical"
    elif percent_used >= 85:
        return "Warning"
    elif percent_used >= 75:
        return "Caution"
    else:
        return "Good"

def partition_usage(path: str) -> Tuple[int, int, float]:
    """Get partition usage for a given path."""
    try:
        statvfs = os.statvfs(path)
        total = statvfs.f_frsize * statvfs.f_blocks
        free = statvfs.f_frsize * statvfs.f_bavail
        used = total - free
        percent = (used / total) * 100 if total > 0 else 0
        return total, used, percent
    except OSError:
        return 0, 0, 0.0

def disk_usage(path: str) -> Tuple[int, int, int, float]:
    """Get disk usage for a path."""
    try:
        statvfs = os.statvfs(path)
        total = statvfs.f_frsize * statvfs.f_blocks
        free = statvfs.f_frsize * statvfs.f_bavail
        used = total - free
        percent = (used / total) * 100 if total > 0 else 0
        return total, used, free, percent
    except OSError:
        return 0, 0, 0, 0.0

def same_partition(path1: str, path2: str) -> bool:
    """Check if two paths are on the same partition."""
    try:
        stat1 = os.stat(path1)
        stat2 = os.stat(path2)
        return stat1.st_dev == stat2.st_dev
    except OSError:
        return False

def calculate_space_freed(health_before: Dict, health_after: Dict) -> int:
    """Calculate actual space freed based on health data."""
    total_freed = 0
    for mount_point in health_before:
        if mount_point in health_after:
            try:
                used_before = health_before[mount_point]['used']
                used_after = health_after[mount_point]['used']
                
                # Convert human readable sizes to bytes for calculation
                before_bytes = convert_size_to_bytes(used_before)
                after_bytes = convert_size_to_bytes(used_after)
                
                if before_bytes > after_bytes:
                    total_freed += (before_bytes - after_bytes)
            except (KeyError, ValueError):
                continue
    return total_freed

# Audit Functions
def audit_scan_files(audit_path, disk_percent):
    """
    Scans and deletes audit log files until disk usage drops below 50%.
    """
    audit_files = []
    for filename in glob.glob(f"{audit_path}/audit.log.*"):
        audit_files.append(filename)
    sorted_audit_files = sorted(audit_files)
    current_disk_usage = disk_percent
    
    while current_disk_usage > 50 and sorted_audit_files:
        audit_last_file = sorted_audit_files.pop(-1)
        os.remove(audit_last_file)
        total, used, free, percent = disk_usage(audit_path)
        current_disk_usage = percent
        log.info(logger.action(f"removed file {audit_last_file}", 
                               disk_usage_after=f"{current_disk_usage}%"))
        global_metrics.add_file()
    
    log.info(logger.system("disk cleanup completed"))

def check_auditd(audit_percent=50):
    """
    Checks and cleans up audit logs if disk usage exceeds a threshold.
    """
    audit_path = '/var/log/audit'
    disk_total, disk_used, disk_percent = partition_usage(audit_path)
    
    log.info(logger.system(f"starting audit cleanup for {audit_path}", 
                          current_usage=f"{disk_percent}%", threshold=f"{audit_percent}%"))
    
    if same_partition(audit_path,'/var/log'):
        log.warning(logger.system("/var/log/audit not on dedicated partition, skipping cleanup checks"))
    elif disk_percent > int(audit_percent):
        audit_scan_files(audit_path, disk_percent)

# Service Management Functions
def count_deleted_files_procfs(service_name: str) -> int:
    """Count deleted open file handles for a service using /proc filesystem."""
    count = 0
    try:
        pids = subprocess.check_output(['pgrep', service_name], text=True).strip().split('\n')
        for pid in pids:
            if pid:
                try:
                    fd_dir = f"/proc/{pid}/fd"
                    if os.path.exists(fd_dir):
                        for fd in os.listdir(fd_dir):
                            try:
                                link_target = os.readlink(os.path.join(fd_dir, fd))
                                if '(deleted)' in link_target:
                                    count += 1
                            except (OSError, IOError):
                                continue
                except (OSError, IOError):
                    continue
    except subprocess.CalledProcessError:
        # Service not running
        pass
    except Exception as e:
        log.debug(logger.error_with_context(f"count_deleted_files for {service_name}", e))
    
    return count

def run_check_services(services):
    """
    Checks each service for open deleted file handles and restarts if needed.
    """
    for service in services:
        log.info(logger.system(f"checking {service} for open file handles"))
        service_count = count_deleted_files_procfs(service)
        log.info(logger.system(f"found {service_count} deleted open file handles", 
                              service=service))
        if service_count > 0:
            restart_service(service)

def restart_service(service_name: str) -> None:
    """Restart a systemd service."""
    try:
        subprocess.run(["systemctl", "restart", service_name], check=True)
        log.info(logger.action(f"restarted service {service_name} successfully"))
    except subprocess.CalledProcessError as e:
        log.error(logger.error_with_context(service_name, e))
        global_metrics.add_error()

# Configuration Validation
def validate_config(config: Dict[str, Any]) -> bool:
    """Enhanced configuration validation with detailed checks."""
    try:
        main_config = config['main']
        
        # Validate required fields
        required_fields = ['max_fileage', 'max_filesize', 'directories_to_check', 'file_extensions']
        missing_fields = [field for field in required_fields if field not in main_config]
        if missing_fields:
            if log is not None:
                log.error(logger.config("validation failed - missing required fields", 
                                       missing_fields=missing_fields))
            return False
        
        # Validate data types and ranges
        if not isinstance(main_config['max_fileage'], int) or main_config['max_fileage'] <= 0:
            if log is not None:
                log.error(logger.config("validation failed - max_fileage must be a positive integer"))
            return False
            
        if not isinstance(main_config['audit_percent'], int) or not (0 <= main_config['audit_percent'] <= 100):
            if log is not None:
                log.error(logger.config("validation failed - audit_percent must be an integer between 0 and 100"))
            return False
        
        # Validate file size format
        try:
            convert_size_to_bytes(main_config['max_filesize'])
        except ValueError as e:
            if log is not None:
                log.error(logger.config("validation failed - invalid max_filesize format", error=str(e)))
            return False
        
        # Validate directories exist
        missing_dirs = []
        for dir_path in main_config['directories_to_check']:
            if not os.path.exists(dir_path):
                missing_dirs.append(dir_path)
        
        if missing_dirs:
            if log is not None:
                log.warning(logger.config("directories do not exist", missing_dirs=missing_dirs))
            # Don't fail validation, just warn
                
        return True
    except Exception as e:
        if log is not None:
            log.error(logger.config("validation failed with exception", error=str(e)))
        return False

# UI and Display Functions
def print_health_comparison(health_before: Dict, health_after: Dict, execution_time: float, space_freed: int) -> None:
    """Print a professional side-by-side comparison of system health."""
    console = Console()
    
    # Create comparison table
    table = Table(title="🏥 System Health Comparison - Before vs After Cleanup", show_header=True, header_style="bold magenta")
    table.add_column("Mount Point", justify="left", style="cyan", width=12)
    table.add_column("Before", justify="center", style="red", width=15)
    table.add_column("After", justify="center", style="green", width=15)
    table.add_column("Freed", justify="center", style="bold green", width=12)
    table.add_column("Improvement", justify="center", style="bold yellow", width=12)
    
    # Add rows for each mount point
    for mount_point in sorted(health_before.keys()):
        if mount_point in health_after:
            before_pct = health_before[mount_point]['percent_used']
            after_pct = health_after[mount_point]['percent_used']
            
            # Calculate improvement
            improvement = before_pct - after_pct
            improvement_str = f"-{improvement:.1f}%" if improvement > 0 else "0%"
            
            # Get status indicators
            before_status = health_before[mount_point]['status']
            after_status = health_after[mount_point]['status']
            
            # Color coding for status
            before_color = {"Good": "green", "Caution": "yellow", "Warning": "orange", "Critical": "red"}.get(before_status, "white")
            after_color = {"Good": "green", "Caution": "yellow", "Warning": "orange", "Critical": "red"}.get(after_status, "white")
            
            table.add_row(
                mount_point,
                f"[{before_color}]{before_pct}% ({before_status})[/{before_color}]",
                f"[{after_color}]{after_pct}% ({after_status})[/{after_color}]",
                format_size(space_freed) if improvement > 0 else "0 B",
                f"[bold green]{improvement_str}[/bold green]" if improvement > 0 else "[dim]0%[/dim]"
            )
    
    console.print()
    console.print(table)
    
    # Summary panel
    summary_text = Text()
    summary_text.append("📊 Cleanup Summary\n\n", style="bold")
    summary_text.append("Files Processed: ", style="bold")
    summary_text.append(f"{global_metrics.files_processed:,}", style="cyan")
    summary_text.append("  •  ", style="dim")
    summary_text.append("Space Freed: ", style="bold")
    summary_text.append(format_size(space_freed), style="green")
    summary_text.append("  •  ", style="dim")
    summary_text.append("Execution Time: ", style="bold")
    summary_text.append(f"{execution_time:.1f}s", style="yellow")
    
    if global_metrics.errors_encountered > 0:
        summary_text.append("\n⚠️ Errors: ", style="bold red")
        summary_text.append(str(global_metrics.errors_encountered), style="red")
    
    panel = Panel(
        Align.center(summary_text),
        title="✅ Operation Complete",
        border_style="green",
        padding=(1, 2)
    )
    console.print(panel)

def print_compact_health_summary(health_before: Dict, health_after: Dict) -> None:
    """Print a compact system health summary."""
    console = Console()
    
    summary_text = Text()
    summary_text.append("🖥️ System Status: ", style="bold")
    
    critical_mounts = [mp for mp, data in health_before.items() if data['percent_used'] >= 90]
    if critical_mounts:
        summary_text.append(f"{len(critical_mounts)} critical mount(s)", style="bold red")
    else:
        summary_text.append("All systems nominal", style="bold green")
    
    # Show highest usage mount
    if health_before:
        highest_usage = max(health_before.items(), key=lambda x: x[1]['percent_used'])
        mount_point, data = highest_usage
        summary_text.append(f" • Highest usage: {mount_point} ({data['percent_used']}%)", style="yellow")
    
    console.print(summary_text) 