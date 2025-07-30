import asyncio
import logging
import os
from typing import Optional
import deepl

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

translator = deepl.Translator(os.getenv("DEEPL_AUTH_KEY"))

async def translate(text: str, source: str, target: str) -> Optional[str]:
    try:
        result = await asyncio.to_thread(
            translator.translate_text,
            text,
            source_lang=source,
            target_lang=target,
            preserve_formatting=True
        )
        return result.text
    except Exception as e:
        logger.error(f"Error in [translate]: {e}")
        return None