# diskcleanup.py

This script is a very useful utility to help you keep your /var/log directory clean. It is a very powerful utility that has several capabilities. These include:

- Ability to cleanup individual directories (each with unique settings) to delete files older than XX number of days.
- Monitor Log Files and truncate once they reach XX size (MiB, GiB, TiB)
- Cleanup /var/log/audit directory once it achieves XX disk space usage and bring down to 50%.


## Installation of Python Modules

Install required Python Modules using the requirements.txt, Requires Python 3.6+

```bash
pip3 -r requirements.txt
```

## Installation (using CRONTAB)

It is assumed that you will run the script on some cadence using CRON, you can install the files into any directory that you like (ie: /opt/diskcleanup), below is to have the script run every hour (put into /etc/cron.d/diskcleanup

```python
00 * * * * /opt/diskcleanup/diskcleanup.py
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
| file_extensions | anything |  List of extensions to pay attention to, only will action files matching these extensions | 
| directories_to_check | /var/log | This really should only be set to /var/log |
| audit_percent | 0-100 | Setting this value in (%) percent it will delete files until this percent of disk space is free |
| log_file | anything | Location to write the log file |

### Files Section

This section of the YAML is to list individual files that you want to monitor specifically and the max value setting for this file. If the file reaches over the XX value it will truncate the file to 0 bytes. The table below lists some examples:

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
