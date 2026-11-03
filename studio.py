import asyncio
import base64
import io
import tempfile
import wave
from pathlib import Path
from typing import Annotated

def ffmpeg_binary() -> str:
    if configured := os.getenv("FFMPEG_BINARY") or dotenv_values(ROOT / ".env").get("FFMPEG_BINARY"):
        return configured
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()

from dotenv import dotenv_values
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response
from sarvamai import AsyncSarvamAI
from starlette.middleware.trustedhost import TrustedHostMiddleware
import os

ROOT = Path(__file__).resolve().parent
app = FastAPI(docs_url=None, redoc_url=None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "testserver"])
slots = asyncio.Semaphore(2)


@app.middleware("http")
async def private_requests(request: Request, call_next):
    if request.method == "POST" and request.headers.get("x-keepsay") != "1":
        return Response(status_code=403)
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.get("/")
async def home():
    return FileResponse(ROOT / "keepsay.html")


async def body(request: Request, limit: int) -> bytes:
    data = bytearray()
    async for chunk in request.stream():
        if len(data) + len(chunk) > limit:
            raise HTTPException(413, "File exceeds the size limit.")
        data.extend(chunk)
    return bytes(data)


def validate_clip(data: bytes) -> None:
    try:
        with wave.open(io.BytesIO(data)) as audio:
            frames = audio.getnframes()
            if (audio.getframerate(), audio.getnchannels(), audio.getsampwidth()) != (16000, 1, 2):
                raise ValueError
            if not 48000 <= frames <= 240000 or len(audio.readframes(frames)) != frames * 2:
                raise ValueError
    except (wave.Error, EOFError, ValueError):
        raise HTTPException(422, "Use 3–15 seconds of clear speech. Try an earlier start time.")


@app.post("/clip")
async def extract(request: Request, start: Annotated[float, Query(ge=0, le=86400)] = 0):
    if request.headers.get("x-voice-permission") != "yes":
        raise HTTPException(403, "Confirm permission before preparing the voice.")
    if slots.locked():
        raise HTTPException(429, "The studio is busy. Try again shortly.")
    async with slots:
        data = await body(request, 64 * 1024 * 1024)
        with tempfile.TemporaryDirectory() as folder:
            source, target = Path(folder) / "input", Path(folder) / "clip.wav"
            await asyncio.to_thread(source.write_bytes, data)
            process = await asyncio.create_subprocess_exec(
                ffmpeg_binary(), "-nostdin", "-v", "error",
                "-protocol_whitelist", "file", "-format_whitelist", "mov,matroska,webm,mp3,wav,ogg,flac,aac,avi",
                "-ss", str(start), "-i", str(source), "-map", "0:a:0", "-t", "15",
                "-af", "highpass=f=75,afftdn=nf=-30,dynaudnorm", "-ac", "1", "-ar", "16000",
                str(target), stderr=asyncio.subprocess.DEVNULL)
            try:
                await asyncio.wait_for(process.wait(), 25)
            except TimeoutError:
                raise HTTPException(422, "This file took too long to decode. Trim it and try again.")
            finally:
                if process.returncode is None:
                    process.kill()
                    await process.wait()
            if process.returncode:
                raise HTTPException(422, "No readable audio track. Try MP4, WAV, MP3 or a WhatsApp voice note.")
            clip = await asyncio.to_thread(target.read_bytes)
        validate_clip(clip)
        return Response(clip, media_type="audio/wav")


@app.post("/speak")
async def speak(request: Request):
    import json
    from pydantic import ValidationError
    from models import Message
    try:
        message = Message.model_validate(json.loads(await body(request, 700000)))
        clip = base64.b64decode(message.clip, validate=True)
    except (ValueError, ValidationError):
        raise HTTPException(422, "Check the message, voice sample and permission.")
    validate_clip(clip)
    key = os.getenv("SARVAM_API_KEY") or dotenv_values(ROOT / ".env").get("SARVAM_API_KEY")
    if not key:
        raise HTTPException(503, "Set SARVAM_API_KEY in the project .env.")
    if slots.locked():
        raise HTTPException(429, "The studio is busy. Try again shortly.")
    async with slots:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=80) as transport:
                client = AsyncSarvamAI(api_subscription_key=key, httpx_client=transport)
                audio = await asyncio.wait_for(client.voice_cloning.convert(
                    text=message.text, ref_audio=("reference.wav", clip, "audio/wav"),
                    output_audio_codec="mp3", enable_cached_responses=False,
                    request_options={"max_retries": 0}), 90)
                result = base64.b64decode(audio.audio_b64 or audio.audio, validate=True)
                if not result:
                    raise ValueError("empty audio")
        except Exception as error:
            status = getattr(error, "status_code", None)
            if status in (401, 402, 403):
                raise HTTPException(502, "Check Sarvam key permissions, cloning access and credits.")
            if status in (400, 422):
                raise HTTPException(422, "Sarvam could not use this sample. Try 10–15 seconds of clear solo speech.")
            raise HTTPException(503, "Voice generation is unavailable. Try again shortly.")
    return Response(result, media_type="audio/mpeg")
