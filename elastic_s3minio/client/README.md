This directory contains the 'client' set of scripts used to Restore Indices and to check on status of restores.

Overview of the scripts in this directory.

| Filename | Description |
| --- | --- |
| `elastic_restore_snapshot.py` | Restores a snapshot |
| `snapshotmgr.py` | Snapshot command utility to list snapshots, check status, and show history. |


---
## `elastic_restore_snapshot.py`
> This script will restore an indice from a snapshot.
> It requires you to pass 2 parameters: [ **log pattern** and **date** ] you are looking to match.

```
./elastic_restore_snapshot.py -h
usage: elastic_restore_snapshot.py [-h] [-debug] -d DATE -c COMPONENT [-l LOCATIONS] [-r REPOSITORY] [-t] [-b BATCH] [-m MAXSHARDS] [-n]

options:
  -h, --help            show this help message and exit
  -debug, --debug       Debug information
  -d DATE, --date DATE  Date of indice to restore ( Format: YYYY.mm.dd )
  -c COMPONENT, --component COMPONENT
                        Component (i.e.: logs-XXX )
  -l LOCATIONS, --locations LOCATIONS
                        Location ( defaults to localhost )
  -r REPOSITORY, --repository REPOSITORY
                        Snapshot repository to use
  -n, --dryrun          Perform Dry Run, do not execute.
```

Example Usage:

This command would restore 08/14/2023 indices looking for snapshot with name logs-acm with that specified date. It accounts for the fact that indices aren't rotated possibly daily so it will find the closest match automatically. It will default to whatever cluster is listed as **DEFAULT**.
`elastic_restore_snapshot.py -d 2024.01.18 -c k8s-access`

If you want to just perform a **DRY RUN** without actually doing any restore (use option **-n**)
`elastic_restore_snapshot.py -d 2024.01.18 -c k8s-access -n`

To specify a certain cluster another example of the above but with location being specified. It will require that within the elastic_servers.txt there is entry of SJC51="IP_address_of_SJC51_KCS".
`elastic_restore_snapshot.py -d 2024.01.18 -c logs-acm -l sjc51`

After executing the above command, the script will attempt to find matching Snapshots to meet the criteria. If a match is found it will perform (3) basic cluster checks to ensure a successful restoration.

Check 1: Cluster  "GREEN" status. The cluster must be in GREEN status otherwise the restore attempt will fail.
Check 2: Cluster "Shards Check". This will ensure we have enough Shards in cluster without overwhelming the entire cluster.
Check 3: Cluster "Storage Check". This will ensure that the cluster has enough disk space to restore the requested indices.

Assuming all (3) above checks pass you will see the restoration plan, along with a prompt asking if you want to restore the snapshot.

```
                                               Snapshot matches
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ Repository   ┃ Snapshot Name                                                ┃ Count ┃       Size ┃ Restored ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━┩
│ DEFAULT/9200 │ snapshot_.ds-aex20-c01-logs-gpm-k8s-access-2024.01.18-000059 │     1 │    1.65 GB │    False │
│ DEFAULT/9200 │ snapshot_.ds-aex20-c01-logs-gsb-k8s-access-2024.01.18-000065 │     1 │  655.90 MB │    False │
│ DEFAULT/9200 │ snapshot_.ds-aex20-c01-logs-gas-k8s-access-2024.01.18-000069 │     1 │   11.43 GB │    False │
│ DEFAULT/9200 │ snapshot_.ds-aex20-c01-logs-gpe-k8s-access-2024.01.18-000021 │     1 │    1.23 GB │    False │
│ DEFAULT/9200 │ snapshot_.ds-aex20-c01-logs-gwh-k8s-access-2024.01.18-000021 │     1 │    1.71 GB │    False │
│ DEFAULT/9200 │ snapshot_.ds-aex20-c01-logs-gpp-k8s-access-2024.01.18-000054 │     1 │    1.51 GB │    False │
│ DEFAULT/9200 │ snapshot_.ds-aex20-c01-logs-gpc-k8s-access-2024.01.18-000057 │     1 │    1.52 GB │    False │
│ DEFAULT/9200 │ snapshot_.ds-aex20-c01-logs-ira-k8s-access-2024.01.18-000017 │     1 │    7.00 GB │    False │
│ DEFAULT/9200 │ snapshot_.ds-aex20-c01-logs-ppc-k8s-access-2024.01.18-000048 │     1 │  103.83 MB │    False │
└──────────────┴──────────────────────────────────────────────────────────────┴───────┴────────────┴──────────┘
                     Restore Plan: 9 indice(s), 9 shard(s), with total space of : 26.79 GB
           ES Cluster Health: green, Data Nodes: 7 (940), Storage: avail: 6.29 TB / Total: 11.91 TB


✔ Cluster Health Check: Passed (green)
✔ Shard Allocation Check: Passed
✔ Storage Allocation Checks: Passed
Only Indices with Restored status of 'False' will be restored.
Would you like to restore these Snapshots? [y/n]:
```
*Note: You will want to answer [yes|no] in a reasonable amount of time.  Once you have reached this prompt it will prevent any other user from trying to do a restore job, until you cancel out or restore the indices. This is to prevent from multiple users doing restores into the cluster at the same time.*

You can check on your restore status by using the **snapshotmgr.py** script. See below for further details.




---
## `snapshotmgr.py`

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

Snapshot Manager (command arguments)
| Command | Description |
| --- | --- |
| list | List all snapshots available in database. |
| list-restored | Show Restored Indices |
| list-status | Show Restoration Status |
| list-history | Show History of all Restore Operations |
| clear-staged | Clear Database of any Staged Restorations so database can be unlocked to other users requests.|


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
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Datetime                   ┃ Username     ┃ Status ┃ Message                                                                     ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 2024-03-06T15:03:43.114894 │ devin.acosta │ INFO   │ Query: Component: logs-png-system, Date: 2024.02.05, Locations: ['DEFAULT'] │
├────────────────────────────┼──────────────┼────────┼─────────────────────────────────────────────────────────────────────────────┤
│ 2024-03-06T15:03:55.551972 │ devin.acosta │ INFO   │ Restore Plan: 1 indice(s), 1 shard(s), with total space of : 4.21 MB        │
├────────────────────────────┼──────────────┼────────┼─────────────────────────────────────────────────────────────────────────────┤
│ 2024-03-06T15:04:07.034532 │ devin.acosta │ INFO   │ Query: Component: k8s-access, Date: 2024.01.18, Locations: ['DEFAULT']      │
├────────────────────────────┼──────────────┼────────┼─────────────────────────────────────────────────────────────────────────────┤
│ 2024-03-06T15:04:22.747010 │ devin.acosta │ INFO   │ Restore Plan: 9 indice(s), 9 shard(s), with total space of : 26.79 GB       │
├────────────────────────────┼──────────────┼────────┼─────────────────────────────────────────────────────────────────────────────┤
│ 2024-03-06T15:04:23.242692 │ devin.acosta │ ERROR  │ ERROR: Another RESTORE job is running... exiting script.                    │
├────────────────────────────┼──────────────┼────────┼─────────────────────────────────────────────────────────────────────────────┤
│ 2024-03-06T15:06:57.851229 │ devin.acosta │ INFO   │ User cancelled restore operations!                                          │
├────────────────────────────┼──────────────┼────────┼─────────────────────────────────────────────────────────────────────────────┤
│ 2024-03-06T15:07:22.945490 │ devin.acosta │ INFO   │ Query: Component: logs-png-system, Date: 2024.02.05, Locations: ['DEFAULT'] │
├────────────────────────────┼──────────────┼────────┼─────────────────────────────────────────────────────────────────────────────┤
│ 2024-03-06T15:07:33.908565 │ devin.acosta │ INFO   │ Restore Plan: 1 indice(s), 1 shard(s), with total space of : 4.21 MB        │
├────────────────────────────┼──────────────┼────────┼─────────────────────────────────────────────────────────────────────────────┤
│ 2024-03-06T15:28:17.335434 │ devin.acosta │ INFO   │ Query: Component: logs-png-system, Date: 2024.02.05, Locations: ['DEFAULT'] │
├────────────────────────────┼──────────────┼────────┼─────────────────────────────────────────────────────────────────────────────┤
│ 2024-03-06T15:28:31.485635 │ devin.acosta │ INFO   │ Restore Plan: 1 indice(s), 1 shard(s), with total space of : 4.21 MB        │
├────────────────────────────┼──────────────┼────────┼─────────────────────────────────────────────────────────────────────────────┤
│ 2024-03-06T15:28:40.166018 │ devin.acosta │ INFO   │ User cancelled restore operations!                                          │
├────────────────────────────┼──────────────┼────────┼─────────────────────────────────────────────────────────────────────────────┤
│ 2024-03-06T15:29:04.819389 │ devin.acosta │ INFO   │ Query: Component: logs-png-system, Date: 2024.02.05, Locations: ['DEFAULT'] │
├────────────────────────────┼──────────────┼────────┼─────────────────────────────────────────────────────────────────────────────┤
│ 2024-03-06T15:29:17.087979 │ devin.acosta │ INFO   │ Restore Plan: 1 indice(s), 1 shard(s), with total space of : 4.21 MB        │
├────────────────────────────┼──────────────┼────────┼─────────────────────────────────────────────────────────────────────────────┤
│ 2024-03-06T15:29:21.641701 │ devin.acosta │ INFO   │ User cancelled restore operations!                                          │
├────────────────────────────┼──────────────┼────────┼─────────────────────────────────────────────────────────────────────────────┤
│ 2024-03-06T15:30:34.289135 │ devin.acosta │ INFO   │ Query: Component: logs-png-system, Date: 2024.02.05, Locations: ['DEFAULT'] │
├────────────────────────────┼──────────────┼────────┼─────────────────────────────────────────────────────────────────────────────┤
│ 2024-03-06T15:30:46.002231 │ devin.acosta │ INFO   │ Restore Plan: 1 indice(s), 1 shard(s), with total space of : 4.21 MB        │
├────────────────────────────┼──────────────┼────────┼─────────────────────────────────────────────────────────────────────────────┤
│ 2024-03-06T15:30:49.196677 │ devin.acosta │ INFO   │ User cancelled restore operations!                                          │
├────────────────────────────┼──────────────┼────────┼─────────────────────────────────────────────────────────────────────────────┤
│ 2024-03-08T11:07:44.561871 │ devin.acosta │ INFO   │ Query: Component: k8s-access, Date: 2024.01.18, Locations: ['DEFAULT']      │
├────────────────────────────┼──────────────┼────────┼─────────────────────────────────────────────────────────────────────────────┤
│ 2024-03-08T11:08:04.762713 │ devin.acosta │ INFO   │ Restore Plan: 9 indice(s), 9 shard(s), with total space of : 26.79 GB       │
├────────────────────────────┼──────────────┼────────┼─────────────────────────────────────────────────────────────────────────────┤
│ 2024-03-08T11:10:31.026662 │ devin.acosta │ INFO   │ User cancelled restore operations!                                          │
└────────────────────────────┴──────────────┴────────┴─────────────────────────────────────────────────────────────────────────────┘

# To Clear Database (in case it locked out all user requests)
# ./snapshotmgr.py clear-staged
Cleared all staged indices...

```

# YAML configuration

These scripts utilize a YAML configuration file called **elastic_servers.yml**
This configuration files set some **default values** and allows you to list as many Elastic Search servers as needed.

There are two main sections of this configuration file:
**settings** section sets some Elastic Search defaults for the scripts, it should look like:



    settings:
      elastic_default_timeout: 60
      elastic_restored_maxdays: 0
      elastic_restore_batch_size: 3
      elastic_max_shards_per_node: 1000
      default_retention_maxdays: 14
      elastic_cacerts: '/etc/elasticsearch-1/cacerts.p12'

There should be no reason in most cases to edit any of the above settings.

The next section is the ES server configuration.

    servers:
    - name: DEFAULT
      hostname: 10.18.80.66
      port: 9201
      use_ssl: True
      repository: aex20-repo
      elastic_authentication: True
      elastic_username: username
      elastic_password: password

By default the script will look for a server entry with the name of DEFAULT (all capital). It will always default to this server by default. You can have multiple servers listed and then pass -l {location} with the location name matching the entry.

For example you can name an entry AEX20 with having an entry like:

    - name: AEX20
      hostname: 10.18.80.66
      port: 9201
      use_ssl: True
      repository: aex20-repo
      elastic_authentication: True
      elastic_username: username
      elastic_password: password

Then when you run the script you would do for an example.

This tells the script to use SERVER named AEX20

    ./snapshotmgr.py -l AEX20 list

