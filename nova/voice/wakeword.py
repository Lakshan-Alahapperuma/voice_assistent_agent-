import logging
import re
import subprocess
import threading
import time
from typing import Optional, Callable, List, Any
import numpy as np

logger = logging.getLogger("nova.voice.wakeword")

WAKE_WORDS = ["hey nova", "nova", "hi nova", "hello nova", "okay nova", "ok nova"]

def play_chime(sound_name: str = "Ping"):
    """Plays a native macOS alert chime asynchronously."""
    sound_path = f"/System/Library/Sounds/{sound_name}.aiff"
    try:
        subprocess.Popen(["afplay", sound_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

class ContinuousWakeWordListener:
    """
    Always-on hands-free Wake Word engine.
    Listens on the microphone, detects 'Hey Nova', and triggers autonomous actions.
    """

    def __init__(self, stt_engine: Optional[Any] = None, wake_words: Optional[List[str]] = None, energy_threshold: int = 400):
        if stt_engine is None:
            from nova.voice.stt import WhisperSTT
            self.stt = WhisperSTT()
        else:
            self.stt = stt_engine
        self.wake_words = [w.lower() for w in (wake_words or WAKE_WORDS)]
        self.energy_threshold = energy_threshold
        self.sample_rate = 16000
        self.chunk_size = 1600  # 100ms chunks at 16kHz
        self._running = False

    def extract_command(self, text: str) -> tuple[bool, str]:
        """
        Checks if text contains a wake word.
        Returns (is_wake_word_detected, remaining_command).
        """
        clean = text.strip()
        lower = clean.lower()

        for ww in sorted(self.wake_words, key=len, reverse=True):
            # Check if text starts with or contains the wake word
            pattern = r'\b' + re.escape(ww) + r'\b[,.?!]?'
            match = re.search(pattern, lower)
            if match:
                # Extract text after wake word
                end_pos = match.end()
                remainder = clean[end_pos:].strip()
                # Remove leading commas or colons
                remainder = re.sub(r'^[,\s:;.-]+', '', remainder).strip()
                return True, remainder

        return False, ""

    def listen_loop(self, on_command_callback: Callable[[str], None], status_callback: Optional[Callable[[str], None]] = None):
        """
        Continuous listening loop.
        Monitors microphone for speech, detects 'Hey Nova', and forwards commands.
        """
        import sounddevice as sd

        self._running = True
        silence_limit_chunks = 8  # ~800ms of silence ends speech
        max_chunks = 100  # max ~10s of speech per command

        if status_callback:
            status_callback("Listening for 'Hey Nova'...")

        try:
            with sd.InputStream(samplerate=self.sample_rate, channels=1, dtype='int16', blocksize=self.chunk_size) as stream:
                while self._running:
                    # Read 100ms
                    data, _ = stream.read(self.chunk_size)
                    audio_chunk = data[:, 0]
                    rms = np.sqrt(np.mean(audio_chunk.astype(np.float32)**2))

                    # Speech started?
                    if rms > self.energy_threshold:
                        if status_callback:
                            status_callback("Speech detected... listening...")

                        recorded_frames = [audio_chunk]
                        silent_chunks = 0

                        # Collect speech until trailing silence
                        while self._running and silent_chunks < silence_limit_chunks and len(recorded_frames) < max_chunks:
                            chunk_data, _ = stream.read(self.chunk_size)
                            chunk = chunk_data[:, 0]
                            chunk_rms = np.sqrt(np.mean(chunk.astype(np.float32)**2))
                            recorded_frames.append(chunk)

                            if chunk_rms < self.energy_threshold:
                                silent_chunks += 1
                            else:
                                silent_chunks = 0

                        # Combine audio
                        full_audio = np.concatenate(recorded_frames)

                        # Must be at least 0.8 seconds of audio
                        if len(full_audio) < self.sample_rate * 0.8:
                            continue

                        # Transcribe in-memory with Whisper
                        text = self.stt.transcribe_audio_array(full_audio)
                        if not text:
                            continue

                        is_wake, command = self.extract_command(text)
                        if is_wake:
                            play_chime("Ping")
                            logger.info(f"Wake word detected! Command: '{command}' (Raw: '{text}')")

                            if command:
                                on_command_callback(command)
                            else:
                                # User just said "Hey Nova" without a command yet
                                if status_callback:
                                    status_callback("Wake word heard! Listening for command...")
                                # Listen for follow-up command
                                follow_up = self.stt.listen_and_transcribe(duration=5)
                                if follow_up:
                                    on_command_callback(follow_up)

                            if status_callback:
                                status_callback("Listening for 'Hey Nova'...")

        except Exception as e:
            logger.error(f"Error in continuous wake word listener: {e}")
            raise e

    def stop(self):
        self._running = False

# Backward compatibility alias
WakeWordDetector = ContinuousWakeWordListener
