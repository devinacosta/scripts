"""
ILM (Index Lifecycle Management) command handlers for escmd.

This module contains handlers for ILM policy management and operations.
"""

from .base_handler import BaseHandler


class ILMHandler(BaseHandler):
    """Handler for ILM management commands."""

    def handle_ilm(self):
        """Handle ILM operations based on subcommands."""
        # This method handles various ILM subcommands
        # The actual implementation delegates to esclient methods
        if hasattr(self.args, 'ilm_action'):
            action = self.args.ilm_action
            
            if action == 'status':
                self.es_client.check_ilm_status()
            elif action == 'policies':
                if self.args.format == 'json':
                    import json
                    policies = self.es_client.get_ilm_policies()
                    print(json.dumps(policies))
                else:
                    self.es_client.print_ilm_policies()
            elif action == 'remove-policy':
                self._handle_ilm_remove_policy()
            elif action == 'set-policy':
                self._handle_ilm_set_policy()
            else:
                self.console.print(f"[red]Unknown ILM action: {action}[/red]")
        else:
            # Default action - show ILM status
            self.es_client.check_ilm_status()

    def _handle_ilm_remove_policy(self):
        """Handle ILM policy removal."""
        # Implementation would be extracted from the original method
        # For now, delegate to esclient
        pattern = getattr(self.args, 'pattern', None)
        dry_run = getattr(self.args, 'dry_run', False)
        
        if pattern:
            self.es_client.remove_ilm_policy_by_pattern(pattern, dry_run)
        else:
            self.console.print("[red]Pattern is required for ILM policy removal[/red]")

    def _handle_ilm_set_policy(self):
        """Handle ILM policy assignment."""
        # Implementation would be extracted from the original method
        # For now, delegate to esclient
        pattern = getattr(self.args, 'pattern', None)
        policy = getattr(self.args, 'policy', None)
        dry_run = getattr(self.args, 'dry_run', False)
        
        if pattern and policy:
            self.es_client.set_ilm_policy_by_pattern(pattern, policy, dry_run)
        else:
            self.console.print("[red]Both pattern and policy are required for ILM policy assignment[/red]")
