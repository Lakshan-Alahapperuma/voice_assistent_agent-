import json
from typing import Dict, Any, Callable, Optional
from rich.prompt import Confirm
from rich.console import Console

console = Console()

class SafetyGuardrail:
    """Manages human-in-the-loop approvals for sensitive tools."""

    def __init__(self, auto_confirm: bool = False, confirm_callback: Optional[Callable[[str, Dict[str, Any]], bool]] = None):
        self.auto_confirm = auto_confirm
        self.confirm_callback = confirm_callback

    def request_approval(self, tool_name: str, arguments: Dict[str, Any]) -> bool:
        """
        Requests confirmation from the user.
        If a custom callback (e.g. voice or UI confirmation) is provided, it calls it.
        Otherwise, falls back to rich console confirmation.
        """
        if self.auto_confirm:
            return True

        if self.confirm_callback:
            return self.confirm_callback(tool_name, arguments)

        # Default CLI prompt
        console.print(f"\n[bold yellow]⚠️  Nova requires approval for sensitive action:[/bold yellow]")
        console.print(f"  [cyan]Tool:[/cyan] [bold]{tool_name}[/bold]")
        console.print(f"  [cyan]Parameters:[/cyan] {json.dumps(arguments, indent=2)}")

        try:
            return Confirm.ask("Do you want to proceed with this action?", default=False)
        except Exception:
            return False
