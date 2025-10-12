"""Database models for workflow management system"""
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    DateTime,
    ForeignKey,
    Enum,
    JSON,
    Boolean,
    Float,
)
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from .base import Base


def generate_uuid():
    """Generate UUID as string"""
    return str(uuid.uuid4())


class WorkflowStatus(enum.Enum):
    """Workflow status enumeration"""
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    ARCHIVED = "ARCHIVED"


class ExecutionStatus(enum.Enum):
    """Execution status enumeration"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    WAITING_APPROVAL = "WAITING_APPROVAL"


class StepType(enum.Enum):
    """Step type enumeration"""
    LLM_CALL = "LLM_CALL"
    API_CALL = "API_CALL"
    PYTHON_SCRIPT = "PYTHON_SCRIPT"
    CONDITION = "CONDITION"
    APPROVAL = "APPROVAL"
    NOTIFICATION = "NOTIFICATION"
    DATA_TRANSFORM = "DATA_TRANSFORM"


class TriggerType(enum.Enum):
    """Trigger type enumeration"""
    MANUAL = "MANUAL"
    SCHEDULED = "SCHEDULED"
    EVENT = "EVENT"
    WEBHOOK = "WEBHOOK"


class Folder(Base):
    """Folder for organizing workflows"""
    __tablename__ = "folders"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    parent_id = Column(String, ForeignKey("folders.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    parent = relationship("Folder", remote_side=[id], backref="children")
    workflows = relationship("Workflow", back_populates="folder", cascade="all, delete-orphan")


class Workflow(Base):
    """Workflow definition"""
    __tablename__ = "workflows"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    folder_id = Column(String, ForeignKey("folders.id"), nullable=True)
    status = Column(Enum(WorkflowStatus), default=WorkflowStatus.DRAFT, nullable=False)
    tags = Column(JSON, default=list, nullable=True)  # ["tag1", "tag2"]
    
    # Workflow definition
    definition = Column(JSON, nullable=False)  # Full workflow graph definition
    variables = Column(JSON, default=dict, nullable=True)  # Global workflow variables
    
    # Metadata (using workflow_metadata to avoid SQLAlchemy reserved name)
    workflow_metadata = Column("metadata", JSON, default=dict, nullable=True)  # step_codes, requirements, etc.
    
    # Version info
    version = Column(Integer, default=1, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255), nullable=True)
    
    # Relationships
    folder = relationship("Folder", back_populates="workflows")
    steps = relationship("WorkflowStep", back_populates="workflow", cascade="all, delete-orphan")
    executions = relationship("WorkflowExecution", back_populates="workflow", cascade="all, delete-orphan")
    triggers = relationship("Trigger", back_populates="workflow", cascade="all, delete-orphan")
    versions = relationship("WorkflowVersion", back_populates="workflow", cascade="all, delete-orphan")


class WorkflowStep(Base):
    """Individual step in a workflow"""
    __tablename__ = "workflow_steps"

    id = Column(String, primary_key=True, default=generate_uuid)
    workflow_id = Column(String, ForeignKey("workflows.id"), nullable=False)
    name = Column(String(255), nullable=False)
    step_type = Column(Enum(StepType), nullable=False)
    order = Column(Integer, nullable=False)  # Execution order (0-based)
    
    # Step configuration
    config = Column(JSON, nullable=False)  # Step-specific configuration
    input_mapping = Column(JSON, default=dict, nullable=True)  # Input variable mapping
    output_mapping = Column(JSON, default=dict, nullable=True)  # Output variable mapping
    
    # Conditions
    condition = Column(Text, nullable=True)  # Conditional execution logic
    retry_config = Column(JSON, default=dict, nullable=True)  # Retry configuration
    
    # For PYTHON_SCRIPT type
    code = Column(Text, nullable=True)  # Python code content
    requirements = Column(JSON, default=list, nullable=True)  # Python dependencies
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    workflow = relationship("Workflow", back_populates="steps")
    executions = relationship("StepExecution", back_populates="step", cascade="all, delete-orphan")


class WorkflowExecution(Base):
    """Workflow execution record"""
    __tablename__ = "workflow_executions"

    id = Column(String, primary_key=True, default=generate_uuid)
    workflow_id = Column(String, ForeignKey("workflows.id"), nullable=False)
    trigger_id = Column(String, ForeignKey("triggers.id"), nullable=True)
    
    status = Column(Enum(ExecutionStatus), default=ExecutionStatus.PENDING, nullable=False)
    
    # Execution context
    input_data = Column(JSON, default=dict, nullable=True)  # Input variables
    output_data = Column(JSON, default=dict, nullable=True)  # Final output
    context = Column(JSON, default=dict, nullable=True)  # Execution context/state
    
    # Execution info
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    error_step_id = Column(String, nullable=True)  # Step where error occurred
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    workflow = relationship("Workflow", back_populates="executions")
    trigger = relationship("Trigger", back_populates="executions")
    step_executions = relationship("StepExecution", back_populates="workflow_execution", cascade="all, delete-orphan")


class StepExecution(Base):
    """Individual step execution record"""
    __tablename__ = "step_executions"

    id = Column(String, primary_key=True, default=generate_uuid)
    workflow_execution_id = Column(String, ForeignKey("workflow_executions.id"), nullable=False)
    step_id = Column(String, ForeignKey("workflow_steps.id"), nullable=False)
    
    status = Column(Enum(ExecutionStatus), default=ExecutionStatus.PENDING, nullable=False)
    
    # Execution data
    input_data = Column(JSON, default=dict, nullable=True)
    output_data = Column(JSON, default=dict, nullable=True)
    
    # Execution info
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    
    # Logs and errors
    logs = Column(Text, nullable=True)  # Execution logs
    error_message = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    workflow_execution = relationship("WorkflowExecution", back_populates="step_executions")
    step = relationship("WorkflowStep", back_populates="executions")


class Trigger(Base):
    """Trigger configuration for workflows"""
    __tablename__ = "triggers"

    id = Column(String, primary_key=True, default=generate_uuid)
    workflow_id = Column(String, ForeignKey("workflows.id"), nullable=False)
    name = Column(String(255), nullable=False)
    trigger_type = Column(Enum(TriggerType), nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    
    # Trigger configuration
    config = Column(JSON, nullable=False)  # Type-specific configuration
    # For SCHEDULED: {"cron": "0 9 * * *", "timezone": "Asia/Seoul"}
    # For EVENT: {"event_type": "data_received", "condition": "value > 100"}
    # For WEBHOOK: {"endpoint": "/webhook/abc123", "secret": "..."}
    
    # Execution tracking
    last_triggered_at = Column(DateTime, nullable=True)
    next_trigger_at = Column(DateTime, nullable=True)  # For scheduled triggers
    trigger_count = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    workflow = relationship("Workflow", back_populates="triggers")
    executions = relationship("WorkflowExecution", back_populates="trigger")


class WorkflowVersion(Base):
    """Workflow version history"""
    __tablename__ = "workflow_versions"

    id = Column(String, primary_key=True, default=generate_uuid)
    workflow_id = Column(String, ForeignKey("workflows.id"), nullable=False)
    version = Column(Integer, nullable=False)
    
    # Versioned data
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    definition = Column(JSON, nullable=False)
    workflow_metadata = Column("metadata", JSON, default=dict, nullable=True)
    
    # Change tracking
    change_summary = Column(Text, nullable=True)
    changed_by = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    workflow = relationship("Workflow", back_populates="versions")

