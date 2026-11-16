import logging
import re
import subprocess
import threading
import time
from typing import Optional, Callable, List, Any
import numpy as np

logger = logging.getLogger("nova.voice.wakeword")

WAKE_WORDS = [
    "hey nova", "nova", "hi nova", "hello nova", "okay nova", "ok nova",
    "hey noba", "noba", "hey no va", "no va", "hey neva", "neva",
    "hey novo", "novo", "hey knowa", "knowa", "hey noah", "noah",
    "hey rover", "anova", "a nova"
]

def play_chime(sound_name: str = "Ping"):
    """Plays a native macOS alert chime asynchronously."""
    sound_path = f"/System/Library/Sounds/{sound_name}.aiff"
    try:
        subprocess.Popen(["afplay", sound_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

class ContinuousWakeWordListener:
    """
    Always-on hands-free Wake Word engine with stream pause/resume and auto-gain audio processing.
    """

    def __init__(
        self,
        stt_engine: Optional[Any] = None,
        tts_engine: Optional[Any] = None,
        wake_words: Optional[List[str]] = None,
        energy_threshold: int = 150
    ):
        if stt_engine is None:
            from nova.voice.stt import WhisperSTT
            self.stt = WhisperSTT()
        else:
            self.stt = stt_engine

        if tts_engine is None:
            from nova.voice.tts import MacTTS
            self.tts = MacTTS()
        else:
            self.tts = tts_engine

        self.wake_words = [w.lower() for w in (wake_words or WAKE_WORDS)]
        self.energy_threshold = energy_threshold
        self.sample_rate = 16000
        self.chunk_size = 1600  # 100ms chunks at 16kHz
        self._running = False

    def extract_command(self, text: str) -> tuple[bool, str]:
        """
        Checks if text contains a wake word or phonetic variation.
        Returns (is_wake_word_detected, remaining_command).
        """
        clean = text.strip()
        lower = clean.lower()

        for ww in sorted(self.wake_words, key=len, reverse=True):
            pattern = r'\b' + re.escape(ww) + r'\b[,.?!]?'
            match = re.search(pattern, lower)
            if match:
                end_pos = match.end()
                remainder = clean[end_pos:].strip()
                remainder = re.sub(r'^[,\s:;.-]+', '', remainder).strip()
                return True, remainder

        return False, ""

    def listen_loop(
        self,
        on_command_callback: Callable[[str], None],
        status_callback: Optional[Callable[[str], None]] = None
    ):
        """
        Continuous listening loop with enhanced sensitivity.
        """
        import sounddevice as sd

        # Wait for any prior TTS to finish before opening microphone
        if self.tts:
            self.tts.wait_until_done()
        time.sleep(0.3)

        self._running = True
        silence_limit_chunks = 4  # 400ms of trailing silence ends speech
        max_chunks = 45           # max 4.5s of speech per command (fast response)

        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype='int16',
                blocksize=self.chunk_size
            ) as stream:

                # Calibrate ambient noise floor for 300ms in quiet
                ambient_vals = []
                for _ in range(3):
                    d, _ = stream.read(self.chunk_size)
                    ambient_vals.append(np.sqrt(np.mean(d[:, 0].astype(np.float32)**2)))
                noise_floor = np.mean(ambient_vals)

                # Sensitive speech threshold: between 100 and 260 RMS (easily catches normal speech)
                self.energy_threshold = max(100, min(260, int(noise_floor * 1.3)))
                logger.info(f"Calibrated noise floor: {noise_floor:.1f}, speech threshold: {self.energy_threshold}")

                if status_callback:
                    status_callback(f"Listening for 'Hey Nova'... (Mic sensitivity: High)")

                while self._running:
                    # Read 100ms
                    data, _ = stream.read(self.chunk_size)
                    audio_chunk = data[:, 0]
                    rms = np.sqrt(np.mean(audio_chunk.astype(np.float32)**2))

                    # Speech started
                    if rms > self.energy_threshold:
                        if status_callback:
                            status_callback("🎙️ Hearing speech... listening...")

                        recorded_frames = [audio_chunk]
                        silent_chunks = 0

                        # Collect speech until trailing silence or max limit
                        while self._running and silent_chunks < silence_limit_chunks and len(recorded_frames) < max_chunks:
                            chunk_data, _ = stream.read(self.chunk_size)
                            chunk = chunk_data[:, 0]
                            chunk_rms = np.sqrt(np.mean(chunk.astype(np.float32)**2))
                            recorded_frames.append(chunk)

                            if chunk_rms < self.energy_threshold:
                                silent_chunks += 1
                            else:
                                silent_chunks = 0

                        full_audio = np.concatenate(recorded_frames)

                        # Audio must be at least ~0.4 seconds
                        if len(full_audio) < self.sample_rate * 0.4:
                            if status_callback:
                                status_callback("Listening for 'Hey Nova'...")
                            continue

                        # Transcribe in-memory with auto-gain boosted Whisper
                        text = self.stt.transcribe_audio_array(full_audio)
                        if not text:
                            if status_callback:
                                status_callback("Listening for 'Hey Nova'...")
                            continue

                        is_wake, command = self.extract_command(text)
                        if is_wake:
                            # 1. Stop audio stream immediately to prevent feedback & buffer overflow
                            stream.stop()

                            # 2. Play alert chime
                            play_chime("Ping")
                            logger.info(f"Wake word detected! Command: '{command}'")

                            # 3. Handle command or prompt for one
                            if command:
                                on_command_callback(command)
                            else:
                                if status_callback:
                                    status_callback("Wake word heard! Listening for command...")
                                # Speak brief prompt and listen
                                self.tts.speak("Yes? How can I help?", async_mode=False)
                                follow_up = self.stt.listen_and_transcribe(duration=5)
                                if follow_up:
                                    on_command_callback(follow_up)

                            # 4. Wait for any speech output to finish completely
                            if self.tts:
                                self.tts.wait_until_done()

                            # 5. Brief cool-down for room echo to settle
                            time.sleep(0.4)

                            # 6. Resume stream fresh
                            if self._running:
                                stream.start()
                                if status_callback:
                                    status_callback("Listening for 'Hey Nova'...")

                        else:
                            # Print what Whisper heard to help user see microphone activity
                            if status_callback:
                                status_callback(f"Heard: '{text[:25]}' (Say 'Hey Nova' to activate)")

        except Exception as e:
            logger.error(f"Error in continuous wake word listener: {e}")
            raise e

    def stop(self):
        self._running = False

# Backward compatibility alias
WakeWordDetector = ContinuousWakeWordListener
