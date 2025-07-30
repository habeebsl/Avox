import asyncio
import json
import logging
from typing import Optional
from fastapi import WebSocket, APIRouter
from schemas.speech_generator_schemas import VoiceData
from schemas.ws_schemas import AdRequest
from utils.redis_utils import VoiceSlotManager
from utils.speech_generator_utils.speech_generator import create_speech_generator
from utils.ws_utils.dataclasses import AdProcessingState, StepResult, StepStatus
from utils.ws_utils.steps.insights import step_gather_insights
from utils.ws_utils.steps.merge import step_merge_audio
from utils.ws_utils.steps.music import step_generate_music
from utils.ws_utils.steps.speech import step_generate_speech
from utils.ws_utils.steps.transcript import step_generate_transcript
from utils.ws_utils.ws_helpers import (
    ensure_voice_data_object, 
    safe_send_websocket_message, 
    cleanup_custom_voice)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ws = APIRouter()

async def process_ad_with_granular_handling(
    websocket: WebSocket, 
    index: int, 
    data: AdRequest, 
    voices: list[VoiceData],
    recordings: list[bytes]
):
    """Process ad with granular error handling and status tracking."""
    location = data.locations[index]
    
    # Initialize processing state
    state = AdProcessingState(
        index=index,
        location=location.name,
        insights=StepResult(StepStatus.PENDING, step_name="insights"),
        transcript=StepResult(StepStatus.PENDING, step_name="transcript"),
        speech=StepResult(StepStatus.PENDING, step_name="speech"),
        music=StepResult(StepStatus.PENDING, step_name="music"),
        merge=StepResult(StepStatus.PENDING, step_name="merge"),
        voice_cleanup=StepResult(StepStatus.PENDING, step_name="voice_cleanup")
    )

    voice_id: Optional[str] = None
    slot_manager = VoiceSlotManager()

    try:
        # Step 1: Handle voice cloning if needed
        voice_data = None
        if data.ad_type == 'custom':
            # First validate that the slot reservation is valid
            slot_available = await slot_manager.has_available_slot(data.slot_reservation_id)
            if not slot_available:
                raise Exception("Invalid reservation or no slots available")
            
            # Clone the voice
            async with create_speech_generator() as labs:
                clone_res = None
                if recordings:
                    clone_res = await labs.clone_voice(
                        recordings, 
                        langauge_code=data.clone_language)
                if not clone_res:
                    raise Exception("Error cloning voice")
                
                voice_id = clone_res.voice_id
                
                # Now acquire the slot with the voice_id
                async with slot_manager.acquire_slot_with_reservation(
                    voice_id,
                    data.slot_reservation_id
                ) as acquired:
                    if not acquired:
                        try:
                            await labs.delete_voice(voice_id)
                        except Exception as cleanup_error:
                            logger.error(
                                f"Failed to cleanup voice after slot acquisition failure: {cleanup_error}"
                            )
                        raise Exception("Slot acquisition failed after voice cloning")
                    
                    voice_data = await labs.get_voice(voice_id)
                    if not voice_data:
                        raise Exception("Error getting cloned voice data")
                    
                    voice_data = ensure_voice_data_object(voice_data)

        # Step 2: Gather insights
        state.insights = await step_gather_insights(
            websocket, state, location.name, location.code, 
            data.use_weather, data.forecast_type
        )

        if state.insights.status == StepStatus.FAILED:
            # Send summary and return - can't continue without insights
            return

        # Step 3: Generate transcript
        state.transcript = await step_generate_transcript(
            websocket, state, data, voices, state.insights.data
        )

        if state.transcript.status == StepStatus.FAILED:
            return

        # Prepare voice data
        if not voice_data:
            voice_model = state.transcript.data.results[0].voice_model.lower()
            voice_dict = next(
                (v for v in voices if v.voice_name.lower() == voice_model),
                voices[-1] if voices else None
            )
            voice_data = ensure_voice_data_object(voice_dict)

        # Step 4 & 5: Generate speech and music concurrently
        speech_task = asyncio.create_task(
            step_generate_speech(websocket, state, state.transcript.data, voice_data)
        )
        music_task = asyncio.create_task(
            step_generate_music(
                websocket, state, 
                state.transcript.data.results[0].music_prompt
            )
        )

        # Wait for both and handle partial failures
        speech_result, music_result = await asyncio.gather(
            speech_task, music_task, return_exceptions=True
        )

        # Handle speech result
        if isinstance(speech_result, Exception):
            state.speech = StepResult(
                StepStatus.FAILED, 
                error=str(speech_result), 
                step_name="speech"
            )
        else:
            state.speech = speech_result

        # Handle music result  
        if isinstance(music_result, Exception):
            state.music = StepResult(
                StepStatus.FAILED,
                error=str(music_result),
                step_name="music"
            )
        else:
            state.music = music_result

        # Step 6: Merge audio only if both speech and music succeeded
        if (state.speech.status == StepStatus.SUCCESS and 
            state.music.status == StepStatus.SUCCESS):
            
            state.merge = await step_merge_audio(
                websocket, state, state.speech.data, state.music.data
            )
        else:
            state.merge = StepResult(
                StepStatus.SKIPPED,
                error="Skipped due to speech or music failure",
                step_name="merge"
            )

        # Step 7: Voice cleanup
        if data.ad_type == 'custom' and voice_id:
            cleanup_status = 'completed' if state.merge.status == StepStatus.SUCCESS else 'error'
            await cleanup_custom_voice(voice_id, slot_manager, cleanup_status)
            state.voice_cleanup = StepResult(StepStatus.SUCCESS, step_name="voice_cleanup")

        await safe_send_websocket_message(websocket, {
            "type": "done",
            "index": index
        })

    except Exception as e:
        logger.error(f"Unexpected error in process_ad for index {index}: {e}")
        
        # Clean up voice on unexpected error
        if data.ad_type == 'custom' and voice_id:
            await cleanup_custom_voice(voice_id, slot_manager, 'error')
            
        await safe_send_websocket_message(websocket, {
            "type": "error",
            "index": index,
            "message": f"Unexpected error: {str(e)}"
        })

@ws.websocket("/generate")
async def generate_audio_ads(websocket: WebSocket):
    """Main websocket endpoint with granular error handling."""
    print("Websocket activate")
    await websocket.accept()

    try:
        # Receive and validate initial request
        data = await websocket.receive_json()
        ad_request = AdRequest(**data)
        
        if not ad_request.locations:
            raise ValueError("No locations provided")

        # Send acknowledgment that we received the request
        await safe_send_websocket_message(websocket, {
            "type": "received"
        })

        # Get voices library
        async with create_speech_generator() as labs:
            voices = await labs.get_voices()

        if not voices:
            raise ValueError("Failed to retrieve voices library")

        # Validate slot reservation for custom ads
        if ad_request.ad_type == 'custom':
            slot_manager = VoiceSlotManager()
            is_slot_available = await slot_manager.has_available_slot(
                ad_request.slot_reservation_id
            )
            if not is_slot_available:
                raise ValueError("Invalid reservation ID or no slots available")
        
        # Wait for music buffers and finished signal
        music_buffers = []
        while True:
            try:
                message = await websocket.receive()
                
                if message["type"] == "websocket.receive":
                    if "bytes" in message:
                        # This is a music buffer
                        music_buffers.append(message["bytes"])
                    elif "text" in message:
                        # This is a JSON message
                        json_data = json.loads(message["text"])
                        if json_data.get("type") == "finished":
                            break
                else:
                    break
                    
            except Exception as e:
                logger.error(f"Error receiving message: {e}")
                break

        # Now process with all the data
        # You can use music_buffers here as needed
        
        # Process all locations with granular handling
        tasks = [
            asyncio.create_task(
                process_ad_with_granular_handling(websocket, i, ad_request, voices, music_buffers)
            ) 
            for i in range(len(ad_request.locations))
        ]

        # Wait for all tasks, collecting results
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        await safe_send_websocket_message(websocket, {
            "type": "complete"
        })
        
    except Exception as e:
        logger.error(f"Error in generate_audio_ads: {e}")
        await safe_send_websocket_message(websocket, {
            "type": "fatal_error", 
            "message": str(e)
        })
    finally:
        try:
            await websocket.close()
        except:
            pass