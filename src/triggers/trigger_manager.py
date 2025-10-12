"""Trigger Manager - Manages workflow triggers"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from src.database.models import Trigger, TriggerType, Workflow
from src.utils import get_logger

logger = get_logger("trigger_manager")


class TriggerManager:
    """Manages workflow triggers"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def create_trigger(
        self,
        workflow_id: str,
        name: str,
        trigger_type: TriggerType,
        config: Dict[str, Any],
        enabled: bool = True,
    ) -> Trigger:
        """Create a new trigger
        
        Args:
            workflow_id: Workflow ID
            name: Trigger name
            trigger_type: Type of trigger
            config: Trigger configuration
            enabled: Whether trigger is enabled
            
        Returns:
            Created Trigger record
        """
        logger.info(f"Creating trigger: {name} ({trigger_type.value}) for workflow {workflow_id}")
        
        # Validate workflow exists
        workflow = self.db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        # Validate trigger configuration
        self._validate_trigger_config(trigger_type, config)
        
        # Create trigger
        trigger = Trigger(
            workflow_id=workflow_id,
            name=name,
            trigger_type=trigger_type,
            enabled=enabled,
            config=config,
        )
        
        # Calculate next trigger time for scheduled triggers
        if trigger_type == TriggerType.SCHEDULED and enabled:
            trigger.next_trigger_at = self._calculate_next_trigger_time(config)
        
        self.db.add(trigger)
        self.db.commit()
        self.db.refresh(trigger)
        
        logger.info(f"Trigger created: {trigger.id}")
        
        return trigger
    
    def update_trigger(
        self,
        trigger_id: str,
        name: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        enabled: Optional[bool] = None,
    ) -> Trigger:
        """Update an existing trigger
        
        Args:
            trigger_id: Trigger ID
            name: New name (optional)
            config: New configuration (optional)
            enabled: New enabled status (optional)
            
        Returns:
            Updated Trigger record
        """
        trigger = self.db.query(Trigger).filter(Trigger.id == trigger_id).first()
        if not trigger:
            raise ValueError(f"Trigger not found: {trigger_id}")
        
        if name is not None:
            trigger.name = name
        
        if config is not None:
            self._validate_trigger_config(trigger.trigger_type, config)
            trigger.config = config
            
            # Recalculate next trigger time for scheduled triggers
            if trigger.trigger_type == TriggerType.SCHEDULED and trigger.enabled:
                trigger.next_trigger_at = self._calculate_next_trigger_time(config)
        
        if enabled is not None:
            trigger.enabled = enabled
            
            # Set/clear next trigger time based on enabled status
            if trigger.trigger_type == TriggerType.SCHEDULED:
                if enabled:
                    trigger.next_trigger_at = self._calculate_next_trigger_time(trigger.config)
                else:
                    trigger.next_trigger_at = None
        
        trigger.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(trigger)
        
        logger.info(f"Trigger updated: {trigger_id}")
        
        return trigger
    
    def delete_trigger(self, trigger_id: str) -> bool:
        """Delete a trigger
        
        Args:
            trigger_id: Trigger ID
            
        Returns:
            True if deleted successfully
        """
        trigger = self.db.query(Trigger).filter(Trigger.id == trigger_id).first()
        if not trigger:
            raise ValueError(f"Trigger not found: {trigger_id}")
        
        self.db.delete(trigger)
        self.db.commit()
        
        logger.info(f"Trigger deleted: {trigger_id}")
        
        return True
    
    def get_trigger(self, trigger_id: str) -> Optional[Trigger]:
        """Get a trigger by ID
        
        Args:
            trigger_id: Trigger ID
            
        Returns:
            Trigger record or None
        """
        return self.db.query(Trigger).filter(Trigger.id == trigger_id).first()
    
    def list_triggers(
        self,
        workflow_id: Optional[str] = None,
        trigger_type: Optional[TriggerType] = None,
        enabled: Optional[bool] = None,
    ) -> List[Trigger]:
        """List triggers with filters
        
        Args:
            workflow_id: Filter by workflow ID
            trigger_type: Filter by trigger type
            enabled: Filter by enabled status
            
        Returns:
            List of Trigger records
        """
        query = self.db.query(Trigger)
        
        if workflow_id:
            query = query.filter(Trigger.workflow_id == workflow_id)
        
        if trigger_type:
            query = query.filter(Trigger.trigger_type == trigger_type)
        
        if enabled is not None:
            query = query.filter(Trigger.enabled == enabled)
        
        return query.all()
    
    def get_due_triggers(self) -> List[Trigger]:
        """Get triggers that are due to be executed (for scheduled triggers)
        
        Returns:
            List of due Trigger records
        """
        now = datetime.utcnow()
        
        triggers = self.db.query(Trigger).filter(
            Trigger.trigger_type == TriggerType.SCHEDULED,
            Trigger.enabled == True,
            Trigger.next_trigger_at <= now,
        ).all()
        
        return triggers
    
    def mark_trigger_executed(self, trigger_id: str):
        """Mark a trigger as executed and update next trigger time
        
        Args:
            trigger_id: Trigger ID
        """
        trigger = self.db.query(Trigger).filter(Trigger.id == trigger_id).first()
        if not trigger:
            return
        
        trigger.last_triggered_at = datetime.utcnow()
        trigger.trigger_count += 1
        
        if trigger.trigger_type == TriggerType.SCHEDULED and trigger.enabled:
            trigger.next_trigger_at = self._calculate_next_trigger_time(trigger.config)
        
        self.db.commit()
        
        logger.info(f"Trigger marked as executed: {trigger_id}")
    
    def fire_event_trigger(
        self,
        event_type: str,
        event_data: Dict[str, Any],
    ) -> List[Trigger]:
        """Fire event-based triggers matching the event type
        
        Args:
            event_type: Event type identifier
            event_data: Event data
            
        Returns:
            List of triggered Trigger records
        """
        logger.info(f"Firing event triggers for: {event_type}")
        
        # Find matching event triggers
        triggers = self.db.query(Trigger).filter(
            Trigger.trigger_type == TriggerType.EVENT,
            Trigger.enabled == True,
        ).all()
        
        matched_triggers = []
        for trigger in triggers:
            config = trigger.config or {}
            trigger_event_type = config.get("event_type")
            
            if trigger_event_type == event_type:
                # Check condition if specified
                condition = config.get("condition")
                if condition:
                    try:
                        if eval(condition, {"__builtins__": {}}, event_data):
                            matched_triggers.append(trigger)
                    except Exception as e:
                        logger.error(f"Error evaluating trigger condition: {e}")
                else:
                    matched_triggers.append(trigger)
        
        logger.info(f"Found {len(matched_triggers)} matching event triggers")
        
        return matched_triggers
    
    def _validate_trigger_config(self, trigger_type: TriggerType, config: Dict[str, Any]):
        """Validate trigger configuration
        
        Args:
            trigger_type: Type of trigger
            config: Configuration to validate
            
        Raises:
            ValueError: If configuration is invalid
        """
        if trigger_type == TriggerType.SCHEDULED:
            if "cron" not in config:
                raise ValueError("Scheduled trigger requires 'cron' in config")
        
        elif trigger_type == TriggerType.EVENT:
            if "event_type" not in config:
                raise ValueError("Event trigger requires 'event_type' in config")
        
        elif trigger_type == TriggerType.WEBHOOK:
            if "endpoint" not in config:
                raise ValueError("Webhook trigger requires 'endpoint' in config")
    
    def _calculate_next_trigger_time(self, config: Dict[str, Any]) -> datetime:
        """Calculate next trigger time for scheduled triggers
        
        Args:
            config: Trigger configuration with 'cron' field
            
        Returns:
            Next trigger datetime
        """
        from croniter import croniter
        import pytz
        
        cron_expr = config.get("cron")
        timezone = config.get("timezone", "UTC")
        
        try:
            tz = pytz.timezone(timezone)
            now = datetime.now(tz)
            
            cron = croniter(cron_expr, now)
            next_time = cron.get_next(datetime)
            
            # Convert to UTC for storage
            next_time_utc = next_time.astimezone(pytz.UTC).replace(tzinfo=None)
            
            return next_time_utc
        
        except Exception as e:
            logger.error(f"Error calculating next trigger time: {e}")
            # Default to 1 day from now
            from datetime import timedelta
            return datetime.utcnow() + timedelta(days=1)

