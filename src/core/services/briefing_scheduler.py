import logging
import asyncio
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Callable, List
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.schedulers.base import SchedulerNotRunningError
from .briefing_generator import BriefingGenerator, BriefingConfiguration

# Configure specific logger for briefing system
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Add a stream handler if it doesn't exist
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

class BriefingSchedulerConfiguration:
    """Configuration for the briefing scheduler."""
    def __init__(self,
                refresh_interval_seconds: int = 3600,  # Default: refresh every hour
                generation_interval_hours: int = 24,   # Default: new briefing every day at same time
                daily_reset_hour: int = 0,            # Default: reset daily counters at midnight UTC
                max_retries: int = 3,                 # Maximum retries for failed operations
                retry_delay_seconds: int = 60,        # Delay between retries
                enable_websocket_notifications: bool = True):  # Whether to send WebSocket notifications
        self.refresh_interval_seconds = refresh_interval_seconds
        self.generation_interval_hours = generation_interval_hours
        self.daily_reset_hour = daily_reset_hour
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds
        self.enable_websocket_notifications = enable_websocket_notifications

class BriefingScheduler:
    """Scheduler for automatic briefing generation and updates."""
    
    def __init__(self,
                generator: Optional[BriefingGenerator] = None,
                config: Optional[BriefingSchedulerConfiguration] = None,
                feed_watcher_ref=None):
        """Initialize the briefing scheduler.
        
        Args:
            generator: BriefingGenerator instance to use
            config: Scheduler configuration
            feed_watcher_ref: Reference to the feed_watcher for metrics integration
        """
        self.config = config or BriefingSchedulerConfiguration()
        self.generator = generator or BriefingGenerator()
        self.scheduler = None
        self.feed_watcher = feed_watcher_ref
        self.current_briefing = None
        self.last_generated_time = None
        self.last_refreshed_time = None
        self.notification_callbacks = []
        self._jobs = {}  # Track scheduled jobs
        self.metrics = {
            'total_briefings': 0,
            'last_generation_time': None,
            'flash_alerts_today': 0,
            'flash_alerts_total': 0,
            'generation_time': 0.0,
            'hotspots': [],
            'failed_generations': 0
        }
        logger.info("BriefingScheduler initialized")
        
    def register_notification_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Register a callback for notifications when briefings are updated.
        
        Args:
            callback: Function that receives notification type and payload
        """
        self.notification_callbacks.append(callback)
        logger.debug(f"Registered notification callback: {callback.__name__}")
        
    def send_notification(self, notification_type: str, payload: Dict[str, Any]):
        """Send a notification to all registered callbacks.
        
        Args:
            notification_type: Type of notification (e.g., 'briefing_updated', 'flash_alert')
            payload: Data payload for the notification
        """
        if self.config.enable_websocket_notifications:
            for callback in self.notification_callbacks:
                try:
                    callback(notification_type, payload)
                    logger.debug(f"Sent {notification_type} notification")
                except Exception as e:
                    logger.error(f"Error in notification callback: {str(e)}")
    
    async def start(self):
        """Start the briefing scheduler."""
        if self.scheduler is not None:
            logger.warning("⚠️ Scheduler is already running")
            return

        try:
            logger.info("🚀 Initializing briefing scheduler...")
            
            if not self.generator:
                raise ValueError("🔴 BriefingGenerator not initialized")
                
            self.scheduler = AsyncIOScheduler()
            logger.info("✨ Created new AsyncIOScheduler")
            
            # Schedule daily briefing generation
            try:
                job = self.scheduler.add_job(
                    self.generate_new_daily_briefing,
                    IntervalTrigger(hours=self.config.generation_interval_hours),
                    id='daily_briefing_generation',
                    replace_existing=True
                )
                self._jobs['daily_briefing_generation'] = job
                logger.info(f"📅 Scheduled daily briefing generation every {self.config.generation_interval_hours} hours")
            except Exception as e:
                logger.error(f"🔴 Failed to schedule daily briefing generation: {str(e)}", exc_info=True)
                raise
            
            # Schedule hourly briefing refresh
            try:
                job = self.scheduler.add_job(
                    self.refresh_current_briefing,
                    IntervalTrigger(seconds=self.config.refresh_interval_seconds),
                    id='briefing_refresh',
                    replace_existing=True
                )
                self._jobs['briefing_refresh'] = job
                logger.info(f"🔄 Scheduled briefing refresh every {self.config.refresh_interval_seconds} seconds")
            except Exception as e:
                logger.error(f"🔴 Failed to schedule briefing refresh: {str(e)}", exc_info=True)
                raise
            
            # Schedule reset of daily counters
            try:
                job = self.scheduler.add_job(
                    self.reset_daily_metrics,
                    IntervalTrigger(days=1, start_date=f'2023-01-01 {self.config.daily_reset_hour}:00:00'),
                    id='reset_daily_metrics',
                    replace_existing=True
                )
                self._jobs['reset_daily_metrics'] = job
                logger.info(f"⏰ Scheduled daily metrics reset at hour {self.config.daily_reset_hour}")
            except Exception as e:
                logger.error(f"🔴 Failed to schedule metrics reset: {str(e)}", exc_info=True)
                raise
            
            # Start the scheduler
            try:
                self.scheduler.start()
                logger.info("✅ Briefing scheduler started successfully")
            except Exception as e:
                logger.error(f"🔴 Failed to start scheduler: {str(e)}", exc_info=True)
                raise
            
            # Generate initial briefing
            logger.info("📊 Generating initial briefing...")
            try:
                await self.generate_new_daily_briefing()
                logger.info("✅ Initial briefing generated successfully")
            except Exception as e:
                logger.error(f"🔴 Failed to generate initial briefing: {str(e)}", exc_info=True)
                # Don't raise here, allow scheduler to continue running
            
        except Exception as e:
            logger.error(f"🔴 Critical error in briefing scheduler startup: {str(e)}", exc_info=True)
            if self.scheduler:
                await self.stop()
            raise
        
    async def stop(self):
        """Stop the briefing scheduler."""
        if self.scheduler is not None:
            try:
                # Remove all jobs first
                for job_id in list(self._jobs.keys()):
                    self.scheduler.remove_job(job_id)
                    logger.info(f"Removed job: {job_id}")
                    del self._jobs[job_id]
                
                # Now shutdown the scheduler
                await asyncio.get_event_loop().run_in_executor(None, self.scheduler.shutdown)
                logger.info("Briefing scheduler stopped cleanly")
            except SchedulerNotRunningError:
                logger.warning("Scheduler was already stopped")
            except Exception as e:
                logger.error(f"Error stopping scheduler: {str(e)}")
            finally:
                self.scheduler = None
        else:
            logger.warning("Scheduler was not running")

    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get current status of the scheduler and its jobs."""
        status = {
            'is_running': False,
            'job_count': 0,
            'jobs': {},
            'last_generated': self.last_generated_time.isoformat() if self.last_generated_time else None,
            'last_refreshed': self.last_refreshed_time.isoformat() if self.last_refreshed_time else None,
            'next_generation': None,
            'next_refresh': None
        }
        
        if self.scheduler and self.scheduler.running:
            status['is_running'] = True
            status['job_count'] = len(self._jobs)
            
            for job_id, job in self._jobs.items():
                next_run = job.next_run_time.isoformat() if job.next_run_time else None
                status['jobs'][job_id] = {
                    'next_run': next_run,
                    'trigger': str(job.trigger)
                }
                
                if job_id == 'daily_briefing_generation':
                    status['next_generation'] = next_run
                elif job_id == 'briefing_refresh':
                    status['next_refresh'] = next_run
        
        return status

    async def generate_new_daily_briefing(self):
        """Generate a new daily briefing."""
        logger.info("📝 Starting daily briefing generation...")
        
        try:
            # Set time window for briefing
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=24)
            
            logger.info(f"🕒 Generating briefing for window: {start_time.isoformat()} to {end_time.isoformat()}")
            
            # Generate briefing
            briefing, generation_time, flash_alerts_count, hotspots = await self.generator.generate_daily_briefing(
                start_time=start_time,
                end_time=end_time
            )
            
            if not briefing:
                raise ValueError("Empty briefing returned from generator")
            
            # Update metrics
            self.metrics['total_briefings'] += 1
            self.metrics['last_generation_time'] = end_time
            self.metrics['flash_alerts_today'] = flash_alerts_count
            self.metrics['flash_alerts_total'] += flash_alerts_count
            self.metrics['generation_time'] = generation_time
            self.metrics['hotspots'] = hotspots
            
            # Store current briefing
            self.current_briefing = briefing
            self.last_generated_time = end_time
            
            # Update feed watcher metrics
            if self.feed_watcher:
                # No need to process hotspot names since hotspots are already strings
                self.feed_watcher.update_briefing_metrics(
                    briefing_generated=True,
                    refresh_success=False,
                    generation_time=generation_time,
                    flash_alerts=flash_alerts_count,
                    regional_hotspots=hotspots
                )
            
            # Send notification
            self.send_notification('new_briefing_generated', {
                'timestamp': end_time.isoformat(),
                'generation_time': generation_time,
                'flash_alerts': flash_alerts_count
            })
            
            logger.info(f"✅ Daily briefing generated successfully with {flash_alerts_count} flash alerts")
            logger.info(f"⚡ Generation time: {generation_time:.2f}s")
            logger.info(f"🌍 Active hotspots: {', '.join(hotspots) if hotspots else 'None'}")
            
            return briefing
            
        except Exception as e:
            logger.error(f"🔴 Error generating daily briefing: {str(e)}", exc_info=True)
            self.metrics['failed_generations'] += 1
            
            if self.feed_watcher:
                self.feed_watcher.update_briefing_metrics(
                    briefing_generated=False,
                    refresh_success=False,
                    generation_time=0.0,
                    flash_alerts=0
                )
            return None

    async def refresh_current_briefing(self):
        """Refresh the current briefing with new information."""
        if not self.current_briefing:
            # No current briefing to refresh, generate a new one instead
            await self.generate_new_daily_briefing()
            return
            
        try:
            logger.info("Refreshing current briefing")
            
            # Refresh the briefing
            updated_briefing, refresh_time, flash_alerts_added, hotspots = await self.generator.refresh_briefing(
                self.current_briefing
            )
            
            # Store the updated briefing
            self.current_briefing = updated_briefing
            self.last_refreshed_time = datetime.now(timezone.utc)
            
            # Update feed watcher metrics
            if self.feed_watcher:
                hotspot_names = hotspots if isinstance(hotspots, list) else []
                self.feed_watcher.update_briefing_metrics(
                    briefing_generated=False,  # This is a refresh, not a new generation
                    refresh_success=True,
                    refresh_time=refresh_time,
                    flash_alerts=flash_alerts_added,
                    regional_hotspots=hotspot_names
                )
            
            # Only notify if there are new flash alerts or significant changes
            if flash_alerts_added > 0:
                self.send_notification('new_flash_alerts', {
                    'timestamp': self.last_refreshed_time.isoformat(),
                    'count': flash_alerts_added,
                    'alerts': updated_briefing.get('flash', {}).get('items', [])[:flash_alerts_added]
                })
            
            # Always send a simple refresh notification
            self.send_notification('briefing_refreshed', {
                'timestamp': self.last_refreshed_time.isoformat(),
                'changes_detected': flash_alerts_added > 0
            })
            
            logger.info(
                f"Briefing refreshed in {refresh_time:.2f}s with {flash_alerts_added} new flash alerts"
            )
            
            return updated_briefing
            
        except Exception as e:
            logger.error(f"Error refreshing briefing: {str(e)}", exc_info=True)
            
            # Update feed watcher metrics on failure
            if self.feed_watcher:
                self.feed_watcher.update_briefing_metrics(
                    briefing_generated=False,
                    refresh_success=False,
                    refresh_time=0.0,
                    flash_alerts=0
                )
                
            return self.current_briefing  # Return the unchanged current briefing
    
    def reset_daily_metrics(self):
        """Reset daily metrics at midnight UTC."""
        logger.info("Resetting daily briefing metrics")
        
        if self.feed_watcher:
            self.feed_watcher.reset_daily_briefing_metrics()
            
    def get_current_briefing(self) -> Dict[str, Any]:
        """Get the current briefing data.
        
        Returns:
            The current briefing or empty dict if none exists
        """
        return self.current_briefing or {
            'metadata': {
                'generated_at': None,
                'total_articles': 0,
                'regional_hotspots': []
            },
            'executive_summary': {
                'text': 'No briefing has been generated yet.',
                'key_points': []
            },
            'flash': {'items': []},
            'summary': {'items': [], 'regions': []},
            'context': {'items': [], 'categories': []}
        }
        
    async def maintain_24h_rolling_window(self, start_timestamp=None, end_timestamp=None):
        """Maintain a 24-hour rolling window for the briefing.
        
        This updates the briefing to focus on the most recent 24 hours,
        which can be different than just refreshing with new content.
        
        Args:
            start_timestamp: Optional explicit start time for window
            end_timestamp: Optional explicit end time for window
        """
        # Default to last 24 hours if not specified
        if end_timestamp is None:
            end_timestamp = datetime.now(timezone.utc)
        if start_timestamp is None:
            start_timestamp = end_timestamp - timedelta(hours=24)
            
        try:
            logger.info(f"Updating briefing window to {start_timestamp} -> {end_timestamp}")
            
            # Generate a new briefing with the specified window
            briefing, generation_time, flash_count, hotspots = await self.generator.generate_daily_briefing(
                start_time=start_timestamp,
                end_time=end_timestamp
            )
            
            # Store the updated briefing
            self.current_briefing = briefing
            self.last_refreshed_time = datetime.now(timezone.utc)
            
            # Update metrics
            if self.feed_watcher:
                hotspot_names = [r['name'] for r in hotspots] if hotspots else []
                self.feed_watcher.update_briefing_metrics(
                    briefing_generated=True,  # This is essentially a regeneration
                    refresh_success=True,
                    generation_time=generation_time,
                    refresh_time=generation_time,
                    flash_alerts=flash_count,
                    regional_hotspots=hotspot_names
                )
                
            # Notify subscribers of window update
            self.send_notification('briefing_window_updated', {
                'timestamp': self.last_refreshed_time.isoformat(),
                'window_start': start_timestamp.isoformat(),
                'window_end': end_timestamp.isoformat(),
                'flash_count': flash_count
            })
            
            logger.info(f"Briefing window updated with {flash_count} flash alerts and {len(hotspots)} hotspots")
            
            return briefing
            
        except Exception as e:
            logger.error(f"Error updating briefing window: {str(e)}", exc_info=True)
            return self.current_briefing  # Return unchanged on error