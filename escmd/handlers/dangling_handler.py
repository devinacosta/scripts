#!/usr/bin/env python3

import json
import logging
import time
import os
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from rich.table import Table, Table as InnerTable
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn

from .base_handler import BaseHandler


class DanglingHandler(BaseHandler):
    """Handler for Elasticsearch dangling indices operations."""

    def handle_dangling(self):
        """Handle dangling indices command - list, delete, or cleanup all based on arguments."""
        console = self.console

        try:
            # Set up logging if log file is specified
            logger = None
            if hasattr(self.args, 'log_file') and self.args.log_file:
                logger = self._setup_dangling_logging(self.args.log_file)
            
            # Check for cleanup all functionality
            if hasattr(self.args, 'cleanup_all') and self.args.cleanup_all:
                self._handle_dangling_cleanup_all(logger)
                return
            
            # Check if deletion is requested for single index
            if hasattr(self.args, 'delete') and self.args.delete:
                if hasattr(self.args, 'uuid') and self.args.uuid:
                    self._handle_dangling_delete()
                    return
                else:
                    self.es_client.show_message_box(
                        "Missing UUID Parameter",
                        "❌ UUID is required for deletion.\nUsage: ./escmd.py dangling <uuid> --delete",
                        message_style="bold red",
                        border_style="red"
                    )
                    return

            # Regular listing functionality (existing code)
            # Get dangling indices data first
            dangling_result = self._get_dangling_indices_enhanced()
            
            if "error" in dangling_result:
                self.es_client.show_message_box(
                    "Error",
                    f"❌ Error retrieving dangling indices: {dangling_result['error']}",
                    message_style="bold red",
                    border_style="red"
                )
                return
            
            dangling_indices = dangling_result.get('dangling_indices', [])

            # Handle JSON format - return immediately with pure JSON output
            if getattr(self.args, 'format', 'table') == 'json':
                self.es_client.pretty_print_json({"dangling_indices": dangling_indices})
                return

            # Get cluster information for context (only for table format)
            try:
                health_data = self.es_client.get_cluster_health()
                cluster_name = health_data.get('cluster_name', 'Unknown')
                total_nodes = health_data.get('number_of_nodes', 0)
            except:
                cluster_name = 'Unknown'
                total_nodes = 0

            # Create title panel
            title_panel = Panel(
                Text(f"🔍 Dangling Indices Analysis", style="bold orange1", justify="center"),
                subtitle=f"Cluster: {cluster_name} | Nodes: {total_nodes}",
                border_style="orange1",
                padding=(1, 2)
            )

            print()
            console.print(title_panel)
            print()

            # Check if there are dangling indices
            if not dangling_indices:
                # No dangling indices found - success case
                self.es_client.show_message_box(
                    "✅ Cluster Index Status: Clean",
                    "🎉 No dangling indices found in the cluster!\n\n" +
                    "This indicates that:\n" +
                    "• All indices are properly assigned to nodes\n" +
                    "• No orphaned index metadata exists\n" +
                    "• Cluster index management is healthy",
                    message_style="green",
                    border_style="green"
                )
                
                # Create quick actions panel
                actions_table = InnerTable(show_header=False, box=None, padding=(0, 1))
                actions_table.add_column("Action", style="bold cyan", no_wrap=True)
                actions_table.add_column("Command", style="dim white")
                
                actions_table.add_row("Check cluster health:", "./escmd.py health")
                actions_table.add_row("List all indices:", "./escmd.py indices")
                actions_table.add_row("View cluster nodes:", "./escmd.py nodes")
                actions_table.add_row("Monitor recovery:", "./escmd.py recovery")

                actions_panel = Panel(
                    actions_table,
                    title="🚀 Related Commands",
                    border_style="cyan",
                    padding=(1, 2)
                )
                
                print()
                console.print(actions_panel)
                print()
                return

            # Calculate statistics
            total_dangling = len(dangling_indices)
            unique_nodes = set()
            creation_dates = []
            
            for idx in dangling_indices:
                node_ids = idx.get('node_ids', [])
                unique_nodes.update(node_ids)
                creation_date = idx.get('creation_date', 'Unknown')
                if creation_date != 'Unknown':
                    creation_dates.append(creation_date)

            # Create statistics panel
            stats_table = InnerTable(show_header=False, box=None, padding=(0, 1))
            stats_table.add_column("Label", style="bold", no_wrap=True)
            stats_table.add_column("Icon", justify="left", width=3)
            stats_table.add_column("Value", no_wrap=True)

            stats_table.add_row("Total Dangling:", "⚠️", f"{total_dangling:,}")
            stats_table.add_row("Affected Nodes:", "🖥️", f"{len(unique_nodes):,}")
            stats_table.add_row("Cluster Nodes:", "📊", f"{total_nodes:,}")
            
            if creation_dates:
                # Find oldest creation date
                oldest_date = min(creation_dates)
                stats_table.add_row("Oldest Found:", "📅", oldest_date)

            stats_panel = Panel(
                stats_table,
                title="📊 Dangling Indices Summary",
                border_style="yellow",
                padding=(1, 2)
            )

            # Create information panel about dangling indices
            info_text = ("🔍 About Dangling Indices:\n\n"
                        "• Indices that exist on disk but are not part of cluster metadata\n"
                        "• Often caused by node failures or split-brain scenarios\n"
                        "• Can be imported back to cluster or deleted manually\n"
                        "• May contain important data that needs recovery")

            info_panel = Panel(
                info_text,
                title="ℹ️ Information",
                border_style="blue",
                padding=(1, 2)
            )

            # Display summary panels
            console.print(Columns([stats_panel, info_panel], expand=True))
            print()

            # Get node mapping once for efficient hostname resolution
            node_id_to_hostname_map = self.es_client.get_node_id_to_hostname_map()

            # Create detailed dangling indices table
            table = Table(show_header=True, header_style="bold white", expand=True)
            table.add_column("🆔 Index UUID", style="cyan", no_wrap=True, width=38)
            table.add_column("📅 Creation Date", style="yellow", width=20, no_wrap=True)
            table.add_column("🖥️ Hostnames", style="magenta", no_wrap=False)
            table.add_column("📊 Node Count", style="white", width=12, justify="center")

            # Add rows to the table
            for idx in dangling_indices:
                index_uuid = idx.get('index_uuid', 'N/A')
                creation_date = idx.get('creation_date', 'N/A')
                node_ids = idx.get('node_ids', [])
                node_count = len(node_ids)
                
                # Resolve node IDs to hostnames using pre-built mapping
                if node_ids:
                    hostnames = self.es_client.resolve_node_ids_to_hostnames(node_ids, node_id_to_hostname_map)
                    # Format hostnames - truncate if too many
                    if len(hostnames) > 3:
                        node_display = ', '.join(hostnames[:3]) + f' (+{len(hostnames)-3} more)'
                    else:
                        node_display = ', '.join(hostnames)
                else:
                    node_display = 'N/A'

                # Color coding based on node count
                if node_count > 1:
                    row_style = "yellow"  # Multiple nodes have this dangling index
                elif node_count == 1:
                    row_style = "red"     # Only one node has this index
                else:
                    row_style = "dim"     # No nodes specified

                table.add_row(
                    index_uuid,
                    creation_date,
                    node_display,
                    str(node_count),
                    style=row_style
                )

            # Create table panel
            table_panel = Panel(
                table,
                title="⚠️ Dangling Indices Details",
                border_style="orange1",
                padding=(1, 2)
            )

            console.print(table_panel)
            print()

            # Create warning and actions panel
            warning_text = ("⚠️ WARNING: Dangling indices detected!\n\n"
                           f"Found {total_dangling} dangling indices across {len(unique_nodes)} nodes.\n"
                           "These indices contain data that is not accessible through normal cluster operations.\n\n"
                           "🚨 IMPORTANT: Review these indices carefully before taking action.\n"
                           "Consider consulting Elasticsearch documentation for recovery procedures.")

            warning_panel = Panel(
                warning_text,
                title="🚨 Action Required",
                border_style="red",
                padding=(1, 2)
            )

            # Create recovery actions panel
            recovery_table = InnerTable(show_header=False, box=None, padding=(0, 1))
            recovery_table.add_column("Action", style="bold red", no_wrap=True)
            recovery_table.add_column("Command", style="dim white")

            recovery_table.add_row("Delete Single Index:", f"./escmd.py dangling <uuid> --delete")
            recovery_table.add_row("Delete All (Dry Run):", f"./escmd.py dangling --cleanup-all --dry-run")
            recovery_table.add_row("Delete All (DANGER):", f"./escmd.py dangling --cleanup-all --yes-i-really-mean-it")
            recovery_table.add_row("Check Logs:", "Review Elasticsearch logs for root cause")

            recovery_panel = Panel(
                recovery_table,
                title="🔧 Recovery Options",
                border_style="magenta",
                padding=(1, 2)
            )

            console.print(Columns([warning_panel, recovery_panel], expand=True))
            print()

        except Exception as e:
            self.es_client.show_message_box(
                "Error",
                f"❌ Error handling dangling indices: {str(e)}",
                message_style="bold red",
                border_style="red"
            )

    def _setup_dangling_logging(self, log_file=None):
        """
        Set up logging for dangling operations.
        
        Args:
            log_file: Optional path to log file
            
        Returns:
            Configured logger instance
        """
        logger = logging.getLogger('dangling_cleanup')
        logger.setLevel(logging.INFO)
        
        # Clear any existing handlers
        logger.handlers.clear()
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Add console handler (always works)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # Add file handler if specified
        if log_file:
            try:
                file_handler = logging.FileHandler(log_file)
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)
                logger.info(f"Logging to file: {log_file}")
            except Exception as e:
                logger.warning(f"Could not set up file logging to {log_file}: {e}")
        
        return logger

    def _delete_dangling_index_with_retry(self, index_uuid, index_name=None, max_retries=3, retry_delay=5, dry_run=False, logger=None):
        """
        Delete a single dangling index with retry logic.
        
        Args:
            index_uuid: UUID of the dangling index
            index_name: Optional name of the index for logging
            max_retries: Maximum number of retry attempts
            retry_delay: Delay in seconds between retry attempts
            dry_run: If True, only simulate the deletion
            logger: Logger instance for output
            
        Returns:
            True if deletion successful, False otherwise
        """
        if not logger:
            logger = logging.getLogger('dangling_cleanup')
            
        index_info = f"'{index_name}' ({index_uuid})" if index_name else f"UUID: {index_uuid}"
        
        if dry_run:
            logger.info(f"DRY RUN: Would delete dangling index {index_info}")
            return True
        
        # Retry logic for dangling index deletion
        for attempt in range(1, max_retries + 1):
            try:
                if attempt > 1:
                    logger.info(f"Retrying deletion of dangling index {index_info} (attempt {attempt}/{max_retries})")
                else:
                    logger.info(f"Deleting dangling index {index_info}")
                
                # Delete the dangling index using the existing method
                delete_response = self.es_client.delete_dangling_index(index_uuid)
                
                if "error" in delete_response:
                    error_msg = delete_response['error']
                    
                    # Check if this is a retryable error
                    if attempt < max_retries and ("timeout" in error_msg.lower() or "503" in str(error_msg)):
                        logger.warning(f"Retryable error deleting dangling index {index_info}: {error_msg}")
                        time.sleep(retry_delay)
                        continue
                    else:
                        logger.error(f"Error deleting dangling index {index_info}: {error_msg}")
                        return False
                
                logger.info(f"Successfully deleted dangling index {index_info}")
                return True
                
            except Exception as e:
                # Handle specific error types
                error_msg = str(e)
                
                if "process_cluster_event_timeout_exception" in error_msg:
                    if attempt < max_retries:
                        logger.warning(f"Timeout deleting dangling index {index_info} - retrying in {retry_delay} seconds")
                        time.sleep(retry_delay)
                        continue
                    else:
                        logger.warning(f"Timeout deleting dangling index {index_info} after {max_retries} attempts. The deletion may still complete in the background.")
                        return True  # Consider this a partial success
                        
                elif "No dangling index found for UUID" in error_msg:
                    logger.warning(f"Dangling index {index_info} was already cleaned up or doesn't exist anymore - skipping")
                    return True  # Consider this a success as the index is already gone
                    
                elif "illegal_argument_exception" in error_msg and "No dangling index found" in error_msg:
                    logger.warning(f"Dangling index {index_info} no longer exists - likely already cleaned up")
                    return True
                    
                else:
                    if attempt < max_retries:
                        logger.warning(f"Error deleting dangling index {index_info}: {e} - retrying in {retry_delay} seconds")
                        time.sleep(retry_delay)
                        continue
                    else:
                        logger.error(f"Error deleting dangling index {index_info} after {max_retries} attempts: {e}")
                        return False
        
        return False

    def _get_dangling_indices_enhanced(self):
        """
        Get dangling indices with enhanced error handling.
        
        Returns:
            Dictionary with dangling_indices list or error information
        """
        try:
            return self.es_client.list_dangling_indices()
        except Exception as e:
            return {"error": str(e)}

    def _handle_dangling_cleanup_all(self, logger=None):
        """Handle cleanup of all dangling indices with confirmation and logging."""
        from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

        console = self.console
        if not logger:
            logger = logging.getLogger('dangling_cleanup')

        try:
            # First, get the list of dangling indices
            with console.status("[bold blue]Scanning for dangling indices..."):
                dangling_result = self._get_dangling_indices_enhanced()
            
            if "error" in dangling_result:
                self.es_client.show_message_box(
                    "Error",
                    f"❌ Error retrieving dangling indices: {dangling_result['error']}",
                    message_style="bold red",
                    border_style="red"
                )
                return
            
            dangling_indices = dangling_result.get('dangling_indices', [])
            
            if not dangling_indices:
                self.es_client.show_message_box(
                    "Cluster is clean",
                    "✅ No dangling indices found to clean up!",
                    message_style="bold green",
                    border_style="green"
                )
                return

            total_count = len(dangling_indices)
            
            # Check for dry run mode
            dry_run = hasattr(self.args, 'dry_run') and self.args.dry_run
            
            # Create summary panel
            summary_text = f"Found {total_count} dangling indices to {'simulate deletion' if dry_run else 'delete'}.\n\n"
            if dry_run:
                summary_text += "🔍 DRY RUN MODE: No actual deletions will occur.\n"
                summary_text += "This is a simulation to show what would be deleted."
            else:
                summary_text += "⚠️ DANGER: This will permanently delete all dangling indices!\n"
                summary_text += "This action cannot be undone."

            summary_panel = Panel(
                Text(summary_text, justify="center"),
                title=f"🧹 Cleanup All Dangling Indices {'(DRY RUN)' if dry_run else ''}",
                border_style="yellow" if dry_run else "red",
                padding=(1, 2)
            )
            
            print()
            console.print(summary_panel)
            print()

            # Safety confirmation (unless --yes-i-really-mean-it is used)
            if not dry_run and not (hasattr(self.args, 'yes_i_really_mean_it') and self.args.yes_i_really_mean_it):
                console.print(f"[bold red]⚠️ WARNING: About to delete {total_count} dangling indices![/bold red]")
                console.print("[dim]This action is irreversible and will permanently remove data.[/dim]")
                print()
                
                try:
                    confirmation = input("Type 'yes-i-really-mean-it' to proceed with deletion: ")
                    if confirmation != 'yes-i-really-mean-it':
                        console.print("[bold yellow]❌ Operation cancelled.[/bold yellow]")
                        return
                except KeyboardInterrupt:
                    console.print("\n[bold yellow]❌ Operation cancelled by user.[/bold yellow]")
                    return
                
                print()

            # Process deletions with progress tracking
            successful_deletions = []
            failed_deletions = []
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console
            ) as progress:
                
                cleanup_task = progress.add_task(
                    f"[bold {'blue' if dry_run else 'red'}]{'Simulating' if dry_run else 'Deleting'} dangling indices...", 
                    total=total_count
                )
                
                for i, idx in enumerate(dangling_indices):
                    index_uuid = idx.get('index_uuid', 'Unknown')
                    index_name = idx.get('index_name', f'Unknown-{i+1}')
                    
                    progress.update(cleanup_task, description=f"[bold {'blue' if dry_run else 'red'}]Processing {index_name}...")
                    
                    # Attempt deletion with retry
                    success = self._delete_dangling_index_with_retry(
                        index_uuid=index_uuid,
                        index_name=index_name,
                        max_retries=3,
                        retry_delay=2,
                        dry_run=dry_run,
                        logger=logger
                    )
                    
                    if success:
                        successful_deletions.append({
                            'uuid': index_uuid,
                            'name': index_name
                        })
                    else:
                        failed_deletions.append({
                            'uuid': index_uuid, 
                            'name': index_name
                        })
                    
                    progress.advance(cleanup_task)
                    time.sleep(0.1)  # Small delay to prevent overwhelming the cluster

            # Results summary
            print()
            
            if successful_deletions:
                success_count = len(successful_deletions)
                success_text = f"{'Simulated' if dry_run else 'Successfully deleted'} {success_count} dangling indices"
                if not dry_run:
                    success_text += ":\n\n"
                    for idx in successful_deletions[:5]:  # Show first 5
                        success_text += f"• {idx['name']} ({idx['uuid'][:8]}...)\n"
                    if success_count > 5:
                        success_text += f"• ... and {success_count - 5} more indices"
                else:
                    success_text += " (simulation completed successfully)"

                success_panel = Panel(
                    success_text,
                    title=f"✅ {'Simulation' if dry_run else 'Cleanup'} Results",
                    border_style="green",
                    padding=(1, 2)
                )
                console.print(success_panel)

            if failed_deletions:
                failed_count = len(failed_deletions)
                failure_text = f"Failed to {'simulate' if dry_run else 'delete'} {failed_count} dangling indices:\n\n"
                for idx in failed_deletions[:5]:  # Show first 5 failures
                    failure_text += f"• {idx['name']} ({idx['uuid'][:8]}...)\n"
                if failed_count > 5:
                    failure_text += f"• ... and {failed_count - 5} more indices"

                failure_panel = Panel(
                    failure_text,
                    title="❌ Failed Operations",
                    border_style="red",
                    padding=(1, 2)
                )
                print()
                console.print(failure_panel)

            # Final summary
            print()
            final_summary = f"Operation completed: {len(successful_deletions)} successful, {len(failed_deletions)} failed"
            if dry_run:
                final_summary += " (dry run simulation)"
            logger.info(final_summary)

        except KeyboardInterrupt:
            console.print("\n[bold yellow]❌ Operation cancelled by user.[/bold yellow]")
            if logger:
                logger.info("Cleanup operation cancelled by user")
        except Exception as e:
            error_panel = Panel(
                Text(f"❌ Error during cleanup operation: {str(e)}", style="bold red", justify="center"),
                subtitle="Check logs for details",
                border_style="red",
                padding=(1, 2)
            )
            print()
            console.print(error_panel)
            print()
            if logger:
                logger.error(f"Error during cleanup operation: {str(e)}")

    def _handle_dangling_delete(self):
        """Handle deletion of a single dangling index by UUID."""
        console = self.console
        index_uuid = self.args.uuid

        try:
            # Get cluster info for context
            try:
                health_data = self.es_client.get_cluster_health()
                cluster_name = health_data.get('cluster_name', 'Unknown')
            except:
                cluster_name = 'Unknown'

            # Create title panel
            title_panel = Panel(
                Text(f"🗑️ Delete Dangling Index", style="bold red", justify="center"),
                subtitle=f"UUID: {index_uuid} | Cluster: {cluster_name}",
                border_style="red",
                padding=(1, 2)
            )

            print()
            console.print(title_panel)
            print()

            # Check if this is a dry run
            dry_run = hasattr(self.args, 'dry_run') and self.args.dry_run

            if dry_run:
                console.print("[bold blue]🔍 DRY RUN MODE: Simulating deletion...[/bold blue]")
                print()

            # Verify the dangling index exists
            with console.status(f"Verifying dangling index {index_uuid[:8]}..."):
                dangling_result = self._get_dangling_indices_enhanced()
            
            if "error" in dangling_result:
                error_panel = Panel(
                    Text(f"❌ Error retrieving dangling indices: {dangling_result['error']}", 
                         style="bold red", justify="center"),
                    subtitle="Cannot verify index existence",
                    border_style="red",
                    padding=(1, 2)
                )
                console.print(error_panel)
                print()
                return

            dangling_indices = dangling_result.get('dangling_indices', [])
            target_index = None
            
            # Find the specific index
            for idx in dangling_indices:
                if idx.get('index_uuid') == index_uuid:
                    target_index = idx
                    break
            
            if not target_index:
                warning_panel = Panel(
                    Text(f"⚠️ Dangling index with UUID {index_uuid} not found.\n\n"
                         "Possible reasons:\n"
                         "• Index was already deleted\n"
                         "• UUID was mistyped\n"
                         "• Index was recovered by cluster", 
                         style="yellow", justify="center"),
                    title="Index Not Found",
                    border_style="yellow",
                    padding=(1, 2)
                )
                console.print(warning_panel)
                print()
                return

            # Display index information
            creation_date = target_index.get('creation_date', 'Unknown')
            node_ids = target_index.get('node_ids', [])
            
            # Get node hostnames
            node_id_to_hostname_map = self.es_client.get_node_id_to_hostname_map()
            if node_ids:
                hostnames = self.es_client.resolve_node_ids_to_hostnames(node_ids, node_id_to_hostname_map)
                nodes_display = ', '.join(hostnames)
            else:
                nodes_display = 'N/A'

            # Create info table
            info_table = InnerTable(show_header=False, box=None, padding=(0, 1))
            info_table.add_column("Label", style="bold", no_wrap=True)
            info_table.add_column("Icon", justify="left", width=3)
            info_table.add_column("Value", no_wrap=True)

            info_table.add_row("Index UUID:", "🆔", index_uuid)
            info_table.add_row("Created:", "📅", creation_date)
            info_table.add_row("Nodes:", "🖥️", nodes_display)
            info_table.add_row("Node Count:", "📊", str(len(node_ids)))

            info_panel = Panel(
                info_table,
                title="📋 Index Information",
                border_style="cyan",
                padding=(1, 2)
            )

            # Create operation details
            op_table = InnerTable(show_header=False, box=None, padding=(0, 1))
            op_table.add_column("Label", style="bold", no_wrap=True)
            op_table.add_column("Icon", justify="left", width=3)
            op_table.add_column("Value", no_wrap=True)

            op_table.add_row("Operation:", "🗑️", "Delete Dangling Index")
            op_table.add_row("Mode:", "🔍" if dry_run else "💥", "Dry Run" if dry_run else "Actual Deletion")
            op_table.add_row("Reversible:", "❌", "No - Permanent")
            op_table.add_row("Data Loss:", "⚠️", "Yes - All data will be lost")

            op_panel = Panel(
                op_table,
                title="⚙️ Operation Details",
                border_style="red" if not dry_run else "blue",
                padding=(1, 2)
            )

            console.print(Columns([info_panel, op_panel], expand=True))
            print()

            # Confirmation for actual deletion (skip for dry run)
            if not dry_run:
                if not (hasattr(self.args, 'yes') and self.args.yes):
                    console.print(f"[bold red]⚠️ WARNING: About to permanently delete dangling index![/bold red]")
                    console.print(f"[dim]UUID: {index_uuid}[/dim]")
                    console.print(f"[dim]This action cannot be undone and will result in permanent data loss.[/dim]")
                    print()
                    
                    try:
                        confirmation = input("Type 'yes' to confirm deletion: ")
                        if confirmation.lower() != 'yes':
                            console.print("[bold yellow]❌ Operation cancelled.[/bold yellow]")
                            return
                    except KeyboardInterrupt:
                        console.print("\n[bold yellow]❌ Operation cancelled by user.[/bold yellow]")
                        return
                    
                    print()

            # Perform the deletion
            with console.status(f"{'Simulating' if dry_run else 'Deleting'} dangling index..."):
                success = self._delete_dangling_index_with_retry(
                    index_uuid=index_uuid,
                    index_name=f"dangling-{index_uuid[:8]}",
                    max_retries=3,
                    retry_delay=2,
                    dry_run=dry_run
                )

            if success:
                if dry_run:
                    success_panel = Panel(
                        Text(f"🎉 Dry run completed successfully!\n\n"
                             f"The dangling index {index_uuid[:8]}... would be deleted.\n"
                             f"No actual changes were made to the cluster.",
                             style="green", justify="center"),
                        title="✅ Simulation Successful",
                        border_style="green",
                        padding=(1, 2)
                    )
                else:
                    success_panel = Panel(
                        Text(f"🎉 Dangling index deleted successfully!\n\n"
                             f"UUID: {index_uuid}\n"
                             f"The index has been permanently removed from the cluster.",
                             style="green", justify="center"),
                        title="✅ Deletion Successful",
                        border_style="green",
                        padding=(1, 2)
                    )
                
                console.print(success_panel)
                print()
            else:
                error_panel = Panel(
                    Text(f"❌ Failed to {'simulate deletion of' if dry_run else 'delete'} dangling index.\n\n"
                         f"UUID: {index_uuid}\n"
                         f"Check cluster logs for detailed error information.",
                         style="red", justify="center"),
                    title=f"❌ {'Simulation' if dry_run else 'Deletion'} Failed",
                    border_style="red",
                    padding=(1, 2)
                )
                console.print(error_panel)
                print()

        except KeyboardInterrupt:
            console.print("\n[bold yellow]❌ Operation cancelled by user.[/bold yellow]")
        except Exception as e:
            error_panel = Panel(
                Text(f"❌ Error during dangling index {'simulation' if hasattr(self.args, 'dry_run') and self.args.dry_run else 'deletion'}: {str(e)}", 
                     style="bold red", justify="center"),
                subtitle="Check cluster connectivity and permissions",
                border_style="red",
                padding=(1, 2)
            )
            print()
            console.print(error_panel)
            print()
