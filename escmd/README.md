# escmd.py

escmd is a command line utility to make interacting with Elastic Search more enjoyable.

## Features

- Check Cluster Health
- Check Cluster Settings 
- List Recovery Status
- List (Nodes, Masters, Indices, Shards)
- Export data into JSON format (so you can pipe to another command)



## Installation

escmd requires Python 3.6+, with a handful of Python Modules.


Install Python Requirements

```sh
pip3 install -r requirements.txt
```

Edit elastic_servers.yml
> By default the script will look for an entry with name 'default'. It will default to this cluster by default.
> You can change the style of the Tables displayed by script, by editing (box_style), see below.
```yaml
settings:
  # Options for Box_Style: SIMPLE, ASCII, SQUARE, ROUNDED, SQUARE_DOUBLE_HEAD
  box_style:  SQUARE_DOUBLE_HEAD

servers:
  - name: default
    hostname: 192.168.1.100
    port: 9200
    use_ssl: False 
    elastic_authentication: False
    elastic_username: None 
    elastic_password: None
  - name: cluster2
    hostname: 192.168.1.200
    port: 9200
    use_ssl: False
    verify_certs: False
    elastic_authentication: False
    elastic_username: None
    elastic_password: None
```

# Usage

##### _The script was designed to be used with many clusters._
You can specify the specific cluster by using the "name" of the server defined in elastic_servers.yml.
If you do not wish to have to supply the command argument **-l** all the time, you can specify which cluster to default to by using command 'set-default'.

#### Set Cluster to use Cluster named cluster2.
It assumes you have already defined cluster2 in elastic_servers.yml
```
./escmd.py set-default cluster2
Current cluster set to: cluster2
```

#### Check Cluster Default Setting
```
./escmd.py get-default
Current Default Cluster is: default
```

#### Check Cluster Health
```
./escmd.py health
            Elastic Health Status            
┌───────────────────────────┬───────────────┐
│ Key                       │ Value         │
╞═══════════════════════════╪═══════════════╡
│ cluster_name              │ elasticsearch │
│ cluster_status            │ green         │
│ number_of_nodes           │ 2             │
│ number_of_data_nodes      │ 2             │
│ active_primary_shards     │ 15            │
│ active_shards             │ 30            │
│ unassigned_shards         │ 0             │
│ delayed_unassigned_shards │ 0             │
│ number_of_pending_tasks   │ 0             │
│ number_of_in_flight_fetch │ 0             │
│ active_shards_percent     │ 100.0         │
└───────────────────────────┴───────────────┘
```

#### List Nodes
```
# ./escmd.py nodes
┌──────────┬───────────────┬─────────────┐
│ name     │ hostname      │ roles       │
╞══════════╪═══════════════╪═════════════╡
│ node-1 * │ 192.168.10.87 │ cdfhilmrstw │
│ node-2   │ 192.168.10.69 │ cdfhrstw    │
└──────────┴───────────────┴─────────────┘
```
#### If you want to show the output in (**JSON**) format
> Note almost all the commands support --format json (where it makes sense).
```
# ./escmd.py nodes --format json
[{"nodeid": "1xOzAPAmQGyVXmc_JIGnCg", "name": "node-1", "hostname": "192.168.10.87", "roles": ["data", "data_cold", "data_content", "data_frozen", "data_hot", "data_warm", "ingest", "master", 
"ml", "remote_cluster_client", "transform"], "indices": 154, "shards": 15}, {"nodeid": "S2jUQNQVSnS-k1A2R-vDmg", "name": "node-2", "hostname": "192.168.10.69", "roles": ["data", "data_cold", 
"data_content", "data_frozen", "data_hot", "data_warm", "remote_cluster_client", "transform"], "indices": 154, "shards": 15}]
```

#### List Master Servers
> It will show * next to item that is currently the master (just like Elasticsearch does).
```
./escmd.py masters
┌──────────┬───────────────┬─────────────┐
│ name     │ hostname      │ roles       │
╞══════════╪═══════════════╪═════════════╡
│ node-1 * │ 192.168.10.87 │ cdfhilmrstw │
└──────────┴───────────────┴─────────────┘
```

#### Listing Indices
> Again you can 
```
./escmd.py indices
                                                         Indices                                                          
┌────────┬───────┬─────────────────────────────────┬────────────────────────┬──────┬─────────┬──────────────┬────────────┐
│ Health │ Satus │ Indice                          │ UUID                   │ Docs │ Pri/Rep │ Size Primary │ Size Total │
╞════════╪═══════╪═════════════════════════════════╪════════════════════════╪══════╪═════════╪══════════════╪════════════╡
│  green │  open │ .geoip_databases                │ yy1vkEZTRlmDnKLE6o4qVQ │   34 │   1|1   │       31.8mb │     66.7mb │
│  green │  open │ .kibana_7.15.1_001              │ ai8UxsjoRNSISyPPsHB-Yg │   37 │   1|1   │        2.3mb │      4.7mb │
│  green │  open │ rc_minios3_state                │ IkQOWl94RveQNt1qG9GfAA │    1 │   1|1   │        5.7kb │     11.4kb │
│  green │  open │ .apm-custom-link                │ wGrJhqfvQh-qvnp7qPd6OA │    0 │   1|1   │         208b │       416b │
│  green │  open │ .kibana-event-log-7.15.1-000002 │ JuACAiDgTEW6jUlB2WmGjw │    0 │   1|1   │         208b │       416b │
│  green │  open │ .kibana-event-log-7.15.1-000003 │ 1p4MvXrUSxaCE_z4zhrx6w │    0 │   1|1   │         208b │       416b │
│  green │  open │ .apm-agent-configuration        │ XohVkMI0RRK_dMn4-lbykg │    0 │   1|1   │         208b │       416b │
│  green │  open │ .kibana-event-log-7.15.1-000004 │ YA5iFGE7S7KXMNU7XWkdvA │    1 │   1|1   │          6kb │     12.1kb │
│  green │  open │ .kibana-event-log-7.15.1-000005 │ 81m0kZjgQLWRTPGB9q47zw │    0 │   1|1   │         208b │       416b │
│  green │  open │ .tasks                          │ LX-JzYRdSr-Ejaqgem-VUQ │    2 │   1|1   │        7.8kb │     15.6kb │
│  green │  open │ .kibana_task_manager_7.15.1_001 │ dXVcdtOhSTSKVubVmoyfrg │   15 │   1|1   │       38.3mb │     70.9mb │
└────────┴───────┴─────────────────────────────────┴────────────────────────┴──────┴─────────┴──────────────┴────────────┘
```
#### Listing Indices (REGEX)
> You can use REGEX to limit the indice search to only the specified pattern. It assumes pattern:  \*{keyword}\*
```
./escmd.py indices kibana
                                                         Indices                                                          
┌────────┬───────┬─────────────────────────────────┬────────────────────────┬──────┬─────────┬──────────────┬────────────┐
│ Health │ Satus │ Indice                          │ UUID                   │ Docs │ Pri/Rep │ Size Primary │ Size Total │
╞════════╪═══════╪═════════════════════════════════╪════════════════════════╪══════╪═════════╪══════════════╪════════════╡
│  green │  open │ .kibana_7.15.1_001              │ ai8UxsjoRNSISyPPsHB-Yg │   37 │   1|1   │        2.3mb │      4.7mb │
│  green │  open │ .kibana-event-log-7.15.1-000002 │ JuACAiDgTEW6jUlB2WmGjw │    0 │   1|1   │         208b │       416b │
│  green │  open │ .kibana-event-log-7.15.1-000003 │ 1p4MvXrUSxaCE_z4zhrx6w │    0 │   1|1   │         208b │       416b │
│  green │  open │ .kibana-event-log-7.15.1-000004 │ YA5iFGE7S7KXMNU7XWkdvA │    1 │   1|1   │          6kb │     12.1kb │
│  green │  open │ .kibana-event-log-7.15.1-000005 │ 81m0kZjgQLWRTPGB9q47zw │    0 │   1|1   │         208b │       416b │
│  green │  open │ .kibana_task_manager_7.15.1_001 │ dXVcdtOhSTSKVubVmoyfrg │   15 │   1|1   │       38.3mb │     70.9mb │
└────────┴───────┴─────────────────────────────────┴────────────────────────┴──────┴─────────┴──────────────┴────────────┘
```

#### Check Indice Recoveries
> Please note clusters with a larger number of indices, this command can take some time to complete. It will only show indice recoveries in progress.
```
./escmd.py recovery
╭────────────────────────────── Cluster Recovery ──────────────────────────────╮
│                            No Recovery Jobs Found                            │
╰──────────────────────────────────────────────────────────────────────────────╯
```

#### Check Shards
```
./escmd.py shards
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━┳━━━━━━━━┳━━━━━━━━┓
┃ Index Name                          ┃ Shard Number ┃ Pri/Rep ┃ State      ┃ Docs ┃ Store  ┃ Node   ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━╇━━━━━━━━╇━━━━━━━━┩
│ .apm-agent-configuration            │ 0            │ p       │ STARTED    │ 0    │ 208b   │ node-1 │
│ .apm-custom-link                    │ 0            │ p       │ STARTED    │ 0    │ 208b   │ node-1 │
│ .ds-ilm-history-5-2024.01.10-000002 │ 0            │ p       │ STARTED    │ N/A  │ N/A    │ node-1 │
│ .ds-ilm-history-5-2024.02.09-000003 │ 0            │ p       │ STARTED    │ N/A  │ N/A    │ node-1 │
│ .ds-ilm-history-5-2024.03.10-000004 │ 0            │ p       │ STARTED    │ N/A  │ N/A    │ node-1 │
│ .ds-ilm-history-5-2024.04.09-000005 │ 0            │ p       │ STARTED    │ N/A  │ N/A    │ node-1 │
│ .geoip_databases                    │ 0            │ p       │ STARTED    │ 35   │ 32.5mb │ node-1 │
│ .kibana-event-log-7.15.1-000002     │ 0            │ p       │ STARTED    │ 0    │ 208b   │ node-1 │
│ .kibana-event-log-7.15.1-000003     │ 0            │ p       │ STARTED    │ 0    │ 208b   │ node-1 │
│ .kibana-event-log-7.15.1-000004     │ 0            │ p       │ STARTED    │ 1    │ 6kb    │ node-1 │
│ .kibana-event-log-7.15.1-000005     │ 0            │ p       │ STARTED    │ 3    │ 12.2kb │ node-1 │
│ .kibana_7.15.1_001                  │ 0            │ p       │ STARTED    │ 37   │ 2.3mb  │ node-1 │
│ .kibana_task_manager_7.15.1_001     │ 0            │ p       │ STARTED    │ 15   │ 36.7mb │ node-1 │
│ .tasks                              │ 0            │ p       │ STARTED    │ 4    │ 21.3kb │ node-1 │
│ rc_minios3_state                    │ 0            │ p       │ STARTED    │ 1    │ 5.7kb  │ node-1 │
│ rc_minios3_state                    │ 0            │ r       │ UNASSIGNED │ N/A  │ N/A    │ N/A    │
└─────────────────────────────────────┴──────────────┴─────────┴────────────┴──────┴────────┴────────┘
```
You can use REGEX pattern after shards to limit to show only certain shards
```
./escmd.py shards .kibana
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━┳━━━━━━━━┳━━━━━━━━┓
┃ Index Name                      ┃ Shard Number ┃ Pri/Rep ┃ State   ┃ Docs ┃ Store  ┃ Node   ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━╇━━━━━━╇━━━━━━━━╇━━━━━━━━┩
│ .kibana-event-log-7.15.1-000002 │ 0            │ p       │ STARTED │ 0    │ 208b   │ node-1 │
│ .kibana-event-log-7.15.1-000003 │ 0            │ p       │ STARTED │ 0    │ 208b   │ node-1 │
│ .kibana_7.15.1_001              │ 0            │ p       │ STARTED │ 37   │ 2.3mb  │ node-1 │
│ .kibana_task_manager_7.15.1_001 │ 0            │ p       │ STARTED │ 15   │ 36.6mb │ node-1 │
│ .kibana-event-log-7.15.1-000004 │ 0            │ p       │ STARTED │ 1    │ 6kb    │ node-1 │
│ .kibana-event-log-7.15.1-000005 │ 0            │ p       │ STARTED │ 3    │ 12.2kb │ node-1 │
└─────────────────────────────────┴──────────────┴─────────┴─────────┴──────┴────────┴────────┘
```

#### Check Cluster Settings
> Note that it will only show settings if they were configured from the default settings. (So not showing much is normal).
```
./escmd.py settings
                   Cluster Settings                    
┌─────────────────────────────────────────────┬───────┐
│ Key                                         │ Value │
╞═════════════════════════════════════════════╪═══════╡
│ transient.cluster.routing.allocation.enable │ all   │
└─────────────────────────────────────────────┴───────┘
```

#### Disable Allocation for Patching/Rebooting
> You will want to disable allocation during any restart of the Elasticsearch nodes. Use the commands below to complete this task.

To Disable Allocation Use:
```
./escmd.py allocation disable
Cluster allocation change has completed successfully.
Successfully changed allocation to primaries only.
```

To Enable Allocation Use:
```
./escmd.py allocation enable
Cluster allocation change has completed successfully.
Successfully re-enabled all shards allocation.
```

You can check the allocation setting by using:
./escmd.py settings

## License

MIT

**Free Software, Hell Yeah!**
