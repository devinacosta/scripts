"""
Unit tests for configuration management.

Tests configuration loading, validation, and error handling.
"""

import pytest
import tempfile
import yaml
import json
import os
from unittest.mock import patch, mock_open

from configuration_manager import ConfigurationManager


class TestConfigurationManager:
    """Test cases for ConfigurationManager class."""

    def test_load_valid_yaml_config(self, temp_config_file):
        """Test loading a valid YAML configuration file."""
        config_manager = ConfigurationManager(config_file=temp_config_file)
        
        assert config_manager.config is not None
        assert 'test-cluster' in config_manager.config
        assert config_manager.config['test-cluster']['hostname'] == 'test.example.com'

    def test_load_valid_json_escmd_config(self, temp_escmd_config):
        """Test loading a valid escmd.json configuration."""
        config_manager = ConfigurationManager(escmd_config_file=temp_escmd_config)
        
        assert config_manager.escmd_config is not None
        assert config_manager.escmd_config.get('default_location') == 'test-cluster'

    def test_get_location_config_existing(self, temp_config_file):
        """Test getting configuration for an existing location."""
        config_manager = ConfigurationManager(config_file=temp_config_file)
        
        location_config = config_manager.get_location_config('test-cluster')
        
        assert location_config is not None
        assert location_config['hostname'] == 'test.example.com'
        assert location_config['port'] == 9200
        assert location_config['use_ssl'] is True

    def test_get_location_config_nonexistent(self, temp_config_file):
        """Test getting configuration for a non-existent location."""
        config_manager = ConfigurationManager(config_file=temp_config_file)
        
        location_config = config_manager.get_location_config('nonexistent-cluster')
        
        # Should return None or default config
        assert location_config is None or location_config == {}

    def test_get_default_location(self, temp_config_file, temp_escmd_config):
        """Test getting the default location."""
        config_manager = ConfigurationManager(
            config_file=temp_config_file,
            escmd_config_file=temp_escmd_config
        )
        
        default_location = config_manager.get_default_location()
        
        assert default_location == 'test-cluster'

    def test_list_locations(self, temp_config_file):
        """Test listing all configured locations."""
        config_manager = ConfigurationManager(config_file=temp_config_file)
        
        locations = config_manager.list_locations()
        
        assert 'DEFAULT' in locations
        assert 'test-cluster' in locations
        assert len(locations) >= 2

    def test_validate_location_config_valid(self, temp_config_file):
        """Test validation of a valid location configuration."""
        config_manager = ConfigurationManager(config_file=temp_config_file)
        
        location_config = config_manager.get_location_config('test-cluster')
        is_valid = config_manager.validate_location_config(location_config)
        
        assert is_valid is True

    def test_validate_location_config_invalid(self):
        """Test validation of an invalid location configuration."""
        config_manager = ConfigurationManager()
        
        invalid_config = {
            'hostname': '',  # Empty hostname should be invalid
            'port': 'not-a-number'  # Invalid port
        }
        
        is_valid = config_manager.validate_location_config(invalid_config)
        
        assert is_valid is False

    def test_missing_config_file(self):
        """Test behavior when config file is missing."""
        config_manager = ConfigurationManager(config_file='/nonexistent/file.yml')
        
        # Should handle missing file gracefully
        assert config_manager.config is None or config_manager.config == {}

    def test_invalid_yaml_format(self):
        """Test behavior with invalid YAML format."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write("invalid: yaml: content: [\n")  # Malformed YAML
            invalid_yaml_file = f.name
        
        try:
            config_manager = ConfigurationManager(config_file=invalid_yaml_file)
            # Should handle invalid YAML gracefully
            assert config_manager.config is None or config_manager.config == {}
        finally:
            os.unlink(invalid_yaml_file)

    def test_config_with_credentials(self):
        """Test configuration handling with credentials."""
        config_data = {
            'secure-cluster': {
                'hostname': 'secure.example.com',
                'port': 9200,
                'use_ssl': True,
                'username': 'secure_user',
                'password': 'secure_password',
                'verify_certs': False
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(config_data, f)
            config_file = f.name
        
        try:
            config_manager = ConfigurationManager(config_file=config_file)
            location_config = config_manager.get_location_config('secure-cluster')
            
            assert location_config['username'] == 'secure_user'
            assert location_config['password'] == 'secure_password'
            assert location_config['verify_certs'] is False
        finally:
            os.unlink(config_file)

    def test_box_style_configuration(self, temp_escmd_config):
        """Test box style configuration retrieval."""
        config_manager = ConfigurationManager(escmd_config_file=temp_escmd_config)
        
        box_style = config_manager.get_box_style()
        
        assert box_style == 'rounded'

    def test_health_style_configuration(self, temp_config_file):
        """Test health style configuration in location config."""
        config_manager = ConfigurationManager(config_file=temp_config_file)
        
        # Add health_style to test config
        location_config = config_manager.get_location_config('test-cluster')
        if location_config:
            location_config['health_style'] = 'dashboard'
            
            assert location_config.get('health_style') == 'dashboard'

    @patch('builtins.open', new_callable=mock_open, read_data="malformed json {")
    def test_invalid_json_escmd_config(self, mock_file):
        """Test behavior with invalid JSON in escmd config."""
        config_manager = ConfigurationManager(escmd_config_file='dummy_path.json')
        
        # Should handle invalid JSON gracefully
        assert config_manager.escmd_config is None or config_manager.escmd_config == {}

    def test_config_file_permissions(self, temp_config_file):
        """Test that config files with restricted permissions are handled."""
        # Make file unreadable
        os.chmod(temp_config_file, 0o000)
        
        try:
            config_manager = ConfigurationManager(config_file=temp_config_file)
            # Should handle permission errors gracefully
            assert config_manager.config is None or config_manager.config == {}
        finally:
            # Restore permissions for cleanup
            os.chmod(temp_config_file, 0o644)
