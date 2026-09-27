"""Measure decoded audio, including browser WebM files without duration metadata."""

import asyncio
import math
import tempfile
from pathlib import Path

from fastapi import HTTPException


async def audio_seconds(content: bytes) -> int:
    with tempfile.TemporaryDirectory(prefix="pilot-audio-") as folder:
        path = Path(folder) / "input"
        path.write_bytes(content)
        try:
            process = await asyncio.create_subprocess_exec(
                "ffmpeg",
                "-nostdin",
                "-v",
                "error",
                "-threads",
                "1",
                "-protocol_whitelist",
                "file,pipe",
                "-format_whitelist",
                "wav,mp3,mov,aac,matroska,webm",
                "-i",
                str(path),
                "-map",
                "0:a:0",
                "-t",
                "181",
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-f",
                "s16le",
                "pipe:1",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
        except OSError:
            raise HTTPException(
                503, "Audio validation is unavailable. Please try again later."
            ) from None
        try:
            output, _ = await asyncio.wait_for(process.communicate(), timeout=30)
        except TimeoutError:
            if process.returncode is None:
                process.kill()
            await process.wait()
            raise HTTPException(
                422, "Audio validation timed out. Try a shorter recording."
            ) from None
        except BaseException:
            if process.returncode is None:
                process.kill()
            await process.wait()
            raise
        if process.returncode or not output:
            raise HTTPException(422, "This audio could not be read. Please use another recording.")
        seconds = math.ceil(len(output) / 32000)
        if seconds > 180:
            raise HTTPException(422, "Pilot recordings must be three minutes or shorter.")
        return seconds
