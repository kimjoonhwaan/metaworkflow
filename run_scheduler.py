"""Background trigger scheduler service

이 스크립트는 백그라운드에서 실행되어 트리거를 주기적으로 확인하고 자동으로 실행합니다.

사용법:
    python run_scheduler.py
    
실행 중지:
    Ctrl+C
"""
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.triggers.scheduler import TriggerScheduler
from src.utils.logger import get_logger

logger = get_logger("trigger_scheduler_main")


async def main():
    """Start the trigger scheduler service"""
    logger.info("=" * 60)
    logger.info("🚀 Starting Trigger Scheduler Service")
    logger.info("=" * 60)
    logger.info("ℹ️ Check interval: 60 seconds")
    logger.info("ℹ️ Press Ctrl+C to stop gracefully")
    logger.info("=" * 60)
    
    scheduler = TriggerScheduler(check_interval=60)
    
    try:
        # Start scheduler
        await scheduler.start()
        logger.info("✅ Scheduler started successfully")
        logger.info("")
        
        # Keep running indefinitely
        while True:
            await asyncio.sleep(1)
    
    except KeyboardInterrupt:
        logger.info("")
        logger.info("⛔ Keyboard interrupt detected. Shutting down...")
        await scheduler.stop()
        logger.info("✅ Scheduler stopped gracefully")
        logger.info("=" * 60)
        sys.exit(0)
    
    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"❌ Fatal error in scheduler: {e}", exc_info=True)
        logger.error("=" * 60)
        try:
            await scheduler.stop()
        except:
            pass
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("✅ Scheduler terminated")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
        sys.exit(1)
