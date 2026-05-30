# ============================================================
# TTS Endpoint — Proxy for Munsit API
# ============================================================
"""
Provides Text-to-Speech capabilities by proxying requests to the Munsit API.
Converts the raw PCM stream into a WAV stream so the browser can play it directly.
"""

from __future__ import annotations

import logging
import struct
from typing import AsyncGenerator

import httpx
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import get_settings
from app.auth.middleware import get_current_user

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/tts", tags=["TTS"])

class TTSRequest(BaseModel):
    text: str
    voice_id: str = "ar-najdi-male-2"
    speed: float = 1.0

def create_wav_header(sample_rate: int = 24000, num_channels: int = 1, bits_per_sample: int = 16) -> bytes:
    """
    Creates a standard RIFF/WAVE header for streaming PCM data.
    Uses 0xFFFFFFFF for data size since we are streaming and don't know the exact size upfront.
    """
    data_size = 0xFFFFFFFF - 36  # Max size for streaming under 32-bit limits (4GB)
    byte_rate = sample_rate * num_channels * (bits_per_sample // 8)
    block_align = num_channels * (bits_per_sample // 8)
    
    header = struct.pack(
        '<4sI4s4sIHHIIHH4sI',
        b'RIFF',
        36 + data_size,
        b'WAVE',
        b'fmt ',
        16,
        1,  # PCM format
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b'data',
        data_size
    )
    return header

async def stream_munsit_audio(text: str, voice_id: str, speed: float) -> AsyncGenerator[bytes, None]:
    """Streams audio from Munsit API and prepends a WAV header."""
    if not settings.MUNSIT_API_KEY or settings.MUNSIT_API_KEY == "YOUR_API_KEY":
        raise HTTPException(status_code=500, detail="Munsit API key not configured")

    url = "https://api.munsit.com/api/v1/text-to-speech/faseeh-v1-preview"
    headers = {
        "x-api-key": settings.MUNSIT_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "voice_id": voice_id,
        "text": text,
        "streaming": True,
        "stability": 0.5,
        "speed": speed
    }

    # Yield the WAV header first so the browser knows how to decode the stream
    yield create_wav_header(sample_rate=24000)

    try:
        async with httpx.AsyncClient() as client:
            async with client.stream("POST", url, headers=headers, json=payload, timeout=30.0) as response:
                if response.status_code != 200:
                    error_detail = await response.aread()
                    logger.error(f"Munsit API Error: {response.status_code} - {error_detail}")
                    return
                
                async for chunk in response.aiter_bytes():
                    yield chunk
    except Exception as e:
        logger.error(f"Error streaming from Munsit: {e}")

@router.post("", summary="Convert Text to Speech")
async def generate_speech(request: TTSRequest, current_user: dict = Depends(get_current_user)):
    """
    Converts text to speech using Munsit API.
    Returns a WAV audio stream.
    Requires authentication.
    """
    generator = stream_munsit_audio(request.text, request.voice_id, request.speed)
    return StreamingResponse(generator, media_type="audio/wav")
