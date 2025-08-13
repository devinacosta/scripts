from rich import print
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
import json
import re
import yaml

console = Console()

def show_message_box(title, message, message_style="bold white", panel_style="white on blue"):
    """
    Display a message in a formatted box using rich.
    
    Args:
        title (str): The title of the message box
        message (str): The message to display
        message_style (str): The style for the message text
        panel_style (str): The style for the panel
    """
    message = Text(f"{message}", style=message_style, justify="center")
    panel = Panel(message, style=panel_style, title=title, border_style="bold white", width=80)
    console.print("\n")
    console.print(panel, markup=True)
    console.print("\n")

def find_matching_index(indices_data, indice):
    """
    Check if a given index exists in the provided indices data.
    
    Args:
        indices_data (list or str): List of dictionaries or JSON string containing index data
        indice (str): The index name to search for
        
    Returns:
        bool: True if the index is found, False otherwise
    """
    # Ensure indices_data is a list of dictionaries, not a JSON string
    if isinstance(indices_data, str):
        try:
            indices_data = json.loads(indices_data)  # Convert JSON string to Python object
        except json.JSONDecodeError:
            print("Error: Provided data is not valid JSON.")
            return False

    for data in indices_data:
        if isinstance(data, dict) and data.get("index") == indice:
            return True
    return False  # Return False if no match is found

def find_matching_node(json_data, indice, server):
    """
    Find the first node name in json_data where 'index' equals `indice`
    and 'node' matches the regex `server`.

    Args:
        json_data (list): List of dictionaries.
        indice (str): Index name to match exactly.
        server (str): Regex pattern to match node name.

    Returns:
        str or None: Node name that matches, or None if not found.
    """
    pattern_server = rf".*{server}.*"
    pattern = re.compile(pattern_server)
    for entry in json_data:
        if entry.get("index") == indice and pattern.search(entry.get("node", "")):
            return entry["node"]
    return None

def show_locations(config_file):
    """
    Display a table of all configured Elasticsearch locations.
    
    Args:
        config_file (str): Path to the configuration file
    """
    with open(config_file, 'r') as file:
        data = yaml.safe_load(file)

    servers = data['servers']
    sorted_data = sorted(servers, key=lambda x: x['name'])

    # Create a table
    table = Table(title="Elasticsearch Configured Clusters")

    # Add columns
    table.add_column("Name", justify="left", style="cyan", no_wrap=True)
    table.add_column("Hostname", justify="left", style="magenta")
    table.add_column("Hostname2", justify="left", style="magenta")
    table.add_column("Port", justify="right", style="green")
    table.add_column("Use SSL", justify="center", style="red")
    table.add_column("Verify Certs", justify="center", style="red")
    table.add_column("Username", justify="left", style="yellow")
    table.add_column("Password", justify="left", style="yellow")

    # Add rows
    for item in sorted_data:
        table.add_row(
            item.get('name', ''),
            item.get('hostname', ''),
            item.get('hostname2', ''),
            str(item.get('port', '')),
            str(item.get('use_ssl', '')),
            str(item.get('verify_certs', '')),
            item.get('elastic_username', ''),
            item.get('elastic_password', '')
        )

    # Print the table
    console.print(table)

def print_json_as_table(json_data):
    """
    Prints a JSON object as a pretty table using the rich module.

    Args:
        json_data (dict): Dictionary representing JSON key-value pairs.
    """
    table = Table(title="JSON Data", show_header=True, header_style="bold magenta")

    table.add_column("Key", style="cyan", justify="left")
    table.add_column("Value", style="green", justify="left")

    for key, value in json_data.items():
        table.add_row(str(key), str(value))

    console.print(table)

def convert_dict_list_to_dict(dict_list):
    """
    Convert a list of dictionaries into a single dictionary using the 'name' key.

    Args:
        dict_list (list): List of dictionaries, each containing a 'name' key.

    Returns:
        dict: Dictionary with 'name' values as keys and remaining data as values.
    """
    result_dict = {}
    for item in dict_list:
        name = item.pop('name').lower()
        result_dict[name] = item
    return result_dict 