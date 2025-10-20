"""LangGraph-based workflow execution engine"""
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import asyncio

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from src.database.models import WorkflowStep, StepType, ExecutionStatus
from src.engines.workflow_state import WorkflowState, StepStatus
from src.engines.step_executor import StepExecutor
from src.utils import get_logger

logger = get_logger("workflow_engine")


class WorkflowEngine:
    """LangGraph-based workflow execution engine"""
    
    def __init__(self):
        self.step_executor = StepExecutor()
        self.memory = MemorySaver()
    
    def create_graph(
        self,
        workflow_steps: List[WorkflowStep],
        on_step_complete: Optional[Callable] = None,
    ) -> StateGraph:
        """Create LangGraph StateGraph from workflow steps
        
        Args:
            workflow_steps: List of workflow steps
            on_step_complete: Callback function called after each step
            
        Returns:
            Configured StateGraph
        """
        # Sort steps by order
        sorted_steps = sorted(workflow_steps, key=lambda s: s.order)
        
        # Create graph
        graph = StateGraph(WorkflowState)
        
        # Add nodes for each step
        for i, step in enumerate(sorted_steps):
            node_name = f"step_{step.order}_{step.id}"
            
            # Create node function
            async def step_node(state: WorkflowState, step=step, step_idx=i) -> WorkflowState:
                return await self._execute_step_node(state, step, step_idx, on_step_complete)
            
            graph.add_node(node_name, step_node)
        
        # Add edges (sequential execution with conditional branching)
        for i, step in enumerate(sorted_steps):
            current_node = f"step_{step.order}_{step.id}"
            
            if i == 0:
                # First step
                graph.set_entry_point(current_node)
            
            if i < len(sorted_steps) - 1:
                next_step = sorted_steps[i + 1]
                next_node = f"step_{next_step.order}_{next_step.id}"
                
                # Add conditional edge for control flow
                graph.add_conditional_edges(
                    current_node,
                    lambda state: self._should_continue(state),
                    {
                        "continue": next_node,
                        "stop": END,
                        "wait_approval": END,
                    }
                )
            else:
                # Last step
                graph.add_edge(current_node, END)
        
        return graph.compile(checkpointer=self.memory)
    
    async def _execute_step_node(
        self,
        state: WorkflowState,
        step: WorkflowStep,
        step_idx: int,
        on_step_complete: Optional[Callable] = None,
    ) -> WorkflowState:
        """Execute a single step node
        
        Args:
            state: Current workflow state
            step: Step to execute
            step_idx: Step index
            on_step_complete: Callback after step completion
            
        Returns:
            Updated workflow state
        """
        step_id = step.id
        logger.info(f"Executing step {step_idx + 1}/{state['total_steps']}: {step.name} (ID: {step_id})")
        
        # Update step status to RUNNING
        state["step_statuses"][step_id] = StepStatus.RUNNING
        state["current_step"] = step_idx + 1
        state["logs"].append(f"[{datetime.utcnow().isoformat()}] Starting step: {step.name}")
        
        try:
            # Check if condition is met (if specified)
            if step.condition:
                condition_met = await self._evaluate_condition(step.condition, state["variables"])
                if not condition_met:
                    logger.info(f"Step condition not met, skipping: {step.name}")
                    state["step_statuses"][step_id] = StepStatus.SKIPPED
                    state["logs"].append(f"[{datetime.utcnow().isoformat()}] Step skipped (condition not met): {step.name}")
                    return state
            
            # Prepare input variables for the step
            input_vars = self._prepare_step_input(step, state)
            
            # Debug: Log input variables
            logger.info(f"Step '{step.name}' input variables: {list(input_vars.keys())}")
            logger.debug(f"Step '{step.name}' full input: {input_vars}")
            logger.info(f"Step '{step.name}' state variables: {list(state['variables'].keys())}")
            logger.info(f"Step '{step.name}' step outputs: {list(state['step_outputs'].keys())}")
            
            # Execute the step
            start_time = datetime.utcnow()
            result = await self.step_executor.execute_step(
                step_type=step.step_type.value,
                step_config=step.config,
                variables=input_vars,
                code=step.code,
            )
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            # Check if approval is required
            if result.get("requires_approval"):
                state["step_statuses"][step_id] = StepStatus.WAITING_APPROVAL
                state["waiting_approval"] = True
                state["approval_step_id"] = step_id
                state["logs"].append(f"[{datetime.utcnow().isoformat()}] Waiting for approval: {step.name}")
                logger.info(f"Step requires approval: {step.name}")
                
                if on_step_complete:
                    await on_step_complete(step_id, ExecutionStatus.WAITING_APPROVAL, result, duration)
                
                return state
            
            # Process step output
            output_data = result.get("output", {})
            state["step_outputs"][step_id] = output_data
            
            # Debug: Log output
            logger.info(f"Step '{step.name}' output type: {type(output_data)}, keys: {list(output_data.keys()) if isinstance(output_data, dict) else 'N/A'}")
            
            # Update variables based on output mapping
            if step.output_mapping:
                logger.info(f"Step '{step.name}' output_mapping: {step.output_mapping}")
                for var_name, output_key in step.output_mapping.items():
                    # If output_key is "output" or empty, use entire output_data
                    if output_key == "output" or not output_key:
                        state["variables"][var_name] = output_data
                        logger.info(f"Mapped entire output to variable '{var_name}'")
                    # If output_data is a dict and has the key, use that value
                    elif isinstance(output_data, dict) and output_key in output_data:
                        state["variables"][var_name] = output_data[output_key]
                        logger.info(f"Mapped output['{output_key}'] to variable '{var_name}'")
                    # Otherwise, use the entire output_data
                    else:
                        state["variables"][var_name] = output_data
                        logger.warning(f"Output key '{output_key}' not found in output, using entire output for variable '{var_name}'")
            
            # Mark step as SUCCESS
            state["step_statuses"][step_id] = StepStatus.SUCCESS
            state["logs"].append(
                f"[{datetime.utcnow().isoformat()}] Step completed successfully: {step.name} (Duration: {duration:.2f}s)"
            )
            
            logger.info(f"Step completed successfully: {step.name} (Duration: {duration:.2f}s)")
            
            # Call callback
            if on_step_complete:
                await on_step_complete(step_id, ExecutionStatus.SUCCESS, result, duration)
        
        except Exception as e:
            # Mark step as FAILED
            state["step_statuses"][step_id] = StepStatus.FAILED
            error_info = {
                "step_id": step_id,
                "step_name": step.name,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
            state["errors"].append(error_info)
            state["should_stop"] = True
            state["logs"].append(f"[{datetime.utcnow().isoformat()}] Step failed: {step.name} - {str(e)}")
            
            logger.error(f"Step failed: {step.name} - {str(e)}", exc_info=True)
            
            # Call callback
            if on_step_complete:
                await on_step_complete(step_id, ExecutionStatus.FAILED, {"error": str(e)}, 0)
        
        return state
    
    def _prepare_step_input(self, step: WorkflowStep, state: WorkflowState) -> Dict[str, Any]:
        """Prepare input variables for a step based on input mapping
        
        Args:
            step: Workflow step
            state: Current workflow state
            
        Returns:
            Input variables dictionary
        """
        # Start with all current variables
        input_vars = state["variables"].copy()
        
        # Also include all step outputs in case they're referenced directly
        input_vars.update(state["step_outputs"])
        
        # Apply input mapping if specified (this can override or add new mappings)
        if step.input_mapping:
            for step_var, workflow_var in step.input_mapping.items():
                if workflow_var in state["variables"]:
                    input_vars[step_var] = state["variables"][workflow_var]
                elif workflow_var in state["step_outputs"]:
                    input_vars[step_var] = state["step_outputs"][workflow_var]
                else:
                    logger.warning(f"Input mapping variable '{workflow_var}' not found in state for step '{step.name}'")
        
        return input_vars
    
    async def _evaluate_condition(self, condition: str, variables: Dict[str, Any]) -> bool:
        """Evaluate a condition expression
        
        Args:
            condition: Condition expression (Python code)
            variables: Variables to use in evaluation
            
        Returns:
            True if condition is met, False otherwise
        """
        try:
            result = eval(condition, {"__builtins__": {}}, variables)
            return bool(result)
        except Exception as e:
            logger.error(f"Condition evaluation failed: {e}")
            return False
    
    def _should_continue(self, state: WorkflowState) -> str:
        """Determine if workflow should continue to next step
        
        Args:
            state: Current workflow state
            
        Returns:
            "continue", "stop", or "wait_approval"
        """
        if state["should_stop"]:
            return "stop"
        
        if state["waiting_approval"]:
            return "wait_approval"
        
        return "continue"
    
    async def run_workflow(
        self,
        workflow_id: str,
        execution_id: str,
        workflow_steps: List[WorkflowStep],
        initial_variables: Dict[str, Any],
        on_step_complete: Optional[Callable] = None,
    ) -> WorkflowState:
        """Run a complete workflow
        
        Args:
            workflow_id: Workflow ID
            execution_id: Execution ID
            workflow_steps: List of workflow steps
            initial_variables: Initial workflow variables
            on_step_complete: Callback after each step
            
        Returns:
            Final workflow state
        """
        logger.info(f"Starting workflow execution: {workflow_id}")
        
        # Create graph
        graph = self.create_graph(workflow_steps, on_step_complete)
        
        # Initialize state
        initial_state: WorkflowState = {
            "workflow_id": workflow_id,
            "execution_id": execution_id,
            "current_step": 0,
            "total_steps": len(workflow_steps),
            "step_statuses": {step.id: StepStatus.PENDING for step in workflow_steps},
            "variables": initial_variables.copy(),
            "step_outputs": {},
            "errors": [],
            "should_stop": False,
            "waiting_approval": False,
            "approval_step_id": None,
            "started_at": datetime.utcnow().isoformat(),
            "logs": [f"[{datetime.utcnow().isoformat()}] Workflow started"],
        }
        
        # Run graph
        try:
            config = {"configurable": {"thread_id": execution_id}}
            final_state = await graph.ainvoke(initial_state, config)
            
            logger.info(f"Workflow execution completed: {workflow_id}")
            return final_state
        
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}", exc_info=True)
            initial_state["should_stop"] = True
            initial_state["errors"].append({
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            })
            return initial_state

