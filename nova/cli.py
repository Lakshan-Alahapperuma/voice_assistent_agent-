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

def test_microphone_diagnostics():
    import sounddevice as sd
    import numpy as np
    import time
    from nova.voice.stt import WhisperSTT, enhance_and_normalize_audio

    console.print("[bold cyan]🎙️  Testing Microphone & Audio Levels...[/bold cyan]\n")
    devices = sd.query_devices()
    default_input = sd.default.device[0]
    dev_name = devices[default_input]['name'] if default_input is not None and default_input >= 0 else "Default Mic"
    console.print(f"• Active Input Device: [bold green]{dev_name}[/bold green]")
    console.print("• Recording 3 seconds of audio... [bold red]Speak now (e.g. 'Hey Nova testing 1 2 3')[/bold red]:\n")

    time.sleep(0.5)
    sample_rate = 16000
    with console.status("[bold red]Recording 3 seconds from microphone... Speak now![/bold red]"):
        audio_data = sd.rec(int(3.0 * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
        sd.wait()

    console.print("  [green]Done recording![/green]\n")

    audio_flat = audio_data[:, 0]
    raw_peak = int(np.max(np.abs(audio_flat)))
    raw_rms = int(np.sqrt(np.mean(audio_flat.astype(np.float32)**2)))

    # Enhanced audio
    audio_boosted = enhance_and_normalize_audio(audio_flat)
    boosted_peak = float(np.max(np.abs(audio_boosted)))

    # Whisper transcription
    stt = WhisperSTT()
    with console.status("[bold cyan]Transcribing with enhanced Whisper model...[/bold cyan]"):
        text = stt.transcribe_audio_array(audio_flat)

    percent = min(100, int((raw_peak / 3000.0) * 100))
    bar = "█" * (percent // 5) + "░" * (20 - (percent // 5))

    table = Table(title="Microphone Diagnostic Results", border_style="cyan")
    table.add_column("Metric", style="bold")
    table.add_column("Value", style="green")
    table.add_column("Evaluation")

    table.add_row("Microphone Device", dev_name, "[green]Online[/green]")
    table.add_row("Raw Peak Amplitude", f"{raw_peak} / 32768", f"[{bar}] {percent}%")
    table.add_row("Raw RMS Level", f"{raw_rms}", "Normal speech is 150–1200")
    table.add_row("Normalized Signal Peak", f"{boosted_peak:.2f} / 1.0", "[green]Studio Reference Level[/green]")
    table.add_row("Whisper Transcribed Text", f"\"{text}\"", "[bold green]Captured Successfully[/bold green]" if text else "[yellow]No speech detected[/yellow]")

    console.print(table)
    if text:
        console.print(f"\n[bold green]✅ Success![/bold green] Nova clearly heard: [italic cyan]\"{text}\"[/italic cyan]\n")
    else:
        console.print("\n[bold yellow]⚠️  Notice:[/bold yellow] No speech was detected. Make sure to speak close to the microphone and that Terminal has microphone access in System Settings > Privacy & Security > Microphone.\n")

def run_cli():
    parser = argparse.ArgumentParser(description="Nova - Personal AI Assistant for macOS")
    parser.add_argument("--model", type=str, default=MODEL_NAME, help="Ollama model to use")
    parser.add_argument("--voice", action="store_true", help="Enable spoken voice output via macOS say")
    parser.add_argument("--talk", action="store_true", help="Launch in push-to-talk voice conversation mode")
    parser.add_argument("--wake", action="store_true", help="Launch in always-on 'Hey Nova' wake word detection mode")
    parser.add_argument("--test-mic", action="store_true", help="Test microphone audio input levels and Whisper accuracy")
    parser.add_argument("--check-system", action="store_true", help="Run system diagnostics")
    parser.add_argument("--auto-confirm", action="store_true", help="Auto-confirm safe actions without prompt")
    args = parser.parse_args()

    if args.check_system:
        check_system_diagnostics()
        return

    if args.test_mic:
        test_microphone_diagnostics()
        return

    display_banner()

    enable_voice = args.voice or args.talk or args.wake
    agent = NovaAgent(
        model_name=args.model,
        enable_voice=enable_voice,
        auto_confirm=args.auto_confirm
    )

    # Initial check if Ollama is running
    if not agent.brain.is_connected():
        console.print("[bold red]⚠️  Notice:[/bold red] Ollama daemon is not detected at [cyan]http://127.0.0.1:11434[/cyan].")
        console.print("   Please start it in another Terminal with: [bold green]ollama serve[/bold green]\n")

    # Mode 1: Always-on Wake Word detection ("Hey Nova")
    if args.wake:
        console.print(Panel(
            "[bold green]🟢 Always-On Wake Word Mode Active![/bold green]\n\n"
            "• Say [bold cyan]'Hey Nova'[/bold cyan] followed by your command at any time.\n"
            "• Example: [italic]'Hey Nova, open Safari and check my battery.'[/italic]\n"
            "• Nova will chime ([dim]Ping[/dim]), run the task, and speak back to you.\n"
            "• Press [bold yellow]Ctrl+C[/bold yellow] at any time to stop.",
            title="Hands-Free Wake Word",
            border_style="green"
        ))

        agent.tts.speak("Nova is listening. Say Hey Nova whenever you need me.", async_mode=True)
        agent.tts.wait_until_done()
        import time
        time.sleep(0.3)

        from nova.voice.wakeword import ContinuousWakeWordListener
        listener = ContinuousWakeWordListener(stt_engine=agent.stt, tts_engine=agent.tts)

        def handle_wake_command(command: str):
            console.print(f"\n[bold green]You (voice)[/bold green] > [cyan]{command}[/cyan]")
            with console.status("[bold cyan]Nova is executing...[/bold cyan]"):
                reply = agent.run_turn(command)
            console.print(f"\n[bold cyan]Nova[/bold cyan]:")
            console.print(Markdown(reply))
            console.print()
            # Wait for spoken speech to finish before resuming mic
            agent.tts.wait_until_done()

        try:
            listener.listen_loop(
                on_command_callback=handle_wake_command,
                status_callback=lambda s: console.print(f"[dim]{s}[/dim]", end="\r")
            )
        except KeyboardInterrupt:
            console.print("\n[bold cyan]Nova:[/bold cyan] Wake word detection stopped. Goodbye!")
            agent.tts.speak("Goodbye!")
        return

    # Mode 2 & 3: Interactive CLI with text, /mic, and push-to-talk
    console.print(Panel(
        f"[bold green]Nova is active![/bold green]\n"
        f"• Model: [cyan]{args.model}[/cyan]\n"
        f"• Voice output (Speaker): [cyan]{'Enabled (say)' if enable_voice else 'Disabled (add --voice to enable)'}[/cyan]\n"
        f"• Voice input (Microphone): [cyan]{'Ready (Type /mic to talk, /wake for Hey Nova, or run with --wake)' if agent.stt.is_available() else 'Not available'}[/cyan]\n"
        f"• Type [bold yellow]'exit'[/bold yellow] or [bold yellow]'quit'[/bold yellow] to exit.\n"
        f"• Type [bold yellow]'/mic'[/bold yellow] to speak into your microphone.\n"
        f"• Type [bold yellow]'/wake'[/bold yellow] to switch to 'Hey Nova' wake word listening.\n"
        f"• Type [bold yellow]'/tools'[/bold yellow] to list available agent actions.",
        title="Session Info",
        border_style="cyan"
    ))

    if args.talk:
        agent.tts.speak("Hello Lakshana, I'm Nova. I'm ready to listen.", async_mode=True)

    while True:
        try:
            if args.talk:
                prompt_text = "[bold green]Press ENTER to speak to Nova[/bold green] (or type text) > "
            else:
                prompt_text = "[bold green]You[/bold green] > "

            user_input = console.input(prompt_text).strip()

            # In talk mode, pressing Enter without text activates microphone
            if args.talk and not user_input:
                user_input = "/mic"

            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit", "q"):
                console.print("\n[bold cyan]Nova:[/bold cyan] Goodbye! Have a productive day.")
                if agent.enable_voice:
                    agent.tts.speak("Goodbye! Have a productive day.")
                break

            if user_input.lower() in ("/mic", "/listen", "listen"):
                if not agent.stt.is_available():
                    console.print("[yellow]Whisper STT or sounddevice is not available. Please type your message.[/yellow]")
                    continue

                console.print("\n[bold red]🎙️  Listening... Speak your command now (5 seconds)![/bold red]")
                with console.status("[bold red]Recording audio from microphone...[/bold red]"):
                    transcription = agent.stt.listen_and_transcribe(duration=5)

                if not transcription:
                    console.print("[yellow]Didn't catch any speech. Please try speaking a little louder or type '/mic' again.[/yellow]\n")
                    continue

                console.print(f"[bold green]You (voice)[/bold green] > [italic cyan]{transcription}[/italic cyan]")
                user_input = transcription

            if user_input.lower() in ("/wake", "wake mode", "wake up", "hey nova"):
                console.print(Panel(
                    "[bold green]🟢 Switched to Always-On Wake Word Mode![/bold green]\n\n"
                    "• Say [bold cyan]'Hey Nova'[/bold cyan] followed by your command at any time.\n"
                    "• Example: [italic]'Hey Nova, open Safari and check my battery.'[/italic]\n"
                    "• Press [bold yellow]Ctrl+C[/bold yellow] to return to text prompt.",
                    title="Wake Word Active",
                    border_style="green"
                ))
                agent.enable_voice = True
                agent.tts.speak("Listening for Hey Nova.", async_mode=True)
                from nova.voice.wakeword import ContinuousWakeWordListener
                listener = ContinuousWakeWordListener(stt_engine=agent.stt, tts_engine=agent.tts)

                def handle_wake_cmd(cmd: str):
                    console.print(f"\n[bold green]You (voice)[/bold green] > [cyan]{cmd}[/cyan]")
                    with console.status("[bold cyan]Nova is executing...[/bold cyan]"):
                        reply = agent.run_turn(cmd)
                    console.print(f"\n[bold cyan]Nova[/bold cyan]:")
                    console.print(Markdown(reply))
                    console.print()
                    agent.tts.wait_until_done()

                try:
                    listener.listen_loop(on_command_callback=handle_wake_cmd)
                except KeyboardInterrupt:
                    console.print("\n[yellow]Returned to interactive prompt.[/yellow]\n")
                continue

            if user_input.lower() == "/tools":
                tools_table = Table(title="Nova Registered Tools")
                tools_table.add_column("Tool Name", style="bold cyan")
                tools_table.add_column("Requires Confirmation", style="yellow")
                tools_table.add_column("Description")
                for t in agent.registry.list_tools():
                    tools_table.add_row(t.name, "Yes" if t.requires_confirmation else "No", t.description)
                console.print(tools_table)
                continue

            if user_input.lower() in ("/voice", "python main.py --voice", "turn on voice", "enable voice", "voice on"):
                agent.enable_voice = True
                console.print("[bold green]🔊 Spoken voice output is now enabled![/bold green] Nova will speak all responses out loud.")
                agent.tts.speak("Voice output is now enabled. How can I help you?", async_mode=True)
                continue

            if user_input.lower() in ("turn off voice", "disable voice", "voice off", "mute"):
                agent.enable_voice = False
                console.print("[yellow]🔇 Voice output is now disabled.[/yellow]")
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

        except KeyboardInterrupt:
            console.print("\n[bold cyan]Nova:[/bold cyan] Goodbye!")
            break
        except Exception as e:
            console.print(f"\n[bold red]Error:[/bold red] {str(e)}")

if __name__ == "__main__":
    run_cli()
