# ============================================================
# TTS Endpoint — Proxy for Munsit API
# ============================================================
"""
Provides Text-to-Speech capabilities by proxying requests to the Munsit API.
Converts the raw PCM stream into a WAV stream so the browser and robot can play it directly.
"""

from __future__ import annotations

import logging
import struct
from typing import AsyncGenerator, Optional

import httpx
import jwt
from fastapi import APIRouter, HTTPException, Depends, Query, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.auth.middleware import get_current_user, bearer_scheme
from app.auth.schemas import TokenPayload
from app.auth.service import decode_access_token
from app.dependencies import get_db_session
from app.db.models import Student

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/tts", tags=["TTS"])

class TTSRequest(BaseModel):
    text: str
    voice_id: str = "3NQTWYgRxBR3hOgdLtF0U02d"  # Default to user's Arabic voice ID
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

def is_female_student(first_name: str) -> bool:
    """Heuristic to check if a student's first name is feminine (Arabic or English)."""
    name_clean = first_name.strip().lower()
    
    # Common English-transliterated female names in seed/system
    english_female_names = {"noor", "lina", "aya", "rania", "salma", "dana", "layla", "sarah", "fatima"}
    if name_clean in english_female_names:
        return True
        
    # Common Arabic female names
    arabic_female_names = {"نور", "لينا", "آية", "رانيا", "سلمى", "دانا", "ليلى", "سارة", "فاطمة"}
    if name_clean in arabic_female_names:
        return True
        
    # Heuristic for Arabic names ending in Teh Marbuta (ة) or Alef Maksura (ى) or Alef (ا)
    if name_clean and (name_clean.endswith("ة") or name_clean.endswith("ى") or name_clean.endswith("ا")):
        return True
        
    return False

async def stream_munsit_audio(text: str, voice_id: str, speed: float) -> AsyncGenerator[bytes, None]:
    """Streams audio from Munsit API and prepends a WAV header."""
    if not settings.MUNSIT_API_KEY or settings.MUNSIT_API_KEY == "YOUR_API_KEY":
        raise HTTPException(status_code=500, detail="Munsit API key not configured")

    # Map old default voice IDs to the new Arabic voice ID to ensure seamless migration
    if voice_id in ("ar-najdi-male-2", "pCKbQ4EPGE06zpEPGNvS", "rHzpDFOsbm9Cy1gYfoVllk38"):
        voice_id = "3NQTWYgRxBR3hOgdLtF0U02d"

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

async def get_current_user_from_token(
    token: Optional[str] = Query(None, description="JWT token via query parameter"),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> TokenPayload:
    actual_token = None
    if token:
        actual_token = token
    elif credentials:
        actual_token = credentials.credentials

    if not actual_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a Bearer token or token query parameter.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(actual_token)
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token received: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

@router.post("", summary="Convert Text to Speech")
async def generate_speech(
    request: TTSRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Converts text to speech using Munsit API.
    Returns a WAV audio stream.
    Requires authentication.
    """
    student_id = getattr(current_user, "student_id", None)
    first_name = ""
    
    if student_id:
        try:
            result = await db.execute(select(Student).where(Student.id == student_id))
            student = result.scalar_one_or_none()
            if student:
                first_name = student.first_name
        except Exception as e:
            logger.error(f"Error fetching student name for TTS: {e}")

    voice_id = request.voice_id
    if voice_id in ("ar-najdi-male-2", "pCKbQ4EPGE06zpEPGNvS", "rHzpDFOsbm9Cy1gYfoVllk38", "3NQTWYgRxBR3hOgdLtF0U02d", "ar-msa-female-1"):
        if first_name and is_female_student(first_name):
            voice_id = "ar-msa-female-1"
            logger.info(f"TTS: Student '{first_name}' detected as Female. Using voice ar-msa-female-1.")
        else:
            voice_id = "3NQTWYgRxBR3hOgdLtF0U02d"
            logger.info(f"TTS: Student '{first_name}' detected as Male or fallback. Using voice 3NQTWYgRxBR3hOgdLtF0U02d.")

    generator = stream_munsit_audio(request.text, voice_id, request.speed)
    return StreamingResponse(generator, media_type="audio/wav")

@router.get("", summary="Convert Text to Speech via GET")
async def generate_speech_get(
    text: str,
    voice_id: str = "3NQTWYgRxBR3hOgdLtF0U02d",
    speed: float = 1.0,
    token: Optional[str] = None,
    current_user: TokenPayload = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Converts text to speech using Munsit API via GET request.
    Returns a WAV audio stream. Allows query param token auth for HTML5 Audio streaming.
    """
    student_id = getattr(current_user, "student_id", None)
    first_name = ""
    
    if student_id:
        try:
            result = await db.execute(select(Student).where(Student.id == student_id))
            student = result.scalar_one_or_none()
            if student:
                first_name = student.first_name
        except Exception as e:
            logger.error(f"Error fetching student name for TTS: {e}")

    if voice_id in ("ar-najdi-male-2", "pCKbQ4EPGE06zpEPGNvS", "rHzpDFOsbm9Cy1gYfoVllk38", "3NQTWYgRxBR3hOgdLtF0U02d", "ar-msa-female-1"):
        if first_name and is_female_student(first_name):
            voice_id = "ar-msa-female-1"
            logger.info(f"TTS: Student '{first_name}' detected as Female. Using voice ar-msa-female-1.")
        else:
            voice_id = "3NQTWYgRxBR3hOgdLtF0U02d"
            logger.info(f"TTS: Student '{first_name}' detected as Male or fallback. Using voice 3NQTWYgRxBR3hOgdLtF0U02d.")

    generator = stream_munsit_audio(text, voice_id, speed)
    return StreamingResponse(generator, media_type="audio/wav")
