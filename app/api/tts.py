# ============================================================
# TTS Endpoint — Proxy for ElevenLabs API
# ============================================================
"""
Provides Text-to-Speech capabilities by proxying requests to the ElevenLabs API.
Converts the raw PCM stream into a WAV stream so the browser and robot can play it directly.
"""

from __future__ import annotations

import logging
import struct
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.auth.middleware import get_current_user
from app.dependencies import get_db_session
from app.db.models import Student

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/tts", tags=["TTS"])

class TTSRequest(BaseModel):
    text: str
    voice_id: str = "pCKbQ4EPGE06zpEPGNvS"  # Default to Abdullah's voice ID
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

async def stream_elevenlabs_audio(text: str, voice_id: str) -> AsyncGenerator[bytes, None]:
    """Streams audio from ElevenLabs API and prepends a WAV header."""
    if not settings.ELEVEN_API_KEY:
        raise HTTPException(status_code=500, detail="ElevenLabs API key not configured")

    logger.info(f"ElevenLabs TTS request: text_len={len(text)}, voice={voice_id}")

    try:
        from elevenlabs.client import AsyncElevenLabs
        client = AsyncElevenLabs(api_key=settings.ELEVEN_API_KEY)
        
        # Request uncompressed PCM 24kHz stream
        audio_stream = await client.text_to_speech.convert_as_stream(
            text=text,
            voice_id=voice_id,
            model_id="eleven_multilingual_v2",
            output_format="pcm_24000"
        )

        # Prepend standard WAV header for PCM 24kHz, 16-bit, mono
        yield create_wav_header(sample_rate=24000)

        chunk_count = 0
        async for chunk in audio_stream:
            if isinstance(chunk, bytes):
                chunk_count += 1
                yield chunk

        logger.info(f"ElevenLabs TTS completed: {chunk_count} chunks streamed")

    except Exception as e:
        logger.error(f"Error streaming from ElevenLabs: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"ElevenLabs connection error: {str(e)}")

@router.post("", summary="Convert Text to Speech")
async def generate_speech(
    request: TTSRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Converts text to speech using ElevenLabs API.
    Returns a WAV audio stream.
    Automatically detects student gender and uses voice Abdullah (male) or Sarah (female).
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

    # Voice assignment
    # Abdullah: pCKbQ4EPGE06zpEPGNvS
    # Sarah: jAAHNNqlbAX9iWjJPEtE
    if first_name and is_female_student(first_name):
        selected_voice = "jAAHNNqlbAX9iWjJPEtE"  # Sarah (female)
        logger.info(f"TTS: Student '{first_name}' detected as Female. Using voice Sarah.")
    else:
        selected_voice = "pCKbQ4EPGE06zpEPGNvS"  # Abdullah (male)
        logger.info(f"TTS: Student '{first_name}' detected as Male or fallback. Using voice Abdullah.")

    generator = stream_elevenlabs_audio(request.text, selected_voice)
    return StreamingResponse(generator, media_type="audio/wav")
