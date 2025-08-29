"""
AllocationHandler - Handles cluster allocation and node exclusion operations

This module contains handlers for:
- allocation: Cluster-level shard allocation management (enable, disable, exclude operations)
- exclude: Index-level exclusion from specific nodes
- exclude-reset: Reset index exclusion settings
"""

from .base_handler import BaseHandler
import json


class AllocationHandler(BaseHandler):
    """Handler for allocation and exclusion operations."""

    def handle_allocation(self):
        """Handle cluster-level allocation management operations."""
        # Handle main allocation actions
        if not hasattr(self.args, 'allocation_action') or self.args.allocation_action is None:
            # Default to display if no action specified
            format_type = getattr(self.args, 'format', 'table')
            if format_type == 'json':
                settings = self.es_client.es.cluster.get_settings(include_defaults=False)
                import json
                self.es_client.pretty_print_json(settings)
            else:
                self.es_client.print_enhanced_allocation_settings()
            return

        if self.args.allocation_action == "display":
            format_type = getattr(self.args, 'format', 'table')
            if format_type == 'json':
                settings = self.es_client.es.cluster.get_settings(include_defaults=False)
                import json
                self.es_client.pretty_print_json(settings)
            else:
                self.es_client.print_enhanced_allocation_settings()
            return

        elif self.args.allocation_action == "enable":
            success = self.es_client.change_shard_allocation('all')
            if success:
                self.es_client.show_message_box("Success", "✅ Successfully enabled shard allocation (all shards).", message_style="bold white", panel_style="green")
                # Show updated settings
                format_type = getattr(self.args, 'format', 'table')
                if format_type == 'json':
                    settings = self.es_client.es.cluster.get_settings(include_defaults=False)
                    import json
                    self.es_client.pretty_print_json(settings)
                else:
                    self.es_client.print_enhanced_allocation_settings()
            else:
                self.es_client.show_message_box("Error", "❌ An ERROR occurred trying to enable allocation", message_style="bold white", panel_style="red")
                exit(1)
            return

        elif self.args.allocation_action == "disable":
            success = self.es_client.change_shard_allocation('primary')
            if success:
                self.es_client.show_message_box("Success", "⚠️ Successfully disabled shard allocation (primaries only).\nReplica shards will not be allocated or moved.", message_style="bold white", panel_style="yellow")
                # Show updated settings
                format_type = getattr(self.args, 'format', 'table')
                if format_type == 'json':
                    settings = self.es_client.es.cluster.get_settings(include_defaults=False)
                    import json
                    self.es_client.pretty_print_json(settings)
                else:
                    self.es_client.print_enhanced_allocation_settings()
            else:
                self.es_client.show_message_box("Error", "❌ An ERROR occurred trying to disable allocation", message_style="bold white", panel_style="red")
                exit(1)
            return

        elif self.args.allocation_action == "exclude":
            # Handle exclude subcommands
            if not hasattr(self.args, 'exclude_action') or self.args.exclude_action is None:
                self.es_client.show_message_box("Error", "No exclude action specified. Use 'add', 'remove', or 'reset'.", message_style="bold white", panel_style="red")
                return

            if self.args.exclude_action == "add":
                if not hasattr(self.args, 'hostname') or not self.args.hostname:
                    self.es_client.show_message_box("Error", "Hostname is required for exclude add operation", message_style="bold white", panel_style="red")
                    return

                success = self.es_client.exclude_node_from_allocation(self.args.hostname)
                if success:
                    self.es_client.show_message_box("Success", f"✅ Successfully excluded node '{self.args.hostname}' from allocation.\nShards will be moved away from this node.", message_style="bold white", panel_style="green")
                    # Show updated settings
                    format_type = getattr(self.args, 'format', 'table')
                    if format_type == 'json':
                        settings = self.es_client.es.cluster.get_settings(include_defaults=False)
                        import json
                        self.es_client.pretty_print_json(settings)
                    else:
                        self.es_client.print_enhanced_allocation_settings()
                else:
                    self.es_client.show_message_box("Error", "❌ An ERROR occurred trying to exclude node from allocation", message_style="bold white", panel_style="red")
                    exit(1)
                return

            elif self.args.exclude_action == "remove":
                if not hasattr(self.args, 'hostname') or not self.args.hostname:
                    self.es_client.show_message_box("Error", "Hostname is required for exclude remove operation", message_style="bold white", panel_style="red")
                    return
                self._handle_allocation_remove()
                return

            elif self.args.exclude_action == "reset":
                # Get current exclusions to show what will be reset
                current_exclusions = self._get_current_exclusions()
                
                if not current_exclusions:
                    self.es_client.show_message_box("Info", "ℹ️ No hosts are currently excluded from allocation.\nNothing to reset.", message_style="bold white", panel_style="blue")
                    return
                
                # Check if confirmation bypass flag is used
                if not getattr(self.args, 'yes_i_really_mean_it', False):
                    # Show warning and require confirmation
                    excluded_hosts_list = "\n".join([f"  • {host}" for host in current_exclusions])
                    warning_message = f"""⚠️  WARNING: This will reset ALL node allocation exclusions!
                    
Currently excluded hosts:
{excluded_hosts_list}

This action will:
• Remove all node exclusions from the cluster
• Allow shard allocation on ALL nodes
• Potentially cause significant shard movement

This is a cluster-wide operation that cannot be undone easily."""

                    self.es_client.show_message_box("WARNING", warning_message, message_style="bold yellow", panel_style="red")
                    
                    # Require confirmation
                    confirmation = input("\nType 'RESET' to confirm this cluster-wide reset: ").strip()
                    
                    if confirmation != 'RESET':
                        self.es_client.show_message_box("Cancelled", "❌ Reset operation cancelled. No changes made.", message_style="bold white", panel_style="yellow")
                        return
                
                success = self.es_client.reset_node_allocation_exclusion()
                if success:
                    self.es_client.show_message_box("Success", "✅ Successfully reset node allocation exclusions.\nAll nodes are now available for allocation.", message_style="bold white", panel_style="green")
                    # Show updated settings
                    format_type = getattr(self.args, 'format', 'table')
                    if format_type == 'json':
                        settings = self.es_client.es.cluster.get_settings(include_defaults=False)
                        import json
                        self.es_client.pretty_print_json(settings)
                    else:
                        self.es_client.print_enhanced_allocation_settings()
                else:
                    self.es_client.show_message_box("Error", "❌ An ERROR occurred trying to reset node allocation exclusion", message_style="bold white", panel_style="red")
                    exit(1)
                return

        elif self.args.allocation_action == "explain":
            self._handle_allocation_explain()
            return
        else:
            self.es_client.show_message_box("Error", f"Unknown allocation action: {self.args.allocation_action}", message_style="bold white", panel_style="red")

    def handle_exclude(self):
        """Handle index-level exclusion from specific nodes."""
        if not self.args.indice or not self.args.server:
            self._show_exclude_error()
            return
        self._process_exclude()

    def handle_exclude_reset(self):
        """Handle resetting index exclusion settings."""
        if not self.args.indice:
            self.es_client.show_message_box("ERROR", "You must pass indice name \n(i.e.: .ds-aex10-c01-logs-ueb-main-2025.04.03-000732)", message_style="bold white", panel_style="red")
            exit(1)
        self._process_exclude_reset()

    def _handle_allocation_remove(self):
        """Remove a specific host from the cluster-wide exclusion list."""
        hostname = self.args.hostname

        # Get current exclusions
        current_exclusions = self._get_current_exclusions()

        if not current_exclusions:
            self.es_client.show_message_box("Info", "ℹ️ No hosts are currently excluded from allocation", message_style="bold white", panel_style="blue")
            return

        # Check if hostname is in exclusion list
        if hostname not in current_exclusions:
            self.es_client.show_message_box("Info", f"ℹ️ Host '{hostname}' is not in the exclusion list.\n\nCurrently excluded hosts:\n• {chr(10).join(['• ' + host for host in current_exclusions])}", message_style="bold white", panel_style="blue")
            return

        # Remove hostname from list
        updated_exclusions = [host for host in current_exclusions if host != hostname]

        # Apply updated exclusions
        if updated_exclusions:
            # Set exclusions with remaining hosts
            success = self._set_exclusions(updated_exclusions)
            if success:
                self.es_client.show_message_box("Success", f"✅ Successfully removed '{hostname}' from exclusion list.\n\nRemaining excluded hosts:\n• {chr(10).join(['• ' + host for host in updated_exclusions])}", message_style="bold white", panel_style="green")
                # Show updated settings
                format_type = getattr(self.args, 'format', 'table')
                if format_type == 'json':
                    settings = self.es_client.es.cluster.get_settings(include_defaults=False)
                    import json
                    self.es_client.pretty_print_json(settings)
                else:
                    self.es_client.print_enhanced_allocation_settings()
            else:
                self.es_client.show_message_box("Error", f"❌ Failed to remove '{hostname}' from exclusion list", message_style="bold white", panel_style="red")
        else:
            # Reset if no hosts remain
            success = self._reset_all_exclusions()
            if success:
                self.es_client.show_message_box("Success", f"✅ Successfully removed '{hostname}' from exclusion list.\n\nNo hosts remain excluded - all nodes are available for allocation.", message_style="bold white", panel_style="green")
                # Show updated settings
                format_type = getattr(self.args, 'format', 'table')
                if format_type == 'json':
                    settings = self.es_client.es.cluster.get_settings(include_defaults=False)
                    import json
                    self.es_client.pretty_print_json(settings)
                else:
                    self.es_client.print_enhanced_allocation_settings()
            else:
                self.es_client.show_message_box("Error", f"❌ Failed to remove '{hostname}' from exclusion list", message_style="bold white", panel_style="red")

    def _handle_allocation_explain(self):
        """
        Handle allocation explain command.
        Provides detailed allocation information for a specific index/shard.
        """
        try:
            index_name = self.args.index
            shard_number = getattr(self.args, 'shard', 0)

            # Auto-detect primary vs replica if not specified
            if hasattr(self.args, 'primary') and self.args.primary:
                is_primary = True
            else:
                # Auto-detect by checking shard status
                try:
                    shards_data = self.es_client.get_shards_as_dict()
                    index_shards = [s for s in shards_data if s['index'] == index_name and s['shard'] == str(shard_number)]

                    if index_shards:
                        # If we have both primary and replica, prefer primary for explanation
                        primary_shard = next((s for s in index_shards if s['prirep'] == 'p'), index_shards[0])
                        is_primary = primary_shard['prirep'] == 'p'
                    else:
                        # Default to primary if we can't find the shard
                        is_primary = True
                except:
                    # Fallback to primary if detection fails
                    is_primary = True

            # Get allocation explanation
            explain_result = self.es_client.get_enhanced_allocation_explain(index_name, shard_number, is_primary)

            if self.args.format == 'json':
                self.es_client.pretty_print_json(explain_result)
            else:
                self.es_client.print_allocation_explain_results(explain_result)

        except Exception as e:
            self.es_client.show_message_box("Error", f"Failed to explain allocation for {self.args.index}: {str(e)}", message_style="bold white", panel_style="red")

    def _get_current_exclusions(self):
        """Get list of currently excluded hosts."""
        try:
            settings = self.es_client.es.cluster.get_settings()
            exclusions_setting = settings.get('transient', {}).get('cluster', {}).get('routing', {}).get('allocation', {}).get('exclude', {}).get('_name', '')

            if exclusions_setting:
                return [host.strip() for host in exclusions_setting.split(',') if host.strip()]
            return []
        except Exception as e:
            print(f"Error getting current exclusions: {str(e)}")
            return []

    def _set_exclusions(self, hostnames):
        """Set exclusions to specific list of hostnames."""
        try:
            exclusion_string = ','.join(hostnames)
            settings = {
                "transient": {
                    "cluster.routing.allocation.exclude._name": exclusion_string
                }
            }
            self.es_client.es.cluster.put_settings(body=settings)
            return True
        except Exception as e:
            print(f"Error setting exclusions: {str(e)}")
            return False

    def _reset_all_exclusions(self):
        """Reset all exclusions (same as existing reset functionality)."""
        try:
            settings = {
                "transient": {
                    "cluster.routing.allocation.exclude._name": None
                }
            }
            self.es_client.es.cluster.put_settings(body=settings)
            return True
        except Exception as e:
            print(f"Error resetting exclusions: {str(e)}")
            return False

    def _show_exclude_error(self):
        """Show error message for missing exclude parameters."""
        if not self.args.indice:
            print("Error, You must pass indice name (i.e.: .ds-aex10-c01-logs-ueb-main-2025.04.03-000732)")
        if not self.args.server:
            print("Error, -s {server} (ie: aex10-c01-ess01-1) is required for this parameter.")
        exit(1)

    def _process_exclude(self):
        """Process index exclusion from specific server."""
        args_server = self.args.server[0]
        cluster_active_indices = self.es_client.get_indices_stats(pattern=None, status=None)

        if not self.es_client.find_matching_index(cluster_active_indices, self.args.indice):
            self.es_client.show_message_box('ERROR', f"No such indice found: {self.args.indice}", message_style="white", panel_style="white")
            exit(1)

        cluster_shards = self.es_client.get_shards_stats(pattern='*')
        indice_server_fullname = self.es_client.find_matching_node(cluster_shards, self.args.indice, args_server)

        if not indice_server_fullname:
            self.es_client.show_message_box('ERROR', f"ERROR: No matching Shard for {self.args.indice} on Server {args_server}", message_style="white", panel_style="white")
            exit(1)

        response = self.es_client.exclude_index_from_host(self.args.indice, indice_server_fullname)
        if response:
            self.es_client.show_message_box('SUCCESS', f"Indice: {self.args.indice}\nHost: {indice_server_fullname}")
        else:
            self.es_client.show_message_box('ERROR', "An error has occured trying to exclude indice from host.")
            exit(1)

    def _process_exclude_reset(self):
        """Process resetting index exclusion settings."""
        response, message = self.es_client.exclude_index_reset(self.args.indice)
        if response:
            self.es_client.show_message_box("SUCCESS", f"Succesfully removed exclude settings from indice {self.args.indice}")
        else:
            self.es_client.show_message_box("ERROR", message)
            exit(1)
