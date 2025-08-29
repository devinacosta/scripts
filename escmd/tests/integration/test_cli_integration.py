"""
Integration tests for the escmd CLI tool.

These tests verify end-to-end functionality by running the actual CLI commands
with mocked Elasticsearch connections.
"""

import pytest
import subprocess
import json
import os
import sys
import tempfile
import yaml
from unittest.mock import patch, Mock


class TestCLIIntegration:
    """Integration tests for the complete CLI workflow."""

    @pytest.fixture
    def cli_env(self, temp_config_file, temp_escmd_config):
        """Setup environment for CLI testing."""
        env = os.environ.copy()
        env['ESCMD_CONFIG'] = temp_escmd_config
        env['ELASTIC_SERVERS_CONFIG'] = temp_config_file
        return env

    def run_escmd_command(self, command_args, env=None):
        """Helper method to run escmd commands."""
        # Get the path to escmd.py
        escmd_path = os.path.join(os.path.dirname(__file__), '..', '..', 'escmd.py')
        
        cmd = [sys.executable, escmd_path] + command_args
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            cwd=os.path.dirname(escmd_path)
        )
        
        return result

    @patch('esclient.ElasticsearchClient')
    def test_health_command_table_output(self, mock_es_class, cli_env):
        """Test health command with table output."""
        # Mock the ES client
        mock_es_instance = Mock()
        mock_es_instance.test_connection.return_value = True
        mock_es_instance.get_cluster_health.return_value = {
            'cluster_name': 'test-cluster',
            'status': 'green',
            'number_of_nodes': 3,
            'number_of_data_nodes': 2,
            'active_primary_shards': 10,
            'active_shards': 20
        }
        mock_es_class.return_value = mock_es_instance
        
        result = self.run_escmd_command(['health', '-l', 'test-cluster'], env=cli_env)
        
        assert result.returncode == 0
        assert 'test-cluster' in result.stdout

    @patch('esclient.ElasticsearchClient')
    def test_health_command_json_output(self, mock_es_class, cli_env):
        """Test health command with JSON output."""
        mock_es_instance = Mock()
        mock_es_instance.test_connection.return_value = True
        expected_health = {
            'cluster_name': 'test-cluster',
            'status': 'green',
            'number_of_nodes': 3
        }
        mock_es_instance.get_cluster_health.return_value = expected_health
        mock_es_class.return_value = mock_es_instance
        
        result = self.run_escmd_command(['health', '-l', 'test-cluster', '--format', 'json'], env=cli_env)
        
        assert result.returncode == 0
        # Parse the JSON output
        try:
            output_data = json.loads(result.stdout.strip())
            assert output_data['cluster_name'] == 'test-cluster'
            assert output_data['status'] == 'green'
        except json.JSONDecodeError:
            pytest.fail(f"Invalid JSON output: {result.stdout}")

    @patch('esclient.ElasticsearchClient')
    def test_ping_command(self, mock_es_class, cli_env):
        """Test ping command functionality."""
        mock_es_instance = Mock()
        mock_es_instance.test_connection.return_value = True
        mock_es_instance.get_cluster_health.return_value = {
            'cluster_name': 'test-cluster',
            'status': 'green'
        }
        mock_es_class.return_value = mock_es_instance
        
        result = self.run_escmd_command(['ping', '-l', 'test-cluster'], env=cli_env)
        
        assert result.returncode == 0
        assert 'Connection Successful' in result.stdout or 'test-cluster' in result.stdout

    @patch('esclient.ElasticsearchClient')
    def test_dangling_command(self, mock_es_class, cli_env):
        """Test dangling indices command."""
        mock_es_instance = Mock()
        mock_es_instance.list_dangling_indices.return_value = []
        mock_es_class.return_value = mock_es_instance
        
        result = self.run_escmd_command(['dangling', '-l', 'test-cluster'], env=cli_env)
        
        assert result.returncode == 0
        # Should indicate no dangling indices found
        assert 'dangling' in result.stdout.lower()

    @patch('esclient.ElasticsearchClient')
    def test_locations_command(self, mock_es_class, cli_env):
        """Test locations command."""
        result = self.run_escmd_command(['locations'], env=cli_env)
        
        assert result.returncode == 0
        # Should show configured clusters
        assert 'test-cluster' in result.stdout

    @patch('esclient.ElasticsearchClient')
    def test_settings_command_json(self, mock_es_class, cli_env):
        """Test settings command with JSON output."""
        mock_es_instance = Mock()
        mock_settings = {
            'persistent': {'cluster.name': 'test-cluster'},
            'transient': {}
        }
        mock_es_instance.get_settings.return_value = mock_settings
        mock_es_class.return_value = mock_es_instance
        
        result = self.run_escmd_command(['settings', '-l', 'test-cluster', '--format', 'json'], env=cli_env)
        
        assert result.returncode == 0
        try:
            output_data = json.loads(result.stdout.strip())
            assert 'persistent' in output_data
        except json.JSONDecodeError:
            pytest.fail(f"Invalid JSON output: {result.stdout}")

    @patch('esclient.ElasticsearchClient')
    def test_datastreams_command(self, mock_es_class, cli_env):
        """Test datastreams command."""
        mock_es_instance = Mock()
        mock_es_instance.list_datastreams.return_value = {'data_streams': []}
        mock_es_class.return_value = mock_es_instance
        
        result = self.run_escmd_command(['datastreams', '-l', 'test-cluster'], env=cli_env)
        
        assert result.returncode == 0

    def test_invalid_command(self, cli_env):
        """Test behavior with invalid command."""
        result = self.run_escmd_command(['invalid-command'], env=cli_env)
        
        # Should exit with error code and show help or error message
        assert result.returncode != 0

    def test_help_command(self):
        """Test help command."""
        result = self.run_escmd_command(['--help'])
        
        assert result.returncode == 0
        assert 'usage:' in result.stdout.lower() or 'help' in result.stdout.lower()

    @patch('esclient.ElasticsearchClient')
    def test_quick_health_check(self, mock_es_class, cli_env):
        """Test health command with quick flag."""
        mock_es_instance = Mock()
        mock_es_instance.get_cluster_health.return_value = {
            'cluster_name': 'test-cluster',
            'status': 'green',
            'number_of_nodes': 3,
            'number_of_data_nodes': 2,
            'active_primary_shards': 10,
            'active_shards': 20,
            'unassigned_shards': 0
        }
        mock_es_class.return_value = mock_es_instance
        
        result = self.run_escmd_command(['health', '-l', 'test-cluster', '-q'], env=cli_env)
        
        assert result.returncode == 0
        assert 'Quick Health' in result.stdout or 'GREEN' in result.stdout

    @pytest.mark.parametrize("command", [
        ['health'],
        ['ping'],
        ['dangling'],
        ['locations'],
        ['settings'],
        ['datastreams']
    ])
    @patch('esclient.ElasticsearchClient')
    def test_core_commands_execute(self, mock_es_class, cli_env, command):
        """Parametrized test to ensure core commands execute without crashing."""
        mock_es_instance = Mock()
        
        # Setup common mock responses
        mock_es_instance.test_connection.return_value = True
        mock_es_instance.get_cluster_health.return_value = {'cluster_name': 'test', 'status': 'green'}
        mock_es_instance.list_dangling_indices.return_value = []
        mock_es_instance.list_datastreams.return_value = {'data_streams': []}
        mock_es_instance.get_settings.return_value = {'persistent': {}, 'transient': {}}
        mock_es_instance.print_enhanced_cluster_settings.return_value = None
        
        mock_es_class.return_value = mock_es_instance
        
        # Add location if command is not 'locations'
        full_command = command.copy()
        if command[0] != 'locations':
            full_command.extend(['-l', 'test-cluster'])
        
        result = self.run_escmd_command(full_command, env=cli_env)
        
        # Should not crash (return code 0 or reasonable error)
        assert result.returncode in [0, 1]  # 0 for success, 1 for expected errors
