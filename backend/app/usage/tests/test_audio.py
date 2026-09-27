import io
import shutil
import wave

import pytest
from fastapi import HTTPException

from app.usage.audio import audio_seconds

pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg runtime required")


def wav(seconds):
    output = io.BytesIO()
    with wave.open(output, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16000)
        audio.writeframes(b"\0\0" * 16000 * seconds)
    return output.getvalue()


async def test_decoded_duration_boundary():
    assert await audio_seconds(wav(180)) == 180
    with pytest.raises(HTTPException) as denied:
        await audio_seconds(wav(181))
    assert denied.value.status_code == 422


async def test_invalid_and_playlist_inputs_are_rejected():
    for content in (b"not audio", b"#EXTM3U\nhttp://127.0.0.1/private.wav\n"):
        with pytest.raises(HTTPException) as denied:
            await audio_seconds(content)
        assert denied.value.status_code == 422
