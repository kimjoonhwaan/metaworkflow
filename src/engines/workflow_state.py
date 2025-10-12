"""Workflow state definition for LangGraph"""
from typing import TypedDict, Dict, Any, List, Optional
from enum import Enum


class StepStatus(str, Enum):
    """Step execution status"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    WAITING_APPROVAL = "WAITING_APPROVAL"


class WorkflowState(TypedDict):
    """State structure for workflow execution"""
    
    # Workflow identification
    workflow_id: str
    execution_id: str
    
    # Current execution state
    current_step: int
    total_steps: int
    
    # Step statuses
    step_statuses: Dict[str, StepStatus]  # step_id -> status
    
    # Variables and data
    variables: Dict[str, Any]  # Global workflow variables
    step_outputs: Dict[str, Any]  # step_id -> output data
    
    # Error tracking
    errors: List[Dict[str, Any]]  # List of errors occurred
    
    # Control flags
    should_stop: bool
    waiting_approval: bool
    approval_step_id: Optional[str]
    
    # Execution metadata
    started_at: Optional[str]
    logs: List[str]

