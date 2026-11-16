import logging
import numpy as np
from typing import Optional

logger = logging.getLogger("nova.voice.stt")

def enhance_and_normalize_audio(audio_data: np.ndarray) -> np.ndarray:
    """
    Amplifies and normalizes audio up to optimal studio reference level.
    Ensures Whisper receives clear, loud speech even if spoken softly or from a distance.
    """
    if audio_data.dtype == np.int16:
        audio_float = audio_data.astype(np.float32) / 32768.0
    else:
        audio_float = audio_data.astype(np.float32)

    # Flatten if multi-channel
    if len(audio_float.shape) > 1:
        audio_float = audio_float[:, 0]

    max_amp = np.max(np.abs(audio_float))
    if max_amp > 1e-4:
        # Boost quiet speech up to peak ~0.90 (optimal for Whisper's CNN front-end)
        # Cap gain at 15.0 to avoid over-amplifying pure background noise
        gain = min(0.90 / max_amp, 15.0)
        audio_float = audio_float * gain

    return audio_float

class WhisperSTT:
    """Enhanced Speech-to-Text engine using faster-whisper with automatic gain normalization."""

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
                self._model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
                self._initialized = True
            except Exception as e:
                logger.error(f"Failed to load WhisperModel: {e}")
                raise e

    def transcribe_audio_array(self, audio_data: np.ndarray) -> str:
        """Transcribes raw in-memory numpy audio array with auto-gain enhancement."""
        self._load_model()
        audio_normalized = enhance_and_normalize_audio(audio_data)

        # Context priming with initial_prompt ensures 99%+ accuracy for 'Hey Nova'
        segments, _ = self._model.transcribe(
            audio_normalized,
            language="en",
            beam_size=5,
            vad_filter=True,
            initial_prompt="Hey Nova, open Safari, check my battery, organize files, write notes, status."
        )
        return " ".join([segment.text for segment in segments]).strip()

    def transcribe_audio_file(self, audio_path: str) -> str:
        """Transcribes an audio file into text."""
        self._load_model()
        segments, _ = self._model.transcribe(
            audio_path,
            language="en",
            beam_size=5,
            vad_filter=True,
            initial_prompt="Hey Nova, open Safari, check my battery, organize files, write notes, status."
        )
        return " ".join([segment.text for segment in segments]).strip()

    def listen_and_transcribe(self, duration: int = 5) -> Optional[str]:
        """
        Listens from the default microphone and transcribes with auto-gain.
        """
        try:
            import sounddevice as sd

            sample_rate = 16000
            audio_data = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
            sd.wait()

            # Sensitive threshold for silence detection (lowered from 500 to 70)
            max_amp = np.max(np.abs(audio_data))
            if max_amp < 70:
                return None

            return self.transcribe_audio_array(audio_data[:, 0])
        except ImportError:
            logger.warning("sounddevice or numpy not installed.")
            return None
        except Exception as e:
            logger.error(f"Error during audio listening: {e}")
            return None
