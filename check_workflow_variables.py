#!/usr/bin/env python3
"""Check workflow variables for weather API"""

import asyncio
import sys
import os
import json

# Add src to path
sys.path.insert(0, 'src')

from src.database.session import get_session
from src.database.models import Workflow

def check_workflow_variables():
    """Check workflow variables"""
    print("🔍 기상청 API 워크플로우 변수 확인...")
    
    try:
        with get_session() as session:
            # Find weather-related workflows
            workflows = session.query(Workflow).filter(
                Workflow.name.contains("기상") | 
                Workflow.name.contains("날씨") |
                Workflow.name.contains("weather") |
                Workflow.name.contains("KMA")
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
                
                # Check steps
                print("   🔧 스텝 정보:")
                for step in workflow.steps:
                    print(f"     - {step.name} ({step.step_type.value})")
                    if step.step_type.value == "API_CALL":
                        config = step.config
                        print(f"       URL: {config.get('url', 'N/A')}")
                        print(f"       Method: {config.get('method', 'GET')}")
                        if 'params' in config:
                            print(f"       Params: {config['params']}")
                        print(f"       Input mapping: {step.input_mapping}")
                        print(f"       Output mapping: {step.output_mapping}")
                
                # Show workflow definition
                print(f"\n   📄 워크플로우 정의 (일부):")
                definition = workflow.definition
                if 'steps' in definition:
                    for i, step_def in enumerate(definition['steps']):
                        if step_def.get('step_type') == 'API_CALL':
                            print(f"     스텝 {i}: {step_def.get('name')}")
                            print(f"       URL: {step_def.get('config', {}).get('url')}")
                            print(f"       Input mapping: {step_def.get('input_mapping')}")
                            print(f"       Output mapping: {step_def.get('output_mapping')}")
    
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_workflow_variables()
