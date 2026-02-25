"""
Speech-to-Text Agent.
Transcribes audio files using the free Google Speech Recognition API
via the SpeechRecognition library (no API key required).
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


async def transcribe(audio_file_path: str) -> Dict[str, Any]:
    """
    Transcribe the given audio file using Google's free Speech Recognition.

    Parameters
    ----------
    audio_file_path : str
        Absolute or relative path to a WAV audio file.

    Returns
    -------
    dict   {"transcript": str, "confidence": float}
    """
    logger.info("STTAgent: transcribing %s", audio_file_path)

    path = Path(audio_file_path)
    if not path.exists():
        logger.error("STTAgent: audio file not found — %s", audio_file_path)
        raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

    def _transcribe_sync() -> Dict[str, Any]:
        """Run speech recognition in a thread so it doesn't block the event loop."""
        import speech_recognition as sr

        recognizer = sr.Recognizer()

        with sr.AudioFile(str(path)) as source:
            # Adjust for ambient noise if the file is long enough
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio_data = recognizer.record(source)

        try:
            # Use Google's free web Speech Recognition API (no key needed)
            # show_all=True returns the full response with confidence scores
            result = recognizer.recognize_google(
                audio_data,
                language="en-US",
                show_all=True,
            )

            if not result or not isinstance(result, dict):
                # Fallback: simple recognition without confidence
                text = recognizer.recognize_google(audio_data, language="en-US")
                return {"transcript": text, "confidence": 0.85}

            # Extract the best alternative and its confidence
            alternatives = result.get("alternative", [])
            if alternatives:
                best = alternatives[0]
                transcript: str = best.get("transcript", "")
                raw_confidence: float = float(best.get("confidence", 0.85))
                confidence: float = float(round(raw_confidence, 4))
                return {"transcript": transcript, "confidence": confidence}

            return {"transcript": "", "confidence": 0.0}

        except sr.UnknownValueError:
            logger.warning("STTAgent: could not understand the audio")
            return {"transcript": "", "confidence": 0.0}
        except sr.RequestError as exc:
            logger.error("STTAgent: Google SR API error: %s", exc)
            raise RuntimeError(f"Speech recognition service error: {exc}") from exc

    return await asyncio.to_thread(_transcribe_sync)
