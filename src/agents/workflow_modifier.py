"""Workflow Modifier Agent - Modifies existing workflows"""
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage, AIMessage

from src.agents.prompts import WORKFLOW_MODIFICATION_SYSTEM_PROMPT
from src.utils import settings, get_logger, CodeValidator
from src.services.rag_service import get_rag_service

logger = get_logger("workflow_modifier")


class WorkflowModifier:
    """Agent that modifies existing workflows based on user requests or error feedback"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=1,
        )
        self.rag_service = get_rag_service()
    
    async def modify_workflow(
        self,
        current_workflow: Dict[str, Any],
        modification_request: str,
        error_logs: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], List[str], Dict[str, Any]]:
        """Modify workflow based on user request or error logs
        
        Args:
            current_workflow: Current workflow definition
            modification_request: User's modification request
            error_logs: Optional error logs from failed execution
            
        Returns:
            Tuple of (modified_workflow, list_of_changes)
        """
        logger.info(f"Modifying workflow: {modification_request[:100]}...")
        
        # Get relevant context from RAG
        rag_context = ""
        rag_used = False
        if error_logs:
            rag_context = await self.rag_service.get_relevant_context_for_error_fix(
                error_logs, 
                json.dumps(current_workflow, indent=2)
            )
        else:
            rag_context = await self.rag_service.get_relevant_context_for_workflow_generation(
                modification_request
            )
        
        rag_used = bool(rag_context)
        
        # Build prompt
        prompt = f"""Current workflow:
```json
{json.dumps(current_workflow, indent=2)}
```

Modification request: {modification_request}
"""
        
        if error_logs:
            prompt += f"""

Error logs from recent execution:
```
{error_logs}
```

Please analyze the error and fix the issue. Provide COMPLETE corrected code for any PYTHON_SCRIPT steps that need fixing.
"""
        
        prompt += """

Generate the complete modified workflow with all changes applied. Explain what you changed in the "changes" list."""
        
        # Add RAG context to system prompt
        enhanced_system_prompt = WORKFLOW_MODIFICATION_SYSTEM_PROMPT
        if rag_context:
            enhanced_system_prompt += "\n\n" + rag_context
            logger.info(f"Enhanced modification prompt with RAG context: {len(rag_context)} chars")
        
        messages = [
            SystemMessage(content=enhanced_system_prompt),
            HumanMessage(content=prompt),
        ]
        
        try:
            response = await self.llm.ainvoke(messages)
            response_text = response.content
            
            logger.info(f"Modification response received: {len(response_text)} chars")
            
            # Parse response
            modified_workflow, changes = self._parse_modification_response(response_text)
            
            if modified_workflow:
                # Validate Python code in modified workflow
                code_validation_failed = False
                validation_issues = []
                
                for step in modified_workflow.get("steps", []):
                    if step.get("step_type") == "PYTHON_SCRIPT" and step.get("code"):
                        is_valid, issues = CodeValidator.validate_python_code(step["code"])
                        if not is_valid:
                            code_validation_failed = True
                            validation_issues.append(f"Step '{step.get('name')}': {issues[0]}")
                
                # If validation failed, ask AI to fix (one retry)
                if code_validation_failed:
                    logger.warning(f"Code validation failed in modified workflow: {validation_issues}")
                    
                    fix_request = (
                        f"수정한 워크플로우에 코드 오류가 있습니다:\n\n" +
                        "\n".join(f"- {issue}" for issue in validation_issues) +
                        "\n\n이 오류들을 수정해주세요. "
                        "특히 f-string 안에서 따옴표 중첩을 피하고, 변수를 먼저 추출하세요:\n"
                        "올바른 예: title = item.get('title'); f\"Title: {title}\"\n"
                        "잘못된 예: f'Title: {item['title']}'"
                    )
                    
                    # Retry once
                    logger.info("Requesting AI to fix code validation issues...")
                    retry_messages = messages + [
                        AIMessage(content=response_text),
                        HumanMessage(content=fix_request)
                    ]
                    
                    retry_response = await self.llm.ainvoke(retry_messages)
                    retry_text = retry_response.content
                    
                    # Parse retry response
                    modified_workflow, changes = self._parse_modification_response(retry_text)
                    
                    if not modified_workflow:
                        raise ValueError("Failed to parse modified workflow after retry")
                    
                    # Validate again (don't retry infinitely)
                    for step in modified_workflow.get("steps", []):
                        if step.get("step_type") == "PYTHON_SCRIPT" and step.get("code"):
                            is_valid, issues = CodeValidator.validate_python_code(step["code"])
                            if not is_valid:
                                logger.error(f"Validation still failed after retry: {issues}")
                                # Return anyway with warning
                                changes.append("⚠️ 경고: 일부 코드에 검증 경고가 있습니다")
                
                logger.info(f"Workflow modified successfully with {len(changes)} changes")
                return modified_workflow, changes, {"rag_used": rag_used, "rag_context_length": len(rag_context) if rag_context else 0}
            else:
                raise ValueError("Failed to parse modified workflow from response")
        
        except Exception as e:
            logger.error(f"Error modifying workflow: {e}", exc_info=True)
            raise
    
    def _parse_modification_response(self, response_text: str) -> Tuple[Optional[Dict[str, Any]], List[str]]:
        """Parse modification response
        
        Args:
            response_text: LLM response text
            
        Returns:
            Tuple of (workflow_definition, changes_list)
        """
        try:
            # Try multiple strategies to find JSON
            
            # Strategy 1: Look for JSON code block
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(1)
                data = json.loads(json_text)
                workflow = data.get("workflow")
                changes = data.get("changes", [])
                if workflow:
                    return workflow, changes
            
            # Strategy 2: Look for { "workflow": ... } pattern
            workflow_match = re.search(r'\{\s*"workflow"\s*:\s*\{', response_text)
            if workflow_match:
                start_idx = workflow_match.start()
                # Find matching closing brace
                brace_count = 0
                end_idx = start_idx
                for i in range(start_idx, len(response_text)):
                    if response_text[i] == '{':
                        brace_count += 1
                    elif response_text[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_idx = i + 1
                            break
                
                if end_idx > start_idx:
                    json_text = response_text[start_idx:end_idx]
                    data = json.loads(json_text)
                    workflow = data.get("workflow")
                    changes = data.get("changes", [])
                    if workflow:
                        return workflow, changes
            
            # Strategy 3: Look for direct workflow definition (without "workflow" key)
            # Find JSON that has "name" and "steps" keys
            json_matches = re.finditer(r'\{[^{}]*"name"[^{}]*"steps"[^{}]*\}', response_text, re.DOTALL)
            for match in json_matches:
                try:
                    # Find the complete JSON by matching braces
                    start_idx = match.start()
                    brace_count = 0
                    end_idx = start_idx
                    for i in range(start_idx, len(response_text)):
                        if response_text[i] == '{':
                            brace_count += 1
                        elif response_text[i] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end_idx = i + 1
                                break
                    
                    if end_idx > start_idx:
                        json_text = response_text[start_idx:end_idx]
                        data = json.loads(json_text)
                        
                        # Check if it's a direct workflow definition
                        if "name" in data and "steps" in data:
                            logger.info("Found direct workflow definition (no 'workflow' key)")
                            return data, []
                        
                        # Or if it has "workflow" key
                        if "workflow" in data:
                            return data.get("workflow"), data.get("changes", [])
                except:
                    continue
            
            # Strategy 4: Original method - find first { and last }
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_text = response_text[start_idx:end_idx]
                try:
                    data = json.loads(json_text)
                    
                    # Check if it's a direct workflow definition
                    if "name" in data and "steps" in data:
                        logger.info("Found direct workflow definition in fallback")
                        return data, []
                    
                    # Or if it has "workflow" key
                    workflow = data.get("workflow")
                    changes = data.get("changes", [])
                    
                    if workflow:
                        return workflow, changes
                except json.JSONDecodeError:
                    pass
            
            logger.error("Could not find valid JSON in response")
            return None, []
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            logger.debug(f"Response text preview: {response_text[:1000]}")
            return None, []
        except Exception as e:
            logger.error(f"Error parsing modification response: {e}")
            logger.debug(f"Response text preview: {response_text[:1000] if response_text else 'Empty'}")
            return None, []
    
    async def fix_workflow_from_error(
        self,
        workflow: Dict[str, Any],
        error_info: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Fix workflow based on execution error
        
        Args:
            workflow: Current workflow definition
            error_info: Error information including logs, step_id, error message
            
        Returns:
            Fixed workflow definition
        """
        error_step_id = error_info.get("error_step_id")
        error_message = error_info.get("error_message")
        error_traceback = error_info.get("error_traceback", "")
        logs = error_info.get("logs", "")
        
        error_logs = f"""Error Step ID: {error_step_id}
Error Message: {error_message}

Traceback:
{error_traceback}

Execution Logs:
{logs}
"""
        
        modification_request = f"Fix the error that occurred in step {error_step_id}: {error_message}"
        
        modified_workflow, changes = await self.modify_workflow(
            current_workflow=workflow,
            modification_request=modification_request,
            error_logs=error_logs,
        )
        
        return modified_workflow
    
    async def suggest_improvements(
        self,
        workflow: Dict[str, Any],
    ) -> List[str]:
        """Suggest improvements for a workflow
        
        Args:
            workflow: Workflow definition
            
        Returns:
            List of improvement suggestions
        """
        logger.info("Generating improvement suggestions")
        
        prompt = f"""Analyze this workflow and suggest improvements:

```json
{json.dumps(workflow, indent=2)}
```

Provide 3-5 specific suggestions for:
1. Performance optimization
2. Error handling
3. Code quality
4. Best practices
5. User experience

Format as a JSON list: ["suggestion1", "suggestion2", ...]"""
        
        messages = [
            SystemMessage(content="You are an expert workflow optimization consultant."),
            HumanMessage(content=prompt),
        ]
        
        try:
            response = await self.llm.ainvoke(messages)
            response_text = response.content
            
            # Try to parse as JSON list
            start_idx = response_text.find('[')
            end_idx = response_text.rfind(']') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_text = response_text[start_idx:end_idx]
                suggestions = json.loads(json_text)
                return suggestions
            
            # Fallback: split by newlines
            suggestions = [
                line.strip() for line in response_text.split('\n')
                if line.strip() and not line.strip().startswith('#')
            ]
            return suggestions[:5]
        
        except Exception as e:
            logger.error(f"Error generating suggestions: {e}")
            return []

