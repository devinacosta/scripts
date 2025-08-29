"""
Lifecycle handler for escmd ILM, rollover and auto-rollover commands.

Handles commands related to Index Lifecycle Management (ILM), rollover operations, and automatic rollover.
"""

import json
import re
from rich import print

from .base_handler import BaseHandler


class LifecycleHandler(BaseHandler):
    """Handler for lifecycle management commands like ILM, rollover, and auto-rollover."""
    
    def handle_rollover(self):
        """Handle rollover command for datastreams."""
        if not self.args.datastream:
            print("ERROR: No Datastream passed.")
            exit(1)
        rollover_stats = self.es_client.rollover_datastream(self.args.datastream)
        self.es_client.print_json_as_table(rollover_stats)

    def handle_auto_rollover(self):
        """Handle automatic rollover based on largest shard."""
        if not self.args.host:
            print("ERROR: No hostname passed.")
            exit(1)
        self._process_auto_rollover()

    def handle_ilm(self):
        """
        Handle ILM (Index Lifecycle Management) related commands.
        """
        if not hasattr(self.args, 'ilm_action') or self.args.ilm_action is None:
            self._show_ilm_help()
            return

        if self.args.ilm_action == 'status':
            self._handle_ilm_status()
        elif self.args.ilm_action == 'policies':
            self._handle_ilm_policies()
        elif self.args.ilm_action == 'policy':
            self._handle_ilm_policy()
        elif self.args.ilm_action == 'explain':
            self._handle_ilm_explain()
        elif self.args.ilm_action == 'errors':
            self._handle_ilm_errors()
        elif self.args.ilm_action == 'remove-policy':
            self._handle_ilm_remove_policy()
        elif self.args.ilm_action == 'set-policy':
            self._handle_ilm_set_policy()
        else:
            self.es_client.show_message_box("Error", f"Unknown ILM action: {self.args.ilm_action}", message_style="bold white", panel_style="red")

    def _process_auto_rollover(self):
        """Process automatic rollover for the largest shard on specified host."""
        shards_data_dict = sorted(self.es_client.get_shards_as_dict(), key=lambda x: x['size'], reverse=True)
        pattern = f".*{self.args.host}.*"
        filtered_data = [item for item in shards_data_dict if re.search(pattern, item['node'], re.IGNORECASE)]
        largest_primary_shard = next((item for item in filtered_data if item["prirep"] == "p"), None)

        if not largest_primary_shard:
            print("No matching shards found")
            return

        datastream_name = self._extract_datastream_name(largest_primary_shard["index"])
        if datastream_name:
            rollover_stats = self.es_client.rollover_datastream(datastream_name)
            self.es_client.print_json_as_table(rollover_stats)
        else:
            print(f"Could not extract datastream name from: {largest_primary_shard['index']}")

    def _extract_datastream_name(self, index_name):
        """Extract datastream name from index name."""
        match = re.search(r'\.ds-(.+)-\d{4}\.\d{2}\.\d{2}-\d+$', index_name)
        if match:
            return match.group(1)
        return None

    def _handle_ilm_status(self):
        """Handle ILM status command with comprehensive multi-panel display."""
        if self.args.format == 'json':
            ilm_data = self.es_client._get_ilm_status()
            self.es_client.pretty_print_json(ilm_data)
        else:
            self.es_client.print_enhanced_ilm_status()

    def _handle_ilm_policies(self):
        """Handle ILM policies list command."""
        if self.args.format == 'json':
            policies = self.es_client.get_ilm_policies()
            self.es_client.pretty_print_json(policies)
        else:
            self.es_client.print_enhanced_ilm_policies()

    def _handle_ilm_policy(self):
        """Handle ILM policy detail command."""
        if self.args.format == 'json':
            policy_data = self.es_client.get_ilm_policy_detail(self.args.policy_name)
            self.es_client.pretty_print_json(policy_data)
        else:
            self.es_client.print_enhanced_ilm_policy_detail(self.args.policy_name)

    def _handle_ilm_explain(self):
        """Handle ILM explain command to show specific index lifecycle status."""
        if self.args.format == 'json':
            explain_data = self.es_client.get_ilm_explain(self.args.index)
            self.es_client.pretty_print_json(explain_data)
        else:
            self.es_client.print_enhanced_ilm_explain(self.args.index)

    def _handle_ilm_errors(self):
        """Handle ILM errors command to show indices with ILM errors."""
        if self.args.format == 'json':
            errors_data = self.es_client.get_ilm_errors()
            self.es_client.pretty_print_json(errors_data)
        else:
            self.es_client.print_enhanced_ilm_errors()

    def _handle_ilm_remove_policy(self):
        """
        Handle ILM policy removal from indices matching regex pattern or from JSON file.
        """
        from_json = getattr(self.args, 'from_json', None)
        pattern = self.args.pattern
        
        # Validate arguments
        if from_json and pattern:
            self.es_client.show_message_box("Invalid Arguments", "Cannot use both pattern and --from-json. Choose one.", message_style="bold white", panel_style="red")
            return
        
        if not from_json and not pattern:
            self.es_client.show_message_box("Invalid Arguments", "Must provide either a pattern or --from-json file.", message_style="bold white", panel_style="red")
            return
        
        try:
            # Get matching indices based on input method
            if from_json:
                # Load indices from JSON file
                matching_indices = self._load_indices_from_json(from_json)
                if not matching_indices:
                    return  # Error already displayed in _load_indices_from_json
                source_description = f"JSON file: {from_json}"
            else:
                # Validate regex pattern
                try:
                    re.compile(pattern)
                except re.error as e:
                    self.es_client.show_message_box("Invalid Pattern", f"Invalid regex pattern '{pattern}': {str(e)}", message_style="bold white", panel_style="red")
                    return
                
                # Get indices matching pattern
                matching_indices = self.es_client.get_matching_indices(pattern)
                if not matching_indices:
                    self.es_client.show_message_box("No Matches", f"No indices found matching pattern '{pattern}'.", message_style="bold white", panel_style="red")
                    return
                source_description = f"pattern: {pattern}"
                
            # Perform bulk ILM policy removal
            results = self.es_client.remove_ilm_policy_from_indices(matching_indices, 
                                                                   dry_run=getattr(self.args, 'dry_run', False), 
                                                                   max_concurrent=getattr(self.args, 'max_concurrent', 5))
            
            # Save results to JSON if requested
            if getattr(self.args, 'save_json', None):
                save_source = from_json if from_json else f"pattern-{pattern}"
                self._save_removed_indices_to_json(results, self.args.save_json, save_source)
            
            # Display results
            if self.args.format == 'json':
                self.es_client.pretty_print_json(results)
            else:
                self.es_client.display_ilm_bulk_operation_results(results, "Policy Removal")
                
        except Exception as e:
            self.es_client.show_message_box("Error", f"Error during ILM policy removal: {str(e)}", message_style="bold white", panel_style="red")

    def _handle_ilm_set_policy(self):
        """
        Handle ILM policy assignment to indices matching regex pattern or from JSON file.
        """        
        policy_name = self.args.policy_name
        from_json = getattr(self.args, 'from_json', None)
        pattern = self.args.pattern
        
        # Validate arguments
        if from_json and pattern:
            self.es_client.show_message_box("Invalid Arguments", "Cannot use both pattern and --from-json. Choose one.", message_style="bold white", panel_style="red")
            return
        
        if not from_json and not pattern:
            self.es_client.show_message_box("Invalid Arguments", "Must provide either a pattern or --from-json file.", message_style="bold white", panel_style="red")
            return
        
        try:
            # Validate policy exists
            if not self.es_client.validate_ilm_policy_exists(policy_name):
                self.es_client.show_message_box("Policy Not Found", f"ILM policy '{policy_name}' does not exist.", message_style="bold white", panel_style="red")
                return
            
            # Get matching indices based on input method
            if from_json:
                # Load indices from JSON file
                matching_indices = self._load_indices_from_json(from_json)
                if not matching_indices:
                    return  # Error already displayed in _load_indices_from_json
                source_description = f"JSON file: {from_json}"
            else:
                # Validate regex pattern
                try:
                    re.compile(pattern)
                except re.error as e:
                    self.es_client.show_message_box("Invalid Pattern", f"Invalid regex pattern '{pattern}': {str(e)}", message_style="bold white", panel_style="red")
                    return
                
                # Get indices matching pattern
                matching_indices = self.es_client.get_matching_indices(pattern)
                if not matching_indices:
                    self.es_client.show_message_box("No Matches", f"No indices found matching pattern '{pattern}'.", message_style="bold white", panel_style="red")
                    return
                source_description = f"pattern: {pattern}"
                
            # Perform bulk ILM policy assignment
            results = self.es_client.set_ilm_policy_for_indices(matching_indices, policy_name, 
                                                               dry_run=getattr(self.args, 'dry_run', False), 
                                                               max_concurrent=getattr(self.args, 'max_concurrent', 5))
            
            # Save results to JSON if requested
            if getattr(self.args, 'save_json', None):
                save_source = from_json if from_json else f"pattern-{pattern}"
                self._save_set_indices_to_json(results, self.args.save_json, save_source, policy_name)
            
            # Display results
            if self.args.format == 'json':
                self.es_client.pretty_print_json(results)
            else:
                self.es_client.display_ilm_bulk_operation_results(results, f"Policy Assignment ({policy_name})")
                
        except Exception as e:
            self.es_client.show_message_box("Error", f"Error during ILM policy assignment: {str(e)}", message_style="bold white", panel_style="red")

    def _load_indices_from_json(self, file_path):
        """Load indices list from JSON file."""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'indices' in data:
                return data['indices']
            else:
                self.es_client.show_message_box("Invalid JSON Format", f"JSON file must contain a list of indices or an object with 'indices' key.", message_style="bold white", panel_style="red")
                return None
                
        except FileNotFoundError:
            self.es_client.show_message_box("File Not Found", f"JSON file '{file_path}' not found.", message_style="bold white", panel_style="red")
            return None
        except json.JSONDecodeError as e:
            self.es_client.show_message_box("Invalid JSON", f"Invalid JSON in file '{file_path}': {str(e)}", message_style="bold white", panel_style="red")
            return None
        except Exception as e:
            self.es_client.show_message_box("File Load Error", f"Error loading JSON file: {str(e)}", message_style="bold white", panel_style="red")
            return None

    def _save_removed_indices_to_json(self, results, file_path, source):
        """Save removed indices results to JSON file."""
        try:
            output_data = {
                "operation": "remove_policy",
                "source": source,
                "timestamp": json.dumps({"timestamp": "now"}, default=str),  # Placeholder for timestamp
                "results": results
            }
            
            with open(file_path, 'w') as f:
                json.dump(output_data, f, indent=2)
            
            print(f"Results saved to: {file_path}")
            
        except Exception as e:
            self.es_client.show_message_box("Save Error", f"Error saving results to JSON file: {str(e)}", message_style="bold white", panel_style="red")

    def _save_set_indices_to_json(self, results, file_path, source, policy_name):
        """Save set policy results to JSON file."""
        try:
            output_data = {
                "operation": "set_policy",
                "policy_name": policy_name,
                "source": source,
                "timestamp": json.dumps({"timestamp": "now"}, default=str),  # Placeholder for timestamp
                "results": results
            }
            
            with open(file_path, 'w') as f:
                json.dump(output_data, f, indent=2)
            
            print(f"Results saved to: {file_path}")
            
        except Exception as e:
            self.es_client.show_message_box("Save Error", f"Error saving results to JSON file: {str(e)}", message_style="bold white", panel_style="red")

    def _show_ilm_help(self):
        """Display ILM help menu with available commands and examples."""
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        
        console = Console()
        
        # Create command table
        help_table = Table.grid(padding=(0, 3))
        help_table.add_column(style="bold cyan", min_width=15)
        help_table.add_column(style="white")
        
        help_table.add_row("📊 status", "Show comprehensive ILM status and statistics")
        help_table.add_row("📋 policies", "List all ILM policies with phase configurations")
        help_table.add_row("🔍 policy <name>", "Show detailed configuration for specific ILM policy")
        help_table.add_row("🔎 explain <index>", "Show ILM status for specific index")
        help_table.add_row("⚠️ errors", "Show indices with ILM errors")
        help_table.add_row("➕ set-policy <policy> <pattern>", "Assign ILM policy to indices matching pattern")
        help_table.add_row("➖ remove-policy <pattern>", "Remove ILM policy from indices matching pattern")
        
        # Create examples table  
        examples_table = Table.grid(padding=(0, 3))
        examples_table.add_column(style="bold green", min_width=15)
        examples_table.add_column(style="dim white")
        
        examples_table.add_row("Basic Status:", "./escmd.py ilm status")
        examples_table.add_row("List Policies:", "./escmd.py ilm policies")
        examples_table.add_row("Policy Details:", "./escmd.py ilm policy logs")
        examples_table.add_row("Check Index:", "./escmd.py ilm explain myindex-001")
        examples_table.add_row("Set Policy:", "./escmd.py ilm set-policy 30-days-default 'logs-*'")
        examples_table.add_row("Remove Policy:", "./escmd.py ilm remove-policy 'temp-*'")
        examples_table.add_row("JSON Output:", "./escmd.py ilm status --format json")
        
        # Display help
        print()
        console.print(Panel(
            help_table,
            title="🔄 Index Lifecycle Management (ILM) Commands",
            border_style="blue",
            padding=(1, 2)
        ))
        
        print()
        console.print(Panel(
            examples_table,
            title="🚀 Usage Examples",
            border_style="green", 
            padding=(1, 2)
        ))
        print()
