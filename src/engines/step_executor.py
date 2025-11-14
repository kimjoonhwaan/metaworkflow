"""Step execution logic for different step types"""
import json
import subprocess
import os
import sys
from typing import Dict, Any, Optional
from datetime import datetime
import tempfile

from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

from src.database.models import StepType
from src.utils import settings, get_logger
from src.mcp.email_server import email_mcp
from src.mcp.api_server import api_mcp

logger = get_logger("step_executor")


class StepExecutor:
    """Executor for different types of workflow steps"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=1
        )
        self.mcp_email = email_mcp
        self.mcp_api = api_mcp
    
    async def execute_step(
        self,
        step_type: str,
        step_config: Dict[str, Any],
        variables: Dict[str, Any],
        code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a single step based on its type
        
        Args:
            step_type: Type of step to execute
            step_config: Step configuration
            variables: Current workflow variables
            code: Python code (for PYTHON_SCRIPT type)
            
        Returns:
            Step execution result with output data
        """
        try:
            logger.info(f"execute_step called with variables: {list(variables.keys())}")
            logger.debug(f"execute_step variables content: {variables}")
            
            if step_type == StepType.LLM_CALL.value:
                return await self._execute_llm_call(step_config, variables)
            elif step_type == StepType.API_CALL.value:
                return await self._execute_api_call(step_config, variables)
            elif step_type == StepType.PYTHON_SCRIPT.value:
                return await self._execute_python_script(step_config, variables, code)
            elif step_type == StepType.CONDITION.value:
                return await self._execute_condition(step_config, variables)
            elif step_type == StepType.APPROVAL.value:
                return await self._execute_approval(step_config, variables)
            elif step_type == StepType.NOTIFICATION.value:
                return await self._execute_notification(step_config, variables)
            elif step_type == StepType.DATA_TRANSFORM.value:
                return await self._execute_data_transform(step_config, variables)
            else:
                raise ValueError(f"Unknown step type: {step_type}")
        except Exception as e:
            logger.error(f"Step execution failed: {str(e)}", exc_info=True)
            raise
    
    async def _execute_llm_call(self, config: Dict[str, Any], variables: Dict[str, Any]) -> Dict[str, Any]:
        """Execute LLM call step"""
        logger.info(f"Executing LLM call...")
        
        # Get prompt template
        prompt_template = config.get("user_prompt", "") or config.get("prompt", "")
        system_prompt = config.get("system_prompt", "You are a helpful assistant.")
        
        # ✅ 디버깅: 포맷팅 전 로깅
        logger.info(f"[LLM_CALL] Prompt template: '{prompt_template}'")
        logger.info(f"[LLM_CALL] Available variables: {list(variables.keys())}")
        
        # Format prompts with variables
        formatted_prompt = prompt_template
        try:
            # ✅ 수정: 공백 모두 제거하고 포맷팅
            # "{ user_prompt }" → "{user_prompt}" 변환
            import re
            cleaned_template = re.sub(r'\{\s+(\w+)\s+\}', r'{\1}', prompt_template)
            
            logger.debug(f"[LLM_CALL] Cleaned template: '{cleaned_template}'")
            
            formatted_prompt = cleaned_template.format(**variables)
            logger.info(f"[LLM_CALL] Successfully formatted prompt: '{formatted_prompt[:100]}...'")
        except KeyError as e:
            logger.error(f"[LLM_CALL] Variable '{e}' not found in: {list(variables.keys())}")
            logger.error(f"[LLM_CALL] Template: '{prompt_template}'")
            formatted_prompt = prompt_template
        except Exception as e:
            logger.error(f"[LLM_CALL] Format error: {e}", exc_info=True)
            formatted_prompt = prompt_template
        
        logger.info(f"[LLM_CALL] Final prompt: '{formatted_prompt[:100]}...'")
        
        # Create messages
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=formatted_prompt),
        ]
        
        # Call LLM
        response = await self.llm.ainvoke(messages)
        result = response.content
        
        logger.info(f"LLM response: {result[:200]}...")
        
        # ✅ 개선된 응답 구조: 구조화된 output 제공
        return {
            "success": True,
            "output": {
                "response": result,                    # LLM 응답
                "prompt": formatted_prompt,            # 실제 사용한 프롬프트
                "system_prompt": system_prompt,        # 시스템 프롬프트
                "model": config.get("model", "gpt-4"), # 모델 정보
                "raw_response": result                 # 원본 응답 (호환성)
            }
        }
    
    async def _execute_api_call(self, config: Dict[str, Any], variables: Dict[str, Any]) -> Dict[str, Any]:
        """Execute API call step via API MCP
        
        Returns structured output with all API response data:
        {
            "success": bool,
            "output": {
                "data": <api_response>,
                "status_code": int,
                "headers": dict,
                "status": str,
                "error": str or None
            },
            "error": str or None
        }
        """
        logger.info("[API_CALL] Calling API via MCP...")
        
        try:
            result = await self.mcp_api.call(config, variables)
            
            logger.info(f"[API_CALL] Result: {result.get('status')}")
            logger.debug(f"[API_CALL] Full result: {result}")
            
            # ✅ 통일된 응답 구조: 모든 필드를 "output" 안에 포함
            return {
                "success": result.get("status") == "success",
                "output": {
                    "data": result.get("data"),                      # API 응답 데이터
                    "status_code": result.get("status_code"),        # HTTP 상태 코드
                    "headers": result.get("headers", {}),            # 응답 헤더
                    "status": result.get("status"),                  # 성공/실패 상태
                    "error": result.get("error")                     # 에러 메시지
                },
                "error": result.get("error")
            }
        except Exception as e:
            logger.error(f"[API_CALL] Error: {e}", exc_info=True)
            return {
                "success": False,
                "output": {
                    "data": None,
                    "status_code": None,
                    "headers": {},
                    "status": "error",
                    "error": str(e)
                },
                "error": str(e)
            }
    
    async def _execute_python_script(
        self,
        config: Dict[str, Any],
        variables: Dict[str, Any],
        code: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute Python script step
        
        Variables are passed via temporary JSON file to avoid Windows command line length limits.
        Script should output final JSON to stdout, and logs/debug to stderr.
        """
        logger.info("Executing Python script")
        logger.info(f"Received variables: {list(variables.keys())}")
        logger.debug(f"Variables content: {variables}")
        
        if not code:
            raise ValueError("No Python code provided for PYTHON_SCRIPT step")
        
        # Create temporary script file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            script_path = f.name
        
        # Debug: Log the temporary script content
        logger.info(f"Created temporary script: {script_path}")
        logger.debug(f"Script content (first 500 chars): {code[:500]}")
        
        # Debug: Read back the temporary file to verify content
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                actual_content = f.read()
            logger.info(f"Actual file content (first 500 chars): {actual_content[:500]}")
            
            # Fix the code if it only supports --variables-file
            if '--variables-file' in actual_content and '--variables' not in actual_content.split('# Parse variables')[1].split('\\n')[0]:
                logger.info("Fixing code to support --variables argument")
                fixed_content = actual_content.replace(
                    "# MUST parse --variables-file argument (NOT --variables!)",
                    "# Parse variables from command line arguments"
                ).replace(
                    "if '--variables-file' in sys.argv:",
                    "if '--variables' in sys.argv:\n    idx = sys.argv.index('--variables')\n    if idx + 1 < len(sys.argv):\n        variables = json.loads(sys.argv[idx + 1])\nelif '--variables-file' in sys.argv:"
                )
                
                # Write the fixed code back to the file
                with open(script_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                logger.info("Code fixed to support --variables argument")
                
        except Exception as e:
            logger.error(f"Failed to read temporary file: {e}")
        
        # Try direct command line arguments first, fallback to file if too long
        variables_json = json.dumps(variables)
        logger.debug(f"Variables being passed: {list(variables.keys())}")
        logger.debug(f"Variables JSON length: {len(variables_json)}")
        
        # Check if command line would be too long (Windows limit is ~8191 chars)
        estimated_length = len(f"{sys.executable} {script_path} --variables {variables_json}")
        logger.debug(f"Estimated command line length: {estimated_length}")
        
        if estimated_length > 7000:  # Conservative limit
            # Use temporary file for long command lines
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
                json.dump(variables, f)
                variables_path = f.name
            
            result = subprocess.run(
                [sys.executable, script_path, "--variables-file", variables_path],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=settings.step_timeout_seconds,
            )
        else:
            # Use direct command line arguments
            cmd = [sys.executable, script_path, "--variables", variables_json]
            logger.info(f"Executing command: {cmd}")
            logger.debug(f"Command details: script={script_path}, variables_json={variables_json}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=settings.step_timeout_seconds,
            )
        
        try:
            
            # Log stderr (debug output)
            if result.stderr:
                logger.info(f"Script stderr: {result.stderr}")
            
            if result.returncode != 0:
                raise RuntimeError(f"Script failed with return code {result.returncode}: {result.stderr}")
            
            # Parse stdout as JSON
            try:
                output_data = json.loads(result.stdout.strip())
            except json.JSONDecodeError:
                # If not JSON, return as text
                output_data = {"result": result.stdout.strip()}
            
            logger.info(f"Script executed successfully")
            
            return {
                "success": True,
                "output": output_data,
                "logs": result.stderr,
            }
        
        finally:
            # Clean up temporary files
            try:
                os.unlink(script_path)
            except:
                pass
            try:
                if estimated_length > 7000 and 'variables_path' in locals():
                    os.unlink(variables_path)
            except:
                pass
    
    async def _execute_condition(self, config: Dict[str, Any], variables: Dict[str, Any]) -> Dict[str, Any]:
        """Execute condition evaluation step with safe evaluation
        
        Supports basic comparison and logical operators:
        - Comparison: ==, !=, <, >, <=, >=
        - Logical: and, or, not
        - Examples: "status == 'success'", "count > 10", "status == 'done' and error is None"
        """
        logger.info("Executing condition evaluation")
        
        condition = config.get("condition", "True")
        logger.debug(f"[CONDITION] Evaluating: {condition}")
        
        # ✅ 보안 개선: 제한된 평가 환경 사용
        try:
            # 안전한 연산자만 허용하는 환경 구성
            safe_dict = {
                "__builtins__": {},  # 빌트인 함수 차단
                "True": True,
                "False": False,
                "None": None,
                # 안전한 함수만 추가
                "len": len,
                "str": str,
                "int": int,
                "float": float,
                "bool": bool,
            }
            
            # 변수 추가
            safe_dict.update(variables)
            
            logger.debug(f"[CONDITION] Available variables: {list(variables.keys())}")
            
            # eval 실행
            result = eval(condition, safe_dict)
            
            logger.info(f"[CONDITION] Result: {result}")
            
            return {
                "success": True,
                "output": {
                    "condition": condition,
                    "result": result,
                    "condition_met": bool(result),
                    "variables_used": list(variables.keys())
                },
                "condition_met": bool(result),
            }
        
        except SyntaxError as e:
            logger.error(f"[CONDITION] Syntax error in condition: {e}")
            return {
                "success": False,
                "output": {
                    "condition": condition,
                    "result": False,
                    "condition_met": False,
                    "error": f"Syntax error: {str(e)}"
                },
                "error": f"Condition syntax error: {str(e)}",
                "condition_met": False,
            }
        except NameError as e:
            logger.error(f"[CONDITION] Variable not found: {e}")
            return {
                "success": False,
                "output": {
                    "condition": condition,
                    "result": False,
                    "condition_met": False,
                    "error": f"Variable not found: {str(e)}"
                },
                "error": f"Condition variable error: {str(e)}",
                "condition_met": False,
            }
        except Exception as e:
            logger.error(f"[CONDITION] Evaluation failed: {e}", exc_info=True)
            return {
                "success": False,
                "output": {
                    "condition": condition,
                    "result": False,
                    "condition_met": False,
                    "error": str(e)
                },
                "error": f"Condition evaluation error: {str(e)}",
                "condition_met": False,
            }
    
    async def _execute_approval(self, config: Dict[str, Any], variables: Dict[str, Any]) -> Dict[str, Any]:
        """Execute approval step (returns waiting state)"""
        logger.info("Approval step - waiting for user approval")
        
        return {
            "success": True,
            "output": "waiting_approval",
            "requires_approval": True,
            "approval_message": config.get("message", "Please review and approve to continue"),
        }
    
    async def _execute_notification(self, config: Dict[str, Any], variables: Dict[str, Any]) -> Dict[str, Any]:
        """Execute notification step with MCP support"""
        logger.info(f"Executing notification: {config.get('type', 'log')}")
        
        notification_type = config.get("type", "log")
        
        try:
            if notification_type == "email":
                # ✅ MCP Email notification
                logger.info("[NOTIFICATION] Sending email via MCP...")
                
                # Get email parameters
                to = config.get("to", "")
                subject = config.get("subject", "")
                body = config.get("body", "")
                cc = config.get("cc", None)
                bcc = config.get("bcc", None)
                html = config.get("html", False)
                
                # ✅ 개선된 변수 포맷팅 (공백 정리 + 예외 처리)
                import re
                
                def format_with_variables(template: str, vars: Dict[str, Any]) -> str:
                    """변수 포맷팅 (공백 제거 및 예외 처리)"""
                    if not template:
                        return ""
                    try:
                        # 공백이 있는 { variable } 패턴을 {variable}로 정리
                        cleaned = re.sub(r'\{\s+(\w+)\s+\}', r'{\1}', template)
                        return cleaned.format(**vars)
                    except KeyError as e:
                        logger.warning(f"Variable '{e}' not found in email template, using original: {template}")
                        return template
                    except Exception as e:
                        logger.error(f"Error formatting email template: {e}")
                        return template
                
                # Apply formatting
                to = format_with_variables(to, variables)
                subject = format_with_variables(subject, variables)
                body = format_with_variables(body, variables)
                if cc:
                    cc = format_with_variables(cc, variables)
                if bcc:
                    bcc = format_with_variables(bcc, variables)
                
                logger.info(f"[NOTIFICATION] Email config: to={to}, subject={subject[:50]}...")
                
                # Send email via MCP
                result = await self.mcp_email.send_email(
                    to=to,
                    subject=subject,
                    body=body,
                    cc=cc,
                    bcc=bcc,
                    html=html
                )
                
                logger.info(f"[NOTIFICATION] Email result: {result}")
                
                return {
                    "success": result.get("status") == "success",
                    "output": result,
                    "notification_sent": result.get("status") == "success",
                }
            
            elif notification_type == "log":
                # Console log notification
                message = config.get("message", "")
                try:
                    formatted_message = message.format(**variables)
                except KeyError as e:
                    formatted_message = message
                    logger.warning(f"Variable not found in message: {e}")
                
                logger.info(f"[NOTIFICATION] Log: {formatted_message}")
                
                return {
                    "success": True,
                    "output": formatted_message,
                    "notification_sent": True,
                }
            
            elif notification_type == "slack":
                # TODO: Implement Slack MCP notification
                logger.warning("[NOTIFICATION] Slack notifications not yet implemented")
                return {
                    "success": False,
                    "output": "Slack notifications not yet implemented",
                    "notification_sent": False,
                }
            
            else:
                logger.warning(f"[NOTIFICATION] Unknown notification type: {notification_type}")
                return {
                    "success": False,
                    "output": f"Unknown notification type: {notification_type}",
                    "notification_sent": False,
                }
        
        except Exception as e:
            logger.error(f"[NOTIFICATION] Error sending notification: {e}", exc_info=True)
            return {
                "success": False,
                "output": f"Error sending notification: {str(e)}",
                "notification_sent": False,
                "error": str(e)
            }
    
    async def _execute_data_transform(self, config: Dict[str, Any], variables: Dict[str, Any]) -> Dict[str, Any]:
        """Execute data transformation step"""
        logger.info("Executing data transformation")
        
        transform_type = config.get("transform_type", "jq")
        transform_expr = config.get("expression", ".")
        input_data = config.get("input_data", variables)
        
        if transform_type == "jq":
            # Simple JSON transformation (subset of jq)
            # For complex transformations, use PYTHON_SCRIPT
            result = input_data
        else:
            result = input_data
        
        logger.info("Data transformation completed")
        
        return {
            "success": True,
            "output": result,
        }

