import os
import sys
import time
import logging
import threading
import subprocess
from pathlib import Path
from typing import Optional
import rumps
from PyObjCTools import AppHelper

from nova.agent import NovaAgent
from nova.voice.wakeword import ContinuousWakeWordListener, play_chime
from nova.ui.service import is_service_installed, install_launch_agent, uninstall_launch_agent

# Configure persistent file logging in ~/.nova/menubar.log
log_dir = Path.home() / ".nova"
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "menubar.log"

logging.basicConfig(
    filename=str(log_file),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("nova.menubar")

class NovaMenuBarApp(rumps.App):
    """Native macOS Status Bar Application for Nova."""

    def __init__(self, model_name: Optional[str] = None):
        super(NovaMenuBarApp, self).__init__("🎙️ Nova", quit_button=None)
        logger.info("Initializing NovaMenuBarApp...")

        self.agent = NovaAgent(model_name=model_name or "qwen2.5:3b", enable_voice=True, auto_confirm=True)
        self.listener = ContinuousWakeWordListener(stt_engine=self.agent.stt, tts_engine=self.agent.tts)

        self.is_paused = False
        self.is_app_running = True
        self._listener_thread: Optional[threading.Thread] = None

        # Build menu items
        self.status_item = rumps.MenuItem("● Status: Listening for 'Hey Nova'", callback=None)
        self.pause_item = rumps.MenuItem("⏸️ Pause Listening", callback=self.toggle_pause)
        self.command_item = rumps.MenuItem("💬 Send Command...", callback=self.open_command_dialog)
        self.test_mic_item = rumps.MenuItem("🎙️ Test Microphone", callback=self.trigger_mic_test)

        # Service toggle
        service_state = "✓ Starts on Login" if is_service_installed() else "Start on System Login"
        self.service_item = rumps.MenuItem(service_state, callback=self.toggle_service)

        self.quit_item = rumps.MenuItem("❌ Quit Nova", callback=self.quit_app)

        self.menu = [
            self.status_item,
            rumps.separator,
            self.pause_item,
            self.command_item,
            self.test_mic_item,
            rumps.separator,
            self.service_item,
            rumps.separator,
            self.quit_item
        ]

        # Auto-start Ollama in background if offline
        self.agent.brain.ensure_service_running()

        # Startup chime & notification
        play_chime("Ping")
        rumps.notification(
            title="Nova Assistant",
            subtitle="Online & Listening",
            message="Say 'Hey Nova' anytime to give a command!"
        )

        # Start wake word listener in background
        self.start_background_listener()

    def set_title_safe(self, new_title: str):
        """Thread-safe update of Menu Bar title on macOS main thread."""
        AppHelper.callAfter(lambda: setattr(self, 'title', new_title))

    def start_background_listener(self):
        def _worker():
            logger.info("Background wake word listener thread started.")

            def _handle_command(cmd: str):
                lower_cmd = cmd.lower().strip()
                logger.info(f"Command received: {cmd}")

                # Voice command to sleep
                if any(phrase in lower_cmd for phrase in ("go to sleep", "stop listening", "pause listening", "sleep mode")):
                    AppHelper.callAfter(self.pause_listening)
                    self.agent.tts.speak("Going to sleep. You can wake me from the menu bar.", async_mode=False)
                    rumps.notification("Nova Assistant", "Paused", "Nova is now asleep. Resume from the menu bar.")
                    return

                # Normal command execution
                self.set_title_safe("⚡ Nova")
                try:
                    reply = self.agent.run_turn(cmd)
                    short_reply = reply.replace("\n", " ")[:120]
                    rumps.notification(
                        title="Nova Assistant",
                        subtitle=f"Command: {cmd[:30]}",
                        message=short_reply
                    )
                except Exception as e:
                    logger.error(f"Error during command turn: {e}", exc_info=True)
                    rumps.notification("Nova Assistant", "Error", str(e))
                finally:
                    if not self.is_paused:
                        self.set_title_safe("🎙️ Nova")

            while self.is_app_running:
                if self.is_paused:
                    time.sleep(0.5)
                    continue

                try:
                    self.listener.listen_loop(
                        on_command_callback=_handle_command
                    )
                except Exception as e:
                    logger.error(f"Listener loop exception: {e}", exc_info=True)
                    time.sleep(1.0)

        self._listener_thread = threading.Thread(target=_worker, daemon=True)
        self._listener_thread.start()

    def toggle_pause(self, _):
        if self.is_paused:
            self.resume_listening()
        else:
            self.pause_listening()

    def pause_listening(self):
        self.is_paused = True
        self.set_title_safe("⏸️ Nova")
        self.status_item.title = "○ Status: Paused"
        self.pause_item.title = "▶️ Resume Listening"
        self.listener.stop()
        logger.info("Nova paused.")

    def resume_listening(self):
        self.is_paused = False
        self.set_title_safe("🎙️ Nova")
        self.status_item.title = "● Status: Listening for 'Hey Nova'"
        self.pause_item.title = "⏸️ Pause Listening"
        self.listener._running = True
        logger.info("Nova resumed.")

    def open_command_dialog(self, _):
        window = rumps.Window(
            message="Enter a command for Nova (e.g. 'Open Safari and check battery'):",
            title="Nova Assistant",
            default_text="",
            ok="Execute",
            cancel="Cancel",
            dimensions=(320, 40)
        )
        response = window.run()
        if response.clicked and response.text.strip():
            cmd = response.text.strip()
            self.set_title_safe("⚡ Nova")

            def _run():
                try:
                    reply = self.agent.run_turn(cmd)
                    rumps.notification("Nova Assistant", f"Result: {cmd[:25]}", reply[:120])
                except Exception as e:
                    logger.error(f"Error executing dialog command: {e}", exc_info=True)
                    rumps.notification("Nova Assistant", "Error", str(e))
                finally:
                    self.set_title_safe("🎙️ Nova" if not self.is_paused else "⏸️ Nova")

            threading.Thread(target=_run, daemon=True).start()

    def trigger_mic_test(self, _):
        self.set_title_safe("🎙️ Testing...")
        rumps.notification("Nova Assistant", "Microphone Test", "Recording 3 seconds... speak now!")

        def _test():
            try:
                text = self.agent.stt.listen_and_transcribe(duration=3)
                if text:
                    rumps.notification("Nova Assistant", "Heard Successfully", f"\"{text}\"")
                    self.agent.tts.speak(f"I heard: {text}", async_mode=True)
                else:
                    rumps.notification("Nova Assistant", "Microphone Test", "No speech detected.")
            except Exception as e:
                logger.error(f"Error in mic test: {e}", exc_info=True)
            finally:
                self.set_title_safe("🎙️ Nova" if not self.is_paused else "⏸️ Nova")

        threading.Thread(target=_test, daemon=True).start()

    def toggle_service(self, sender):
        if is_service_installed():
            res = uninstall_launch_agent()
            sender.title = "Start on System Login"
            rumps.notification("Nova Assistant", "Auto-Start Disabled", res["message"])
        else:
            res = install_launch_agent()
            sender.title = "✓ Starts on Login"
            rumps.notification("Nova Assistant", "Auto-Start Enabled", res["message"])

    def quit_app(self, _):
        logger.info("Quitting Nova application...")
        self.is_app_running = False
        self.listener.stop()
        rumps.quit_application()

def launch_menubar_app(model_name: Optional[str] = None):
    """Starts the Nova Menu Bar application."""
    app = NovaMenuBarApp(model_name=model_name)
    app.run()

if __name__ == "__main__":
    launch_menubar_app()
