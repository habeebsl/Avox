import json
import logging

from fastapi import WebSocket

from prompts import transcript_prompts
from schemas.gpt_schemas import TranscriptRequest
from schemas.speech_generator_schemas import VoiceData
from schemas.ws_schemas import AdRequest
from utils.gpt_utils.gpts import create_gpt_client
from utils.ws_utils.dataclasses import AdProcessingState, StepResult, StepStatus
from utils.ws_utils.ws_helpers import safe_send_websocket_message


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def step_generate_transcript(
    websocket: WebSocket,
    state: AdProcessingState,
    data: AdRequest,
    voices: list[VoiceData],
    insights_data: dict
) -> StepResult:
    """Step 2: Generate transcript."""
    try:
        async with create_gpt_client() as gpt:
            user_prompt = transcript_prompts.user_prompt(
                data.product_name,
                data.product_summary,
                data.offer_summary,
                data.cta,
                data.locations[state.index].model_dump(),
                insights_data.get("taste_data", {}),
                [voice.model_dump() for voice in voices],
                insights_data["trends"],
                insights_data["slangs"],
                insights_data["forecast_data"],
            )

            transcript_request = TranscriptRequest(
                user_prompt=json.dumps(user_prompt),
                with_forecast=data.use_weather,
                forecast_days=data.forecast_type,
                variations=1
            )
            
            transcript_results = await gpt.generate_transcripts(transcript_request)

        if not transcript_results or not transcript_results.results:
            return StepResult(
                status=StepStatus.FAILED,
                error="Transcript generation failed",
                step_name="transcript"
            )

        insights = transcript_results.results[0].insight_details
        if insights:
            await safe_send_websocket_message(websocket, {
                "type": "insight",
                "index": state.index,
                "insights": [insight.model_dump() for insight in insights]
            })

        return StepResult(
            status=StepStatus.SUCCESS,
            data=transcript_results,
            step_name="transcript"
        )

    except Exception as e:
        logger.error(f"Error in step_generate_transcript for index {state.index}: {e}")
        await safe_send_websocket_message(websocket, {
            "type": "error",
            "index": state.index,
            "step": "transcript",
            "message": f"Transcript generation failed: {str(e)}"
        })
        return StepResult(
            status=StepStatus.FAILED,
            error=str(e),
            step_name="transcript"
        )