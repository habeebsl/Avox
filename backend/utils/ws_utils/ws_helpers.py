import json
import logging
import struct

from fastapi import WebSocket

from schemas.speech_generator_schemas import VoiceData
from utils.redis_utils import VoiceSlotManager
from utils.speech_generator_utils.speech_generator import create_speech_generator
from utils.ws_utils.dataclasses import AdProcessingState, StepStatus


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_message_bytes(metadata: dict, audio_bytes: bytes) -> bytes:
    meta_json = json.dumps(metadata)
    meta_bytes = meta_json.encode('utf-8')
    meta_length = struct.pack('<I', len(meta_bytes))
    message = meta_length + meta_bytes + audio_bytes

    return message

async def safe_send_websocket_message(websocket: WebSocket, message: dict):
    """Safely send websocket message with connection handling."""
    try:
        await websocket.send_json(message)
        return True
    except Exception as e:
        logger.error(f"Failed to send websocket message: {e}")
        return False
    
def ensure_voice_data_object(voice_data_source) -> VoiceData:
    """Ensure voice data is a VoiceData object, not a dictionary."""
    if isinstance(voice_data_source, dict):
        return VoiceData(
            voice_name=voice_data_source.get("voice_name", ""),
            voice_id=voice_data_source.get("voice_id", ""),
            labels=voice_data_source.get("labels", {})
        )
    return voice_data_source

async def cleanup_custom_voice(voice_id: str, slot_manager: VoiceSlotManager, status: str):
    """Clean up custom voice and update slot status."""
    try:
        async with create_speech_generator() as labs:
            deleted = await labs.delete_voice(voice_id)
            if not deleted:
                logger.warning(f"Failed to delete voice {voice_id}")
        
        await slot_manager.update_slot_status(voice_id, status)
        logger.info(f"Voice {voice_id} cleaned up with status: {status}")
        
    except Exception as cleanup_error:
        logger.error(f"Error during voice cleanup for {voice_id}: {cleanup_error}")

async def send_processing_summary(websocket: WebSocket, state: AdProcessingState):
    """Send a summary of what succeeded/failed for this ad."""
    summary = {
        "type": "summary",
        "index": state.index,
        "location": state.location,
        "steps": {
            "insights": {
                "status": state.insights.status.value,
                "error": state.insights.error
            },
            "transcript": {
                "status": state.transcript.status.value, 
                "error": state.transcript.error
            },
            "speech": {
                "status": state.speech.status.value,
                "error": state.speech.error
            },
            "music": {
                "status": state.music.status.value,
                "error": state.music.error
            },
            "merge": {
                "status": state.merge.status.value,
                "error": state.merge.error
            }
        },
        "overall_success": (
            state.insights.status == StepStatus.SUCCESS and
            state.transcript.status == StepStatus.SUCCESS and
            state.speech.status == StepStatus.SUCCESS and
            state.music.status == StepStatus.SUCCESS and
            state.merge.status == StepStatus.SUCCESS
        )
    }
    
    await safe_send_websocket_message(websocket, summary)