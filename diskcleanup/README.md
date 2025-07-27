# diskcleanup.py

This script is a comprehensive disk cleanup utility designed to help maintain clean systems with intelligent file management and detailed reporting. The utility provides robust cleanup capabilities with comprehensive logging and metrics tracking.

## Features

- **Directory Cleanup**: Remove files older than specified age with configurable file extension patterns
- **Log File Management**: Monitor and truncate log files when they exceed size limits  
- **ABRT Crash Management**: Clean up crash dumps based on age and size thresholds
- **Pattern-Based Cleanup**: Advanced directory cleanup with regex pattern matching
- **Audit Log Management**: Cleanup audit logs when disk usage exceeds thresholds
- **Service Management**: Detect and restart services with deleted file handles
- **Dry-Run Support**: Preview cleanup operations without making changes
- **Rich Logging**: Detailed operation tracking with correlation IDs and metrics
- **Health Monitoring**: Before/after system health comparison

## Architecture

The application uses a modular 3-file architecture:
- `diskcleanup.py` - Main orchestration script
- `diskcleanup_core.py` - Core business logic and cleanup functions  
- `diskcleanup_logging.py` - Logging infrastructure and metrics

## Testing

Comprehensive test scripts are provided to validate all cleanup functionality:
- `generate_test_files.sh` - Creates test files for all cleanup scenarios
- `cleanup_test_files.sh` - Removes all test files after validation
- `TEST_SCRIPTS_USAGE.md` - Complete testing documentation


## Installation of Python Modules

Install required Python Modules using the requirements.txt, Requires Python 3.6+

```bash
pip3 -r requirements.txt
```

## Usage

### Command Line Options

```bash
# Show version information
python diskcleanup.py --version
python diskcleanup.py -V

# Show version in GUI dialog (if GUI support available)
python diskcleanup.py --version-dialog

# Standard cleanup
sudo python diskcleanup.py

# Dry-run mode (preview only)
sudo python diskcleanup.py --dry-run

# Custom configuration file
sudo python diskcleanup.py --config /path/to/config.yaml

# Verbose output
sudo python diskcleanup.py --verbose
```

### Testing Your Configuration

```bash
# 1. Generate test files
sudo ./generate_test_files.sh

# 2. Run cleanup (dry-run first recommended)
sudo python diskcleanup.py --dry-run

# 3. Run actual cleanup
sudo python diskcleanup.py

# 4. Clean up test files
sudo ./cleanup_test_files.sh
```

## Installation (using CRONTAB)

For automated cleanup, install via CRON:

```bash
# Hourly cleanup
00 * * * * /opt/diskcleanup/diskcleanup.py

# Daily cleanup with logging
00 2 * * * /opt/diskcleanup/diskcleanup.py 2>&1 | logger -t diskcleanup
```

## YAML Configuration

The script reads a YAML configuration file to tell the script all the settings that it needs to know in order to function properly.

### Main Section

```yml
main:
  cleanup: true
  abrt_maxage: 30
  abrt_maxsize: 50 MB
  abrt_directory: /var/log/crash/abrt
  max_filesize: 2 GiB
  max_fileage: 30
  check_services:
    - filebeat
  file_extensions:
    - "tar.gz"
    - ".gz"
  directories_to_check:
    - "/var/log"
  audit_percent: 50
  log_file: diskcleanup.log
```
The above configuration is explained as follows:

| Config Parameter | Value |  Explanation |
| :---: | :---: | :---: |
| abrt_maxage | days | Set max file age of ABRT files |
| abrt_maxsize | size | Purge if directory over this size (MB or GB) |
| abrt_directory | directory | Directory of ABRT crash files |
| cleanup | (true,false) | (this tells the program whether or not to perform cleanup of the /var/log directory)|
| max_filesize | (KiB,MiB,GiB,TiB) | Sets file Limit Size (There must be space between value and size (i.e.: 2 GiB) |
| max_fileage | days | Set file Max Age in number of days (i.e.: 30 days) |
| check_services | List | List of services to check for deleted open file handles | 
| file_extensions | anything |  List of extensions to pay attention to, only will action files matching these extensions |
| directories_to_check | /var/log | This really should only be set to /var/log |
| audit_percent | 0-100 | Setting this value in (%) percent it will delete files until this percent of disk space is free |
| log_file | anything | Location to write the log file |

### Files Section

This section of the YAML is to list individual files that you want to monitor specifically and the max value setting for this file. If the file r

```yml
files:
  "/var/log/mysqld.log": "2 GiB"
  "/var/log/mysql/mysql-slow.log" : "3 GiB"
  "/var/log/logstash/logstash-plain.log": {}
```
In the above example of files to watch, the following will happen:
- File /var/log/mysqld.log will be truncated to 0 bytes once it reaches 2 GiB in size.
- File /var/log/mysql-slow.log will be truncated to 0 bytes once it reaches 3 GiB in size.
- File /var/log/logstash/logstash-plain.log will be truncated to 0 bytes once it reaches whatever the MAX Global setting is configured (max_filesize) which in this case is 2 GiB, so once it reaches 2 GiB it will be truncated.

### Directories Section

This section allows you to specifically individual directories to check across the filesystem and the appropriate configuration settings.

If you plan to watch multiple file REGEX patterns within a single directory, you will need to use the REGEX | parameter, something like:
**file_pattern: "[logfile1_.\*|filebeat-.\*]"**. This would look for logs beginning with logfile1_\*, or filebeat-\*.

```yml
directories:
  "/var/log/directory_1":
    file_pattern: "[log_.*\\.log]"
  "/var/log/directory_2":
    max_fileage: 3
    file_pattern: "file_.*\\.csv"
```

In the example of directories to watch, the following will happen:
- Directory /var/log/directory_1, any file that matches REGEX pattern will be deleted, since no max_fileage was provided it will default to using Global Default [max_fileage] which in this case would be 30 days.
- Directory /var/log/directory_2, any file that matches REGEX pattern will be deleted, in this case anything over 3 days.

## License

[MIT](https://choosealicense.com/licenses/mit/)
