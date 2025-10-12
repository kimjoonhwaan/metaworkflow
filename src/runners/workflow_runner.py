"""Workflow Runner - Executes workflows and manages execution lifecycle"""
import os
import json
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from src.database.models import (
    Workflow,
    WorkflowStep,
    WorkflowExecution,
    StepExecution,
    ExecutionStatus,
)
from src.engines import WorkflowEngine
from src.utils import settings, get_logger

logger = get_logger("workflow_runner")


class WorkflowRunner:
    """Manages workflow execution lifecycle"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.engine = WorkflowEngine()
    
    async def execute_workflow(
        self,
        workflow_id: str,
        input_data: Optional[Dict[str, Any]] = None,
        trigger_id: Optional[str] = None,
    ) -> WorkflowExecution:
        """Execute a workflow
        
        Args:
            workflow_id: Workflow ID to execute
            input_data: Input data for the workflow
            trigger_id: Trigger ID if triggered automatically
            
        Returns:
            WorkflowExecution record
        """
        logger.info(f"Starting workflow execution: {workflow_id}")
        
        # Load workflow from database
        workflow = self.db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        # Load steps
        steps = self.db.query(WorkflowStep).filter(
            WorkflowStep.workflow_id == workflow_id
        ).order_by(WorkflowStep.order).all()
        
        if not steps:
            raise ValueError(f"No steps found for workflow: {workflow_id}")
        
        # Create execution record
        execution = WorkflowExecution(
            workflow_id=workflow_id,
            trigger_id=trigger_id,
            status=ExecutionStatus.PENDING,
            input_data=input_data or {},
            started_at=datetime.utcnow(),
        )
        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)
        
        logger.info(f"Created execution record: {execution.id}")
        
        try:
            # Update status to RUNNING
            execution.status = ExecutionStatus.RUNNING
            self.db.commit()
            
            # Prepare initial variables
            initial_variables = workflow.variables.copy() if workflow.variables else {}
            initial_variables.update(input_data or {})
            
            # Create step execution records
            step_executions = {}
            for step in steps:
                step_exec = StepExecution(
                    workflow_execution_id=execution.id,
                    step_id=step.id,
                    status=ExecutionStatus.PENDING,
                )
                self.db.add(step_exec)
                step_executions[step.id] = step_exec
            self.db.commit()
            
            # Define callback for step completion
            async def on_step_complete(step_id: str, status: ExecutionStatus, result: Dict[str, Any], duration: float):
                """Update step execution record"""
                step_exec = step_executions.get(step_id)
                if step_exec:
                    step_exec.status = status
                    step_exec.output_data = result
                    step_exec.duration_seconds = duration
                    step_exec.completed_at = datetime.utcnow()
                    
                    if status == ExecutionStatus.FAILED:
                        step_exec.error_message = result.get("error", "Unknown error")
                        step_exec.error_traceback = result.get("traceback", "")
                    
                    if status == ExecutionStatus.SUCCESS:
                        step_exec.logs = result.get("logs", "")
                    
                    self.db.commit()
            
            # Execute workflow using engine
            final_state = await self.engine.run_workflow(
                workflow_id=workflow_id,
                execution_id=execution.id,
                workflow_steps=steps,
                initial_variables=initial_variables,
                on_step_complete=on_step_complete,
            )
            
            # Update execution record with results
            execution.context = {
                "final_state": {
                    "step_statuses": final_state["step_statuses"],
                    "current_step": final_state["current_step"],
                    "total_steps": final_state["total_steps"],
                }
            }
            execution.output_data = final_state["step_outputs"]
            execution.completed_at = datetime.utcnow()
            execution.duration_seconds = (
                execution.completed_at - execution.started_at
            ).total_seconds()
            
            # Determine final status
            if final_state["waiting_approval"]:
                execution.status = ExecutionStatus.WAITING_APPROVAL
                logger.info(f"Workflow waiting for approval: {execution.id}")
            elif final_state["errors"]:
                execution.status = ExecutionStatus.FAILED
                execution.error_message = final_state["errors"][-1].get("error", "Unknown error")
                execution.error_step_id = final_state["errors"][-1].get("step_id")
                logger.error(f"Workflow execution failed: {execution.id}")
            else:
                execution.status = ExecutionStatus.SUCCESS
                logger.info(f"Workflow execution completed successfully: {execution.id}")
            
            self.db.commit()
            self.db.refresh(execution)
            
            return execution
        
        except Exception as e:
            logger.error(f"Workflow execution error: {e}", exc_info=True)
            
            # Update execution record with error
            execution.status = ExecutionStatus.FAILED
            execution.error_message = str(e)
            execution.completed_at = datetime.utcnow()
            if execution.started_at:
                execution.duration_seconds = (
                    execution.completed_at - execution.started_at
                ).total_seconds()
            
            self.db.commit()
            self.db.refresh(execution)
            
            return execution
    
    async def retry_execution(
        self,
        execution_id: str,
        from_step: Optional[int] = None,
    ) -> WorkflowExecution:
        """Retry a failed workflow execution
        
        Args:
            execution_id: Execution ID to retry
            from_step: Optional step index to retry from (default: failed step)
            
        Returns:
            New WorkflowExecution record
        """
        logger.info(f"Retrying execution: {execution_id}")
        
        # Load original execution
        original_execution = self.db.query(WorkflowExecution).filter(
            WorkflowExecution.id == execution_id
        ).first()
        
        if not original_execution:
            raise ValueError(f"Execution not found: {execution_id}")
        
        # Create new execution with same parameters
        return await self.execute_workflow(
            workflow_id=original_execution.workflow_id,
            input_data=original_execution.input_data,
            trigger_id=original_execution.trigger_id,
        )
    
    async def approve_execution(
        self,
        execution_id: str,
        approved: bool = True,
    ) -> WorkflowExecution:
        """Approve or reject a workflow execution waiting for approval
        
        Args:
            execution_id: Execution ID
            approved: Whether to approve (True) or reject (False)
            
        Returns:
            Updated WorkflowExecution record
        """
        logger.info(f"Processing approval for execution: {execution_id} (approved={approved})")
        
        execution = self.db.query(WorkflowExecution).filter(
            WorkflowExecution.id == execution_id
        ).first()
        
        if not execution:
            raise ValueError(f"Execution not found: {execution_id}")
        
        if execution.status != ExecutionStatus.WAITING_APPROVAL:
            raise ValueError(f"Execution is not waiting for approval: {execution_id}")
        
        if approved:
            # Continue execution from approval step
            # TODO: Implement resume functionality
            execution.status = ExecutionStatus.SUCCESS
            execution.completed_at = datetime.utcnow()
            logger.info(f"Execution approved and completed: {execution_id}")
        else:
            # Reject and cancel
            execution.status = ExecutionStatus.CANCELLED
            execution.completed_at = datetime.utcnow()
            execution.error_message = "User rejected approval"
            logger.info(f"Execution rejected: {execution_id}")
        
        self.db.commit()
        self.db.refresh(execution)
        
        return execution
    
    def cancel_execution(
        self,
        execution_id: str,
    ) -> WorkflowExecution:
        """Cancel a running workflow execution
        
        Args:
            execution_id: Execution ID to cancel
            
        Returns:
            Updated WorkflowExecution record
        """
        logger.info(f"Cancelling execution: {execution_id}")
        
        execution = self.db.query(WorkflowExecution).filter(
            WorkflowExecution.id == execution_id
        ).first()
        
        if not execution:
            raise ValueError(f"Execution not found: {execution_id}")
        
        if execution.status not in [ExecutionStatus.PENDING, ExecutionStatus.RUNNING, ExecutionStatus.WAITING_APPROVAL]:
            raise ValueError(f"Cannot cancel execution in status: {execution.status}")
        
        execution.status = ExecutionStatus.CANCELLED
        execution.completed_at = datetime.utcnow()
        if execution.started_at:
            execution.duration_seconds = (
                execution.completed_at - execution.started_at
            ).total_seconds()
        
        self.db.commit()
        self.db.refresh(execution)
        
        logger.info(f"Execution cancelled: {execution_id}")
        
        return execution
    
    def get_execution_logs(
        self,
        execution_id: str,
    ) -> Dict[str, Any]:
        """Get detailed execution logs
        
        Args:
            execution_id: Execution ID
            
        Returns:
            Dictionary with execution details and logs
        """
        execution = self.db.query(WorkflowExecution).filter(
            WorkflowExecution.id == execution_id
        ).first()
        
        if not execution:
            raise ValueError(f"Execution not found: {execution_id}")
        
        # Load step executions
        step_executions = self.db.query(StepExecution).filter(
            StepExecution.workflow_execution_id == execution_id
        ).all()
        
        step_logs = []
        for step_exec in step_executions:
            step = self.db.query(WorkflowStep).filter(
                WorkflowStep.id == step_exec.step_id
            ).first()
            
            step_logs.append({
                "step_id": step_exec.step_id,
                "step_name": step.name if step else "Unknown",
                "step_order": step.order if step else 0,
                "status": step_exec.status.value,
                "started_at": step_exec.started_at.isoformat() if step_exec.started_at else None,
                "completed_at": step_exec.completed_at.isoformat() if step_exec.completed_at else None,
                "duration_seconds": step_exec.duration_seconds,
                "input_data": step_exec.input_data,
                "output_data": step_exec.output_data,
                "logs": step_exec.logs,
                "error_message": step_exec.error_message,
                "error_traceback": step_exec.error_traceback,
                "retry_count": step_exec.retry_count,
            })
        
        # Sort by step order
        step_logs.sort(key=lambda x: x["step_order"])
        
        return {
            "execution_id": execution.id,
            "workflow_id": execution.workflow_id,
            "status": execution.status.value,
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "duration_seconds": execution.duration_seconds,
            "input_data": execution.input_data,
            "output_data": execution.output_data,
            "error_message": execution.error_message,
            "error_step_id": execution.error_step_id,
            "step_executions": step_logs,
        }

