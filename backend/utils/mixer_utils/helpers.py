import asyncio
import io
from pathlib import Path
from typing import Union

import structlog

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

async def load_audio_from_file(file_path: Union[str, Path]) -> io.BytesIO:
    """Load audio file into BytesIO buffer"""
    try:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {path}")
        
        def _load_sync() -> io.BytesIO:
            with open(path, "rb") as f:
                data = f.read()
            return io.BytesIO(data)
        
        return await asyncio.to_thread(_load_sync)
    except Exception as e:
        logger.error("Error loading audio file", file_path=str(file_path), error=str(e))
        raise


async def save_audio_to_file(buffer: io.BytesIO, file_path: Union[str, Path]) -> None:
    """Save BytesIO buffer to audio file"""
    try:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        def _save_sync():
            buffer.seek(0)
            with open(path, "wb") as f:
                f.write(buffer.read())
        
        await asyncio.to_thread(_save_sync)
        logger.info("Audio saved successfully", file_path=str(path))
    except Exception as e:
        logger.error("Error saving audio file", file_path=str(file_path), error=str(e))
        raise