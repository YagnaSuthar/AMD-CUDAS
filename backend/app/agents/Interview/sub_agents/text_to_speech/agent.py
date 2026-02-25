"""
Text-to-Speech Agent.
Synthesises text into audio using gTTS (Google Text-to-Speech) — free, no API key.
"""

import asyncio
import logging
import uuid
from pathlib import Path
from typing import Dict

from app.core.config import settings

logger = logging.getLogger(__name__)


async def synthesize(text: str, output_dir: str | None = None) -> Dict[str, str]:
    """
    Convert text to speech using gTTS and save the resulting MP3 file.

    Parameters
    ----------
    text : str
        The text to synthesise into speech.
    output_dir : str | None
        Directory to save the audio. Defaults to ``settings.AUDIO_OUTPUT_DIR``.

    Returns
    -------
    dict   {"audio_path": str}
    """
    logger.info("TTSAgent: synthesising %d characters of text", len(text))

    out_dir = Path(output_dir) if output_dir else settings.AUDIO_OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    hex_id = uuid.uuid4().hex
    filename: str = f"tts_{hex_id[:12]}.mp3"
    output_path = out_dir / filename

    def _synth_gtts() -> str:
        """Run gTTS in a thread so it doesn't block the event loop."""
        from gtts import gTTS

        tts = gTTS(text=text, lang="en", slow=False)
        tts.save(str(output_path))
        return str(output_path)

    try:
        path = await asyncio.to_thread(_synth_gtts)
        logger.info("TTSAgent: audio saved to %s", path)
        return {"audio_path": path}
    except Exception as exc:
        logger.error("TTSAgent: gTTS failed: %s", exc)
        raise RuntimeError(f"Text-to-speech synthesis failed: {exc}") from exc
