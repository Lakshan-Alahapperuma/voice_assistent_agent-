import argparse
import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown

from nova.agent import NovaAgent
from nova.config import MODEL_NAME, NOVA_VOICE, OLLAMA_HOST
from nova.brain.llm import NovaBrain
from nova.voice.tts import MacTTS
from nova.voice.stt import WhisperSTT

console = Console()

def display_banner():
    banner = """[bold cyan]
███╗   ██╗ ██████╗ ██╗   ██╗ █████╗ 
████╗  ██║██╔═══██╗██║   ██║██╔══██╗
██╔██╗ ██║██║   ██║██║   ██║███████║
██║╚██╗██║██║   ██║╚██╗ ██╔╝██╔══██║
██║ ╚████║╚██████╔╝ ╚████╔╝ ██║  ██║
╚═╝  ╚═══╝ ╚═════╝   ╚═══╝  ╚═╝  ╚═╝
[/bold cyan]
[dim]Personal Autonomous AI Voice Assistant for macOS[/dim]
"""
    console.print(banner)

def check_system_diagnostics():
    console.print("[bold yellow]Running Nova System Diagnostics...[/bold yellow]\n")

    table = Table(title="System & Dependency Status", border_style="cyan")
    table.add_column("Component", style="bold")
    table.add_column("Status", style="green")
    table.add_column("Details")

    # 1. Ollama check
    brain = NovaBrain()
    if brain.is_connected():
        models = brain.list_models()
        table.add_row("Ollama Service", "[green]Online[/green]", f"Available Models: {', '.join(models) if models else 'None pulled yet'}")
    else:
        table.add_row("Ollama Service", "[red]Offline[/red]", f"Cannot connect to {OLLAMA_HOST}. Run 'ollama serve' in terminal.")

    # 2. macOS say (TTS)
    voices = MacTTS.get_available_voices()
    if voices:
        table.add_row("macOS TTS (say)", "[green]Available[/green]", f"Detected {len(voices)} installed voices. Active voice: {NOVA_VOICE}")
    else:
        table.add_row("macOS TTS (say)", "[yellow]Warning[/yellow]", "No system voices detected.")

    # 3. Whisper STT
    stt = WhisperSTT()
    if stt.is_available():
        table.add_row("Whisper STT", "[green]Installed[/green]", "Speech-to-text is ready.")
    else:
        table.add_row("Whisper STT", "[yellow]Not Installed[/yellow]", "Install with 'pip install -r requirements-voice.txt'")

    # 4. Built-in Tools
    agent = NovaAgent()
    tools = agent.registry.list_tools()
    table.add_row("Nova Tools", "[green]Loaded[/green]", f"{len(tools)} tools registered ({', '.join([t.name for t in tools[:4]])}...)")

    console.print(table)

def run_cli():
    parser = argparse.ArgumentParser(description="Nova - Personal AI Assistant for macOS")
    parser.add_argument("--model", type=str, default=MODEL_NAME, help="Ollama model to use")
    parser.add_argument("--voice", action="store_true", help="Enable spoken voice output via macOS say")
    parser.add_argument("--check-system", action="store_true", help="Run system diagnostics")
    parser.add_argument("--auto-confirm", action="store_true", help="Auto-confirm safe actions without prompt")
    args = parser.parse_args()

    if args.check_system:
        check_system_diagnostics()
        return

    display_banner()

    agent = NovaAgent(
        model_name=args.model,
        enable_voice=args.voice,
        auto_confirm=args.auto_confirm
    )

    console.print(Panel(
        f"[bold green]Nova is active![/bold green]\n"
        f"• Model: [cyan]{args.model}[/cyan]\n"
        f"• Voice output: [cyan]{'Enabled (say)' if args.voice else 'Disabled (add --voice to enable)'}[/cyan]\n"
        f"• Type [bold yellow]'exit'[/bold yellow] or [bold yellow]'quit'[/bold yellow] to exit.\n"
        f"• Type [bold yellow]'/tools'[/bold yellow] to list available agent actions.\n"
        f"• Type [bold yellow]'/voice'[/bold yellow] to toggle spoken response.",
        title="Session Info",
        border_style="cyan"
    ))

    # Initial check if Ollama is running
    if not agent.brain.is_connected():
        console.print("[bold red]⚠️  Notice:[/bold red] Ollama daemon is not detected at [cyan]http://127.0.0.1:11434[/cyan].")
        console.print("   Please start it in another Terminal with: [bold green]ollama serve[/bold green]\n")

    while True:
        try:
            user_input = console.input("[bold green]You[/bold green] > ").strip()
            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit", "q"):
                console.print("\n[bold cyan]Nova:[/bold cyan] Goodbye! Have a productive day.")
                if agent.enable_voice:
                    agent.tts.speak("Goodbye! Have a productive day.")
                break

            if user_input.lower() == "/tools":
                tools_table = Table(title="Nova Registered Tools")
                tools_table.add_column("Tool Name", style="bold cyan")
                tools_table.add_column("Requires Confirmation", style="yellow")
                tools_table.add_column("Description")
                for t in agent.registry.list_tools():
                    tools_table.add_row(t.name, "Yes" if t.requires_confirmation else "No", t.description)
                console.print(tools_table)
                continue

            if user_input.lower() == "/voice":
                agent.enable_voice = not agent.enable_voice
                state = "enabled" if agent.enable_voice else "disabled"
                console.print(f"[cyan]Voice output is now {state}.[/cyan]")
                continue

            if user_input.lower() == "/history":
                history = agent.memory.get_task_history(limit=5)
                if not history:
                    console.print("[dim]No tasks executed in history yet.[/dim]")
                else:
                    for h in history:
                        console.print(f"[bold]{h['tool_name']}[/bold] ({h['status']}): {h['result'][:100]}...")
                continue

            # Process input through Nova
            with console.status("[bold cyan]Nova is thinking & orchestrating actions...[/bold cyan]"):
                reply = agent.run_turn(user_input)

            console.print(f"\n[bold cyan]Nova[/bold cyan]:")
            console.print(Markdown(reply))
            console.print()

        except KeyboardInterrupt:
            console.print("\n[bold cyan]Nova:[/bold cyan] Goodbye!")
            break
        except Exception as e:
            console.print(f"\n[bold red]Error:[/bold red] {str(e)}")

if __name__ == "__main__":
    run_cli()
