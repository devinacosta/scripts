"""
Unit tests for HealthHandler class.

Tests the health monitoring functionality with mocked Elasticsearch client.
"""

import pytest
import json
import argparse
from unittest.mock import Mock, patch, call

from handlers.health_handler import HealthHandler


class TestHealthHandler:
    """Test cases for HealthHandler class."""

    @pytest.fixture
    def health_handler(self, mock_es_client, mock_console, temp_config_file, location_config):
        """Create a HealthHandler instance for testing."""
        args = argparse.Namespace()
        args.format = 'table'
        args.command = 'health'
        
        return HealthHandler(
            es_client=mock_es_client,
            args=args,
            console=mock_console,
            config_file=temp_config_file,
            location_config=location_config,
            current_location='test-cluster'
        )

    def test_handle_ping_success(self, health_handler, mock_es_client):
        """Test successful ping command."""
        # Setup mock return values
        mock_es_client.test_connection.return_value = True
        mock_es_client.get_cluster_health.return_value = {
            'cluster_name': 'test-cluster',
            'status': 'green',
            'number_of_nodes': 3,
            'number_of_data_nodes': 2
        }
        
        with patch('builtins.print') as mock_print:
            health_handler.handle_ping()
            
        # Verify ES client methods were called
        mock_es_client.test_connection.assert_called_once()
        mock_es_client.get_cluster_health.assert_called_once()

    def test_handle_ping_json_format(self, health_handler, mock_es_client):
        """Test ping command with JSON output format."""
        health_handler.args.format = 'json'
        
        mock_es_client.test_connection.return_value = True
        expected_health_data = {
            'cluster_name': 'test-cluster',
            'status': 'green',
            'number_of_nodes': 3
        }
        mock_es_client.get_cluster_health.return_value = expected_health_data
        
        with patch('builtins.print') as mock_print:
            health_handler.handle_ping()
            
        # Should print JSON data
        mock_print.assert_called()
        # Check that JSON was printed (the exact call will contain formatted JSON)
        printed_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any('test-cluster' in str(call) for call in printed_calls)

    def test_handle_health_quick_mode(self, health_handler, mock_es_client):
        """Test health command in quick mode."""
        health_handler.args.quick = True
        
        mock_es_client.get_cluster_health.return_value = {
            'cluster_name': 'test-cluster',
            'status': 'green',
            'number_of_nodes': 3,
            'number_of_data_nodes': 2,
            'active_primary_shards': 10,
            'active_shards': 20,
            'unassigned_shards': 0
        }
        
        with patch.object(health_handler, '_handle_health_quick') as mock_quick:
            health_handler.handle_health()
            mock_quick.assert_called_once()

    def test_handle_health_json_format(self, health_handler, mock_es_client):
        """Test health command with JSON output."""
        health_handler.args.format = 'json'
        
        expected_health_data = {
            'cluster_name': 'test-cluster',
            'status': 'green',
            'number_of_nodes': 3
        }
        mock_es_client.get_cluster_health.return_value = expected_health_data
        
        with patch('builtins.print') as mock_print:
            health_handler.handle_health()
            
        mock_es_client.get_cluster_health.assert_called_once()
        # Should print JSON
        expected_json = json.dumps(expected_health_data)
        mock_print.assert_called_with(expected_json)

    def test_handle_health_comparison_mode(self, health_handler):
        """Test health command in comparison mode."""
        health_handler.args.compare = True
        
        with patch.object(health_handler, '_handle_health_compare') as mock_compare:
            health_handler.handle_health()
            mock_compare.assert_called_once()

    def test_handle_health_group_mode(self, health_handler):
        """Test health command in group mode."""
        health_handler.args.group = True
        
        with patch.object(health_handler, '_handle_health_group') as mock_group:
            health_handler.handle_health()
            mock_group.assert_called_once()

    def test_handle_cluster_check(self, health_handler, mock_es_client):
        """Test cluster check functionality."""
        # Mock the cluster check method
        mock_es_client.comprehensive_cluster_check.return_value = {
            'status': 'healthy',
            'issues': [],
            'summary': 'All checks passed'
        }
        
        with patch('builtins.print'):
            health_handler.handle_cluster_check()
            
        mock_es_client.comprehensive_cluster_check.assert_called_once()

    def test_sanitize_for_json(self, health_handler):
        """Test the _sanitize_for_json utility method."""
        test_data = {
            'string_field': 'test',
            'int_field': 123,
            'float_field': 45.67,
            'none_field': None,
            'nested': {
                'inner_string': 'inner_test',
                'inner_int': 456
            }
        }
        
        result = health_handler._sanitize_for_json(test_data)
        
        assert result['string_field'] == 'test'
        assert result['int_field'] == 123
        assert result['float_field'] == 45.67
        assert result['none_field'] is None
        assert result['nested']['inner_string'] == 'inner_test'
        assert result['nested']['inner_int'] == 456

    def test_ping_connection_failure(self, health_handler, mock_es_client):
        """Test ping command when connection fails."""
        mock_es_client.test_connection.return_value = False
        
        with patch('builtins.print') as mock_print:
            health_handler.handle_ping()
            
        mock_es_client.test_connection.assert_called_once()
        # Should not call get_cluster_health if connection fails
        mock_es_client.get_cluster_health.assert_not_called()

    @pytest.mark.parametrize("health_status,expected_style", [
        ('green', 'dashboard'),
        ('yellow', 'dashboard'),
        ('red', 'dashboard'),
    ])
    def test_health_styles(self, health_handler, mock_es_client, health_status, expected_style):
        """Test that different health statuses are handled properly."""
        mock_es_client.get_cluster_health.return_value = {
            'cluster_name': 'test-cluster',
            'status': health_status,
            'number_of_nodes': 3
        }
        
        # Set the style in location config
        health_handler.location_config['health_style'] = expected_style
        
        with patch('builtins.print'):
            health_handler.handle_health()
            
        mock_es_client.get_cluster_health.assert_called_once()
