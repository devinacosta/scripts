import json
import os
import yaml
from rich.console import Console
from rich.table import Table
from rich import box

class ConfigurationManager:
    def __init__(self, config_file_path, state_file_path):
        self.config_file_path = config_file_path
        self.state_file_path = state_file_path
        self.config = self._read_yaml_file()
        self.default_settings = self.config.get('settings', {}) if self.config else {}
        self.servers_settings = self.config.get('servers', [{"name": 'DEFAULT', "hostname": 'localhost', "port": 9200, "use_ssl": False}]) if self.config else [{"name": 'DEFAULT', "hostname": 'localhost', "port": 9200, "use_ssl": False}]
        self.servers_dict = self._convert_dict_list_to_dict(self.servers_settings)
        self.cluster_groups = self.config.get('cluster_groups', {}) if self.config else {}
        self.passwords = self.config.get('passwords', {}) if self.config else {}  # Load password configurations
        self.box_style = self._get_box_style()

    def _read_yaml_file(self):
        """
        Read and parse the YAML configuration file.

        Returns:
            dict: The parsed YAML configuration
        """
        if os.path.exists(self.config_file_path):
            with open(self.config_file_path, 'r') as file:
                return yaml.safe_load(file)
        return {}

    def _convert_dict_list_to_dict(self, dict_list):
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

    def _get_box_style(self):
        """
        Get the box style from configuration or return default.

        Returns:
            box: The box style to use for tables
        """
        box_style_string = self.default_settings.get('box_style', 'SQUARE_DOUBLE_HEAD')
        box_styles = {
            "SIMPLE": box.SIMPLE,
            "ASCII": box.ASCII,
            "SQUARE": box.SQUARE,
            "ROUNDED": box.ROUNDED,
            "SQUARE_DOUBLE_HEAD": box.SQUARE_DOUBLE_HEAD
        }
        return box_styles.get(box_style_string)

    def get_paging_enabled(self):
        """
        Get whether paging is enabled from configuration.

        Returns:
            bool: True if paging is enabled, False otherwise (defaults to False)
        """
        return self.default_settings.get('enable_paging', False)

    def get_paging_threshold(self):
        """
        Get the paging threshold from configuration.

        Returns:
            int: Number of items that triggers automatic paging
        """
        return self.default_settings.get('paging_threshold', 50)

    def get_show_legend_panels(self):
        """
        Get whether legend and quick actions panels should be shown.

        Returns:
            bool: True if legend panels should be shown, False otherwise (defaults to False)
        """
        return self.default_settings.get('show_legend_panels', False)

    def get_ascii_mode(self):
        """
        Get whether ASCII mode is enabled from configuration.

        Returns:
            bool: True if ASCII mode is enabled, False otherwise (defaults to False)
        """
        return self.default_settings.get('ascii_mode', False)

    def _resolve_password(self, server_config):
        """
        Resolve password using the new environment-based password scheme.
        
        Priority order:
        1. Direct password reference (elastic_password_ref)
        2. Environment-based password (use_env_password=True)
        3. Traditional explicit password (elastic_password)
        4. Default password from settings
        
        Args:
            server_config (dict): Server configuration dictionary
            
        Returns:
            str: Resolved password or None if not found
        """
        # Option 1: Direct password reference (e.g., "prod.kibana_system")
        if 'elastic_password_ref' in server_config:
            password_ref = server_config['elastic_password_ref']
            try:
                env, username = password_ref.split('.', 1)
                return self.passwords.get(env, {}).get(username)
            except (ValueError, AttributeError):
                print(f"Warning: Invalid password reference format: {password_ref}")
                
        # Option 2: Environment-based password resolution
        if server_config.get('use_env_password', False):
            env = server_config.get('env')
            username = server_config.get('elastic_username')
            if env and username and env in self.passwords:
                password = self.passwords[env].get(username)
                if password:
                    return password
                else:
                    print(f"Warning: No password found for {username} in environment '{env}'")
                    
        # Option 3: Traditional explicit password (backwards compatibility)
        explicit_password = server_config.get('elastic_password')
        if explicit_password:
            return explicit_password
            
        # Option 4: Default password from settings
        return self.default_settings.get('elastic_password', None)

    def get_server_config(self, location):
        """
        Get the server configuration for a specific location.

        Args:
            location (str): The location name to get configuration for.

        Returns:
            dict: The server configuration or None if not found.
        """
        return self.servers_dict.get(location.lower())

    def get_default_cluster(self):
        """
        Get the current default cluster from the state file.

        Returns:
            str: The name of the default cluster.
        """
        try:
            with open(self.state_file_path, 'r') as file:
                return json.load(file)['current_cluster']
        except FileNotFoundError:
            return "default"

    def set_default_cluster(self, value):
        """
        Set the default cluster in the state file.

        Args:
            value (str): The name of the cluster to set as default.
        """
        try:
            with open(self.state_file_path, 'r') as file:
                settings = json.load(file)
        except FileNotFoundError:
            settings = {"current_cluster": "default"}

        settings["current_cluster"] = value
        with open(self.state_file_path, 'w') as file:
            json.dump(settings, file, indent=4)
        print(f"Current cluster set to: {value}")

    def show_locations(self):
        """
        Display an enhanced overview of all configured Elasticsearch locations with cluster groups.
        """
        from rich.panel import Panel
        from rich.columns import Columns
        from rich.text import Text

        console = Console()

        # Create title panel
        title_panel = Panel(
            Text("🗺️  Elasticsearch Cluster Directory", style="bold cyan", justify="center"),
            subtitle="Configuration overview and cluster groups",
            border_style="cyan",
            padding=(1, 2)
        )

        # Create clusters table with enhanced styling
        servers_list = [{'name': name, **config} for name, config in self.servers_dict.items()]
        sorted_data = sorted(servers_list, key=lambda x: x['name'])

        # Clusters table with full width
        clusters_table = Table(show_header=True, header_style="bold white", expand=True)
        clusters_table.add_column("🏷️  Cluster", style="bold yellow", no_wrap=True, min_width=20)
        clusters_table.add_column("🖥️  Primary Host", style="cyan", no_wrap=True, min_width=45)
        clusters_table.add_column("🔄 Backup Host", style="dim cyan", no_wrap=True, min_width=45)
        clusters_table.add_column("🔌 Port", style="white", justify="center", width=8)
        clusters_table.add_column("🛡️  SSL", style="white", justify="center", width=6)
        clusters_table.add_column("🔑 Auth", style="white", justify="center", width=7)
        clusters_table.add_column("📊 Style", style="white", justify="center", width=10)

        # Add rows with enhanced formatting
        for item in sorted_data:
            ssl_status = "🔒" if item.get('use_ssl') else "🔓"
            auth_status = "🔐" if item.get('elastic_authentication') else "🚪"
            health_style = item.get('health_style', 'dashboard')
            health_icon = "📊" if health_style == 'dashboard' else "📋"

            backup_host = item.get('hostname2', '')
            backup_display = backup_host if backup_host else "[dim]none[/dim]"

            clusters_table.add_row(
                item.get('name', ''),
                item.get('hostname', ''),
                backup_display,
                str(item.get('port', 9200)),
                ssl_status,
                auth_status,
                health_style
            )

        clusters_panel = Panel(
            clusters_table,
            title="[bold white]🏢 Configured Clusters[/bold white]",
            border_style="white",
            padding=(1, 1)
        )

        # Create cluster groups panel if groups exist
        if self.cluster_groups:
            groups_table = Table(show_header=True, header_style="bold white", box=None)
            groups_table.add_column("🏷️  Group Name", style="bold green", no_wrap=True)
            groups_table.add_column("📋 Clusters", style="cyan")
            groups_table.add_column("📊 Count", style="white", justify="center")

            for group_name, cluster_list in self.cluster_groups.items():
                clusters_text = ", ".join(cluster_list)

                groups_table.add_row(
                    group_name,
                    clusters_text,
                    str(len(cluster_list))
                )

            groups_panel = Panel(
                groups_table,
                title="[bold white]🏗️  Cluster Groups[/bold white]",
                border_style="green",
                padding=(1, 1)
            )
        else:
            # No groups configured
            no_groups_table = Table.grid(padding=(0, 1))
            no_groups_table.add_column(style="dim white", justify="center")
            no_groups_table.add_row("ℹ️  No cluster groups configured")
            no_groups_table.add_row("Add 'cluster_groups' section to elastic_servers.yml")

            groups_panel = Panel(
                no_groups_table,
                title="[bold white]🏗️  Cluster Groups[/bold white]",
                border_style="dim white",
                padding=(1, 1)
            )

        # Summary statistics
        total_clusters = len(sorted_data)
        ssl_enabled = sum(1 for item in sorted_data if item.get('use_ssl'))
        auth_enabled = sum(1 for item in sorted_data if item.get('elastic_authentication'))

        summary_table = Table.grid(padding=(0, 2))
        summary_table.add_column(style="bold white", no_wrap=True)
        summary_table.add_column(style="bold cyan")
        summary_table.add_row("📊 Total Clusters:", str(total_clusters))
        summary_table.add_row("🔒 SSL Enabled:", f"{ssl_enabled}/{total_clusters}")
        summary_table.add_row("🔐 Auth Enabled:", f"{auth_enabled}/{total_clusters}")
        summary_table.add_row("🏗️  Cluster Groups:", str(len(self.cluster_groups)))

        summary_panel = Panel(
            summary_table,
            title="[bold white]📈 Summary[/bold white]",
            border_style="cyan",
            padding=(1, 1),
            width=30
        )

        # Usage examples
        usage_table = Table.grid(padding=(0, 1))
        usage_table.add_column(style="bold cyan", no_wrap=True)
        usage_table.add_column(style="dim white")
        usage_table.add_row("Set Default:", "./escmd.py set-default <cluster>")
        usage_table.add_row("Health Check:", "./escmd.py -l <cluster> health")
        usage_table.add_row("Group Health:", "./escmd.py health --group <group>")
        usage_table.add_row("Compare:", "./escmd.py health --compare <cluster>")

        usage_panel = Panel(
            usage_table,
            title="[bold white]🚀 Quick Commands[/bold white]",
            border_style="magenta",
            padding=(1, 1),
            width=40
        )

        # Display everything
        print()
        console.print(title_panel)
        print()
        console.print(clusters_panel)
        print()
        console.print(Columns([groups_panel], equal=False, expand=True))
        print()
        console.print(Columns([summary_panel, usage_panel], equal=False, expand=True))
        print()

    def get_server_config_by_location(self, location):
        """
        Get server configuration for a specific location with defaults.

        Args:
            location (str): The location name to get configuration for.

        Returns:
            dict: The server configuration with defaults applied.
        """
        server_config = self.get_server_config(location)
        if not server_config:
            return None

        return {
            'elastic_host': server_config.get('hostname', self.default_settings.get('hostname', 'localhost')),
            'elastic_host2': server_config.get('hostname2', self.default_settings.get('hostname2', 'localhost')),
            'elastic_port': server_config.get('port', self.default_settings.get('port', 9200)),
            'use_ssl': server_config.get('use_ssl', self.default_settings.get('use_ssl', False)),
            'verify_certs': server_config.get('verify_certs', self.default_settings.get('verify_certs', False)),
            'elastic_authentication': server_config.get('elastic_authentication', self.default_settings.get('elastic_authentication', False)),
            'elastic_username': server_config.get('elastic_username', self.default_settings.get('elastic_username', None)),
            'elastic_password': self._resolve_password(server_config),
            'repository': server_config.get('repository', self.default_settings.get('repository', 'default-repo')),
            'elastic_s3snapshot_repo': server_config.get('elastic_s3snapshot_repo', self.default_settings.get('elastic_s3snapshot_repo', None)),
            'health_style': server_config.get('health_style', self.default_settings.get('health_style', 'dashboard')),
            'classic_style': server_config.get('classic_style', self.default_settings.get('classic_style', 'panel')),
            'ascii_mode': server_config.get('ascii_mode', self.default_settings.get('ascii_mode', False))
        }

    def get_cluster_groups(self):
        """
        Get all available cluster groups.

        Returns:
            dict: Dictionary of cluster group names and their members
        """
        return self.cluster_groups

    def get_cluster_group_members(self, group_name):
        """
        Get the list of clusters in a specific group.

        Args:
            group_name (str): The name of the cluster group

        Returns:
            list: List of cluster names in the group, or None if group doesn't exist
        """
        return self.cluster_groups.get(group_name)

    def is_cluster_group(self, name):
        """
        Check if a given name is a cluster group.

        Args:
            name (str): The name to check

        Returns:
            bool: True if it's a cluster group, False otherwise
        """
        return name in self.cluster_groups
