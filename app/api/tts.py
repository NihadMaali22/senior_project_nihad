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

    logger.info(f"Munsit TTS request: text_len={len(text)}, voice={voice_id}, speed={speed}")

    try:
        async with httpx.AsyncClient() as client:
            async with client.stream("POST", url, headers=headers, json=payload, timeout=60.0) as response:
                if response.status_code != 200:
                    error_detail = await response.aread()
                    error_msg = error_detail.decode("utf-8", errors="replace")
                    logger.error(f"Munsit API Error: {response.status_code} - {error_msg}")
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Munsit API error: {error_msg}"
                    )

                # Only yield WAV header AFTER confirming API responded with 200
                yield create_wav_header(sample_rate=24000)

                chunk_count = 0
                async for chunk in response.aiter_bytes():
                    chunk_count += 1
                    yield chunk

                logger.info(f"Munsit TTS completed: {chunk_count} chunks streamed")

    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except httpx.TimeoutException:
        logger.error("Munsit API timed out after 60 seconds")
        raise HTTPException(status_code=504, detail="Munsit API timed out")
    except Exception as e:
        logger.error(f"Error streaming from Munsit: {type(e).__name__}: {e}")
        raise HTTPException(status_code=502, detail=f"Munsit connection error: {str(e)}")

@router.post("", summary="Convert Text to Speech")
async def generate_speech(request: TTSRequest, current_user: dict = Depends(get_current_user)):
    """
    Converts text to speech using Munsit API.
    Returns a WAV audio stream.
    Requires authentication.
    """
    generator = stream_munsit_audio(request.text, request.voice_id, request.speed)
    return StreamingResponse(generator, media_type="audio/wav")
