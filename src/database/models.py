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


class KnowledgeBaseCategory(enum.Enum):
    """Knowledge base category enumeration"""
    WORKFLOW_PATTERNS = "WORKFLOW_PATTERNS"
    ERROR_SOLUTIONS = "ERROR_SOLUTIONS"
    CODE_TEMPLATES = "CODE_TEMPLATES"
    INTEGRATION_EXAMPLES = "INTEGRATION_EXAMPLES"
    BEST_PRACTICES = "BEST_PRACTICES"


class DocumentContentType(enum.Enum):
    """Document content type enumeration"""
    TEXT = "TEXT"
    CODE = "CODE"
    EXAMPLE = "EXAMPLE"
    ERROR_SOLUTION = "ERROR_SOLUTION"
    TEMPLATE = "TEMPLATE"


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


class KnowledgeBase(Base):
    """Knowledge base for RAG system"""
    __tablename__ = "knowledge_bases"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    category = Column(Enum(KnowledgeBaseCategory), nullable=False)
    
    # Configuration
    is_active = Column(Boolean, default=True)
    embedding_model = Column(String(100), default="text-embedding-3-small")
    chunk_size = Column(Integer, default=500)
    chunk_overlap = Column(Integer, default=50)
    
    # Metadata
    kb_metadata = Column("metadata", JSON, default=dict, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    documents = relationship("Document", back_populates="knowledge_base", cascade="all, delete-orphan")


class Document(Base):
    """Document in knowledge base"""
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=generate_uuid)
    knowledge_base_id = Column(String, ForeignKey("knowledge_bases.id"), nullable=False)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    content_type = Column(Enum(DocumentContentType), nullable=False)
    
    # Vector storage reference
    embedding_id = Column(String, nullable=True)  # ChromaDB collection ID
    vector_count = Column(Integer, default=0)
    
    # Metadata
    kb_metadata = Column("metadata", JSON, default=dict, nullable=True)
    tags = Column(JSON, default=list, nullable=True)
    
    # Processing status
    is_processed = Column(Boolean, default=False)
    processing_error = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    knowledge_base = relationship("KnowledgeBase", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    """Document chunk for vector storage"""
    __tablename__ = "document_chunks"

    id = Column(String, primary_key=True, default=generate_uuid)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    
    # Vector storage reference
    embedding_id = Column(String, nullable=True)  # ChromaDB document ID
    embedding_vector = Column(JSON, nullable=True)  # 임시 저장용 (선택적)
    
    # Chunk metadata
    start_char = Column(Integer, nullable=True)
    end_char = Column(Integer, nullable=True)
    token_count = Column(Integer, nullable=True)
    
    # Search metadata
    search_score = Column(Float, nullable=True)  # 최근 검색 점수
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    document = relationship("Document", back_populates="chunks")


class RAGQuery(Base):
    """RAG query history for analytics"""
    __tablename__ = "rag_queries"

    id = Column(String, primary_key=True, default=generate_uuid)
    
    # Query details
    query_text = Column(Text, nullable=False)
    query_category = Column(Enum(KnowledgeBaseCategory), nullable=True)
    
    # Results
    results_count = Column(Integer, default=0)
    top_score = Column(Float, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    
    # Context usage
    used_in_generation = Column(Boolean, default=False)
    generation_success = Column(Boolean, nullable=True)
    
    # Metadata
    user_context = Column(JSON, default=dict, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

