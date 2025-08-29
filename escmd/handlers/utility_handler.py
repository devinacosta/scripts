"""
Utility handler for miscellaneous escmd commands.

Handles commands like locations, datastreams, and cluster-check.
"""

import json
import os
from rich.table import Table
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.prompt import Confirm

from .base_handler import BaseHandler
from configuration_manager import ConfigurationManager


class UtilityHandler(BaseHandler):
    """Handler for utility commands like locations, datastreams, and cluster health checks."""
    
    def handle_locations(self):
        """
        Display all configured Elasticsearch locations.
        """
        config_manager = ConfigurationManager(self.config_file, os.path.join(os.path.dirname(self.config_file), 'escmd.json'))
        config_manager.show_locations()

    def handle_datastreams(self):
        """Handle datastreams command - list all datastreams, show details, or delete a specific one"""
        try:
            if self.args.name and self.args.delete:
                # Delete the specified datastream with confirmation
                self._handle_datastream_delete()
            elif self.args.name:
                # Show details for a specific datastream
                datastream_details = self.es_client.get_datastream_details(self.args.name)

                if self.args.format == 'json':
                    self.es_client.pretty_print_json(datastream_details)
                else:
                    self._print_datastream_details_table(datastream_details)
            elif self.args.delete:
                # Delete option requires a datastream name
                print("❌ Error: Datastream name is required when using --delete option")
                print("Usage: ./escmd.py datastreams <datastream_name> --delete")
            else:
                # List all datastreams
                datastreams_data = self.es_client.list_datastreams()

                if self.args.format == 'json':
                    self.es_client.pretty_print_json(datastreams_data)
                else:
                    self._print_datastreams_table(datastreams_data)

        except Exception as e:
            print(f"Error with datastreams operation: {e}")

    def handle_cluster_check(self):
        """Handle comprehensive cluster health checking command."""
        import time

        max_shard_size = getattr(self.args, 'max_shard_size', 50)  # Default 50GB
        show_details = getattr(self.args, 'show_details', False)
        skip_ilm = getattr(self.args, 'skip_ilm', False)

        if self.args.format == 'json':
            # Gather all data for JSON output
            check_results = self.es_client.perform_cluster_health_checks(max_shard_size, skip_ilm)
            
            # Handle replica fixing if requested
            fix_replicas = getattr(self.args, 'fix_replicas', None)
            if fix_replicas is not None:
                replica_results = self._perform_replica_fixing_json(check_results, fix_replicas)
                check_results['replica_fixing'] = replica_results
                
            # Sanitize the data to ensure valid JSON
            sanitized_results = self._sanitize_for_json(check_results)
            self.es_client.pretty_print_json(sanitized_results)
        else:
            # Rich formatted output with progress tracking
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=self.console,
                transient=True
            ) as progress:

                # Create main task (adjust total based on whether ILM is skipped)
                total_steps = 3 if skip_ilm else 4
                main_task = progress.add_task("[bold cyan]Running cluster health checks...", total=total_steps)

                # Step 1: ILM errors check (skip if requested)
                if not skip_ilm:
                    progress.update(main_task, description="[bold yellow]🔍 Checking for ILM errors...")
                    ilm_errors = self.es_client.check_ilm_errors()
                    progress.advance(main_task)
                    time.sleep(0.1)
                else:
                    ilm_errors = {'skipped': True, 'reason': 'ILM checks skipped via --skip-ilm flag'}

                # Step 2: No replicas check
                progress.update(main_task, description="[bold blue]📊 Checking indices with no replicas...")
                no_replica_indices = self.es_client.check_no_replica_indices()
                progress.advance(main_task)
                time.sleep(0.1)

                # Step 3: Large shards check
                progress.update(main_task, description="[bold orange1]📏 Checking for oversized shards...")
                large_shards = self.es_client.check_large_shards(max_shard_size)
                progress.advance(main_task)
                time.sleep(0.1)

                # Step 4: Generate report
                progress.update(main_task, description="[bold green]📋 Generating health report...")
                progress.advance(main_task)

            # Display comprehensive health report
            self.es_client.display_cluster_health_report({
                'ilm_results': ilm_errors,  # Pass as ilm_results to match new format
                'no_replica_indices': no_replica_indices,
                'large_shards': large_shards,
                'max_shard_size': max_shard_size,
                'show_details': show_details
            })
            
            # Handle replica fixing if requested
            fix_replicas = getattr(self.args, 'fix_replicas', None)
            if fix_replicas is not None:
                self._handle_replica_fixing_in_cluster_check(no_replica_indices, fix_replicas)

    def handle_set_replicas(self):
        """Handle replica count management command."""
        import json
        
        # Extract arguments
        target_count = getattr(self.args, 'count', 1)
        indices_arg = getattr(self.args, 'indices', None)
        pattern = getattr(self.args, 'pattern', None)
        no_replicas_only = getattr(self.args, 'no_replicas_only', False)
        dry_run = getattr(self.args, 'dry_run', False)
        force = getattr(self.args, 'force', False)
        format_output = getattr(self.args, 'format', 'table')
        
        try:
            # Initialize replica manager from esclient
            if not hasattr(self.es_client, 'replica_manager'):
                self.es_client.init_replica_manager()
            
            # Parse indices if provided
            target_indices = []
            if indices_arg:
                target_indices = [idx.strip() for idx in indices_arg.split(',') if idx.strip()]
            
            # Get indices to update
            if format_output == 'json':
                # JSON output mode
                result = self.es_client.replica_manager.plan_replica_updates(
                    target_count=target_count,
                    indices=target_indices,
                    pattern=pattern,
                    no_replicas_only=no_replicas_only
                )
                if not dry_run and result['indices_to_update']:
                    result = self.es_client.replica_manager.execute_replica_updates(
                        result['indices_to_update'], 
                        target_count
                    )
                self.es_client.pretty_print_json(result)
            else:
                # Rich formatted output
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    console=self.console,
                    transient=True
                ) as progress:
                    
                    # Plan the updates
                    plan_task = progress.add_task("[bold cyan]Planning replica updates...", total=1)
                    plan_result = self.es_client.replica_manager.plan_replica_updates(
                        target_count=target_count,
                        indices=target_indices,
                        pattern=pattern,
                        no_replicas_only=no_replicas_only
                    )
                    progress.advance(plan_task)
                
                # Display the plan
                self.es_client.replica_manager.display_update_plan(plan_result, dry_run)
                
                # Execute if not dry run and there are updates
                if not dry_run and plan_result['indices_to_update']:
                    if not force:
                        if not Confirm.ask(f"\n⚠️  This will update {len(plan_result['indices_to_update'])} indices. Continue?"):
                            self.console.print("[yellow]Operation cancelled.[/yellow]")
                            return
                    
                    # Execute the updates
                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        BarColumn(),
                        TaskProgressColumn(),
                        console=self.console,
                        transient=True
                    ) as progress:
                        
                        update_task = progress.add_task("[bold green]Updating replica counts...", total=len(plan_result['indices_to_update']))
                        result = self.es_client.replica_manager.execute_replica_updates(
                            plan_result['indices_to_update'], 
                            target_count,
                            progress=progress,
                            task_id=update_task
                        )
                    
                    # Display results
                    self.es_client.replica_manager.display_update_results(result)
                    
        except Exception as e:
            if format_output == 'json':
                error_result = {'error': str(e), 'success': False}
                self.es_client.pretty_print_json(error_result)
            else:
                self.console.print(f"[red]Error: {str(e)}[/red]")

    def _print_datastreams_table(self, datastreams_data):
        """Print datastreams list in table format"""
        console = Console()
        
        # Check if there are any datastreams
        datastreams_list = datastreams_data.get('data_streams', [])
        if not datastreams_list:
            # Create a nice panel showing no datastreams found
            from rich.panel import Panel
            from rich.text import Text
            
            content = Text()
            content.append("🔍 ", style="bold cyan")
            content.append("No datastreams found in this cluster", style="bold white")
            content.append("\n\n💡 ", style="bold yellow")
            content.append("Datastreams store time-series data (logs, metrics).", style="dim")
            content.append("\n   Create using index templates with 'data_stream' config.", style="dim")
            
            panel = Panel(
                content,
                title="📊 Datastreams",
                border_style="cyan",
                padding=(1, 2),
                width=100
            )
            
            print()
            console.print(panel)
            print()
            return
        
        table = Table(show_header=True, header_style="bold magenta", title="📊 Datastreams")

        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Status", style="green")
        table.add_column("Template", style="yellow")
        table.add_column("ILM Policy", style="blue")
        table.add_column("Generation", style="white", justify="right")
        table.add_column("Indices Count", style="white", justify="right")

        for datastream in datastreams_list:
            name = datastream.get('name', 'N/A')
            status = datastream.get('status', 'N/A')
            template = datastream.get('template', 'N/A')
            ilm_policy = datastream.get('ilm_policy', 'N/A')
            generation = str(datastream.get('generation', 0))
            indices_count = str(len(datastream.get('indices', [])))

            table.add_row(name, status, template, ilm_policy, generation, indices_count)

        console.print(table)

    def _print_datastream_details_table(self, datastream_data):
        """Print detailed datastream information in table format"""
        console = Console()

        if 'data_streams' not in datastream_data or not datastream_data['data_streams']:
            console.print("[red]No datastream found or datastream data is empty[/red]")
            return

        datastream = datastream_data['data_streams'][0]

        # Main datastream info panel
        # Basic info table
        info_table = Table.grid(padding=(0, 3))
        info_table.add_column(style="bold cyan", min_width=15)
        info_table.add_column(style="white")

        info_table.add_row("📛 Name:", datastream.get('name', 'N/A'))
        info_table.add_row("📊 Status:", datastream.get('status', 'N/A'))
        info_table.add_row("📋 Template:", datastream.get('template', 'N/A'))
        info_table.add_row("🔄 ILM Policy:", datastream.get('ilm_policy', 'N/A'))
        info_table.add_row("🔢 Generation:", str(datastream.get('generation', 0)))

        panel = Panel(info_table, title="🗂️ Datastream Details", border_style="cyan")
        console.print(panel)

        # Indices table
        indices = datastream.get('indices', [])
        if indices:
            indices_table = Table(show_header=True, header_style="bold magenta", title="📚 Backing Indices")
            indices_table.add_column("Index Name", style="cyan")
            indices_table.add_column("UUID", style="yellow")

            for index in indices:
                indices_table.add_row(
                    index.get('index_name', 'N/A'),
                    index.get('index_uuid', 'N/A')
                )

            console.print(indices_table)

    def _handle_datastream_delete(self):
        """Handle datastream deletion with confirmation and validation"""
        console = Console()
        datastream_name = self.args.name

        try:
            # First, verify the datastream exists by getting its details
            console.print(f"\n🔍 Verifying datastream '{datastream_name}'...")

            try:
                datastream_details = self.es_client.get_datastream_details(datastream_name)
                if not datastream_details.get('data_streams'):
                    console.print(f"❌ [bold red]Datastream '{datastream_name}' not found[/bold red]")
                    return

                datastream = datastream_details['data_streams'][0]
            except Exception as e:
                console.print(f"❌ [bold red]Error: Datastream '{datastream_name}' not found or inaccessible[/bold red]")
                console.print(f"Details: {str(e)}")
                return

            # Show datastream information before deletion
            info_table = Table(show_header=False, box=None, padding=(0, 1))
            info_table.add_column(style="bold white", no_wrap=True)
            info_table.add_column(style="cyan")

            info_table.add_row("📛 Name:", datastream.get('name', 'N/A'))
            info_table.add_row("📊 Status:", datastream.get('status', 'N/A'))
            info_table.add_row("📋 Template:", datastream.get('template', 'N/A'))
            info_table.add_row("🔄 ILM Policy:", datastream.get('ilm_policy', 'N/A'))
            info_table.add_row("🔢 Generation:", str(datastream.get('generation', 0)))

            indices_count = len(datastream.get('indices', []))
            info_table.add_row("📚 Backing Indices:", str(indices_count))

            warning_panel = Panel(
                info_table,
                title="⚠️  [bold yellow]Datastream to be Deleted[/bold yellow]",
                border_style="yellow",
                padding=(1, 2)
            )

            console.print()
            console.print(warning_panel)

            # Show backing indices that will be deleted
            indices = datastream.get('indices', [])
            if indices:
                console.print(f"\n💥 [bold red]WARNING: This will also delete {len(indices)} backing indices:[/bold red]")
                for i, index in enumerate(indices[:5]):  # Show first 5 indices
                    console.print(f"   • {index.get('index_name', 'N/A')}")

                if len(indices) > 5:
                    console.print(f"   ... and {len(indices) - 5} more indices")

            # Confirmation prompt
            console.print(f"\n🚨 [bold red]DANGER: This action cannot be undone![/bold red]")
            console.print(f"You are about to permanently delete datastream '[bold cyan]{datastream_name}[/bold cyan]' and all its backing indices.")

            # Interactive confirmation
            try:
                confirmation = input(f"\nType 'DELETE {datastream_name}' to confirm deletion: ").strip()

                if confirmation != f"DELETE {datastream_name}":
                    console.print(f"\n❌ [bold yellow]Deletion cancelled - confirmation text did not match[/bold yellow]")
                    console.print(f"Expected: 'DELETE {datastream_name}'")
                    console.print(f"Got: '{confirmation}'")
                    return

                # Perform deletion
                console.print(f"\n🗑️  [bold red]Deleting datastream '{datastream_name}'...[/bold red]")

                delete_result = self.es_client.delete_datastream(datastream_name)

                # Success confirmation
                success_panel = Panel(
                    Text(f"✅ Datastream '{datastream_name}' has been successfully deleted!\n\n"
                         f"• Datastream and all backing indices have been removed\n"
                         f"• {indices_count} indices were deleted\n"
                         f"• Operation completed successfully",
                         style="green"),
                    title="🎉 Deletion Successful",
                    border_style="green",
                    padding=(1, 2)
                )

                console.print()
                console.print(success_panel)
                console.print()

                # Show next steps
                actions_table = Table(show_header=False, box=None, padding=(0, 1))
                actions_table.add_column("Action", style="bold cyan", no_wrap=True)
                actions_table.add_column("Command", style="dim white")

                actions_table.add_row("List datastreams:", "./escmd.py datastreams")
                actions_table.add_row("Check indices:", "./escmd.py indices")
                actions_table.add_row("View cluster health:", "./escmd.py health")

                actions_panel = Panel(
                    actions_table,
                    title="🚀 Next Steps",
                    border_style="cyan",
                    padding=(1, 2)
                )

                console.print(actions_panel)
                console.print()

            except KeyboardInterrupt:
                console.print(f"\n❌ [bold yellow]Deletion cancelled by user[/bold yellow]")
                return

        except Exception as e:
            error_panel = Panel(
                Text(f"❌ Failed to delete datastream '{datastream_name}': {str(e)}",
                     style="bold red"),
                title="💥 Deletion Failed",
                border_style="red",
                padding=(1, 2)
            )
            console.print()
            console.print(error_panel)
            console.print()

    def _sanitize_for_json(self, obj):
        """Recursively sanitize data to ensure valid JSON by removing problematic fields and characters."""
        import re
        
        if isinstance(obj, dict):
            # Remove problematic fields that contain stack traces
            sanitized_dict = {}
            for key, value in obj.items():
                if key in ['stack_trace', 'step_info']:
                    # For step_info, keep only essential fields
                    if key == 'step_info' and isinstance(value, dict):
                        clean_step_info = {}
                        for step_key, step_value in value.items():
                            if step_key in ['type', 'reason'] and isinstance(step_value, str):
                                # Clean the reason/type but remove stack traces
                                cleaned = re.sub(r'[\x00-\x1F]', ' ', str(step_value))
                                cleaned = re.sub(r'\\n.*', '', cleaned)  # Remove everything after \n
                                clean_step_info[step_key] = cleaned[:200]  # Limit length
                        sanitized_dict[key] = clean_step_info
                    # Skip stack_trace entirely
                elif key == 'reason' and isinstance(value, str) and '\\n' in value:
                    # For reason fields, keep only the first line
                    cleaned = value.split('\\n')[0]
                    cleaned = re.sub(r'[\x00-\x1F]', ' ', cleaned)
                    sanitized_dict[key] = cleaned[:200]  # Limit length
                else:
                    sanitized_dict[key] = self._sanitize_for_json(value)
            return sanitized_dict
        elif isinstance(obj, list):
            return [self._sanitize_for_json(item) for item in obj]
        elif isinstance(obj, str):
            # Aggressively clean strings - remove all control characters
            sanitized = re.sub(r'[\x00-\x1F]', ' ', obj)
            # Limit very long strings
            if len(sanitized) > 500:
                sanitized = sanitized[:497] + "..."
            return sanitized
        else:
            return obj

    def _handle_replica_fixing_in_cluster_check(self, no_replica_indices, target_count):
        """Handle replica fixing in table mode during cluster-check."""
        if not no_replica_indices:
            self.console.print("\n[green]✅ No indices found with 0 replicas - nothing to fix![/green]")
            return
        
        # Extract arguments
        dry_run = getattr(self.args, 'dry_run', False)
        force = getattr(self.args, 'force', False)
        
        try:
            # Initialize replica manager
            if not hasattr(self.es_client, 'replica_manager'):
                self.es_client.init_replica_manager()
            
            # Convert no_replica_indices to the format expected by ReplicaManager
            target_indices = [idx['index'] for idx in no_replica_indices]
            
            # Plan the updates
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=self.console,
                transient=True
            ) as progress:
                plan_task = progress.add_task("[bold cyan]🔧 Planning replica fixes...", total=1)
                plan_result = self.es_client.replica_manager.plan_replica_updates(
                    target_count=target_count,
                    indices=target_indices,
                    no_replicas_only=True
                )
                progress.advance(plan_task)
            
            # Display section header
            header_text = f"🔧 Replica Fixing (Integrated with Cluster Check)"
            header_panel = Panel(
                header_text,
                title="🏥➜🔧 Health Check ➜ Replica Fixing",
                border_style="blue",
                padding=(1, 2)
            )
            self.console.print(header_panel)
            print()
            
            # Display the plan
            self.es_client.replica_manager.display_update_plan(plan_result, dry_run)
            
            # Execute if not dry run and there are updates
            if not dry_run and plan_result['indices_to_update']:
                if not force:
                    if not Confirm.ask(f"\n⚠️  This will update {len(plan_result['indices_to_update'])} indices found during health check. Continue?"):
                        self.console.print("[yellow]Replica fixing cancelled.[/yellow]")
                        return
                
                # Execute the updates
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    console=self.console,
                    transient=True
                ) as progress:
                    
                    update_task = progress.add_task("[bold green]🔧 Fixing replica counts...", total=len(plan_result['indices_to_update']))
                    result = self.es_client.replica_manager.execute_replica_updates(
                        plan_result['indices_to_update'], 
                        target_count,
                        progress=progress,
                        task_id=update_task
                    )
                
                # Display results
                self.es_client.replica_manager.display_update_results(result)
            elif dry_run:
                self.console.print("\n[yellow]ℹ️  This was a dry run - no changes were applied. Remove --dry-run to execute the fixes.[/yellow]")
                
        except Exception as e:
            self.console.print(f"[red]Error during replica fixing: {str(e)}[/red]")

    def _perform_replica_fixing_json(self, check_results, target_count):
        """Handle replica fixing in JSON mode during cluster-check."""
        dry_run = getattr(self.args, 'dry_run', False)
        
        try:
            # Initialize replica manager
            if not hasattr(self.es_client, 'replica_manager'):
                self.es_client.init_replica_manager()
            
            # Extract no replica indices from check results
            no_replica_indices = check_results.get('checks', {}).get('no_replica_indices', [])
            if not no_replica_indices:
                return {
                    'status': 'no_action_needed',
                    'message': 'No indices found with 0 replicas',
                    'target_count': target_count,
                    'dry_run': dry_run
                }
            
            # Convert to format expected by ReplicaManager
            target_indices = [idx['index'] for idx in no_replica_indices]
            
            # Plan the updates
            plan_result = self.es_client.replica_manager.plan_replica_updates(
                target_count=target_count,
                indices=target_indices,
                no_replicas_only=True
            )
            
            # Execute if not dry run
            if not dry_run and plan_result['indices_to_update']:
                execution_result = self.es_client.replica_manager.execute_replica_updates(
                    plan_result['indices_to_update'], 
                    target_count
                )
                return {
                    'status': 'executed',
                    'plan': plan_result,
                    'execution': execution_result,
                    'target_count': target_count,
                    'dry_run': dry_run
                }
            else:
                return {
                    'status': 'planned_only' if dry_run else 'no_updates_needed',
                    'plan': plan_result,
                    'target_count': target_count,
                    'dry_run': dry_run
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'target_count': target_count,
                'dry_run': dry_run
            }
