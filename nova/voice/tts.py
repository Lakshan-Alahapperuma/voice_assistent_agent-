import subprocess
import re
import threading
import shutil
from typing import List, Dict, Optional
from nova.config import NOVA_VOICE, NOVA_SPEECH_RATE

def clean_text_for_speech(text: str) -> str:
    """Strips Markdown syntax, URLs, and code blocks to make text natural when spoken."""
    if not text:
        return ""
    # Remove code blocks
    cleaned = re.sub(r'```[\s\S]*?```', 'code block omitted', text)
    # Remove inline code backticks
    cleaned = re.sub(r'`([^`]+)`', r'\1', cleaned)
    # Convert markdown links [text](url) to just text
    cleaned = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', cleaned)
    # Remove bold/italic markers
    cleaned = re.sub(r'[*_~]', '', cleaned)
    # Remove header markers (#, ##)
    cleaned = re.sub(r'^[#]+\s+', '', cleaned, flags=re.MULTILINE)
    # Remove bullet markers (-, *, >)
    cleaned = re.sub(r'^[ \t]*[-*+>]\s+', '', cleaned, flags=re.MULTILINE)
    # Clean multiple spaces and newlines
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

class MacTTS:
    """macOS native Text-to-Speech synthesizer using `say`."""

    def __init__(self, voice: str = NOVA_VOICE, rate: int = NOVA_SPEECH_RATE):
        self.voice = voice
        self.rate = rate
        self._current_process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()

    def speak(self, text: str, async_mode: bool = False):
        """Speaks the provided text using macOS say."""
        spoken_text = clean_text_for_speech(text)
        if not spoken_text:
            return

        def _run():
            with self._lock:
                self.stop()
                cmd = ["say", "-v", self.voice, "-r", str(self.rate), spoken_text]
                try:
                    self._current_process = subprocess.Popen(cmd)
                    self._current_process.wait()
                except Exception as e:
                    print(f"TTS error: {e}")
                finally:
                    self._current_process = None

        if async_mode:
            thread = threading.Thread(target=_run, daemon=True)
            thread.start()
        else:
            _run()

    def stop(self):
        """Stops any currently playing speech."""
        if self._current_process and self._current_process.poll() is None:
            try:
                self._current_process.terminate()
            except Exception:
                pass
            self._current_process = None

    @staticmethod
    def get_available_voices() -> List[Dict[str, str]]:
        """Returns list of installed macOS voices."""
        try:
            res = subprocess.run(["say", "-v", "?"], capture_output=True, text=True, check=False)
            voices = []
            for line in res.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    name = parts[0]
                    locale = parts[1]
                    voices.append({"name": name, "locale": locale})
            return voices
        except Exception:
            return []
