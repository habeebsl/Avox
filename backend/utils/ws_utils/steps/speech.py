import logging

from fastapi import WebSocket

from schemas.gpt_schemas import ResponseSchema
from schemas.speech_generator_schemas import VoiceData, SpeechRequest
from utils.deepl_utils import translate
from utils.speech_generator_utils.helpers import map_timestamps_to_transcript
from utils.speech_generator_utils.speech_generator import create_speech_generator
from utils.ws_utils.dataclasses import AdProcessingState, StepResult, StepStatus
from utils.ws_utils.ws_helpers import get_message_bytes, safe_send_websocket_message


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def generate_ad_speech(
    websocket: WebSocket,
    index: int,
    transcript_results: ResponseSchema, 
    voice_data: VoiceData
):
    """Generate speech audio for an ad."""
    try:
        transcript_data = transcript_results.results[0]
        
        english_transcript = transcript_data.transcript
        translation = None
        language = voice_data.labels.get("language")

        if language:
            logger.info(f"voice language is present: {language}")
        
        if language and language != 'en':
            logger.info(f"Intializing translation to {language} language")
            translation = await translate(english_transcript, "EN", language.upper())
            if translation:
                logger.info(f"Translation Successful")

        async with create_speech_generator() as labs:
            transcript = translation if translation else english_transcript


            speech_request = SpeechRequest(
                text=transcript,
                voice_id=voice_data.voice_id
            )
            audio_buffer = await labs.generate_speech(
                speech_request
            )

            if not audio_buffer:
                raise ValueError("Voice generation failed")

            forced_alignment = await labs.get_forced_alignment(
                transcript,
                audio_buffer
            )

        sentence_alignment = None
        if forced_alignment:
            sentence_alignment = await map_timestamps_to_transcript(
                transcript,
                forced_alignment.words
            )

        response_data = {
            "type": "speech",
            "index": index,
            "transcript": transcript_data.transcript,
            "translations": translation.split("\n") if translation else None,
            "alignments": sentence_alignment
        }

        message_bytes = get_message_bytes(response_data, audio_buffer.getvalue())

        await websocket.send_bytes(message_bytes)
        return audio_buffer
        
    except Exception as e:
        logger.error(f"Error in [generate_ad_speech] for index {index}: {e}")

async def step_generate_speech(
    websocket: WebSocket,
    state: AdProcessingState,
    transcript_results: ResponseSchema,
    voice_data: VoiceData
) -> StepResult:
    """Step 3: Generate speech."""
    try:
        speech_buffer = await generate_ad_speech(
            websocket,
            state.index,
            transcript_results,
            voice_data
        )

        if not speech_buffer:
            return StepResult(
                status=StepStatus.FAILED,
                error="Speech generation failed",
                step_name="speech"
            )

        return StepResult(
            status=StepStatus.SUCCESS,
            data=speech_buffer,
            step_name="speech"
        )

    except Exception as e:
        logger.error(f"Error in step_generate_speech for index {state.index}: {e}")
        await safe_send_websocket_message(websocket, {
            "type": "error",
            "index": state.index,
            "step": "speech",
            "message": f"Speech generation failed: {str(e)}"
        })
        return StepResult(
            status=StepStatus.FAILED,
            error=str(e),
            step_name="speech"
        )
