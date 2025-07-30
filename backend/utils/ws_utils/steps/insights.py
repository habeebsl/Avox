import asyncio
import logging

from fastapi import WebSocket
from utils.ws_utils.dataclasses import StepResult, StepStatus, AdProcessingState
from utils.ws_utils.handlers import get_forecast_info, get_insights, get_slangs, get_trends
from utils.ws_utils.ws_helpers import safe_send_websocket_message


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def step_gather_insights(
    websocket: WebSocket,
    state: AdProcessingState,
    location_name: str,
    location_code: str,
    use_weather: bool,
    forecast_type: str
) -> StepResult:
    """Step 1: Gather all insights data."""
    try:
        tasks = [
            asyncio.create_task(get_insights(location_name)),
            asyncio.create_task(get_trends(location_code)),
            asyncio.create_task(get_forecast_info(location_name, use_weather, forecast_type)),
            asyncio.create_task(get_slangs(location_name))
        ]

        taste_data, trends, forecast_data, slangs = await asyncio.gather(*tasks)

        if not taste_data:
            return StepResult(
                status=StepStatus.FAILED,
                error="Taste generation failed",
                step_name="insights"
            )

        insights_data = {
            "taste_data": taste_data,
            "trends": trends,
            "forecast_data": forecast_data,
            "slangs": slangs
        }

        return StepResult(
            status=StepStatus.SUCCESS,
            data=insights_data,
            step_name="insights"
        )

    except Exception as e:
        logger.error(f"Error in step_gather_insights for index {state.index}: {e}")
        await safe_send_websocket_message(websocket, {
            "type": "error",
            "index": state.index,
            "step": "insights",
            "message": f"Failed to gather insights: {str(e)}"
        })
        return StepResult(
            status=StepStatus.FAILED,
            error=str(e),
            step_name="insights"
        )