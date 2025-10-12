"""Trigger Scheduler - Background service for executing scheduled triggers"""
import asyncio
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from src.database.session import get_db_context
from src.triggers.trigger_manager import TriggerManager
from src.runners.workflow_runner import WorkflowRunner
from src.utils import get_logger

logger = get_logger("trigger_scheduler")


class TriggerScheduler:
    """Background scheduler for executing triggers"""
    
    def __init__(self, check_interval: int = 60):
        """Initialize scheduler
        
        Args:
            check_interval: Interval in seconds to check for due triggers
        """
        self.check_interval = check_interval
        self.running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the scheduler"""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        self.running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Trigger scheduler started")
    
    async def stop(self):
        """Stop the scheduler"""
        if not self.running:
            return
        
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("Trigger scheduler stopped")
    
    async def _run_loop(self):
        """Main scheduler loop"""
        logger.info(f"Scheduler loop started (check interval: {self.check_interval}s)")
        
        while self.running:
            try:
                await self._check_and_execute_triggers()
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}", exc_info=True)
            
            # Wait for next check
            await asyncio.sleep(self.check_interval)
    
    async def _check_and_execute_triggers(self):
        """Check for due triggers and execute them"""
        with get_db_context() as db:
            trigger_manager = TriggerManager(db)
            
            # Get due triggers
            due_triggers = trigger_manager.get_due_triggers()
            
            if not due_triggers:
                return
            
            logger.info(f"Found {len(due_triggers)} due triggers")
            
            # Execute each trigger
            for trigger in due_triggers:
                try:
                    logger.info(f"Executing trigger: {trigger.name} (ID: {trigger.id})")
                    
                    # Create workflow runner
                    runner = WorkflowRunner(db)
                    
                    # Execute workflow
                    execution = await runner.execute_workflow(
                        workflow_id=trigger.workflow_id,
                        trigger_id=trigger.id,
                    )
                    
                    logger.info(
                        f"Trigger execution completed: {trigger.id} -> {execution.id} "
                        f"(Status: {execution.status.value})"
                    )
                    
                    # Mark trigger as executed
                    trigger_manager.mark_trigger_executed(trigger.id)
                
                except Exception as e:
                    logger.error(f"Error executing trigger {trigger.id}: {e}", exc_info=True)
    
    async def execute_trigger_once(self, trigger_id: str) -> str:
        """Execute a specific trigger immediately (for testing/manual execution)
        
        Args:
            trigger_id: Trigger ID to execute
            
        Returns:
            Execution ID
        """
        logger.info(f"Manual trigger execution: {trigger_id}")
        
        with get_db_context() as db:
            trigger_manager = TriggerManager(db)
            trigger = trigger_manager.get_trigger(trigger_id)
            
            if not trigger:
                raise ValueError(f"Trigger not found: {trigger_id}")
            
            if not trigger.enabled:
                raise ValueError(f"Trigger is disabled: {trigger_id}")
            
            # Execute workflow
            runner = WorkflowRunner(db)
            execution = await runner.execute_workflow(
                workflow_id=trigger.workflow_id,
                trigger_id=trigger.id,
            )
            
            # Mark trigger as executed
            trigger_manager.mark_trigger_executed(trigger.id)
            
            logger.info(f"Manual trigger execution completed: {execution.id}")
            
            return execution.id

