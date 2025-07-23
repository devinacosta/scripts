#!/usr/bin/python3
"""
Disk Cleanup Utility - Main Script

A comprehensive disk cleanup solution with intelligent file management, health monitoring,
and detailed reporting capabilities. Supports dry-run analysis, pattern-based cleanup,
service restart detection, and real-time system health tracking.

Author: Devin Acosta
Version: 2.0.4
Date: 2025-07-23
License: MIT

Features:
    - Intelligent directory cleanup with configurable age and pattern matching
    - Log file size monitoring and truncation
    - System health monitoring with before/after comparison
    - ABRT crash dump management
    - Service restart for applications with deleted file handles
    - Audit log cleanup with disk usage thresholds
    - Dry-run mode with potential savings analysis
    - Rich console output with progress tracking
    - Comprehensive logging with correlation IDs
    - YAML-based configuration management

Requirements:
    - Python 3.6+
    - PyYAML, rich, arrow packages
    - Root privileges for system cleanup operations
    - Linux system with /proc filesystem

Usage:
    ./diskcleanup.py [--dry-run] [--config /path/to/config.yaml] [--verbose]

Configuration:
    See diskcleanup.yaml for configuration options and examples.
"""

import argparse
import logging
import os
import sys
import time

# Import from our modular components
from diskcleanup_logging import (
    setup_logging, OperationContext, set_current_operation_id
)
from diskcleanup_core import (
    # Core functionality
    readConfig, validate_config, setup_rc_files, find_yaml_config,
    # Cleanup operations
    directory_cleanup, advanced_cleanup_directory, disk_cleanup,
    delete_old_abrt_directories, delete_abrt_directories_by_size,
    check_auditd, run_check_services,
    # System monitoring
    check_system_health, calculate_space_freed,
    # UI functions
    print_health_comparison, print_compact_health_summary,
    # Utilities
    format_size, has_slashes, truncate_log_file,
    # Global variables
    SCRIPTVER, log, logger, global_metrics
)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Advanced disk cleanup utility with health monitoring"
    )
    parser.add_argument(
        '--dry-run', 
        action='store_true', 
        help='Show what would be cleaned without actually removing files'
    )
    parser.add_argument(
        '--config', 
        type=str, 
        help='Path to YAML configuration file'
    )
    parser.add_argument(
        '--verbose', '-v', 
        action='count', 
        default=0, 
        help='Increase verbosity (use -v or -vv)'
    )
    return parser.parse_args()

def main():
    """Main execution function."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Variable setup
    script_name = os.path.basename(__file__)
    current_directory = os.path.abspath(os.path.dirname(__file__))

    # Initialize Config
    yml_config = args.config if args.config else find_yaml_config()
    if yml_config is None:
        print("ERROR: No YAML configuration file found. Exiting.")
        sys.exit(1)

    # Read configuration
    try:
        files, files_main_settings, directories_to_check = readConfig(filename=yml_config)
    except Exception as e:
        print(f"ERROR: Failed to read configuration: {e}")
        sys.exit(1)

    # Validate configuration
    if not validate_config({"main": files_main_settings}):
        print("ERROR: Configuration validation failed. Exiting.")
        sys.exit(1)

    # Extract configuration variables
    dirtochk = files_main_settings["directories_to_check"]
    max_fileage = files_main_settings["max_fileage"]
    file_extensions = files_main_settings["file_extensions"]
    audit_percent = files_main_settings['audit_percent']
    abrt_maxage = files_main_settings['abrt_maxage']
    abrt_maxsize = files_main_settings['abrt_maxsize']
    abrt_directory = files_main_settings['abrt_directory']
    LOGFILE = files_main_settings['log_file']
    check_services = files_main_settings.get('check_services', [])

    # Adjust Log File Path
    if has_slashes(LOGFILE):
        LOGFILE_PATH = LOGFILE
    else:
        LOGFILE_PATH = f"{current_directory}/{LOGFILE}"

    # Truncate log file if over 100M in size
    truncate_log_file(LOGFILE_PATH, '100M')

    # Initialize Logging
    console, logger_helper, global_metrics_instance = setup_logging(LOGFILE_PATH, args.verbose > 0)
    
    # Set up global references in core module
    import diskcleanup_core
    diskcleanup_core.log = logging.getLogger("diskcleanup")
    diskcleanup_core.logger = logger_helper
    diskcleanup_core.global_metrics = global_metrics_instance

    # Set the session-level operation ID for all startup logging
    set_current_operation_id(global_metrics_instance.operation_id)

    # Log startup information and check initial system health
    start_time = time.time()
    health_before = check_system_health()
    diskcleanup_core.log.info(logger_helper.system(f"{script_name} v{SCRIPTVER} starting", 
                          config_file=yml_config, dry_run=args.dry_run))
    diskcleanup_core.log.info(logger_helper.system("System health check - before cleanup"))
    
    # Show initial system status
    console.rule(f"[bold cyan]🚀 Disk Cleanup v{SCRIPTVER} Starting", style="cyan")
    print_compact_health_summary(health_before, health_before)
    console.rule(style="cyan")

    # Track potential/actual space savings
    total_space_freed = 0

    # Set up file monitoring
    setup_rc_files(files, files_main_settings["max_filesize"])

    # Perform Basic Directory Cleanup
    with OperationContext("dir_cleanup", "cleanup", f"scanning_{len(dirtochk)}_dirs") as metrics:
        start_files = diskcleanup_core.global_metrics.files_processed
        start_dirs = diskcleanup_core.global_metrics.directories_processed
        for dir in dirtochk:
            space = directory_cleanup(dir, max_fileage, file_extensions, args.dry_run)
            total_space_freed += space
            metrics.bytes_freed += space
            if space > 0:
                if args.dry_run:
                    diskcleanup_core.log.info(logger_helper.dry_run(f"clean directory {dir}",
                                          potential_savings=format_size(space)))
                else:
                    diskcleanup_core.log.info(logger_helper.action(f"cleaned directory {dir}",
                                         freed=format_size(space)))
        # Sync global metrics to operation metrics
        metrics.files_processed = diskcleanup_core.global_metrics.files_processed - start_files
        metrics.directories_processed = diskcleanup_core.global_metrics.directories_processed - start_dirs

    # File size monitoring and truncation
    with OperationContext("file_truncate", "files", f"checking_{len(files)}_files") as metrics:
        start_files = diskcleanup_core.global_metrics.files_processed
        start_dirs = diskcleanup_core.global_metrics.directories_processed
        if not args.dry_run:
            space = disk_cleanup()
            total_space_freed += space
            metrics.bytes_freed += space
            if space > 0:
                diskcleanup_core.log.info(logger_helper.action("disk cleanup completed", freed=format_size(space)))
        else:
            for file in diskcleanup_core.rc_files:
                file_size = diskcleanup_core.rc_files[file]['file_size']
                file_maxsize = diskcleanup_core.rc_files[file]['file_maxsize']
                if file_size >= file_maxsize and file_size != 0:
                    space = file_size
                    total_space_freed += space
                    metrics.bytes_freed += space
                    diskcleanup_core.log.info(logger_helper.dry_run(f"truncate {file}", saving=format_size(space)))
        # Sync global metrics to operation metrics  
        metrics.files_processed = diskcleanup_core.global_metrics.files_processed - start_files
        metrics.directories_processed = diskcleanup_core.global_metrics.directories_processed - start_dirs

    # Advanced Directory Cleanup
    with OperationContext("pattern_cleanup", "cleanup", f"scanning_{len(directories_to_check)}_pattern_dirs") as metrics:
        start_files = diskcleanup_core.global_metrics.files_processed
        start_dirs = diskcleanup_core.global_metrics.directories_processed
        for directory in directories_to_check:
            # Use directory-specific max_fileage or fall back to global default
            dir_max_fileage = directories_to_check[directory].get('max_fileage', max_fileage)
            file_pattern = directories_to_check[directory]['file_pattern']
            
            space = advanced_cleanup_directory(directory, dir_max_fileage, file_pattern, args.dry_run)
            total_space_freed += space
            metrics.bytes_freed += space
            if space > 0:
                if args.dry_run:
                    diskcleanup_core.log.info(logger_helper.dry_run(f"clean {directory}",
                                          potential_savings=format_size(space)))
                else:
                    diskcleanup_core.log.info(logger_helper.action(f"advanced cleanup of {directory} completed",
                                         freed=format_size(space)))
        # Sync global metrics to operation metrics
        metrics.files_processed = diskcleanup_core.global_metrics.files_processed - start_files
        metrics.directories_processed = diskcleanup_core.global_metrics.directories_processed - start_dirs

    # AuditD Disk Cleanup
    check_auditd(audit_percent)

    # Perform ABRT Cleanups
    with OperationContext("abrt_cleanup", "abrt", abrt_directory.replace('/', '_')) as metrics:
        start_files = diskcleanup_core.global_metrics.files_processed
        start_dirs = diskcleanup_core.global_metrics.directories_processed
        diskcleanup_core.log.info(logger_helper.system("Starting ABRT cleanup", 
                              max_age=abrt_maxage, max_size=abrt_maxsize))
        diskcleanup_core.log.info(logger_helper.system("checking crash dumps by age"))
        space_age = delete_old_abrt_directories(abrt_directory, abrt_maxage, args.dry_run)
        total_space_freed += space_age
        metrics.bytes_freed += space_age
        diskcleanup_core.log.info(logger_helper.system("checking crash dumps by size"))
        space_size = delete_abrt_directories_by_size(abrt_directory, abrt_maxsize, args.dry_run)
        total_space_freed += space_size
        metrics.bytes_freed += space_size
        if space_age > 0 or space_size > 0:
            diskcleanup_core.log.info(logger_helper.action("ABRT cleanup completed", 
                                     freed=format_size(space_age + space_size)))
        # Sync global metrics to operation metrics
        metrics.files_processed = diskcleanup_core.global_metrics.files_processed - start_files
        metrics.directories_processed = diskcleanup_core.global_metrics.directories_processed - start_dirs

    # Check Services
    if len(check_services) > 0:
        with OperationContext("service_restart", "services", f"checking_{len(check_services)}_services") as metrics:
            start_files = diskcleanup_core.global_metrics.files_processed
            start_dirs = diskcleanup_core.global_metrics.directories_processed
            diskcleanup_core.log.info(logger_helper.system("Checking for open file handles", 
                                  services=len(check_services)))
            run_check_services(check_services)
            # Sync global metrics to operation metrics
            metrics.files_processed = diskcleanup_core.global_metrics.files_processed - start_files
            metrics.directories_processed = diskcleanup_core.global_metrics.directories_processed - start_dirs

    # Check system health after cleanup
    health_after = check_system_health()
    execution_time = time.time() - start_time

    # Display results
    if args.dry_run:
        # Dry run - show potential savings
        console.rule("[bold magenta]📋 Dry Run Complete - Analysis Results", style="magenta")
        
        from rich.text import Text
        from rich.panel import Panel
        from rich.align import Align
        
        savings_text = Text()
        savings_text.append("💾 Potential Space Savings\n\n", style="bold magenta")
        savings_text.append("Estimated Space to Free: ", style="bold")
        savings_text.append(format_size(total_space_freed), style="bold green")
        savings_text.append(f"\nFiles to Process: ", style="bold")
        savings_text.append(str(global_metrics_instance.files_processed), style="yellow")
        savings_text.append(f"\nDirectories to Process: ", style="bold")
        savings_text.append(str(global_metrics_instance.directories_processed), style="yellow")
        savings_text.append(f"\nAnalysis Time: ", style="bold")
        savings_text.append(f"{execution_time:.1f}s", style="cyan")
        
        panel = Panel(
            Align.center(savings_text),
            title="📊 Dry Run Summary",
            border_style="magenta",
            padding=(1, 2)
        )
        console.print(panel)
        
        diskcleanup_core.log.info(logger_helper.performance(mode="dry_run",
                                   potential_savings=format_size(total_space_freed),
                                   files_processed=global_metrics_instance.files_processed,
                                   dirs_processed=global_metrics_instance.directories_processed,
                                   errors=global_metrics_instance.errors_encountered,
                                   execution_time=f"{execution_time:.2f}s"))
        diskcleanup_core.log.info(logger_helper.system("dry run completed - no files were modified"))
    else:
        # Production run - show before/after comparison
        console.rule("[bold green]✅ Cleanup Complete - Results Summary", style="green")
        
        actual_space_freed = calculate_space_freed(health_before, health_after)
        space_freed_display = actual_space_freed if actual_space_freed > 0 else total_space_freed
        
        print_health_comparison(health_before, health_after, execution_time, space_freed_display)
        
        diskcleanup_core.log.info(logger_helper.performance(mode="production",
                                   space_freed=format_size(space_freed_display),
                                   files_processed=global_metrics_instance.files_processed,
                                   dirs_processed=global_metrics_instance.directories_processed,
                                   errors=global_metrics_instance.errors_encountered,
                                   execution_time=f"{execution_time:.2f}s"))

    # Email notification (send_notification function not implemented)
    if 'email' in files_main_settings:
        diskcleanup_core.log.info(logger_helper.system("Email notification configured but send_notification function not implemented"))

    # Script Exit
    diskcleanup_core.log.info(logger_helper.system("disk cleanup completed successfully",
                          total_execution_time=f"{execution_time:.2f}s"))

if __name__ == '__main__':
    main()

