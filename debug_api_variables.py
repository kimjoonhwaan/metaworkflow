#!/usr/bin/env python3
"""Debug API variables for weather workflow"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, 'src')

from src.database.session import get_session
from src.database.models import Workflow
from src.engines.step_executor import StepExecutor

async def debug_weather_api_variables():
    """Debug weather API variables"""
    print("🔍 기상청 API 워크플로우 변수 디버깅...")
    
    try:
        with get_session() as session:
            # Find weather-related workflows
            workflows = session.query(Workflow).filter(
                Workflow.name.contains("기상") | 
                Workflow.name.contains("날씨") |
                Workflow.name.contains("weather")
            ).all()
            
            if not workflows:
                print("❌ 기상 관련 워크플로우를 찾을 수 없습니다.")
                return
            
            for workflow in workflows:
                print(f"\n📋 워크플로우: {workflow.name}")
                print(f"   ID: {workflow.id}")
                
                # Check variables
                if workflow.variables:
                    print("   📝 워크플로우 변수:")
                    for key, value in workflow.variables.items():
                        print(f"     {key}: {value}")
                else:
                    print("   ⚠️ 워크플로우 변수가 설정되지 않았습니다.")
                
                # Check API steps
                api_steps = [step for step in workflow.steps if step.step_type.value == "API_CALL"]
                if api_steps:
                    print("   🌐 API 호출 스텝:")
                    for step in api_steps:
                        print(f"     - {step.name}")
                        config = step.config
                        if 'params' in config:
                            print(f"       파라미터: {config['params']}")
                        if 'url' in config:
                            print(f"       URL: {config['url']}")
                else:
                    print("   ⚠️ API 호출 스텝이 없습니다.")
    
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_weather_api_variables())
