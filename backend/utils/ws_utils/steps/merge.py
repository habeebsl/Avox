import io
import logging
from fastapi import WebSocket

from utils.mixer_utils.audio_mixer import create_audio_mixer
from utils.ws_utils.dataclasses import StepResult, StepStatus, AdProcessingState
from utils.ws_utils.ws_helpers import get_message_bytes, safe_send_websocket_message


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def merge_ad_with_music(
        websocket: WebSocket, 
        index: int, 
        speech_buffer: io.BytesIO, 
        music_buffer: io.BytesIO
    ):

    try:
        async with create_audio_mixer() as mixer:
            merged_buffer = await mixer.merge_music_with_speech(
                speech_buffer,
                music_buffer
            )

        if not merged_buffer:
            raise ValueError("Audio mixing failed")

        merged_data = {
            "type": "merged",
            "index": index
        }

        response_bytes = get_message_bytes(merged_data, merged_buffer.getvalue())

        await websocket.send_bytes(response_bytes)
    except Exception as e:
        logger.error(f"Error in [merge_ad_with_music] for index {index}: {e}")


async def step_merge_audio(
    websocket: WebSocket,
    state: AdProcessingState,
    speech_buffer: io.BytesIO,
    music_buffer: io.BytesIO
) -> StepResult:
    """Step 5: Merge audio."""
    try:
        await merge_ad_with_music(websocket, state.index, speech_buffer, music_buffer)
        
        return StepResult(
            status=StepStatus.SUCCESS,
            data=True,
            step_name="merge"
        )

    except Exception as e:
        logger.error(f"Error in step_merge_audio for index {state.index}: {e}")
        await safe_send_websocket_message(websocket, {
            "type": "error",
            "index": state.index,
            "step": "merge", 
            "message": f"Audio merging failed: {str(e)}"
        })
        return StepResult(
            status=StepStatus.FAILED,
            error=str(e),
            step_name="merge"
        )