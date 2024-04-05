
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
| elastic_snapshot_manger.py | Script used to keep snapshot retention, expected to be ran from Cron. Purges old snapshots based upon retention periods set. |
| snapshotmgr.py | Snapshot command utility to list snapshots |

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


---
## snapshotmgr.py

> This command line utility allows you to quickly list all snapshots in the Snapshot Database and to search the list quickly by using regex.
This command line utility reads the elastic_settings.ini to know which ES to talk to.

```
usage: snapshotmgr [-h] [-debug] [-size] command [optional]

manages snapshots in elasticsearch

positional arguments:
  command          Command to run: list, etc.
  optional         Regex of pattern to search for

options:
  -h, --help       show this help message and exit
  -debug, --debug  Debug Information
  -size, --size    Show Snapshot Size

Elastic Snapshot Manager
```

Examples of usage:
> Please note if you use the --size flag, the script will have to query the ES cluster for each snapshot to obtain size information, so please expect a little bit of wait time for that to complete.
```
To List All Snapshots in Database
# ./snapshotmgr.py list


To List All Snapshots (showing Size) of kbm-kubernetes in the snapshot name.
# ./snapshotmgr.py list kbm-kubernetes --size
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┓
┃ id                                                                  ┃ status  ┃ end_time            ┃ duration ┃ total_shards ┃ snapshot_size ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━┩
│ snapshot_.ds-aex20-c01-logs-kbm-kubernetes-events-2024.01.21-000154 │ SUCCESS │ 2024-02-06 11:00:16 │ 1.8s     │ 1            │ 61.56 MB      │
│ snapshot_.ds-aex20-c01-logs-kbm-kubernetes-events-2024.01.24-000155 │ SUCCESS │ 2024-02-09 11:00:18 │ 3.8s     │ 1            │ 67.12 MB      │
│ snapshot_.ds-aex20-c01-logs-kbm-kubernetes-events-2024.01.27-000156 │ SUCCESS │ 2024-02-12 11:30:13 │ 2s       │ 1            │ 60.63 MB      │
│ snapshot_.ds-aex20-c01-logs-kbm-kubernetes-events-2024.01.30-000157 │ SUCCESS │ 2024-02-15 11:30:16 │ 5.6s     │ 1            │ 65.12 MB      │
│ snapshot_.ds-aex20-c01-logs-kbm-kubernetes-events-2024.02.02-000158 │ SUCCESS │ 2024-02-18 11:30:16 │ 1.4s     │ 1            │ 56.71 MB      │
│ snapshot_.ds-aex20-c01-logs-kbm-kubernetes-nodes-2024.01.21-000154  │ SUCCESS │ 2024-02-06 11:00:23 │ 5.8s     │ 1            │ 776.33 MB     │
│ snapshot_.ds-aex20-c01-logs-kbm-kubernetes-nodes-2024.01.24-000155  │ SUCCESS │ 2024-02-09 11:00:21 │ 5.2s     │ 1            │ 757.28 MB     │
│ snapshot_.ds-aex20-c01-logs-kbm-kubernetes-nodes-2024.01.27-000156  │ SUCCESS │ 2024-02-12 11:00:18 │ 7.1s     │ 1            │ 740.10 MB     │
│ snapshot_.ds-aex20-c01-logs-kbm-kubernetes-nodes-2024.01.30-000157  │ SUCCESS │ 2024-02-15 11:00:19 │ 7s       │ 1            │ 767.16 MB     │
│ snapshot_.ds-aex20-c01-logs-kbm-kubernetes-nodes-2024.02.02-000158  │ SUCCESS │ 2024-02-18 11:30:19 │ 8.2s     │ 1            │ 759.90 MB     │
│ snapshot_.ds-aex20-c01-logs-kbm-kubernetes-pods-2024.01.21-000154   │ SUCCESS │ 2024-02-06 11:00:19 │ 6s       │ 1            │ 193.60 MB     │
│ snapshot_.ds-aex20-c01-logs-kbm-kubernetes-pods-2024.01.24-000155   │ SUCCESS │ 2024-02-09 11:00:22 │ 6.8s     │ 1            │ 199.35 MB     │
│ snapshot_.ds-aex20-c01-logs-kbm-kubernetes-pods-2024.01.27-000156   │ SUCCESS │ 2024-02-12 11:00:19 │ 3.8s     │ 1            │ 195.51 MB     │
│ snapshot_.ds-aex20-c01-logs-kbm-kubernetes-pods-2024.01.30-000157   │ SUCCESS │ 2024-02-15 11:00:15 │ 3.2s     │ 1            │ 193.99 MB     │
│ snapshot_.ds-aex20-c01-logs-kbm-kubernetes-pods-2024.02.02-000158   │ SUCCESS │ 2024-02-18 11:30:13 │ 2.8s     │ 1            │ 199.14 MB     │
└─────────────────────────────────────────────────────────────────────┴─────────┴─────────────────────┴──────────┴──────────────┴───────────────┘
Total Snapshots in database: 15

To List Indices already restored
# ./snapshotmgr.py list-restored
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ index_name                                          ┃ osuser       ┃ restore_date                ┃ last_updated                ┃ status   ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│ .ds-aex20-c01-logs-gpn-k8s-access-2024.01.05-000051 │ devin.acosta │ 2024-02-20T13:11:05.377445Z │ 2024-02-20T13:11:06.643371Z │ restored │
│ .ds-aex20-c01-logs-tmt-k8s-access-2024.01.05-000004 │ devin.acosta │ 2024-02-20T13:11:13.680838Z │ 2024-02-20T13:11:14.932346Z │ restored │
│ .ds-aex20-c01-logs-gpt-k8s-access-2024.01.05-000023 │ devin.acosta │ 2024-02-20T13:11:21.514973Z │ 2024-02-20T13:11:22.814145Z │ restored │
│ .ds-aex20-c01-logs-gic-k8s-access-2024.01.05-000052 │ devin.acosta │ 2024-02-20T13:11:41.418213Z │ 2024-02-20T13:11:42.747752Z │ restored │
│ .ds-aex20-c01-logs-gup-k8s-access-2024.01.05-000061 │ devin.acosta │ 2024-02-20T13:11:49.609118Z │ 2024-02-20T13:11:50.940690Z │ restored │
│ .ds-aex20-c01-logs-gum-k8s-access-2024.01.05-000023 │ devin.acosta │ 2024-02-20T13:11:57.327834Z │ 2024-02-20T13:11:58.623263Z │ restored │
│ .ds-aex20-c01-logs-gap-k8s-access-2024.01.05-000027 │ devin.acosta │ 2024-02-20T13:13:40.372723Z │ 2024-02-20T13:13:41.741934Z │ restored │
│ .ds-aex20-c01-logs-gcf-k8s-access-2024.01.05-000058 │ devin.acosta │ 2024-02-20T13:13:48.395646Z │ 2024-02-20T13:13:49.720448Z │ restored │
└─────────────────────────────────────────────────────┴──────────────┴─────────────────────────────┴─────────────────────────────┴──────────┘

# To List History
# ./snapshotmgr.py list-history
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Datetime                   ┃ Username     ┃ Status       ┃ Message                                                                                                                                               ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 2024-02-16T12:52:28.902182 │ devin.acosta │ INFO         │ Query: Component: k8s-access, Date: 2024.01.05, Locations: ['DEFAULT']                                                                                │
│ 2024-02-16T12:52:47.107897 │ devin.acosta │ INFO         │ Restore Plan: 8 indice(s), 8 shard(s), with total space of : 12.64 GB                                                                                 │
│ 2024-02-16T12:54:27.108600 │ devin.acosta │ INFO         │ User cancelled restore operations!                                                                                                                    │
│ 2024-02-16T12:57:38.521840 │ devin.acosta │ INFO         │ Query: Component: k8s-access, Date: 2024.01.05, Locations: ['DEFAULT']                                                                                │
│ 2024-02-16T12:57:55.838729 │ devin.acosta │ INFO         │ Restore Plan: 8 indice(s), 8 shard(s), with total space of : 12.64 GB                                                                                 │
│ 2024-02-16T12:58:04.302731 │ devin.acosta │ INFO         │ User Accepted Restore, restore in progress...                                                                                                         │
│ 2024-02-16T12:58:05.614100 │ devin.acosta │ devin.acosta │ Processing Batch: {'.ds-aex20-c01-logs-gpn-k8s-access-2024.01.05-000051': {'location': '127.0.0.1', 'port': 9200},                                    │
│                            │              │              │ '.ds-aex20-c01-logs-tmt-k8s-access-2024.01.05-000004': {'location': '127.0.0.1', 'port': 9200},                                                       │
│                            │              │              │ '.ds-aex20-c01-logs-gpt-k8s-access-2024.01.05-000023': {'location': '127.0.0.1', 'port': 9200}}                                                       │
│ 2024-02-16T12:58:40.639296 │ devin.acosta │ devin.acosta │ Processing Batch: {'.ds-aex20-c01-logs-gic-k8s-access-2024.01.05-000052': {'location': '127.0.0.1', 'port': 9200},                                    │
│                            │              │              │ '.ds-aex20-c01-logs-gup-k8s-access-2024.01.05-000061': {'location': '127.0.0.1', 'port': 9200},                                                       │
│                            │              │              │ '.ds-aex20-c01-logs-gum-k8s-access-2024.01.05-000023': {'location': '127.0.0.1', 'port': 9200}}                                                       │
│ 2024-02-16T13:00:22.529144 │ devin.acosta │ devin.acosta │ Processing Batch: {'.ds-aex20-c01-logs-gap-k8s-access-2024.01.05-000027': {'location': '127.0.0.1', 'port': 9200},                                    │
│                            │              │              │ '.ds-aex20-c01-logs-gcf-k8s-access-2024.01.05-000058': {'location': '127.0.0.1', 'port': 9200}}                                                       │
│ 2024-02-16T13:00:50.290005 │ devin.acosta │ INFO         │ Script has completed successfully!                                                                                                                    │
│ 2024-02-20T13:02:28.512914 │ devin.acosta │ INFO         │ Query: Component: k8s-access, Date: 2024.01.05, Locations: ['DEFAULT']                                                                                │
│ 2024-02-20T13:02:46.585948 │ devin.acosta │ INFO         │ Restore Plan: 0 indice(s), 0 shard(s), with total space of : 0.00 B                                                                                   │
│ 2024-02-20T13:08:39.153034 │ devin.acosta │ INFO         │ Query: Component: k8s-access, Date: 2024.01.05, Locations: ['DEFAULT']                                                                                │
│ 2024-02-20T13:08:56.885698 │ devin.acosta │ INFO         │ Restore Plan: 8 indice(s), 8 shard(s), with total space of : 12.64 GB                                                                                 │
│ 2024-02-20T13:09:06.870929 │ devin.acosta │ INFO         │ User Accepted Restore, restore in progress...                                                                                                         │
│ 2024-02-20T13:09:08.129105 │ devin.acosta │ INFO         │ Processing Batch: {'.ds-aex20-c01-logs-gpn-k8s-access-2024.01.05-000051': {'location': '127.0.0.1', 'port': 9200},                                    │
│                            │              │              │ '.ds-aex20-c01-logs-tmt-k8s-access-2024.01.05-000004': {'location': '127.0.0.1', 'port': 9200},                                                       │
│                            │              │              │ '.ds-aex20-c01-logs-gpt-k8s-access-2024.01.05-000023': {'location': '127.0.0.1', 'port': 9200}}                                                       │
│ 2024-02-20T13:09:54.408263 │ devin.acosta │ INFO         │ Query: Component: k8s-access, Date: 2024.01.05, Locations: ['DEFAULT']                                                                                │
│ 2024-02-20T13:10:33.124330 │ devin.acosta │ INFO         │ Query: Component: k8s-access, Date: 2024.01.05, Locations: ['DEFAULT']                                                                                │
│ 2024-02-20T13:10:49.260371 │ devin.acosta │ INFO         │ Restore Plan: 8 indice(s), 8 shard(s), with total space of : 12.64 GB                                                                                 │
│ 2024-02-20T13:10:57.621526 │ devin.acosta │ INFO         │ User Accepted Restore, restore in progress...                                                                                                         │
│ 2024-02-20T13:10:59.022423 │ devin.acosta │ INFO         │ Processing Batch: {'.ds-aex20-c01-logs-gpn-k8s-access-2024.01.05-000051': {'location': '127.0.0.1', 'port': 9200},                                    │
│                            │              │              │ '.ds-aex20-c01-logs-tmt-k8s-access-2024.01.05-000004': {'location': '127.0.0.1', 'port': 9200},                                                       │
│                            │              │              │ '.ds-aex20-c01-logs-gpt-k8s-access-2024.01.05-000023': {'location': '127.0.0.1', 'port': 9200}}                                                       │
│ 2024-02-20T13:11:07.399134 │ devin.acosta │ INFO         │ Restored Snapshot snapshot_.ds-aex20-c01-logs-gpn-k8s-access-2024.01.05-000051                                                                        │
│ 2024-02-20T13:11:15.760594 │ devin.acosta │ INFO         │ Restored Snapshot snapshot_.ds-aex20-c01-logs-tmt-k8s-access-2024.01.05-000004                                                                        │
│ 2024-02-20T13:11:23.567608 │ devin.acosta │ INFO         │ Restored Snapshot snapshot_.ds-aex20-c01-logs-gpt-k8s-access-2024.01.05-000023                                                                        │
│ 2024-02-20T13:11:35.690560 │ devin.acosta │ INFO         │ Processing Batch: {'.ds-aex20-c01-logs-gic-k8s-access-2024.01.05-000052': {'location': '127.0.0.1', 'port': 9200},                                    │
│                            │              │              │ '.ds-aex20-c01-logs-gup-k8s-access-2024.01.05-000061': {'location': '127.0.0.1', 'port': 9200},                                                       │
│                            │              │              │ '.ds-aex20-c01-logs-gum-k8s-access-2024.01.05-000023': {'location': '127.0.0.1', 'port': 9200}}                                                       │
│ 2024-02-20T13:11:43.572445 │ devin.acosta │ INFO         │ Restored Snapshot snapshot_.ds-aex20-c01-logs-gic-k8s-access-2024.01.05-000052                                                                        │
│ 2024-02-20T13:11:51.715644 │ devin.acosta │ INFO         │ Restored Snapshot snapshot_.ds-aex20-c01-logs-gup-k8s-access-2024.01.05-000061                                                                        │
│ 2024-02-20T13:11:59.374100 │ devin.acosta │ INFO         │ Restored Snapshot snapshot_.ds-aex20-c01-logs-gum-k8s-access-2024.01.05-000023                                                                        │
│ 2024-02-20T13:13:34.534800 │ devin.acosta │ INFO         │ Processing Batch: {'.ds-aex20-c01-logs-gap-k8s-access-2024.01.05-000027': {'location': '127.0.0.1', 'port': 9200},                                    │
│                            │              │              │ '.ds-aex20-c01-logs-gcf-k8s-access-2024.01.05-000058': {'location': '127.0.0.1', 'port': 9200}}                                                       │
│ 2024-02-20T13:13:42.563907 │ devin.acosta │ INFO         │ Restored Snapshot snapshot_.ds-aex20-c01-logs-gap-k8s-access-2024.01.05-000027                                                                        │
│ 2024-02-20T13:13:50.522502 │ devin.acosta │ INFO         │ Restored Snapshot snapshot_.ds-aex20-c01-logs-gcf-k8s-access-2024.01.05-000058                                                                        │
│ 2024-02-20T13:14:07.420505 │ devin.acosta │ INFO         │ Script has completed successfully!                                                                                                                    │
└────────────────────────────┴──────────────┴──────────────┴───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

```

---

If you have any questions feel free to contact Devin Acosta.
