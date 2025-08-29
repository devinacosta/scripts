#!/usr/bin/env python3
"""
Administration tool for ElasticSearch, simplifies admin tasks.

Refactored for maintainability with modular CLI components.
"""

import os
import getpass
import sys
from pathlib import Path

# Import Rich components
from rich import print
from rich.console import Console
from rich.panel import Panel

# Import core modules
from esclient import ElasticsearchClient
from command_handler import CommandHandler
from configuration_manager import ConfigurationManager

# Import new CLI modules
from cli import (
    create_argument_parser,
    show_custom_help,
    handle_version,
    handle_locations,
    handle_get_default,
    handle_set_default,
    handle_show_settings
)
from cli.special_commands import show_welcome_screen


def handle_help_command(args, console):
    """
    Handle the help command without requiring Elasticsearch connection.
    
    Args:
        args: Parsed command line arguments
        console: Rich console instance
    """
    # Import here to avoid circular imports
    from handlers.help_handler import HelpHandler
    
    # Create a minimal help handler without ES client
    # We pass None for es_client since help handler doesn't use it
    help_handler = HelpHandler(None, args, console, None, None, None)
    help_handler.handle_help()


# Version information
VERSION = '2.5.0'
DATE = "08/29/2025"

# Commands that don't require Elasticsearch connection
NO_CONNECTION_COMMANDS = {
    'version', 'locations', 'get-default', 'set-default', 'show-settings', 'help'
}

# Commands that don't need index preprocessing
NO_PREPROCESS_COMMANDS = {
    'health', 'set-default', 'get-default', 'show-settings', 'version', 'dangling'
}


def should_use_ascii_mode(config_manager):
    """
    Check if ASCII mode should be used by checking environment variable first, then configuration.

    Args:
        config_manager: Configuration manager instance

    Returns:
        bool: True if ASCII mode should be used
    """
    # Environment variable takes precedence
    env_ascii = os.environ.get('ESCMD_ASCII_MODE', '').lower() in ('true', '1', 'yes')
    if env_ascii:
        return True

    # Fall back to configuration file setting
    return config_manager.get_ascii_mode()


def initialize_configuration():
    """Initialize configuration manager."""
    script_directory = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(script_directory, 'elastic_servers.yml')
    state_file = os.path.join(script_directory, 'escmd.json')
    return ConfigurationManager(config_file, state_file)


def handle_special_commands(args, config_manager, console):
    """
    Handle commands that don't require Elasticsearch connection.

    Args:
        args: Parsed command line arguments
        config_manager: Configuration manager instance
        console: Rich console instance

    Returns:
        bool: True if command was handled (should exit), False otherwise
    """
    command = args.command

    if command == 'version':
        handle_version(VERSION, DATE)
        return True

    elif command == 'locations':
        handle_locations(config_manager)
        return True

    elif command == 'get-default':
        handle_get_default(config_manager)
        return True

    elif command == 'set-default':
        location = getattr(args, 'defaultcluster_cmd', 'default')
        handle_set_default(location, config_manager)
        return True

    elif command == 'show-settings':
        format_output = getattr(args, 'format', None)
        handle_show_settings(config_manager, format_output)
        return True

    elif command == 'help':
        handle_help_command(args, console)
        return True

    return False


def get_elasticsearch_config(args, config_manager, console):
    """
    Get Elasticsearch configuration and validate.

    Args:
        args: Parsed command line arguments
        config_manager: Configuration manager instance
        console: Rich console instance

    Returns:
        dict: Location configuration
    """
    # Determine which location to use
    es_location = args.locations if args.locations else config_manager.get_default_cluster()
    location_config = config_manager.get_server_config_by_location(es_location)

    if not location_config:
        error_text = f"Location: {es_location} not found.\nPlease check your elastic_settings.yml config file."
        console.print(Panel.fit(error_text, title="Configuration Error"))
        sys.exit(1)

    return location_config, es_location


def create_elasticsearch_client(location_config, config_manager, args):
    """
    Create and configure Elasticsearch client.

    Args:
        location_config: Location-specific configuration
        config_manager: Configuration manager instance
        args: Parsed command line arguments

    Returns:
        ElasticsearchClient: Configured ES client
    """
    # Extract configuration values
    elastic_host = location_config['elastic_host']
    elastic_host2 = location_config['elastic_host2']
    elastic_port = location_config['elastic_port']
    elastic_use_ssl = location_config['use_ssl']
    elastic_username = location_config['elastic_username']
    elastic_password = location_config['elastic_password']
    elastic_authentication = location_config.get('elastic_authentication', False)
    elastic_verify_certs = location_config.get('verify_certs', False)

    # Get timeout configuration (allow per-server override)
    elastic_read_timeout = location_config.get('read_timeout', config_manager.get_read_timeout())

    # Prompt for password if needed
    if elastic_authentication and (elastic_password is None or elastic_password == "None"):
        elastic_password = getpass.getpass(prompt="Enter your Password: ")

    # Determine if index preprocessing is needed
    preprocess_indices = args.command not in NO_PREPROCESS_COMMANDS

    # Create client
    return ElasticsearchClient(
        host1=elastic_host,
        host2=elastic_host2,
        port=elastic_port,
        use_ssl=elastic_use_ssl,
        timeout=elastic_read_timeout,
        verify_certs=elastic_verify_certs,
        elastic_authentication=elastic_authentication,
        elastic_username=elastic_username,
        elastic_password=elastic_password,
        preprocess_indices=preprocess_indices,
        box_style=config_manager.box_style
    )


def main():
    """Main entry point for escmd."""
    # Initialize console
    console = Console()

    # Create argument parser
    parser = create_argument_parser()

    # Parse arguments
    args = parser.parse_args()

    # Handle help display
    if args.help:
        show_custom_help()
        sys.exit(0)

    # Handle case with no command
    if not args.command:
        show_welcome_screen(console)
        sys.exit(0)

    # Initialize configuration
    config_manager = initialize_configuration()

    # Handle special commands that don't need ES connection
    if handle_special_commands(args, config_manager, console):
        sys.exit(0)

    # Get Elasticsearch configuration
    location_config, es_location = get_elasticsearch_config(args, config_manager, console)
    config_file = config_manager.config_file_path

    # Create Elasticsearch client
    es_client = create_elasticsearch_client(location_config, config_manager, args)

    # Create and execute command handler
    command_handler = CommandHandler(es_client, args, console, config_file, location_config, es_location)
    command_handler.execute()


if __name__ == "__main__":
    main()
