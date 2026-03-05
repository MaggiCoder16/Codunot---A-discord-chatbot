import io
import edge_tts


async def generate_tts_mp3(text: str, voice: str) -> bytes:
    """Generate MP3 audio bytes from *text* using Microsoft Edge TTS.

    Parameters
    ----------
    text:
        The text to synthesize.
    voice:
        An Edge TTS voice code, e.g. ``"en-US-MichelleNeural"``.

    Returns
    -------
    bytes
        Raw MP3 audio data.
    """
    communicate = edge_tts.Communicate(text, voice)
    buffer = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buffer.write(chunk["data"])
    buffer.seek(0)
    return buffer.read()
