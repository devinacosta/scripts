"""
IndexHandler - Handles index-related operations

This module contains handlers for:
- flush: Synced flush operations with retry logic
- freeze: Index freezing for read-only optimization  
- indice: Detailed information about a specific index
- indices: List and manage indices with filtering options
- recovery: Index recovery status monitoring
"""

from .base_handler import BaseHandler
import json
import re
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from rich.table import Table as InnerTable


class IndexHandler(BaseHandler):
    """Handler for index-related operations."""

    def handle_flush(self):
        """Enhanced flush command with Rich formatting and operation details."""
        console = self.console

        try:
            # Get cluster information for context
            try:
                health_data = self.es_client.get_cluster_health()
                cluster_name = health_data.get('cluster_name', 'Unknown')
                total_nodes = health_data.get('number_of_nodes', 0)
            except:
                cluster_name = 'Unknown'
                total_nodes = 0

            # Create title panel
            title_panel = Panel(
                Text(f"🔄 Elasticsearch Flush Operation", style="bold cyan", justify="center"),
                subtitle=f"Synced flush across cluster: {cluster_name} | Nodes: {total_nodes}",
                border_style="cyan",
                padding=(1, 2)
            )

            # Show operation in progress
            print()
            console.print(title_panel)
            print()

            # Enhanced flush with retry logic
            max_retries = 10  # Maximum number of retry attempts
            retry_count = 0
            failed_shards = 1  # Initialize to enter the loop

            while failed_shards > 0 and retry_count <= max_retries:
                retry_count += 1

                # Show current attempt status
                if retry_count == 1:
                    status_message = "Performing synced flush operation..."
                else:
                    status_message = f"Retrying flush operation (attempt {retry_count}/{max_retries + 1})..."

                with console.status(status_message):
                    flushsync = self.es_client.flush_synced_elasticsearch(
                        host=self.es_client.host1,
                        port=self.es_client.port,
                        use_ssl=self.es_client.use_ssl,
                        authentication=self.es_client.elastic_authentication,
                        username=self.es_client.elastic_username,
                        password=self.es_client.elastic_password
                    )

                # Check results
                if isinstance(flushsync, dict):
                    failed_shards = flushsync.get('_shards', {}).get('failed', 0)
                    total_shards = flushsync.get('_shards', {}).get('total', 0)
                    successful_shards = flushsync.get('_shards', {}).get('successful', 0)

                    if failed_shards > 0 and retry_count <= max_retries:
                        # Show retry information
                        retry_panel = Panel(
                            Text(f"⚠️ Flush attempt {retry_count} completed with {failed_shards}/{total_shards} failed shards.\n"
                                f"💤 Waiting 10 seconds before retry {retry_count + 1}...",
                                style="yellow", justify="center"),
                            title=f"🔄 Retry {retry_count}/{max_retries + 1}",
                            border_style="yellow",
                            padding=(1, 2)
                        )
                        console.print(retry_panel)

                        # Wait 10 seconds before retry
                        import time
                        time.sleep(10)
                    elif failed_shards == 0:
                        # Success - show completion message if retries were needed
                        if retry_count > 1:
                            success_panel = Panel(
                                Text(f"🎉 Flush operation successful after {retry_count} attempts!\n"
                                    f"All {total_shards} shards successfully flushed.",
                                    style="green", justify="center"),
                                title="✅ Operation Complete",
                                border_style="green",
                                padding=(1, 2)
                            )
                            console.print(success_panel)
                        break
                else:
                    # Non-dict response, exit retry loop
                    break

            # Check if we hit max retries
            if failed_shards > 0 and retry_count > max_retries:
                max_retry_panel = Panel(
                    Text(f"⚠️ Maximum retry attempts ({max_retries + 1}) exceeded.\n"
                        f"Final result: {failed_shards}/{total_shards} shards still failed.",
                        style="red", justify="center"),
                    title="❌ Max Retries Exceeded",
                    border_style="red",
                    padding=(1, 2)
                )
                console.print(max_retry_panel)
                print()

            # Process and display results
            if isinstance(flushsync, dict):
                # Extract statistics from flush response
                total_shards = flushsync.get('_shards', {}).get('total', 0)
                successful_shards = flushsync.get('_shards', {}).get('successful', 0)
                failed_shards = flushsync.get('_shards', {}).get('failed', 0)
                skipped_shards = flushsync.get('_shards', {}).get('skipped', 0)

                # Calculate success rate
                success_rate = (successful_shards / total_shards * 100) if total_shards > 0 else 0

                # Create operation summary panel
                summary_table = InnerTable(show_header=False, box=None, padding=(0, 1))
                summary_table.add_column("Label", style="bold", no_wrap=True)
                summary_table.add_column("Icon", justify="left", width=3)
                summary_table.add_column("Value", no_wrap=True)

                summary_table.add_row("Total Shards:", "📊", f"{total_shards:,}")
                summary_table.add_row("Successful:", "✅", f"{successful_shards:,}")
                summary_table.add_row("Failed:", "❌", f"{failed_shards:,}")
                summary_table.add_row("Skipped:", "⏭️", f"{skipped_shards:,}")
                summary_table.add_row("Success Rate:", "📈", f"{success_rate:.1f}%")

                # Add retry information if retries were performed
                if retry_count > 1:
                    summary_table.add_row("Retry Attempts:", "🔄", f"{retry_count}")
                    if failed_shards == 0:
                        summary_table.add_row("Final Status:", "🎉", "Success after retries")
                    elif retry_count > max_retries:
                        summary_table.add_row("Final Status:", "⚠️", "Max retries exceeded")

                summary_panel = Panel(
                    summary_table,
                    title="📊 Flush Summary",
                    border_style="green" if failed_shards == 0 else "yellow",
                    padding=(1, 2)
                )

                # Create operation details panel
                details_table = InnerTable(show_header=False, box=None, padding=(0, 1))
                details_table.add_column("Label", style="bold", no_wrap=True)
                details_table.add_column("Icon", justify="left", width=3)
                details_table.add_column("Value", no_wrap=True)

                # Determine operation type and status based on retry attempts
                operation_type = "Synced Flush with Auto-Retry" if retry_count > 1 else "Synced Flush"
                if failed_shards == 0:
                    if retry_count > 1:
                        status_text = f"Success (after {retry_count} attempts)"
                        status_icon = "🎉"
                    else:
                        status_text = "Success"
                        status_icon = "✅"
                elif retry_count > max_retries:
                    status_text = "Failed (max retries exceeded)"
                    status_icon = "❌"
                else:
                    status_text = "Partial Success"
                    status_icon = "⚠️"

                details_table.add_row("Operation:", "🔄", operation_type)
                details_table.add_row("Cluster:", "🏢", cluster_name)
                details_table.add_row("Target:", "🎯", "All Indices")
                details_table.add_row("Status:", status_icon, status_text)

                details_panel = Panel(
                    details_table,
                    title="⚙️ Operation Details",
                    border_style="blue",
                    padding=(1, 2)
                )

                # Show detailed results if there are failures
                if failed_shards > 0 or 'failures' in flushsync:
                    if retry_count > max_retries:
                        failures_content = f"❌ Flush operation failed after {retry_count} attempts (including {retry_count - 1} retries).\n\n"
                        failures_content += f"⚠️ {failed_shards}/{total_shards} shards still failed after maximum retry attempts:\n\n"
                    else:
                        failures_content = "⚠️ Some shards failed to flush:\n\n"

                    failures = flushsync.get('failures', [])
                    for i, failure in enumerate(failures[:5]):  # Show first 5 failures
                        index = failure.get('index', 'Unknown')
                        shard = failure.get('shard', 'Unknown')
                        reason = failure.get('reason', {}).get('reason', 'Unknown error')
                        failures_content += f"• {index}[{shard}]: {reason}\n"

                    if len(failures) > 5:
                        failures_content += f"... and {len(failures) - 5} more failures"

                    # Add retry recommendation if max retries exceeded
                    if retry_count > max_retries:
                        failures_content += f"\n\n💡 Consider investigating cluster health or specific index issues."

                    failures_panel = Panel(
                        failures_content.rstrip(),
                        title="❌ Persistent Flush Failures" if retry_count > max_retries else "⚠️ Flush Failures",
                        border_style="red",
                        padding=(1, 2)
                    )
                else:
                    # Success message
                    if retry_count > 1:
                        success_text = Text(f"🎉 All shards flushed successfully after {retry_count} attempts!\n\nThe synced flush operation completed successfully with automatic retry recovery.", style="green")
                        title = "🎉 Success with Auto-Retry"
                    else:
                        success_text = Text("🎉 All shards flushed successfully!\n\nThe synced flush operation completed without errors.", style="green")
                        title = "✅ Success"

                    failures_panel = Panel(
                        success_text,
                        title=title,
                        border_style="green",
                        padding=(1, 2)
                    )

                # Create quick actions panel
                actions_table = InnerTable(show_header=False, box=None, padding=(0, 1))
                actions_table.add_column("Action", style="bold cyan", no_wrap=True)
                actions_table.add_column("Command", style="dim white")

                actions_table.add_row("Check health:", "./escmd.py health")
                actions_table.add_row("View shards:", "./escmd.py shards")
                actions_table.add_row("Monitor recovery:", "./escmd.py recovery")
                actions_table.add_row("View indices:", "./escmd.py indices")

                actions_panel = Panel(
                    actions_table,
                    title="🚀 Related Commands",
                    border_style="magenta",
                    padding=(1, 2)
                )

                # Display results
                print()
                console.print(Columns([summary_panel, details_panel], expand=True))
                print()
                console.print(failures_panel)
                print()
                console.print(actions_panel)
                print()

            else:
                # Simple response display
                simple_panel = Panel(
                    Text(f"🔄 Flush completed: {flushsync}", style="green", justify="center"),
                    title="✅ Flush Operation Complete",
                    border_style="green",
                    padding=(1, 2)
                )
                print()
                console.print(simple_panel)
                print()

        except Exception as e:
            error_panel = Panel(
                Text(f"❌ Flush operation failed: {str(e)}", style="bold red", justify="center"),
                subtitle="Check cluster connectivity and permissions",
                border_style="red",
                padding=(1, 2)
            )
            print()
            console.print(error_panel)
            print()

    def handle_freeze(self):
        """Enhanced freeze command with Rich formatting and validation details."""
        console = self.console

        try:
            # Get cluster information for context
            try:
                health_data = self.es_client.get_cluster_health()
                cluster_name = health_data.get('cluster_name', 'Unknown')
            except:
                cluster_name = 'Unknown'

            # Create title panel
            title_panel = Panel(
                Text(f"🧊 Elasticsearch Index Freeze Operation", style="bold cyan", justify="center"),
                subtitle=f"Target Index: {self.args.indice} | Cluster: {cluster_name}",
                border_style="cyan",
                padding=(1, 2)
            )

            print()
            console.print(title_panel)
            print()

            # Validate index exists
            with console.status(f"Validating index '{self.args.indice}'..."):
                cluster_active_indices = self.es_client.get_indices_stats(pattern=None, status=None)

            # Ensure cluster_active_indices is a list
            if isinstance(cluster_active_indices, str):
                try:
                    import json
                    cluster_active_indices = json.loads(cluster_active_indices)
                except json.JSONDecodeError:
                    cluster_active_indices = []

            if not cluster_active_indices:
                error_panel = Panel(
                    Text(f"❌ No active indices found in cluster", style="bold red", justify="center"),
                    subtitle="Unable to retrieve cluster indices",
                    border_style="red",
                    padding=(1, 2)
                )
                console.print(error_panel)
                return

            # Find matching index
            if not self.es_client.find_matching_index(cluster_active_indices, self.args.indice):
                # Show available indices for reference
                try:
                    available_indices = [idx.get('index', 'Unknown') for idx in cluster_active_indices[:10] if isinstance(idx, dict)]
                except (AttributeError, TypeError):
                    available_indices = ['Unable to retrieve index list']

                error_content = f"Index '{self.args.indice}' not found in the cluster.\n\n"
                error_content += "Available indices (showing first 10):\n"
                for idx in available_indices:
                    error_content += f"• {idx}\n"

                error_panel = Panel(
                    error_content.rstrip(),
                    title="❌ Index Not Found",
                    border_style="red",
                    padding=(1, 2)
                )
                console.print(error_panel)
                return

            # Get index details before freezing
            try:
                index_info = next((idx for idx in cluster_active_indices if isinstance(idx, dict) and idx.get('index') == self.args.indice), {})
                health = index_info.get('health', 'unknown')
                status = index_info.get('status', 'unknown')
                docs_count = index_info.get('docs.count', '0')
                size = index_info.get('store.size', '0')
            except:
                health = 'unknown'
                status = 'unknown'
                docs_count = '0'
                size = '0'
                size = '0'

            # Create validation summary panel
            validation_table = InnerTable(show_header=False, box=None, padding=(0, 1))
            validation_table.add_column("Label", style="bold", no_wrap=True)
            validation_table.add_column("Icon", justify="left", width=3)
            validation_table.add_column("Value", no_wrap=True)

            health_icon = "🟢" if health == 'green' else "🟡" if health == 'yellow' else "🔴"
            status_icon = "📂" if status == 'open' else "🔒"

            validation_table.add_row("Index Name:", "📋", self.args.indice)
            validation_table.add_row("Health:", health_icon, health.title())
            validation_table.add_row("Status:", status_icon, status.title())
            
            # Format documents count safely
            try:
                formatted_docs = f"{int(docs_count):,}" if docs_count and str(docs_count).isdigit() else str(docs_count)
            except (ValueError, TypeError):
                formatted_docs = str(docs_count) if docs_count else '0'
            
            validation_table.add_row("Documents:", "📊", formatted_docs)
            validation_table.add_row("Size:", "💾", size)

            validation_panel = Panel(
                validation_table,
                title="✅ Index Validation",
                border_style="green",
                padding=(1, 2)
            )

            # Create freeze operation details panel
            operation_table = InnerTable(show_header=False, box=None, padding=(0, 1))
            operation_table.add_column("Label", style="bold", no_wrap=True)
            operation_table.add_column("Icon", justify="left", width=3)
            operation_table.add_column("Value", no_wrap=True)

            operation_table.add_row("Operation:", "🧊", "Freeze Index")
            operation_table.add_row("Effect:", "🔒", "Read-Only Mode")
            operation_table.add_row("Storage:", "💾", "Optimized")
            operation_table.add_row("Searchable:", "🔍", "Yes")
            operation_table.add_row("Writable:", "✏️", "No")

            operation_panel = Panel(
                operation_table,
                title="⚙️ Freeze Operation",
                border_style="blue",
                padding=(1, 2)
            )

            # Display validation
            console.print(Columns([validation_panel, operation_panel], expand=True))
            print()

            # Perform freeze operation
            with console.status(f"Freezing index '{self.args.indice}'..."):
                freeze_result = self.es_client.freeze_index(self.args.indice)

            if freeze_result:
                # Success panel
                success_text = f"🎉 Index '{self.args.indice}' has been successfully frozen!\n\n"
                success_text += "The index is now:\n"
                success_text += "• ✅ Read-only (no new writes allowed)\n"
                success_text += "• 💾 Storage optimized for reduced memory usage\n"
                success_text += "• 🔍 Still searchable but with potential latency\n"
                success_text += "• 🧊 Frozen state persists until manually unfrozen"

                success_panel = Panel(
                    success_text,
                    title="✅ Freeze Operation Successful",
                    border_style="green",
                    padding=(1, 2)
                )

                # Create quick actions panel
                actions_table = InnerTable(show_header=False, box=None, padding=(0, 1))
                actions_table.add_column("Action", style="bold cyan", no_wrap=True)
                actions_table.add_column("Command", style="dim white")

                actions_table.add_row("Verify status:", f"./escmd.py indice {self.args.indice}")
                actions_table.add_row("List indices:", "./escmd.py indices")
                actions_table.add_row("Unfreeze index:", f"./escmd.py unfreeze {self.args.indice}")
                actions_table.add_row("Check settings:", "./escmd.py settings")

                actions_panel = Panel(
                    actions_table,
                    title="🚀 Next Steps",
                    border_style="magenta",
                    padding=(1, 2)
                )

                console.print(success_panel)
                print()
                console.print(actions_panel)
                print()

            else:
                # Failure panel
                error_panel = Panel(
                    Text(f"❌ Failed to freeze index '{self.args.indice}'", style="bold red", justify="center"),
                    subtitle="Check index permissions and cluster status",
                    border_style="red",
                    padding=(1, 2)
                )
                console.print(error_panel)
                print()

        except Exception as e:
            error_panel = Panel(
                Text(f"❌ Freeze operation error: {str(e)}", style="bold red", justify="center"),
                subtitle=f"Failed to freeze index: {self.args.indice}",
                border_style="red",
                padding=(1, 2)
            )
            print()
            console.print(error_panel)
            print()

    def handle_unfreeze(self):
        """Enhanced unfreeze command with regex support and confirmation prompts."""
        import re
        console = self.console

        try:
            # Get cluster information for context
            try:
                health_data = self.es_client.get_cluster_health()
                cluster_name = health_data.get('cluster_name', 'Unknown')
            except:
                cluster_name = 'Unknown'

            # Create title panel
            title_panel = Panel(
                Text(f"❄️  Elasticsearch Index Unfreeze Operation", style="bold cyan", justify="center"),
                subtitle=f"Pattern: {self.args.pattern} | Cluster: {cluster_name}",
                border_style="cyan",
                padding=(1, 2)
            )

            print()
            console.print(title_panel)
            print()

            # Get all indices to search through
            with console.status(f"Retrieving cluster indices..."):
                cluster_active_indices = self.es_client.get_indices_stats(pattern=None, status=None)

            # Ensure cluster_active_indices is a list
            if isinstance(cluster_active_indices, str):
                try:
                    import json
                    cluster_active_indices = json.loads(cluster_active_indices)
                except json.JSONDecodeError:
                    cluster_active_indices = []

            if not cluster_active_indices:
                error_panel = Panel(
                    Text(f"❌ No active indices found in cluster", style="bold red", justify="center"),
                    subtitle="Unable to retrieve cluster indices",
                    border_style="red",
                    padding=(1, 2)
                )
                console.print(error_panel)
                return

            # Find matching indices
            matching_indices = []
            
            if self.args.regex:
                # Use regex matching
                try:
                    pattern = re.compile(self.args.pattern)
                    for idx in cluster_active_indices:
                        if isinstance(idx, dict):
                            index_name = idx.get('index', '')
                            if pattern.search(index_name):
                                matching_indices.append(idx)
                except re.error as e:
                    error_panel = Panel(
                        Text(f"❌ Invalid regex pattern: {str(e)}", style="bold red", justify="center"),
                        subtitle="Please check your regex syntax",
                        border_style="red",
                        padding=(1, 2)
                    )
                    console.print(error_panel)
                    return
            else:
                # Exact match
                for idx in cluster_active_indices:
                    if isinstance(idx, dict) and idx.get('index') == self.args.pattern:
                        matching_indices.append(idx)

            if not matching_indices:
                # Show available indices for reference
                try:
                    available_indices = [idx.get('index', 'Unknown') for idx in cluster_active_indices[:10] if isinstance(idx, dict)]
                except (AttributeError, TypeError):
                    available_indices = ['Unable to retrieve index list']

                error_content = f"No indices found matching pattern '{self.args.pattern}'\n\n"
                error_content += "Available indices (showing first 10):\n"
                for idx in available_indices:
                    error_content += f"• {idx}\n"

                error_panel = Panel(
                    error_content.rstrip(),
                    title="❌ No Matching Indices",
                    border_style="red",
                    padding=(1, 2)
                )
                console.print(error_panel)
                return

            # Display matching indices
            indices_table = InnerTable(show_header=True, box=None, padding=(0, 1))
            indices_table.add_column("Index Name", style="bold cyan", no_wrap=True)
            indices_table.add_column("Health", justify="center", width=8)
            indices_table.add_column("Status", justify="center", width=8)
            indices_table.add_column("Documents", justify="right", width=12)
            indices_table.add_column("Size", justify="right", width=10)

            for idx in matching_indices:
                index_name = idx.get('index', 'Unknown')
                health = idx.get('health', 'unknown')
                status = idx.get('status', 'unknown')
                docs_count = idx.get('docs.count', '0')
                size = idx.get('store.size', '0')

                # Format documents count safely
                try:
                    formatted_docs = f"{int(docs_count):,}" if docs_count and str(docs_count).isdigit() else str(docs_count)
                except (ValueError, TypeError):
                    formatted_docs = str(docs_count) if docs_count else '0'

                health_icon = "🟢" if health == 'green' else "🟡" if health == 'yellow' else "🔴"
                status_icon = "📂" if status == 'open' else "🔒"

                indices_table.add_row(
                    index_name,
                    f"{health_icon} {health.title()}",
                    f"{status_icon} {status.title()}",
                    formatted_docs,
                    size
                )

            indices_panel = Panel(
                indices_table,
                title=f"🎯 Found {len(matching_indices)} Matching Indices",
                border_style="blue",
                padding=(1, 2)
            )

            console.print(indices_panel)
            print()

            # Confirmation prompt for multiple indices
            if len(matching_indices) > 1 and not self.args.yes:
                from rich.prompt import Confirm
                
                warning_text = f"⚠️  You are about to unfreeze {len(matching_indices)} indices.\n\n"
                warning_text += "This operation will:\n"
                warning_text += "• Make all selected indices writable again\n"
                warning_text += "• Remove storage optimizations\n"
                warning_text += "• Allow new documents to be indexed\n\n"
                warning_text += "Are you sure you want to continue?"

                warning_panel = Panel(
                    warning_text,
                    title="⚠️ Multiple Indices Confirmation",
                    border_style="yellow",
                    padding=(1, 2)
                )

                console.print(warning_panel)
                print()

                if not Confirm.ask("Proceed with unfreezing all matched indices?", default=False):
                    cancelled_panel = Panel(
                        Text("❌ Operation cancelled by user", style="bold yellow", justify="center"),
                        subtitle="No indices were unfrozen",
                        border_style="yellow",
                        padding=(1, 2)
                    )
                    console.print(cancelled_panel)
                    return

            # Perform unfreeze operations
            successful_indices = []
            failed_indices = []

            for idx in matching_indices:
                index_name = idx.get('index', 'Unknown')
                
                with console.status(f"Unfreezing index '{index_name}'..."):
                    result = self.es_client.unfreeze_index(index_name)
                
                if result:
                    successful_indices.append(index_name)
                else:
                    failed_indices.append(index_name)

            # Display results
            if successful_indices:
                success_text = f"🎉 Successfully unfrozen {len(successful_indices)} indices!\n\n"
                success_text += "Unfrozen indices:\n"
                for idx in successful_indices:
                    success_text += f"• ✅ {idx}\n"
                
                success_text += "\nThese indices are now:\n"
                success_text += "• ✏️  Writable (accepting new documents)\n"
                success_text += "• 🔄 Using normal memory management\n"
                success_text += "• 🔍 Fully searchable with normal performance\n"

                success_panel = Panel(
                    success_text.rstrip(),
                    title="✅ Unfreeze Operation Successful",
                    border_style="green",
                    padding=(1, 2)
                )
                console.print(success_panel)
                print()

            if failed_indices:
                failure_text = f"❌ Failed to unfreeze {len(failed_indices)} indices:\n\n"
                for idx in failed_indices:
                    failure_text += f"• ❌ {idx}\n"

                failure_panel = Panel(
                    failure_text.rstrip(),
                    title="⚠️ Some Operations Failed",
                    border_style="red",
                    padding=(1, 2)
                )
                console.print(failure_panel)
                print()

            # Create next steps panel
            actions_table = InnerTable(show_header=False, box=None, padding=(0, 1))
            actions_table.add_column("Action", style="bold cyan", no_wrap=True)
            actions_table.add_column("Command", style="dim white")

            actions_table.add_row("Verify status:", "./escmd.py indices")
            actions_table.add_row("Check specific index:", "./escmd.py indice <index-name>")
            if successful_indices:
                actions_table.add_row("Freeze again:", f"./escmd.py freeze <index-name>")

            actions_panel = Panel(
                actions_table,
                title="🚀 Next Steps",
                border_style="magenta",
                padding=(1, 2)
            )
            console.print(actions_panel)
            print()

        except Exception as e:
            error_panel = Panel(
                Text(f"❌ Unfreeze operation error: {str(e)}", style="bold red", justify="center"),
                subtitle=f"Failed to process pattern: {self.args.pattern}",
                border_style="red",
                padding=(1, 2)
            )
            print()
            console.print(error_panel)
            print()

    def handle_indice(self):
        """Display detailed information about a specific index."""
        indice = self.args.indice
        
        # Check if index name was provided
        if not indice:
            from rich.syntax import Syntax
            from rich.console import Console
            from rich.panel import Panel
            from rich.text import Text
            
            console = Console()
            
            # Create syntax-highlighted examples
            usage_code = """# Show details for a specific index
./escmd.py indice myindex-001

# Show details for a datastream index
./escmd.py indice .ds-logs-app-2025.08.28-000001

# To list ALL indices instead:
./escmd.py indices

# To search indices with patterns:
./escmd.py indices "logs-*" """
            
            syntax = Syntax(usage_code, "bash", theme="monokai", line_numbers=False, background_color="default")
            
            # Create the error message
            error_text = Text()
            error_text.append("❌ Index name is required.\n\n", style="bold red")
            error_text.append("Usage: ", style="bold white")
            error_text.append("./escmd.py indice <index_name>", style="bold cyan")
            
            # Print error message
            console.print("\n")
            console.print(Panel(
                error_text,
                title="Missing Index Name",
                border_style="red",
                padding=(1, 2)
            ))
            
            # Print syntax-highlighted examples
            console.print(Panel(
                syntax,
                title="🚀 Command Examples",
                border_style="green",
                padding=(1, 2)
            ))
            console.print("\n")
            return
            
        self.es_client.print_detailed_indice_info(indice)

    def handle_indices(self):
        """List and manage indices with filtering options."""
        if self.args.cold:
            self._handle_cold_indices()
            return

        if self.args.regex:
            self._handle_regex_indices()
            return

        if self.args.format == 'json':
            print(self.es_client.filter_indices(pattern=None, status=self.args.status))
        else:
            indices = self.es_client.filter_indices(pattern=None, status=self.args.status)
            # Check if pager argument exists and use it
            use_pager = getattr(self.args, 'pager', False)
            self.es_client.print_table_indices(indices, use_pager=use_pager)

    def handle_recovery(self):
        """Monitor index recovery status."""
        if self.args.format == "json":
            es_recovery = self.es_client.get_recovery_status()
            self.es_client.pretty_print_json(es_recovery)
        else:
            with self.console.status("Retrieving recovery data..."):
                es_recovery = self.es_client.get_recovery_status()
                self.es_client.print_enhanced_recovery_status(es_recovery)

    def _handle_cold_indices(self):
        """Handle cold indices listing."""
        _data = self.es_client.get_indices_stats(pattern=self.args.regex, status=self.args.status)
        print(_data)
        index_ilms = self.es_client.get_index_ilms(short=True)
        cold_indices = [index for index, info in index_ilms.items() if info.get('phase') == 'cold']
        print(f"Cold Indices: {cold_indices}")

    def _handle_regex_indices(self):
        """Handle indices matching regex patterns."""
        if self.args.format == 'json':
            print(self.es_client.get_indices_stats(pattern=self.args.regex, status=self.args.status))
            return

        indices = self.es_client.filter_indices(pattern=self.args.regex, status=self.args.status)
        if not indices:
            self.es_client.show_message_box("Indices", f"Pattern: {self.args.regex}\nThere were no matching indices found", message_style="white", panel_style="bold white")
            return

        use_pager = getattr(self.args, 'pager', False)
        self.es_client.print_table_indices(indices, use_pager=use_pager)

        if self.args.delete:
            self._handle_indices_deletion(indices)

    def _handle_indices_deletion(self, indices):
        """Handle deletion of multiple indices with confirmation."""
        while True:
            confirm_delete = input("Are you sure you want to delete these indices? (y/n): ")
            if confirm_delete.lower() in ('yes', 'y', 'no', 'n'):
                break
            print("Invalid input. Please enter 'y', 'n', 'yes', 'no'.")

        if confirm_delete.lower() in ('y', 'yes'):
            self.es_client.delete_indices(indices)
        else:
            print("Aborted process... script exiting.")
