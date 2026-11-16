import logging
from typing import Optional

logger = logging.getLogger("nova.voice.stt")

class WhisperSTT:
    """Speech-to-Text engine using faster-whisper or fallback."""

    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self._model = None
        self._initialized = False

    def is_available(self) -> bool:
        """Checks if faster-whisper and audio capture libraries are installed."""
        try:
            import faster_whisper
            return True
        except ImportError:
            return False

    def _load_model(self):
        if not self._initialized:
            try:
                from faster_whisper import WhisperModel
                # On Apple Silicon Mac, int8 or float16 on cpu or metal
                self._model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
                self._initialized = True
            except Exception as e:
                logger.error(f"Failed to load WhisperModel: {e}")
                raise e

    def transcribe_audio_file(self, audio_path: str) -> str:
        """Transcribes an audio file into text."""
        self._load_model()
        segments, _ = self._model.transcribe(audio_path, beam_size=5)
        text = " ".join([segment.text for segment in segments]).strip()
        return text

    def listen_and_transcribe(self, duration: int = 5) -> Optional[str]:
        """
        Listens from the default microphone and transcribes.
        Falls back gracefully if sounddevice/pyaudio is not installed.
        """
        try:
            import sounddevice as sd
            import numpy as np
            import tempfile
            import wave

            sample_rate = 16000
            print("\n🎙️  Listening... Speak now.")
            audio_data = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
            sd.wait()
            print("Processing voice...")

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tf:
                with wave.open(tf.name, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(sample_rate)
                    wf.writeframes(audio_data.tobytes())
                return self.transcribe_audio_file(tf.name)
        except ImportError:
            logger.warning("sounddevice or numpy not installed. Voice recording unavailable.")
            return None
        except Exception as e:
            logger.error(f"Error during audio listening: {e}")
            return None
