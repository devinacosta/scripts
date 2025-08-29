"""
Replica management command handlers for escmd.

This module contains handlers for replica count management operations.
"""

import json
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.prompt import Confirm

from .base_handler import BaseHandler


class ReplicaHandler(BaseHandler):
    """Handler for replica management commands."""

    def handle_set_replicas(self):
        """Handle replica count management command."""
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
                print(json.dumps(result, indent=2))
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
                print(json.dumps(error_result, indent=2))
            else:
                self.console.print(f"[red]Error: {str(e)}[/red]")
