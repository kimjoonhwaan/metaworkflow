"""Meta Workflow Agent - Creates workflows through conversation"""
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage, AIMessage

from src.agents.prompts import (
    WORKFLOW_CREATION_SYSTEM_PROMPT,
    QUESTION_EXTRACTION_PROMPT,
)
from src.utils import settings, get_logger, CodeValidator
from src.services.rag_service import get_rag_service

logger = get_logger("meta_agent")


class MetaWorkflowAgent:
    """Meta agent that creates workflows through natural conversation"""
    
    def __init__(self):
        try:
            self.llm = ChatOpenAI(
                model=settings.openai_model,
                api_key=settings.openai_api_key,
                temperature=1,
            )
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
            raise ValueError("OpenAI API 초기화 실패. API 키를 확인하세요.")
        
        self.conversation_history: List[Dict[str, str]] = []
        self.workflow_context: Dict[str, Any] = {}
        self.rag_service = get_rag_service()
    
    async def process_user_input(
        self,
        user_input: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Tuple[str, Optional[Dict[str, Any]], bool, Dict[str, Any]]:
        """Process user input and generate workflow or ask questions
        
        Args:
            user_input: User's message
            conversation_history: Previous conversation history
            
        Returns:
            Tuple of (response_message, workflow_definition, is_complete)
        """
        logger.info(f"Processing user input: {user_input[:100]}...")
        
        # Use provided history or instance history
        if conversation_history is not None:
            self.conversation_history = conversation_history
        
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_input,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        # Get relevant context from RAG
        rag_context = await self.rag_service.get_relevant_context_for_workflow_generation(user_input)
        rag_used = bool(rag_context)
        
        # Build enhanced system prompt with RAG context
        enhanced_system_prompt = WORKFLOW_CREATION_SYSTEM_PROMPT
        if rag_context:
            enhanced_system_prompt += "\n\n" + rag_context
            logger.info(f"Enhanced system prompt with RAG context: {len(rag_context)} chars")
        
        # Build messages for LLM
        messages = [SystemMessage(content=enhanced_system_prompt)]
        
        for msg in self.conversation_history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
        
        # Call LLM
        try:
            response = await self.llm.ainvoke(messages)
            response_text = response.content
            
            logger.info(f"LLM response received: {len(response_text)} chars")
            
            # Try to parse as JSON workflow definition
            workflow_def, is_ready = self._parse_workflow_response(response_text)
            
            if workflow_def and is_ready:
                # Validate Python code in workflow
                code_validation_failed = False
                validation_issues = []
                
                if "workflow" in workflow_def:
                    actual_workflow = workflow_def["workflow"]
                else:
                    actual_workflow = workflow_def
                
                for step in actual_workflow.get("steps", []):
                    if step.get("step_type") == "PYTHON_SCRIPT" and step.get("code"):
                        is_valid, issues = CodeValidator.validate_python_code(step["code"])
                        if not is_valid:
                            code_validation_failed = True
                            validation_issues.append(f"Step '{step.get('name')}': {issues[0]}")
                
                # If validation failed, ask AI to fix
                if code_validation_failed:
                    logger.warning(f"Code validation failed: {validation_issues}")
                    
                    fix_request = (
                        f"생성한 워크플로우에 코드 오류가 있습니다:\n\n" +
                        "\n".join(f"- {issue}" for issue in validation_issues) +
                        "\n\n이 오류들을 수정한 완전한 워크플로우를 다시 생성해주세요. "
                        "특히 f-string 안에서 따옴표가 중첩되지 않도록 주의하세요."
                    )
                    
                    # Recursively call to fix
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": response_text,
                        "timestamp": datetime.utcnow().isoformat(),
                    })
                    
                    logger.info("Requesting AI to fix code validation issues...")
                    return await self.process_user_input(fix_request, self.conversation_history)
                
                # Workflow is complete and valid
                self.conversation_history.append({
                    "role": "assistant",
                    "content": response_text,
                    "timestamp": datetime.utcnow().isoformat(),
                })
                
                return (
                    "워크플로우가 생성되었습니다. 검토 후 저장해주세요.",
                    workflow_def,
                    True,
                    {"rag_used": rag_used, "rag_context_length": len(rag_context) if rag_context else 0}
                )
            
            elif workflow_def and not is_ready:
                # More questions needed
                questions = workflow_def.get("questions", [])
                self.conversation_history.append({
                    "role": "assistant",
                    "content": response_text,
                    "timestamp": datetime.utcnow().isoformat(),
                })
                
                question_text = self._format_questions(questions)
                return (question_text, None, False, {"rag_used": rag_used, "rag_context_length": len(rag_context) if rag_context else 0})
            
            else:
                # Regular conversation response
                self.conversation_history.append({
                    "role": "assistant",
                    "content": response_text,
                    "timestamp": datetime.utcnow().isoformat(),
                })
                
                return (response_text, None, False, {"rag_used": rag_used, "rag_context_length": len(rag_context) if rag_context else 0})
        
        except Exception as e:
            logger.error(f"Error processing user input: {e}", exc_info=True)
            return (
                f"죄송합니다. 처리 중 오류가 발생했습니다: {str(e)}",
                None,
                False,
                {"rag_used": False, "rag_context_length": 0}
            )
    
    def _parse_workflow_response(self, response_text: str) -> Tuple[Optional[Dict[str, Any]], bool]:
        """Parse LLM response to extract workflow definition
        
        Args:
            response_text: LLM response text
            
        Returns:
            Tuple of (workflow_definition, is_ready)
        """
        try:
            import re
            
            # Strategy 1: Look for JSON code block
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(1)
                data = json.loads(json_text)
                if "workflow" in data or "name" in data:
                    is_ready = data.get("ready", True)
                    return data, is_ready
            
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
                    is_ready = data.get("ready", True)
                    return data, is_ready
            
            # Strategy 3: Look for direct workflow definition
            json_matches = re.finditer(r'\{[^{}]*"name"[^{}]*"steps"[^{}]*\}', response_text, re.DOTALL)
            for match in json_matches:
                try:
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
                        
                        if "name" in data and "steps" in data:
                            logger.info("Found direct workflow definition")
                            return {"workflow": data, "ready": True}, True
                except:
                    continue
            
            # Strategy 4: Original method
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_text = response_text[start_idx:end_idx]
                data = json.loads(json_text)
                
                # Check if it's a workflow definition
                if "workflow" in data:
                    is_ready = data.get("ready", False)
                    return data, is_ready
                elif "name" in data and "steps" in data:
                    return {"workflow": data, "ready": True}, True
            
            logger.debug("Response is not valid JSON, treating as conversation")
            return None, False
        
        except json.JSONDecodeError:
            logger.debug("Response is not valid JSON, treating as conversation")
            return None, False
        except Exception as e:
            logger.error(f"Error parsing workflow response: {e}")
            return None, False
    
    def _format_questions(self, questions: List[str]) -> str:
        """Format questions for display
        
        Args:
            questions: List of questions
            
        Returns:
            Formatted question text
        """
        if not questions:
            return "추가 정보가 필요합니다. 더 자세히 설명해주세요."
        
        formatted = "워크플로우를 생성하기 위해 몇 가지 추가 정보가 필요합니다:\n\n"
        for i, question in enumerate(questions, 1):
            formatted += f"{i}. {question}\n"
        
        return formatted
    
    async def create_workflow_from_description(
        self,
        description: str,
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create workflow directly from description (non-interactive)
        
        Args:
            description: Workflow description
            additional_context: Additional context information
            
        Returns:
            Workflow definition
        """
        logger.info("Creating workflow from description (non-interactive mode)")
        
        prompt = f"""Create a complete workflow based on this description:

{description}

Additional context: {json.dumps(additional_context or {}, indent=2)}

Generate a complete workflow definition with all necessary steps and code. Make reasonable assumptions for missing information."""

        messages = [
            SystemMessage(content=WORKFLOW_CREATION_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]
        
        response = await self.llm.ainvoke(messages)
        workflow_def, is_ready = self._parse_workflow_response(response.content)
        
        if workflow_def and "workflow" in workflow_def:
            return workflow_def["workflow"]
        
        raise ValueError("Failed to create workflow from description")
    
    def reset_conversation(self):
        """Reset conversation history"""
        self.conversation_history = []
        self.workflow_context = {}
        logger.info("Conversation history reset")
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get current conversation history"""
        return self.conversation_history.copy()
    
    def load_conversation_history(self, history: List[Dict[str, str]]):
        """Load conversation history"""
        self.conversation_history = history
        logger.info(f"Loaded {len(history)} conversation messages")

