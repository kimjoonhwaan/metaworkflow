"""Execution Service - Manages workflow executions"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from src.database.models import (
    WorkflowExecution,
    StepExecution,
    ExecutionStatus,
)
from src.utils import get_logger

logger = get_logger("execution_service")


class ExecutionService:
    """Service for managing workflow executions"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def get_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Get execution by ID"""
        return self.db.query(WorkflowExecution).filter(
            WorkflowExecution.id == execution_id
        ).first()
    
    def list_executions(
        self,
        workflow_id: Optional[str] = None,
        status: Optional[ExecutionStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[WorkflowExecution]:
        """List executions with filters
        
        Args:
            workflow_id: Filter by workflow ID
            status: Filter by execution status
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of WorkflowExecution records
        """
        query = self.db.query(WorkflowExecution)
        
        if workflow_id:
            query = query.filter(WorkflowExecution.workflow_id == workflow_id)
        
        if status:
            query = query.filter(WorkflowExecution.status == status)
        
        query = query.order_by(WorkflowExecution.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        return query.all()
    
    def get_execution_stats(
        self,
        workflow_id: Optional[str] = None,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Get execution statistics
        
        Args:
            workflow_id: Optional workflow ID to filter by
            days: Number of days to include
            
        Returns:
            Dictionary with statistics
        """
        since = datetime.utcnow() - timedelta(days=days)
        
        query = self.db.query(WorkflowExecution).filter(
            WorkflowExecution.created_at >= since
        )
        
        if workflow_id:
            query = query.filter(WorkflowExecution.workflow_id == workflow_id)
        
        executions = query.all()
        
        # Calculate stats
        total = len(executions)
        success = sum(1 for e in executions if e.status == ExecutionStatus.SUCCESS)
        failed = sum(1 for e in executions if e.status == ExecutionStatus.FAILED)
        running = sum(1 for e in executions if e.status == ExecutionStatus.RUNNING)
        pending = sum(1 for e in executions if e.status == ExecutionStatus.PENDING)
        waiting_approval = sum(1 for e in executions if e.status == ExecutionStatus.WAITING_APPROVAL)
        
        # Average duration
        completed = [e for e in executions if e.duration_seconds is not None]
        avg_duration = sum(e.duration_seconds for e in completed) / len(completed) if completed else 0
        
        return {
            "total": total,
            "success": success,
            "failed": failed,
            "running": running,
            "pending": pending,
            "waiting_approval": waiting_approval,
            "success_rate": (success / total * 100) if total > 0 else 0,
            "average_duration_seconds": avg_duration,
            "period_days": days,
        }
    
    def get_step_executions(
        self,
        execution_id: str,
    ) -> List[StepExecution]:
        """Get step executions for a workflow execution"""
        return self.db.query(StepExecution).filter(
            StepExecution.workflow_execution_id == execution_id
        ).order_by(StepExecution.created_at).all()
    
    def cleanup_old_executions(
        self,
        days: int = 90,
        keep_failed: bool = True,
    ) -> int:
        """Clean up old execution records
        
        Args:
            days: Delete executions older than this many days
            keep_failed: If True, keep failed executions
            
        Returns:
            Number of deleted executions
        """
        logger.info(f"Cleaning up executions older than {days} days")
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        query = self.db.query(WorkflowExecution).filter(
            WorkflowExecution.created_at < cutoff
        )
        
        if keep_failed:
            query = query.filter(WorkflowExecution.status != ExecutionStatus.FAILED)
        
        count = query.count()
        query.delete()
        self.db.commit()
        
        logger.info(f"Deleted {count} old executions")
        
        return count

