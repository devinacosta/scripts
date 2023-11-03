
This repository contains a set of scripts used to manage Elastic Search Snapshots.

**The scripts are based upon the following idea:**
- **Scripts are installed onto each cluster needing managed by using CRON jobs (i.e.: KCS node)**
- **Cluster is configured to rotate indices using ILM to a cold node for at least 1-2 days.**

> Failure to meet those requirements will render these scripts useless. 

Overview of the scripts in repo.

| Filename | Description |
| --- | --- | 
| elastic_cold_snapshots.py | Creates snapshots by comparing indices in cold status, that do NOT have matching snapshot in snapshot database. |
| elastic_restore_snapshot.py | Restores a snapshot |
| elastic_retention.yml | YAML file used for retention policies |
| elastic_servers.yml | Yaml file that should contain NAME and IP Address of all clusters being managed, used by elastic_restore_snapshot.py script. |
| elastic_settings.ini | INI configuration used by elastic_cold_snapshots.py and elastic_snapshot_manager.py to know of Elastic Search configuration settings | 
| elastic_snapshot_manger.py | Script used to keep snapshot retention. |

---

# elastic_cold_snapshots.py
> This script under normal operation would run without any parameters. The parameters are as follows:

```
usage: elastic_cold_snapshots.py [-h] [-debug] [-pattern PATTERN] [-noaction]

optional arguments:
  -h, --help        show this help message and exit
  -debug, --debug   Show Debugging Information
  -pattern PATTERN  Limit Snapshots to pattern specified
  -noaction         Stop before performing snapshots
 ```
 Examples:
 **elastic_cold_snapshots.py -pattern logs-acm -noaction**
 (Would look for cold indices with name (logs-acm) not having a snapshot and exit after displaying information.)

---
# elastic_restore_snapshot.py
> This script will restore an indice from a snapshot. It requires you to pass the [ log pattern and date ] you are looking to match.

```
python3 elastic_restore_snapshot.py  -h
usage: elastic_restore_snapshot.py [-h] [-debug] -d DATE -c COMPONENT
                                   [-l LOCATIONS] [-r REPOSITORY]

optional arguments:
  -h, --help            show this help message and exit
  -debug, --debug       Debug information
  -d DATE, --date DATE  Date of indice to restore ( Format: YYYY.mm.dd )
  -c COMPONENT, --component COMPONENT
                        Component (i.e.: logs-XXX )
  -l LOCATIONS, --locations LOCATIONS
                        Location ( defaults to localhost )
  -r REPOSITORY, --repository REPOSITORY
                        Snapshot repository to use
```

Example Usage:
This command would restore 08/14/2023 indices looking for snapshot with name logs-acm with that specified date. It accounts for the fact that indices aren't rotated possibly daily so it will find the closest match automatically. It will default to whatever cluster is listed as **DEFAULT**.
`elastic_restore_snapshot.py -d 2023.08.14 -c logs-acm`

To specify a certain cluster another example of the above but with location being specified. It will require that within the elastic_servers.txt there is entry of SJC51="IP_address_of_SJC51_KCS".
`elastic_restore_snapshot.py -d 2023.08.14 -c logs-acm -l sjc51`


---
# elastic_snapshot_manager.py
> This script will manage the snapshots created with elastic_cold_snapshots to ensure that we purge snapshots based upon some retention period. It will read the (elastic_rentention.yml) file to determine what log patterns to use and what is the oldest snapshot that should exist in the snapshot database.

Example of elastic_retention.yml
> Keep filebeat for 30 days, logs-acm for 60 days.
```
retention:
 - name: Retention for filebeat-.*
   pattern: filebeat-.*
   max_days: 30
 - name: Retention for logs-acm
   pattern: logs-acm-.*
   max_days: 60
```
---

## elastic_settings.ini
> This INI configuration file is used by both elastic_cold_snapshots.py and elastic_snapshot_manager.py, it defines the connection settings for ElasticSearch to use for the scripts. You may need to modify the hostname or port as appropriate. If your cluster uses SSL you will need to modify the value in the INI file.

```
[settings]
elastic_host = localhost
elastic_port = 9201
elastic_use_ssl = False
```

---
## elastic_servers.yml
> This configuration file is used ONLY by elastic_restore_snapshot.py, it defines a list of clusters that can be used by the script to talk to various clusters without the need to modify the script. An example of this configuration would look similar to:

```
servers:
  - name: default
    hostname: 127.0.0.1
    repository: lab-minio-backup-repos
```
The hostname can be either DNS name or IP address.


If you have any questions feel free to contact Devin Acosta.
