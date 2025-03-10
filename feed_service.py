"""Stand-alone feed watcher service."""
import asyncio
import logging
import ssl
import time
from src.core.feed_watcher import FeedWatcher, FeedConfiguration
from src.core.priority_feed_processor import PriorityFeedProcessor
from src.core.services.briefing_generator import BriefingGenerator, BriefingConfiguration
from src.core.services.briefing_scheduler import BriefingScheduler, BriefingSchedulerConfiguration
from config.settings import (
    FEED_POLL_INTERVAL, MAX_CONCURRENT_FEEDS,
    BATCH_SIZE, MAX_ENTRIES_PER_FEED,
    API_CALLS_PER_MINUTE, API_CALLS_PER_DAY
)
from src.database.models import init_db, init_briefing_tables

# Configure logging - more selective about what gets logged
logging.basicConfig(
    level=logging.ERROR,  # Set global level to ERROR
    format='%(message)s'  # Simplified format without timestamps and logger names
)

# Only allow status messages from main logger
logging.getLogger(__name__).setLevel(logging.INFO)

# Silence all other loggers
for name in logging.root.manager.loggerDict:
    if name != __name__:
        logging.getLogger(name).setLevel(logging.ERROR)

# Configure specific loggers
logging.getLogger('google_genai').setLevel(logging.ERROR)
logging.getLogger('src.core.feed_watcher').setLevel(logging.INFO)
logging.getLogger('src.core.services.briefing_scheduler').setLevel(logging.INFO)
logging.getLogger('src.core.priority_feed_processor').setLevel(logging.ERROR)
logging.getLogger('src.utils.ai').setLevel(logging.ERROR)
logging.getLogger('asyncio').setLevel(logging.ERROR)
logging.getLogger('aiohttp').setLevel(logging.ERROR)
logging.getLogger('urllib3').setLevel(logging.ERROR)

logger = logging.getLogger(__name__)

def load_feed_urls():
    """Load feed URLs from feeds.txt"""
    try:
        with open("feeds.txt", "r") as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            logger.info(f"📋 Loaded {len(urls)} feed URLs from feeds.txt")
            return urls
    except Exception as e:
        logger.error(f"❌ Error loading feeds: {e}")
        return []

async def run_feed_watcher():
    """Initialize and run the feed watcher service"""
    # Initialize database tables
    init_db()  # This now handles briefing tables initialization internally
    logger.info("📊 Database tables initialized")
    
    config = FeedConfiguration(
        max_concurrent_feeds=MAX_CONCURRENT_FEEDS,
        min_poll_interval=FEED_POLL_INTERVAL[0],
        max_poll_interval=FEED_POLL_INTERVAL[1],
        connect_timeout=30.0,
        total_timeout=60.0,
        batch_size=BATCH_SIZE,
        max_entries_per_feed=MAX_ENTRIES_PER_FEED
    )
    
    # Configure briefing system
    briefing_config = BriefingConfiguration(
        max_flash_items=10,
        flash_sentiment_threshold=0.65,
        refresh_interval_seconds=3600,  # Hourly refresh
        summary_item_limit=25,
        context_item_limit=50,
        hotspot_threshold=10
    )
    
    scheduler_config = BriefingSchedulerConfiguration(
        refresh_interval_seconds=3600,  # Hourly refresh
        generation_interval_hours=24,    # Daily new briefing
        daily_reset_hour=0,             # Reset at midnight UTC
        max_retries=3
    )
    
    max_retries = 3
    retry_delay = 5
    
    logger.info("🚀 Starting feed watcher service")
    logger.info(f"""⚙️ Configuration:
    - Poll interval: {FEED_POLL_INTERVAL[0]}-{FEED_POLL_INTERVAL[1]}s
    - Max concurrent feeds: {MAX_CONCURRENT_FEEDS}
    - Batch size: {BATCH_SIZE}
    - Max entries per feed: {MAX_ENTRIES_PER_FEED}
    - API limits: {API_CALLS_PER_MINUTE}/min, {API_CALLS_PER_DAY}/day
    - Briefing refresh: Every {scheduler_config.refresh_interval_seconds//60} minutes
    - New briefing: Every {scheduler_config.generation_interval_hours} hours""")
    
    # Configure SSL context with more lenient verification for RSS feeds
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False  # Many RSS feeds have mismatched hostnames
    ssl_context.verify_mode = ssl.CERT_NONE  # Temporarily disable strict cert verification
    
    # Note: In production, you should use proper certificate verification
    # This is a temporary solution to handle feeds with SSL issues
    logger.warning("⚠️ SSL certificate verification disabled for testing")
    
    # Load system root certificates
    try:
        ssl_context.load_default_certs()
    except Exception as e:
        logger.warning(f"⚠️ Could not load system certificates: {e}")
    
    for attempt in range(max_retries):
        try:
            feed_watcher = FeedWatcher(config, ssl_context=ssl_context)
            await feed_watcher.init()
            
            # Initialize briefing system
            briefing_generator = BriefingGenerator(briefing_config)
            briefing_scheduler = BriefingScheduler(
                generator=briefing_generator,
                config=scheduler_config,
                feed_watcher_ref=feed_watcher  # Pass reference for metrics
            )
            
            # Start the briefing scheduler
            await briefing_scheduler.start()
            logger.info("📋 Briefing system initialized and scheduler started")
            
            feed_urls = load_feed_urls()
            if not feed_urls:
                logger.error("❌ No feed URLs loaded. Check feeds.txt file.")
                return
                
            # Start feed watching tasks
            feed_tasks = []
            for url in feed_urls:
                task = asyncio.create_task(feed_watcher.watch_feed(url))
                feed_tasks.append(task)
            
            logger.info(f"✨ Feed watcher initialized with {len(feed_urls)} feeds")
            logger.info("▶️ Starting feed monitoring...")
            
            try:
                # Create integrated status update function
                async def update_status_display():
                    display_interval = 1  # Update every second
                    last_update = 0
                    
                    # ANSI escape codes for terminal control
                    CLEAR = '\033[2J'        # Clear entire screen
                    HOME = '\033[H'          # Move cursor to home position
                    CLEAR_DOWN = '\033[J'    # Clear screen from cursor down
                    ALT_SCREEN = '\033[?1049h'  # Switch to alternate screen buffer
                    MAIN_SCREEN = '\033[?1049l'  # Return to main screen buffer
                    SAVE_CURSOR = '\033[s'    # Save cursor position
                    RESTORE_CURSOR = '\033[u' # Restore cursor position
                    
                    try:
                        # Switch to alternate screen buffer
                        print(ALT_SCREEN + CLEAR + HOME, end='', flush=True)
                        
                        while True:
                            current_time = time.time()
                            if current_time - last_update >= display_interval:
                                # Get scheduler status for briefing system metrics
                                scheduler_status = briefing_scheduler.get_scheduler_status()
                                feed_watcher.briefing_status = scheduler_status
                                
                                # Save cursor position before status update
                                print(SAVE_CURSOR, end='', flush=True)
                                
                                # Move cursor to home position and clear screen from cursor down
                                print(HOME + CLEAR_DOWN, end='', flush=True)
                                
                                # Display status (this will now write at cursor position)
                                feed_watcher.print_status()
                                
                                # Restore cursor position to preserve any error messages
                                print(RESTORE_CURSOR, end='', flush=True)
                                
                                last_update = current_time
                                
                            await asyncio.sleep(0.1)  # Small sleep to prevent CPU spinning
                    finally:
                        # Return to main screen buffer on exit
                        print(MAIN_SCREEN, end='', flush=True)
                
                # Create and run tasks
                logger.info("Starting feed monitoring tasks...")
                status_task = asyncio.create_task(update_status_display())
                
                # Run all tasks
                await asyncio.gather(status_task, *feed_tasks)
                
            except asyncio.CancelledError:
                logger.info("Shutting down gracefully...")
                await briefing_scheduler.stop()
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                raise
            
        except Exception as e:
            logger.error(f"❌ Error initializing services (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                logger.info(f"⏳ Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
            else:
                logger.error("❌ Max retries exceeded. Exiting.")
                raise
        finally:
            if 'briefing_scheduler' in locals():
                await briefing_scheduler.stop()
            if 'feed_watcher' in locals():
                await feed_watcher.close()

if __name__ == "__main__":
    try:
        # Initialize database and briefing tables
        init_db()
        logger.info("📦 Database and briefing tables initialized")
        
        # Run the feed watcher
        asyncio.run(run_feed_watcher())
    except KeyboardInterrupt:
        logger.info("\n🛑 Feed watcher service stopped")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        exit(1)