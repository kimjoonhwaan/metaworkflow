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

logger = get_logger("step_executor")


class StepExecutor:
    """Executor for different types of workflow steps"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=1
        )
    
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
        logger.info(f"Executing LLM call: {config.get('prompt', '')[:100]}...")
        
        # Get prompt template and format with variables
        prompt_template = config.get("prompt", "")
        system_prompt = config.get("system_prompt", "You are a helpful assistant.")
        
        # Format prompts with variables
        try:
            formatted_prompt = prompt_template.format(**variables)
        except KeyError as e:
            formatted_prompt = prompt_template
            logger.warning(f"Variable not found in prompt: {e}")
        
        # Create messages
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=formatted_prompt),
        ]
        
        # Call LLM
        response = await self.llm.ainvoke(messages)
        result = response.content
        
        logger.info(f"LLM response: {result[:200]}...")
        
        return {
            "success": True,
            "output": result,
            "raw_response": result,
        }
    
    async def _execute_api_call(self, config: Dict[str, Any], variables: Dict[str, Any]) -> Dict[str, Any]:
        """Execute API call step"""
        import httpx
        
        logger.info(f"Executing API call: {config.get('method', 'GET')} {config.get('url', '')}")
        
        method = config.get("method", "GET").upper()
        url = config.get("url", "")
        headers = config.get("headers", {})
        params = config.get("params", {})
        body = config.get("body", {})
        
        # Format URL, params, and body with variables
        try:
            # Format URL - handle both template strings and variable references
            if url.startswith('{') and url.endswith('}'):
                # Direct variable reference like {api_url}
                var_name = url[1:-1]
                if var_name in variables:
                    url = variables[var_name]
                else:
                    logger.warning(f"Variable {var_name} not found for URL")
            else:
                # Template string with variables
                url = url.format(**variables)
            logger.debug(f"Formatted URL: {url}")
            
            # Format params with variables
            if isinstance(params, dict):
                formatted_params = {}
                for key, value in params.items():
                    if isinstance(value, str):
                        try:
                            formatted_params[key] = value.format(**variables)
                        except KeyError as e:
                            logger.warning(f"Variable {e} not found for param {key}, using original value")
                            formatted_params[key] = value
                    else:
                        formatted_params[key] = value
                params = formatted_params
                logger.debug(f"Formatted params: {params}")
            
            # Format body with variables
            if isinstance(body, str):
                try:
                    body = body.format(**variables)
                except KeyError as e:
                    logger.warning(f"Variable {e} not found in body, using original value")
            
        except KeyError as e:
            logger.warning(f"Variable not found in API config: {e}")
        
        async with httpx.AsyncClient() as client:
            if method == "GET":
                response = await client.get(url, headers=headers, params=params)
            elif method == "POST":
                response = await client.post(url, headers=headers, json=body)
            elif method == "PUT":
                response = await client.put(url, headers=headers, json=body)
            elif method == "DELETE":
                response = await client.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
        
        response.raise_for_status()
        
        try:
            result_data = response.json()
        except:
            result_data = response.text
        
        logger.info(f"API call successful: {response.status_code}")
        
        return {
            "success": True,
            "output": result_data,
            "status_code": response.status_code,
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
        """Execute condition evaluation step"""
        logger.info("Executing condition evaluation")
        
        condition = config.get("condition", "True")
        
        # Evaluate condition with variables
        try:
            result = eval(condition, {"__builtins__": {}}, variables)
        except Exception as e:
            logger.error(f"Condition evaluation failed: {e}")
            result = False
        
        logger.info(f"Condition result: {result}")
        
        return {
            "success": True,
            "output": result,
            "condition_met": bool(result),
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
        """Execute notification step"""
        logger.info(f"Executing notification: {config.get('type', 'log')}")
        
        notification_type = config.get("type", "log")
        message = config.get("message", "")
        
        # Format message with variables
        try:
            formatted_message = message.format(**variables)
        except KeyError as e:
            formatted_message = message
            logger.warning(f"Variable not found in message: {e}")
        
        if notification_type == "log":
            logger.info(f"Notification: {formatted_message}")
        elif notification_type == "email":
            # TODO: Implement email notification
            logger.info(f"Email notification (not implemented): {formatted_message}")
        elif notification_type == "slack":
            # TODO: Implement Slack notification
            logger.info(f"Slack notification (not implemented): {formatted_message}")
        
        return {
            "success": True,
            "output": formatted_message,
            "notification_sent": True,
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

