import asyncio
import json
import logging
from typing import Union, Optional
from fastapi import APIRouter, WebSocket

from prompts import transcript_prompts
from schemas.speech_generator_schemas import VoiceData
from schemas.ws_schemas import AdRequest
from schemas.gpt_schemas import ResponseSchema, TranscriptRequest

from utils.mixer_utils.audio_mixer import create_audio_mixer
from utils.musicgen_utils.musicgen import MusicGen
from utils.deepl_utils import translate
from utils.gpt_utils.gpts import create_gpt_client
from utils.taste_api_utils.taste_api import create_taste_api
from utils.speech_generator_utils.speech_generator import create_speech_generator
from utils.speech_generator_utils.helpers import map_timestamps_to_transcript
from utils.trends_scraper import GoogleTrendsScraper
from utils.news_utils.news_api import create_news_api
from utils.weather_utils.weather_api import create_weather_api
from utils.redis_utils import VoiceSlotManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ws = APIRouter()

async def get_insights(location: str):
    """Get taste insights for a location."""
    async with create_taste_api(location) as taste:
        taste_data = await taste.get_all_insights()
        return taste_data
        
async def get_trends(country_code: str):
    """Get trending topics and related news for a country."""
    async with GoogleTrendsScraper(headless=True) as scraper:
        trends = await scraper.scrape_trending_topics(country_code.upper(), hours=168)
        if not trends:
            return []
        
    trends_list = []
    for topic in trends:
        query = topic.query
        trends_list.append(query)

    async with create_news_api() as news_api:
        news_list = await news_api.get_news_for_query_list(
            trends_list, 
            country_code.lower()
        )
        return [news.model_dump() for news in news_list]
    
async def get_forecast_info(country_name: str, use_weather: bool, days: Union[str, None] = None):
    """Get weather forecast information if weather is enabled."""
    if not use_weather or not days:
        return None
        
    async with create_weather_api() as weather_api:
        forecast_data = await weather_api.get_forecast(country_name, days)
        return [forecast.model_dump() for forecast in forecast_data]

async def get_slangs(country_name: str):
    """Get local slangs for a country."""
    async with create_gpt_client() as gpt:
        slangs = await gpt.get_slangs(country_name)
        return slangs.model_dump()

def ensure_voice_data_object(voice_data_source) -> VoiceData:
    """Ensure voice data is a VoiceData object, not a dictionary."""
    if isinstance(voice_data_source, dict):
        return VoiceData(
            voice_name=voice_data_source.get("voice_name", ""),
            voice_id=voice_data_source.get("voice_id", ""),
            labels=voice_data_source.get("labels", {})
        )
    return voice_data_source

async def generate_ad_speech(
    websocket: WebSocket,
    index: int,
    location: str,
    transcript_results: ResponseSchema, 
    voice_data: VoiceData
):
    """Generate speech audio for an ad."""
    try:
        transcript_data = transcript_results.results[0]
        
        english_transcript = transcript_data.transcript
        translation = None
        language = voice_data.labels.get("language")
        
        if language and language != 'en':
            translation = await translate(english_transcript, "EN", language.upper())

        async with create_speech_generator() as labs:
            transcript = translation if translation else english_transcript

            audio_buffer = await labs.generate_speech(
                transcript,
                voice_data.voice_name,
                voice_data.voice_id
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
            "type": "speech_done",
            "location": location,
            "index": index,
            "speech_buffer": audio_buffer,
            "transcript_data": transcript_results,
            "translation_transcript": translation,
            "alignment": sentence_alignment
        }

        await websocket.send_json(response_data)
        return response_data
        
    except Exception as e:
        logger.error(f"Error in [generate_ad_speech] for index {index}: {e}")
        error_response = {"type": "error", "index": index, "message": str(e)}
        await websocket.send_json(error_response)
        raise

async def process_ad(websocket: WebSocket, index: int, data: AdRequest, voices: list[VoiceData]):
    """Process a single ad for a specific location."""
    voice_id: Optional[str] = None
    slot_manager = VoiceSlotManager()
    
    try:
        # Validate location index
        if index >= len(data.locations):
            raise ValueError(f"Invalid location index: {index}")
            
        location = data.locations[index]
        voice_data = None

        # Handle custom voice cloning
        if data.ad_type == 'custom':
            # First validate that the slot reservation is valid
            slot_available = await slot_manager.has_available_slot(data.slot_reservation_id)
            if not slot_available:
                raise Exception("Invalid reservation or no slots available")
            
            # Clone the voice
            async with create_speech_generator() as labs:
                clone_res = await labs.clone_voice(
                    data.audio_recordings, 
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
                        # Clean up the cloned voice if slot acquisition fails
                        try:
                            await labs.delete_voice(voice_id)
                        except Exception as cleanup_error:
                            logger.error(f"Failed to cleanup voice after slot acquisition failure: {cleanup_error}")
                        raise Exception("Slot acquisition failed after voice cloning")
                    
                    # Get the voice data
                    voice_data = await labs.get_voice(voice_id)
                    if not voice_data:
                        raise Exception("Error getting cloned voice data")
                    
                    voice_data = ensure_voice_data_object(voice_data)

        # Gather all required data concurrently
        tasks = [
            asyncio.create_task(get_insights(location.name)),
            asyncio.create_task(get_trends(location.code)),
            asyncio.create_task(get_forecast_info(
                location.name, 
                data.use_weather,
                data.forecast_type
            )),
            asyncio.create_task(get_slangs(location.name))
        ]

        taste_data, trends, forecast_data, slangs = await asyncio.gather(*tasks)

        if not taste_data:
            raise ValueError("Taste generation failed")

        # Generate transcript
        async with create_gpt_client() as gpt:
            user_prompt = transcript_prompts.user_prompt(
                data.product_summary,
                data.offer_summary,
                data.cta,
                location,
                taste_data,
               [voice.model_dump() for voice in voices],
                trends,
                slangs,
                forecast_data,
            )

            transcript_request = TranscriptRequest(
                user_prompt=json.dumps(user_prompt),
                with_forecast=data.use_weather,
                forecast_days=data.forecast_type,
                variations=1
            )
            
            transcript_results = await gpt.generate_transcripts(transcript_request)

        if not transcript_results or not transcript_results.results:
            raise ValueError("Transcript generation failed")

        # Prepare voice data for non-custom ads
        if not voice_data:
            voice_model = transcript_results.results[0].voice_model.lower()
            voice_dict = next(
                (v for v in voices if v.voice_name.lower() == voice_model),
                voices[-1] if voices else None
            )
            
            if not voice_dict:
                raise ValueError("No suitable voice found")
                
            voice_data = ensure_voice_data_object(voice_dict)
            voice_id = voice_data.voice_id

        # Generate music and speech concurrently
        musicgen = MusicGen()
        music_prompt = transcript_results.results[0].music_prompt

        tasks = [
            asyncio.create_task(generate_ad_speech(
                websocket,
                index, 
                location.name, 
                transcript_results, 
                voice_data
            )),
            asyncio.create_task(musicgen.generate_background_music(data, music_prompt, 40))
        ]

        speech_data, music_buffer = await asyncio.gather(*tasks)

        if not speech_data.get("speech_buffer"):
            raise ValueError("Speech generation failed")
            
        if not music_buffer:
            raise ValueError("Music generation failed")
        
        # Mix audio
        async with create_audio_mixer() as mixer:
            merged_buffer = await mixer.merge_music_with_speech(
                speech_data["speech_buffer"],
                music_buffer
            )

        if not merged_buffer:
            raise ValueError("Audio mixing failed")

        # Prepare final response
        merged_data = {
            "type": "merged_audio_done",
            "merged_buffer": merged_buffer
        }

        response_data = {**speech_data, **merged_data}
        await websocket.send_json(response_data)
        
        # Clean up custom voice if successful
        if data.ad_type == 'custom' and voice_id:
            await _cleanup_custom_voice(voice_id, slot_manager, 'completed')
            
    except Exception as e:
        logger.error(f"Error in [process_ad] for index {index}: {e}")
        
        # Clean up custom voice on error
        if data.ad_type == 'custom' and voice_id:
            await _cleanup_custom_voice(voice_id, slot_manager, 'error')
        
        # Send error to websocket
        error_response = {"type": "error", "index": index, "message": str(e)}
        await websocket.send_json(error_response)
        raise

async def _cleanup_custom_voice(voice_id: str, slot_manager: VoiceSlotManager, status: str):
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

@ws.websocket("/ws/generate")
async def generate_audio_ads(websocket: WebSocket):
    """Main websocket endpoint for generating audio ads."""
    await websocket.accept()

    try:
        # Receive and validate request
        data = await websocket.receive_json()
        ad_request = AdRequest(**data)
        
        # Validate locations
        if not ad_request.locations:
            raise ValueError("No locations provided")

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
        
        # Process all locations concurrently
        tasks = [
            asyncio.create_task(process_ad(websocket, i, ad_request, voices)) 
            for i in range(len(ad_request.locations))
        ]

        # Wait for all tasks to complete, but don't fail if individual tasks fail
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check results and send individual errors if needed
        has_success = False
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Task {i} failed: {result}")
                # Error already sent by process_ad function
            else:
                has_success = True

        if not has_success:
            raise ValueError("All audio ad generations failed")

        # Send completion signal
        await websocket.send_json({"type": "done"})
        
    except Exception as e:
        logger.error(f"Error in [generate_audio_ads]: {e}")
        await websocket.send_json({"type": "error", "message": str(e)})
    finally:
        # Ensure websocket is closed properly
        try:
            await websocket.close()
        except:
            pass