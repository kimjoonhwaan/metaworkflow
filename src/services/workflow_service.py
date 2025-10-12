"""Workflow Service - CRUD operations for workflows"""
import os
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from src.database.models import (
    Workflow,
    WorkflowStep,
    WorkflowStatus,
    StepType,
    WorkflowVersion,
)
from src.utils import settings, get_logger, CodeValidator

logger = get_logger("workflow_service")


class WorkflowService:
    """Service for workflow CRUD operations"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def create_workflow(
        self,
        name: str,
        description: str,
        steps: List[Dict[str, Any]],
        folder_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        variables: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        status: WorkflowStatus = WorkflowStatus.DRAFT,
    ) -> Workflow:
        """Create a new workflow
        
        Args:
            name: Workflow name
            description: Workflow description
            steps: List of step definitions
            folder_id: Optional folder ID
            tags: Optional tags
            variables: Initial workflow variables
            metadata: Workflow metadata (step_codes, requirements, etc.)
            status: Workflow status
            
        Returns:
            Created Workflow record
        """
        logger.info(f"Creating workflow: {name}")
        
        # Create workflow definition
        definition = {
            "name": name,
            "description": description,
            "steps": steps,
            "variables": variables or {},
            "created_at": datetime.utcnow().isoformat(),
        }
        
        # Create workflow record
        workflow = Workflow(
            name=name,
            description=description,
            folder_id=folder_id,
            status=status,
            tags=tags or [],
            definition=definition,
            variables=variables or {},
            workflow_metadata=metadata or {},
            version=1,
        )
        
        self.db.add(workflow)
        self.db.flush()  # Get workflow ID
        
        # Create step records
        for step_data in steps:
            step = self._create_step_from_data(workflow.id, step_data)
            self.db.add(step)
        
        # Create initial version
        version = WorkflowVersion(
            workflow_id=workflow.id,
            version=1,
            name=name,
            description=description,
            definition=definition,
            workflow_metadata=metadata or {},
            change_summary="Initial version",
        )
        self.db.add(version)
        
        self.db.commit()
        self.db.refresh(workflow)
        
        # Generate Python script files if needed
        self._generate_python_scripts(workflow)
        
        logger.info(f"Workflow created: {workflow.id}")
        
        return workflow
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get workflow by ID"""
        return self.db.query(Workflow).filter(Workflow.id == workflow_id).first()
    
    def list_workflows(
        self,
        folder_id: Optional[str] = None,
        status: Optional[WorkflowStatus] = None,
        tags: Optional[List[str]] = None,
        search: Optional[str] = None,
    ) -> List[Workflow]:
        """List workflows with filters
        
        Args:
            folder_id: Filter by folder
            status: Filter by status
            tags: Filter by tags
            search: Search in name/description
            
        Returns:
            List of Workflow records
        """
        query = self.db.query(Workflow)
        
        if folder_id is not None:
            query = query.filter(Workflow.folder_id == folder_id)
        
        if status:
            query = query.filter(Workflow.status == status)
        
        if tags:
            # Filter workflows that have ANY of the specified tags
            for tag in tags:
                query = query.filter(Workflow.tags.contains([tag]))
        
        if search:
            query = query.filter(
                (Workflow.name.ilike(f"%{search}%")) |
                (Workflow.description.ilike(f"%{search}%"))
            )
        
        return query.order_by(Workflow.created_at.desc()).all()
    
    def update_workflow(
        self,
        workflow_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        steps: Optional[List[Dict[str, Any]]] = None,
        folder_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        variables: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        status: Optional[WorkflowStatus] = None,
        change_summary: Optional[str] = None,
    ) -> Workflow:
        """Update workflow
        
        Args:
            workflow_id: Workflow ID
            name: New name
            description: New description
            steps: New steps definition
            folder_id: New folder ID
            tags: New tags
            variables: New variables
            metadata: New metadata
            status: New status
            change_summary: Summary of changes for version history
            
        Returns:
            Updated Workflow record
        """
        logger.info(f"Updating workflow: {workflow_id}")
        
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        # Track if definition changed
        definition_changed = False
        
        if name is not None:
            workflow.name = name
            definition_changed = True
        
        if description is not None:
            workflow.description = description
            definition_changed = True
        
        if folder_id is not None:
            workflow.folder_id = folder_id
        
        if tags is not None:
            workflow.tags = tags
        
        if variables is not None:
            workflow.variables = variables
            definition_changed = True
        
        if metadata is not None:
            workflow.workflow_metadata = metadata
            definition_changed = True
        
        if status is not None:
            workflow.status = status
        
        # Update steps if provided
        if steps is not None:
            # Delete existing steps
            self.db.query(WorkflowStep).filter(
                WorkflowStep.workflow_id == workflow_id
            ).delete()
            
            # Create new steps
            for step_data in steps:
                step = self._create_step_from_data(workflow_id, step_data)
                self.db.add(step)
            
            definition_changed = True
        
        # Create new version if definition changed
        if definition_changed:
            workflow.version += 1
            
            new_definition = {
                "name": workflow.name,
                "description": workflow.description,
                "steps": steps if steps else [self._step_to_dict(s) for s in workflow.steps],
                "variables": workflow.variables,
                "updated_at": datetime.utcnow().isoformat(),
            }
            workflow.definition = new_definition
            
            version = WorkflowVersion(
                workflow_id=workflow.id,
                version=workflow.version,
                name=workflow.name,
                description=workflow.description,
                definition=new_definition,
                workflow_metadata=workflow.workflow_metadata,
                change_summary=change_summary or "Updated workflow",
            )
            self.db.add(version)
        
        workflow.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(workflow)
        
        # Regenerate Python scripts if steps changed
        if steps is not None:
            self._generate_python_scripts(workflow)
        
        logger.info(f"Workflow updated: {workflow_id}")
        
        return workflow
    
    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete workflow and all related data
        
        Args:
            workflow_id: Workflow ID
            
        Returns:
            True if deleted successfully
        """
        logger.info(f"Deleting workflow: {workflow_id}")
        
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        # Delete Python script files
        self._delete_python_scripts(workflow)
        
        # Delete workflow (cascade will delete related records)
        self.db.delete(workflow)
        self.db.commit()
        
        logger.info(f"Workflow deleted: {workflow_id}")
        
        return True
    
    def get_workflow_versions(self, workflow_id: str) -> List[WorkflowVersion]:
        """Get workflow version history"""
        return self.db.query(WorkflowVersion).filter(
            WorkflowVersion.workflow_id == workflow_id
        ).order_by(WorkflowVersion.version.desc()).all()
    
    def restore_workflow_version(self, workflow_id: str, version: int) -> Workflow:
        """Restore workflow to a previous version"""
        logger.info(f"Restoring workflow {workflow_id} to version {version}")
        
        # Get version record
        version_record = self.db.query(WorkflowVersion).filter(
            WorkflowVersion.workflow_id == workflow_id,
            WorkflowVersion.version == version,
        ).first()
        
        if not version_record:
            raise ValueError(f"Version {version} not found for workflow {workflow_id}")
        
        # Restore from version
        steps = version_record.definition.get("steps", [])
        
        return self.update_workflow(
            workflow_id=workflow_id,
            name=version_record.name,
            description=version_record.description,
            steps=steps,
            variables=version_record.definition.get("variables", {}),
            metadata=version_record.workflow_metadata,
            change_summary=f"Restored to version {version}",
        )
    
    def _create_step_from_data(self, workflow_id: str, step_data: Dict[str, Any]) -> WorkflowStep:
        """Create WorkflowStep from step data dictionary"""
        
        # Validate Python code if present
        code = step_data.get("code")
        if code and step_data.get("step_type") == "PYTHON_SCRIPT":
            is_valid, issues = CodeValidator.validate_python_code(code)
            
            if not is_valid:
                error_msg = f"Step '{step_data['name']}' 코드에 문제가 있습니다:\n" + "\n".join(issues)
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            if issues:
                # Log warnings but don't fail
                logger.warning(f"Step '{step_data['name']}' 코드 경고: {'; '.join(issues)}")
        
        step = WorkflowStep(
            workflow_id=workflow_id,
            name=step_data["name"],
            step_type=StepType(step_data["step_type"]),
            order=step_data["order"],
            config=step_data.get("config", {}),
            input_mapping=step_data.get("input_mapping"),
            output_mapping=step_data.get("output_mapping"),
            condition=step_data.get("condition"),
            retry_config=step_data.get("retry_config"),
            code=code,
            requirements=step_data.get("requirements"),
        )
        return step
    
    def _step_to_dict(self, step: WorkflowStep) -> Dict[str, Any]:
        """Convert WorkflowStep to dictionary"""
        return {
            "name": step.name,
            "step_type": step.step_type.value,
            "order": step.order,
            "config": step.config,
            "input_mapping": step.input_mapping,
            "output_mapping": step.output_mapping,
            "condition": step.condition,
            "retry_config": step.retry_config,
            "code": step.code,
            "requirements": step.requirements,
        }
    
    def _generate_python_scripts(self, workflow: Workflow):
        """Generate Python script files for PYTHON_SCRIPT steps
        
        Uses metadata.step_codes if available, otherwise creates scaffold
        """
        logger.info(f"Generating Python scripts for workflow: {workflow.id}")
        
        # Create workflow script directory
        workflow_dir = os.path.join(settings.workflow_scripts_dir, workflow.id)
        os.makedirs(workflow_dir, exist_ok=True)
        
        # Get step codes from metadata
        step_codes = workflow.workflow_metadata.get("step_codes", {}) if workflow.workflow_metadata else {}
        
        # Process each step
        for step in workflow.steps:
            if step.step_type == StepType.PYTHON_SCRIPT:
                # Use code from step.code first, then metadata, then generate scaffold
                if step.code:
                    code = step.code
                elif step.name in step_codes:
                    code = step_codes[step.name]
                elif step.id in step_codes:
                    code = step_codes[step.id]
                else:
                    # Generate scaffold
                    code = self._generate_script_scaffold(step)
                
                # Write to file
                script_path = os.path.join(workflow_dir, f"step_{step.order}_{step.name}.py")
                with open(script_path, 'w', encoding='utf-8') as f:
                    f.write(code)
                
                logger.info(f"Created script file: {script_path}")
    
    def _generate_script_scaffold(self, step: WorkflowStep) -> str:
        """Generate scaffold Python code for a step"""
        return f"""#!/usr/bin/env python3
\"\"\"
Step: {step.name}
Description: {step.config.get('description', 'No description')}
\"\"\"
import json
import sys

def main():
    # Parse input variables from file (to avoid command line length limits)
    variables = {{}}
    if '--variables-file' in sys.argv:
        idx = sys.argv.index('--variables-file')
        if idx + 1 < len(sys.argv):
            with open(sys.argv[idx + 1], 'r', encoding='utf-8') as f:
                variables = json.load(f)
    
    # Debug output (goes to stderr)
    print(f"Received variables: {{list(variables.keys())}}", file=sys.stderr)
    
    try:
        # TODO: Implement your logic here
        # Remember: Extract dict values BEFORE using in f-strings!
        
        result = {{
            "status": "success",
            "message": "Step completed",
        }}
        
        # Output final JSON to stdout
        print(json.dumps(result))
    except Exception as e:
        print(f"Error: {{e}}", file=sys.stderr)
        print(json.dumps({{"status": "error", "error": str(e)}}))
        sys.exit(1)

if __name__ == "__main__":
    main()
"""
    
    def _delete_python_scripts(self, workflow: Workflow):
        """Delete Python script files for a workflow"""
        import shutil
        
        workflow_dir = os.path.join(settings.workflow_scripts_dir, workflow.id)
        if os.path.exists(workflow_dir):
            shutil.rmtree(workflow_dir)
            logger.info(f"Deleted script directory: {workflow_dir}")

