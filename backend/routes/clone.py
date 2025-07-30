import logging
import random
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from schemas.clone_schemas import ReservationResponse, CloningSentencesResponse
from utils.redis_utils import VoiceSlotManager
from utils.constants import cloning_sentences
from utils.deepl_utils import translate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

clone_router = APIRouter()

@clone_router.post("/reservations/create", response_model=ReservationResponse)
async def create_slot_reservation():
    try:
        slot_manager = VoiceSlotManager()
        is_available = await slot_manager.has_available_slot()

        if not is_available:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"created": False, "detail": "No available slots"}
            )
        
        reservation_id = await slot_manager.reserve_slot()

        if not reservation_id:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"created": False, "detail": "Failed to reserve slot"}
            )
        
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"reservation_id": reservation_id, "created": True}
        )
    except Exception as e:
        logger.error(f"Error creating Reservation: {e}")
        raise HTTPException(status_code=500, detail="Error creating Reservation")
    
@clone_router.get("/sentences", response_model=CloningSentencesResponse)
async def get_voice_training_sentences(language_code: str):
    try:
        sentences = random.sample(cloning_sentences, 5)
        sentence_string = "\n\n".join(sentences)
        if language_code.lower() == "en":
            return {
                "sentences": sentences,
                "language": "EN"
            }
        
        translated_str: str = await translate(
            sentence_string, 
            "EN-US", 
            language_code.upper()
        )
        
        if not translated_str:
            raise HTTPException(status_code=500, detail="Error translating sentences to target language")

        return {
            "sentences": translated_str.split("\n\n"),
            "language": language_code.upper()
        } 
    except Exception as e:
        logger.error(f"Error getting voice training sentences: {e}")
        raise HTTPException(status_code=500, detail="Error getting voice training sentences")
