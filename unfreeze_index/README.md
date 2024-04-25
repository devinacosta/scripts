# unfreeze_index.py


I have developed a Python script that interfaces with Elasticsearch to manage index patterns. The script focuses on identifying and unfreezing index patterns that are currently in a frozen state. Using the Elasticsearch Python module, the script first connects to the Elasticsearch instance, taking into account the specified host, port, and SSL configuration. It then searches for frozen index patterns, leveraging Elasticsearch's API to query for indices with the "frozen" state. Upon finding these patterns, the script unfreezes them, allowing for the resumption of normal operations. The script is designed to be efficient and reliable, ensuring that frozen index patterns are promptly identified and addressed to maintain the Elasticsearch cluster's performance and availability.

The screen expects 3 Parameters to be passed:
 - Location (**-l**), it supports multiple locations being passed (i.e.: **esc01,iad41,iad01**)
 - Date (**-d**), date needs to be in format **YYYY.mm.dd**
 - Component (**-c**), it supports multiple components (i.e.: **pwr,gas,pas**)

```commandline
usage: unfreeze_index.py [-h] -l LOCATIONS -d DATE -c COMPONENT

options:
  -h, --help            show this help message and exit
  -l LOCATIONS, --locations LOCATIONS
  -d DATE, --date DATE
  -c COMPONENT, --component COMPONENT
  ```
 >You would typically pass logs-pas, logs-pwr, etc.
 >The _*Date format*_ Needs to be in **YYYY.mm.dd**
 
 
  ```commandline 
└─[$] ./unfreeze_index.py -d 2024.03.26 -c 'logs-pwr' -l 'esc01,iad01'                                                                                [13:33:25]

[13:33:42] UNFREEZE Index Script (v1.1.1  04/25/2024)                                                                                       unfreeze_index.py:316
           Query: DATE: [2024.03.26], COMPONENT: ['logs-pwr'], LOCATIONS ['esc01', 'iad01']                                                 unfreeze_index.py:316
[13:33:57] Search Results: Cluster esc01 : 14 matches found.                                                                                unfreeze_index.py:416
[13:34:04] Search Results: Cluster iad01 : 00 matches found.                                                                                unfreeze_index.py:416


                                              Frozen Indices (action)                                              
┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┓
┃ Cluster        ┃ Index                                                                      ┃ Frozen Status     ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━┩
│ esc01/9201     │ .ds-esc01-c01-logs-pwr-error_pwr_pasapi-2024.03.21-000018                  │ True              │
└────────────────┴────────────────────────────────────────────────────────────────────────────┴───────────────────┘
                                            Unfrozen Indices (noaction)                                            
┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┓
┃ Cluster        ┃ Index                                                                      ┃ Frozen Status     ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━┩
│ esc01/9201     │ .ds-esc01-c01-logs-pwr-access_pwr_wsgapi-2024.03.22-000114                 │ False             │
│ esc01/9201     │ .ds-esc01-c01-logs-pwr-access_pwr_api-2024.03.26-000136                    │ False             │
│ esc01/9201     │ .ds-esc01-c01-logs-pwr-access_pwr_intapi-2024.03.23-000117                 │ False             │
│ esc01/9201     │ .ds-esc01-c01-logs-pwr-access_pwr_pasapi-2024.03.24-000086                 │ False             │
│ esc01/9201     │ .ds-esc01-c01-logs-pwr-access_pwr_vmt-2024.03.25-000086                    │ False             │
│ esc01/9201     │ .ds-esc01-c01-logs-pwr-error_pwr_vmt-2024.03.21-000018                     │ False             │
│ esc01/9201     │ .ds-esc01-c01-logs-pwr-error_pwr_api-2024.03.26-000025                     │ False             │
│ esc01/9201     │ .ds-esc01-c01-logs-pwr-error_pwr_intapi-2024.03.26-000020                  │ False             │
│ esc01/9201     │ .ds-esc01-c01-logs-pwr-gudproxy-2024.03.20-000019                          │ False             │
│ esc01/9201     │ .ds-esc01-c01-logs-pwr-default-2024.03.20-000001                           │ False             │
│ esc01/9201     │ .ds-esc01-c01-logs-pwr-nginx-rc-2024.03.20-000016                          │ False             │
│ esc01/9201     │ .ds-esc01-c01-logs-pwr-error_pwr_wsgapi-2024.03.20-000019                  │ False             │
└────────────────┴────────────────────────────────────────────────────────────────────────────┴───────────────────┘
Would you like to open these Indices? [y/n]: y


[13:34:08] Indice (unfrozen): .ds-esc01-c01-logs-pwr-error_pwr_pasapi-2024.03.21-000018                                                     unfreeze_index.py:225
```

If there are no matches you will see something similar to this:
```commandline
└─[$] ./unfreeze_index.py -d 2024.03.26 -c 'blah' -l 'esc01'                                                                                          [13:20:16]

[13:20:17] UNFREEZE Index Script (v1.1.1  04/25/2024)                                                                                       unfreeze_index.py:316
[13:20:18] Query: DATE: [2024.03.26], COMPONENT: ['blah'], LOCATIONS ['esc01']                                                              unfreeze_index.py:316
[13:20:27] Search Results: Cluster esc01 : 00 matches found.                                                                                        unfreeze_index.py:416


╭────────────────────────────── No Results Found ──────────────────────────────╮
│                 The Script found no frozen indices to open!                  │
╰──────────────────────────────────────────────────────────────────────────────╯

```

The script will ONLY unfreeze Indices that are in FROZEN. You can see by the output above that it shows 2 tables, one for Frozen (action) indices, and one for Unfrozen (no-action).

## Dependencies:
Please ensure you install all the Python3 modules needed by running.
```
pip3 install -r requirements.txt
```

The  servers definitions are inside file called: `unfreeze_servers.txt`
This was separated from main script so that servers can be easily updated without touching main script.
