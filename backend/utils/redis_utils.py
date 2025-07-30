import json
import logging
import os
import secrets
import string
from redis.asyncio import Redis
from dotenv import load_dotenv
from typing import Literal, Optional, List, Dict
from contextlib import asynccontextmanager
import time

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VoiceSlotManager:
    def __init__(self, max_slots: int = 4, slot_ttl: int = 3600):
        self.max_slots = max_slots
        self.slot_ttl = slot_ttl
        self.client: Optional[Redis] = None
        self.slots_key = "voice_slots"
        self.slot_prefix = "voice_slot:"
        self._connection_pool = None

    async def initialize(self):
        """Initialize Redis connection with connection pooling"""
        try:
            redis_url = os.getenv("REDIS_URL")
            if not redis_url:
                raise ValueError("REDIS_URL environment variable not set")
            
            self.client = await Redis.from_url(
                redis_url,
                decode_responses=True,
                max_connections=20,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            await self.client.ping()
            logger.info("Successfully connected to Redis")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis connection: {e}")
            raise

    async def close(self):
        """Clean up Redis connection"""
        if self.client:
            await self.client.close()

    async def _ensure_connection(self):
        """Ensure Redis connection is active"""
        if not self.client:
            await self.initialize()
            return

        try:
            await self.client.ping()
        except Exception as e:
            logger.warning(f"Redis connection lost, reconnecting: {e}")
            await self.initialize()

    async def has_available_slot(self, reservation_id: Optional[str] = None) -> bool:
        """
        Check if there's an available slot or if a reservation ID is valid
        
        Args:
            reservation_id: Optional reservation ID to validate
            
        Returns:
            bool: True if slot is available or reservation is valid
        """
        try:
            await self._ensure_connection()
            
            # If reservation_id is provided, check if it's valid
            if reservation_id:
                reservation_key = f"reservation:{reservation_id}"
                reservation_data = await self.client.get(reservation_key)
                return reservation_data is not None
            
            # Otherwise, check if there are available slots
            current_slots = await self.client.smembers(self.slots_key)
            await self._cleanup_expired_slots(current_slots)
            
            current_count = await self.client.scard(self.slots_key)
            return current_count < self.max_slots
            
        except Exception as e:
            logger.error(f"Error checking slot availability: {e}")
            return False

    async def reserve_slot(self, reservation_ttl: int = 300) -> Optional[str]:
        """
        Reserve a slot and return a reservation ID (ticket)
        
        Args:
            reservation_ttl: Reservation expiry time in seconds (default 5 minutes)
            
        Returns:
            str: 8-character reservation ID if successful, None if no slots available
        """
        try:
            await self._ensure_connection()
            
            # Check if slot is available
            if not await self.has_available_slot():
                return None
            
            # Generate 8-character random ID
            reservation_id = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
            reservation_key = f"reservation:{reservation_id}"
            
            # Store reservation with TTL
            reservation_data = {
                "reservation_id": reservation_id,
                "created_at": int(time.time()),
                "expires_at": int(time.time()) + reservation_ttl
            }
            
            # Use atomic operation to reserve only if slot is still available
            async with self.client.pipeline() as pipe:
                try:
                    await pipe.watch(self.slots_key)
                    
                    # Double-check availability
                    current_slots = await self.client.smembers(self.slots_key)
                    await self._cleanup_expired_slots(current_slots)
                    current_count = await self.client.scard(self.slots_key)
                    
                    if current_count >= self.max_slots:
                        await pipe.unwatch()
                        return None
                    
                    # Create reservation
                    pipe.multi()
                    pipe.setex(reservation_key, reservation_ttl, json.dumps(reservation_data))
                    await pipe.execute()
                    
                    logger.info(f"Created reservation: {reservation_id}")
                    return reservation_id
                    
                except Exception as e:
                    await pipe.unwatch()
                    logger.error(f"Error during reservation: {e}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error reserving slot: {e}")
            return None

    @asynccontextmanager
    async def acquire_slot_with_reservation(self, voice_id: str, reservation_id: str, timeout: int = 30):
        """
        Atomic slot acquisition using a reservation ID
        
        Args:
            voice_id: Unique identifier for the voice
            reservation_id: Valid reservation ID obtained from reserve_slot()
            timeout: Maximum time to wait for slot acquisition (seconds)
            
        Yields:
            bool: True if slot was acquired successfully with valid reservation
        """
        acquired = False
        reservation_key = f"reservation:{reservation_id}"
        
        try:
            await self._ensure_connection()
            
            # Validate reservation
            reservation_data = await self.client.get(reservation_key)
            if not reservation_data:
                logger.warning(f"Invalid reservation ID: {reservation_id}")
                yield False
                return
            
            # Try to acquire slot atomically
            acquired = await self._try_acquire_slot_with_reservation(voice_id, reservation_id)
            if acquired:
                logger.info(f"Acquired slot for voice_id: {voice_id} with reservation: {reservation_id}")
                yield True
                return
            else:
                logger.warning(f"Failed to acquire slot with reservation: {reservation_id}")
                yield False
                
        except Exception as e:
            logger.error(f"Error in acquire_slot_with_reservation: {e}")
            yield False
            
        finally:
            if acquired:
                await self._release_slot(voice_id)
                logger.info(f"Released slot for voice_id: {voice_id}")

    async def _try_acquire_slot_with_reservation(self, voice_id: str, reservation_id: str) -> bool:
        """
        Atomically try to acquire a slot using a reservation ID
        """
        reservation_key = f"reservation:{reservation_id}"
        
        async with self.client.pipeline() as pipe:
            try:
                while True:
                    # Watch both slots and reservation
                    await pipe.watch(self.slots_key, reservation_key)
                    
                    # Validate reservation still exists
                    reservation_data = await self.client.get(reservation_key)
                    if not reservation_data:
                        await pipe.unwatch()
                        return False
                    
                    # Get current slots and clean up expired ones
                    current_slots = await self.client.smembers(self.slots_key)
                    await self._cleanup_expired_slots(current_slots)
                    current_slots = await self.client.smembers(self.slots_key)
                    
                    # Check if slot is available (should be due to reservation)
                    if len(current_slots) >= self.max_slots:
                        await pipe.unwatch()
                        return False
                    
                    # Acquire slot and consume reservation atomically
                    pipe.multi()
                    pipe.sadd(self.slots_key, voice_id)
                    pipe.delete(reservation_key)  # Consume the reservation
                    
                    # Set slot data with TTL
                    slot_data = {
                        "voice_id": voice_id,
                        "status": "pending",
                        "timestamp": int(time.time()),
                        "expires_at": int(time.time()) + self.slot_ttl,
                        "reservation_id": reservation_id
                    }
                    
                    pipe.setex(
                        f"{self.slot_prefix}{voice_id}", 
                        self.slot_ttl, 
                        json.dumps(slot_data)
                    )
                    
                    await pipe.execute()
                    return True
                    
            except Exception as e:
                logger.error(f"Error acquiring slot with reservation: {e}")
                await pipe.unwatch()
                return False
        
    async def _release_slot(self, voice_id: str):
        """Release a slot"""
        try:
            await self._ensure_connection()
            
            async with self.client.pipeline() as pipe:
                pipe.srem(self.slots_key, voice_id)
                pipe.delete(f"{self.slot_prefix}{voice_id}")
                await pipe.execute()
                
        except Exception as e:
            logger.error(f"Error releasing slot {voice_id}: {e}")

    async def update_slot_status(
        self, 
        voice_id: str, 
        status: Literal["pending", "processing", "completed", "error"]
    ):
        """Update slot status"""
        try:
            await self._ensure_connection()
            
            slot_key = f"{self.slot_prefix}{voice_id}"
            slot_data = await self.client.get(slot_key)
            
            if not slot_data:
                logger.warning(f"Slot {voice_id} not found for status update")
                return
            
            data = json.loads(slot_data)
            data["status"] = status
            data["updated_at"] = int(time.time())
            
            await self.client.setex(slot_key, self.slot_ttl, json.dumps(data))
            
        except Exception as e:
            logger.error(f"Error updating slot status: {e}")

    async def get_slot_info(self, voice_id: str) -> Optional[Dict]:
        """Get information about a specific slot"""
        try:
            await self._ensure_connection()
            
            slot_data = await self.client.get(f"{self.slot_prefix}{voice_id}")
            if slot_data:
                return json.loads(slot_data)
            return None
            
        except Exception as e:
            logger.error(f"Error getting slot info: {e}")
            return None

    async def get_all_slots(self) -> List[Dict]:
        """Get information about all active slots"""
        try:
            await self._ensure_connection()
            
            # Clean up expired slots first
            current_slots = await self.client.smembers(self.slots_key)
            await self._cleanup_expired_slots(current_slots)
            
            # Get updated slots
            active_slots = await self.client.smembers(self.slots_key)
            results = []
            
            for voice_id in active_slots:
                slot_data = await self.client.get(f"{self.slot_prefix}{voice_id}")
                if slot_data:
                    results.append(json.loads(slot_data))
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting all slots: {e}")
            return []

    async def get_available_slots(self) -> int:
        """Get number of available slots"""
        try:
            current_slots = await self.client.smembers(self.slots_key)
            await self._cleanup_expired_slots(current_slots)
            
            current_count = await self.client.scard(self.slots_key)
            return max(0, self.max_slots - current_count)
            
        except Exception as e:
            logger.error(f"Error getting available slots: {e}")
            return 0

    async def _cleanup_expired_slots(self, slots_to_check: set = None):
        """Clean up expired slots"""
        try:
            if slots_to_check is None:
                slots_to_check = await self.client.smembers(self.slots_key)
            
            current_time = int(time.time())
            expired_slots = []
            
            for voice_id in slots_to_check:
                slot_data = await self.client.get(f"{self.slot_prefix}{voice_id}")
                if not slot_data:
                    expired_slots.append(voice_id)
                    continue
                
                data = json.loads(slot_data)
                if current_time > data.get("expires_at", 0):
                    expired_slots.append(voice_id)
            
            # Remove expired slots
            if expired_slots:
                async with self.client.pipeline() as pipe:
                    for voice_id in expired_slots:
                        pipe.srem(self.slots_key, voice_id)
                        pipe.delete(f"{self.slot_prefix}{voice_id}")
                    await pipe.execute()
                
                logger.info(f"Cleaned up {len(expired_slots)} expired slots")
                
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    async def force_release_slot(self, voice_id: str):
        """Force release a slot (for error recovery)"""
        try:
            await self._release_slot(voice_id)
            logger.info(f"Force released slot: {voice_id}")
        except Exception as e:
            logger.error(f"Error force releasing slot: {e}")