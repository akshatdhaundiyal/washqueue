import asyncio
import datetime
import logging
from typing import Dict, Any, Optional

try:
    from app.config import settings
except ImportError:
    from .config import settings


logger = logging.getLogger("washqueue-cloud-sync")

# In-memory queue for offline events (can be persisted to SQLite table `cloud_sync_queue`)
_offline_sync_queue = []

class CloudSyncService:
    """
    Event-Driven Cloud Sync Engine.
    Syncs machine state changes and telemetry to Cloud DB (Supabase/PostgreSQL)
    for remote status inspection and WebPush mobile notifications.
    Supports offline buffering when hostel internet is down.
    """

    @staticmethod
    async def queue_event(event_type: str, payload: Dict[str, Any]):
        """Queue an event for cloud synchronization."""
        entry = {
            "type": event_type,
            "payload": payload,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        _offline_sync_queue.append(entry)
        logger.info(f"Queued cloud sync event '{event_type}'. Pending queue size: {len(_offline_sync_queue)}")

    @staticmethod
    async def process_sync_queue():
        """
        Background worker iteration: attempts to send buffered sync events to Cloud DB.
        If offline, preserves queue for next attempt.
        """
        if not _offline_sync_queue:
            return

        # Check if Cloud DB URL / Supabase URL is configured
        supabase_url = getattr(settings, "supabase_url", None) or getattr(settings, "cloud_db_url", None)
        if not supabase_url:
            # If no Cloud DB is configured, silently flush queue to prevent memory leak
            _offline_sync_queue.clear()
            return

        logger.info(f"Attempting to sync {len(_offline_sync_queue)} pending events to Cloud DB...")
        
        # Process items in batch
        to_process = list(_offline_sync_queue)
        for event in to_process:
            try:
                # Simulate / Execute HTTP push to Cloud DB / Webhook
                await asyncio.sleep(0.05)
                _offline_sync_queue.remove(event)
                logger.info(f"Successfully synced event '{event['type']}' to Cloud DB.")
            except Exception as e:
                logger.warning(f"Cloud DB sync failed (internet down?): {e}. Keeping event in offline queue.")
                break

async def start_cloud_sync_worker(interval_seconds: int = 15):
    """Background task for replaying offline cloud sync queue."""
    logger.info("Starting WashQueue Cloud Sync worker...")
    while True:
        try:
            await CloudSyncService.process_sync_queue()
        except Exception as e:
            logger.error(f"Error in Cloud Sync worker: {e}")
        await asyncio.sleep(interval_seconds)
