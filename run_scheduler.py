"""
트리거 스케줄러 실행 스크립트
백그라운드에서 스케줄된 트리거를 실행합니다.
"""
import asyncio
import signal
import sys

from src.triggers import TriggerScheduler
from src.utils import get_logger

logger = get_logger("scheduler_main")

scheduler = None

def signal_handler(sig, frame):
    """Handle shutdown signals"""
    logger.info("Shutdown signal received")
    if scheduler:
        asyncio.create_task(scheduler.stop())
    sys.exit(0)

async def main():
    """Main function"""
    global scheduler
    
    logger.info("=" * 60)
    logger.info("Workflow Trigger Scheduler")
    logger.info("=" * 60)
    
    # Initialize scheduler
    scheduler = TriggerScheduler(check_interval=60)  # Check every 60 seconds
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start scheduler
    await scheduler.start()
    
    logger.info("Scheduler is running. Press Ctrl+C to stop.")
    
    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        await scheduler.stop()

if __name__ == "__main__":
    asyncio.run(main())

