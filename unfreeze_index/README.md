# unfreeze_index.py

This utility unfreezes Elasitcsearch indices that have been Frozen by the ILM process. 
The utility expects that you pass the following parameters:

```
usage: unfreeze_index.py [-h] -l LOCATIONS -d DATE -c COMPONENT

options:
  -h, --help            show this help message and exit
  -l LOCATIONS, --locations LOCATIONS
  -d DATE, --date DATE
  -c COMPONENT, --component COMPONENT
  ```
 You would typically pass logs-pas, logs-pwr, etc.
 
  ```
  Example usage:
   unfreeze_index.py -d 2023.04.25 -c 'logs-pas-main-stat' -l 'es1,es2'                                                                                                                                                                             

UnFreeze_Index (Python Script) has started...

The Script found the following indices to be opened:
┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┓
┃ Cluster    ┃ Indice                                     ┃ Frozen_Status   ┃
┣━━━━━━━━━━━━╋━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╋━━━━━━━━━━━━━━━━━┫
┃ es1/9201   ┃ .ds-es1-logs-pas-main-stat-2023.04.25-0019 ┃ False           ┃
┣━━━━━━━━━━━━╋━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╋━━━━━━━━━━━━━━━━━┫
┃ es2/9201   ┃ .ds-es1-logs-pas-main-stat-2023.04.23-0011 ┃ False           ┃
┗━━━━━━━━━━━━┻━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┻━━━━━━━━━━━━━━━━━┛

Would you like to open these Indices? [y/n]: yes


Action: Skipping Indice .ds-es1-logs-pas-main-stat-2023.04.25-000019, because not in Frozen Status
Action: Skipping Indice .ds-es2-logs-pas-main-stat-2023.04.23-000011, because not in Frozen Status
```

The script will ONLY unfreeze Indices that are in FROZEN, as you can see above it didn't unfreeze because the indices were already opened. 

## Dependencies:
You will want to install the Python pip3 libraries listed in the requirements.txt.
In order to do the fancy output i use `tabulate` python module for example.

The  servers definitions are inside file called: `unfreeze_servers.txt`
This was seperated from main script so that servers can be easily updated without touching main script.

