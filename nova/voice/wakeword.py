import logging
from typing import Optional, Callable, Any

logger = logging.getLogger("nova.voice.wakeword")

class WakeWordDetector:
    """Detects 'Hey Nova' wake word or manages push-to-talk activation."""

    def __init__(self, model_name: str = "hey_nova"):
        self.model_name = model_name
        self._model = None

    def is_openwakeword_available(self) -> bool:
        """Checks if openWakeWord is installed."""
        try:
            import openwakeword
            return True
        except ImportError:
            return False

    def wait_for_push_to_talk(self) -> bool:
        """Simple, ultra-reliable push-to-talk fallback."""
        try:
            input("\n[Press ENTER to talk to Nova, or type Ctrl+C to quit]...")
            return True
        except (KeyboardInterrupt, EOFError):
            return False

    def listen_for_wakeword(self, callback: Callable[[], None], stop_event: Optional[Any] = None):
        """
        Listens continuously on microphone for wake word.
        When detected, calls the callback function.
        """
        if not self.is_openwakeword_available():
            logger.info("openWakeWord is not installed. Using push-to-talk mode instead.")
            while True:
                if stop_event and stop_event.is_set():
                    break
                if self.wait_for_push_to_talk():
                    callback()
                else:
                    break
            return

        # If openwakeword is available
        try:
            import openwakeword
            from openwakeword.model import Model
            import sounddevice as sd
            import numpy as np

            # Load model (can use default openwakeword models or custom hey_nova)
            oww_model = Model()
            chunk_size = 1280  # 80ms at 16kHz

            def audio_callback(indata, frames, time_info, status):
                audio = (indata[:, 0] * 32767).astype(np.int16)
                prediction = oww_model.predict(audio)
                for mdl, score in prediction.items():
                    if score > 0.5:
                        logger.info(f"Wake word detected: {mdl} ({score:.2f})")
                        callback()

            with sd.InputStream(channels=1, samplerate=16000, blocksize=chunk_size, callback=audio_callback):
                while not (stop_event and stop_event.is_set()):
                    sd.sleep(100)
        except Exception as e:
            logger.error(f"Error in wake word listener: {e}")
            # Fall back to push-to-talk
            self.wait_for_push_to_talk()
            callback()
