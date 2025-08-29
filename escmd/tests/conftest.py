"""
Pytest configuration and shared fixtures for escmd tests.
"""

import pytest
import argparse
from unittest.mock import Mock, MagicMock
from rich.console import Console
import tempfile
import yaml
import json

# Import the modules we want to test
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from command_handler import CommandHandler
from configuration_manager import ConfigurationManager


@pytest.fixture
def mock_es_client():
    """Mock Elasticsearch client with common methods."""
    client = Mock()
    
    # Health related methods
    client.get_cluster_health.return_value = {
        'cluster_name': 'test-cluster',
        'status': 'green',
        'number_of_nodes': 3,
        'number_of_data_nodes': 2,
        'active_primary_shards': 10,
        'active_shards': 20
    }
    
    # Index related methods
    client.list_dangling_indices.return_value = []
    client.list_datastreams.return_value = {'data_streams': []}
    client.get_indices_stats.return_value = {}
    
    # Settings
    client.get_settings.return_value = {'persistent': {}, 'transient': {}}
    client.print_enhanced_cluster_settings.return_value = None
    
    # Other common methods
    client.flush_synced_elasticsearch.return_value = {'_shards': {'failed': 0}}
    client.host1 = 'localhost'
    client.port = 9200
    client.use_ssl = False
    client.elastic_authentication = False
    client.elastic_username = None
    client.elastic_password = None
    
    return client


@pytest.fixture
def mock_console():
    """Mock Rich console."""
    return Mock(spec=Console)


@pytest.fixture
def sample_args():
    """Create sample arguments for testing."""
    args = argparse.Namespace()
    args.command = 'health'
    args.format = 'table'
    args.locations = 'test-cluster'
    return args


@pytest.fixture
def temp_config_file():
    """Create a temporary config file for testing."""
    config_data = {
        'DEFAULT': {
            'hostname': '127.0.0.1',
            'port': 9200,
            'use_ssl': False
        },
        'test-cluster': {
            'hostname': 'test.example.com',
            'port': 9200,
            'use_ssl': True,
            'username': 'test_user',
            'password': 'test_pass'
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        yaml.dump(config_data, f)
        yield f.name
    
    # Cleanup
    os.unlink(f.name)


@pytest.fixture
def temp_escmd_config():
    """Create a temporary escmd.json config file."""
    config_data = {
        'default_location': 'test-cluster',
        'box_style': 'rounded',
        'health_style': 'dashboard'
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        yield f.name
    
    # Cleanup
    os.unlink(f.name)


@pytest.fixture
def location_config():
    """Sample location configuration."""
    return {
        'hostname': 'test.example.com',
        'port': 9200,
        'use_ssl': True,
        'username': 'test_user',
        'password': 'test_pass',
        'health_style': 'dashboard'
    }


@pytest.fixture
def command_handler(mock_es_client, sample_args, mock_console, temp_config_file, location_config):
    """Create a CommandHandler instance with mocked dependencies."""
    return CommandHandler(
        es_client=mock_es_client,
        args=sample_args,
        console=mock_console,
        config_file=temp_config_file,
        location_config=location_config,
        current_location='test-cluster'
    )
