import logging
from fastapi import WebSocket
from utils.musicgen_utils.musicgen import MusicGen
from utils.ws_utils.dataclasses import StepResult, StepStatus, AdProcessingState
from utils.ws_utils.ws_helpers import safe_send_websocket_message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def step_generate_music(
    websocket: WebSocket,
    state: AdProcessingState,
    music_prompt: str
) -> StepResult:
    """Step 4: Generate music."""
    try:
        musicgen = MusicGen()
        music_buffer = await musicgen.generate_background_music(music_prompt, 40)

        if not music_buffer:
            return StepResult(
                status=StepStatus.FAILED,
                error="Music generation failed",
                step_name="music"
            )

        return StepResult(
            status=StepStatus.SUCCESS,
            data=music_buffer,
            step_name="music"
        )

    except Exception as e:
        logger.error(f"Error in step_generate_music for index {state.index}: {e}")
        await safe_send_websocket_message(websocket, {
            "type": "error", 
            "index": state.index,
            "step": "music",
            "message": f"Music generation failed: {str(e)}"
        })
        return StepResult(
            status=StepStatus.FAILED,
            error=str(e),
            step_name="music"
        )