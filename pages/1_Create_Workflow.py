"""
워크플로우 생성 페이지 - AI 대화형 생성
"""
import streamlit as st
import asyncio
import json
from datetime import datetime
import os

# Check environment variables first
if not os.getenv("OPENAI_API_KEY"):
    st.error("⚠️ OPENAI_API_KEY 환경 변수가 설정되지 않았습니다. .env 파일을 확인해주세요.")
    st.stop()

from src.database.session import get_session
from src.agents import MetaWorkflowAgent
from src.services import WorkflowService, FolderService
from src.database.models import WorkflowStatus
from src.utils import CodeValidator

def _format_ai_response(content):
    """Format AI response to be more user-friendly"""
    try:
        # Try to parse as JSON first
        if content.strip().startswith('{'):
            data = json.loads(content)
            
            # If it's a workflow response with questions
            if isinstance(data, dict) and "questions" in data:
                workflow = data.get("workflow", {})
                questions = data.get("questions", [])
                
                formatted = []
                
                # Add workflow info
                if workflow:
                    formatted.append(f"**워크플로우명:** {workflow.get('name', 'N/A')}")
                    formatted.append(f"**설명:** {workflow.get('description', 'N/A')}")
                    formatted.append("")
                
                # Add questions
                if questions:
                    formatted.append("**질문사항:**")
                    for i, q in enumerate(questions, 1):
                        formatted.append(f"{i}. {q}")
                    formatted.append("")
                    formatted.append("위 질문들에 답변해주시면 완전한 워크플로우를 생성하겠습니다.")
                
                return "\n".join(formatted)
            
            # If it's a complete workflow
            elif isinstance(data, dict) and "workflow" in data:
                workflow = data["workflow"]
                formatted = []
                
                formatted.append(f"**워크플로우명:** {workflow.get('name', 'N/A')}")
                formatted.append(f"**설명:** {workflow.get('description', 'N/A')}")
                
                steps = workflow.get("steps", [])
                if steps:
                    formatted.append(f"**스텝 수:** {len(steps)}개")
                    formatted.append("")
                    formatted.append("**스텝 목록:**")
                    for i, step in enumerate(steps, 1):
                        formatted.append(f"{i}. {step.get('name', 'Unnamed')} ({step.get('step_type', 'Unknown')})")
                
                return "\n".join(formatted)
        
        # If not JSON or doesn't match expected format, return as is
        return content
        
    except json.JSONDecodeError:
        # If it's not valid JSON, return as is
        return content

st.set_page_config(
    page_title="워크플로우 생성",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 AI 대화형 워크플로우 생성")
st.markdown("자연어로 업무를 설명하면 AI가 자동으로 워크플로우를 만들어드립니다.")
st.markdown("---")

# Initialize (fresh session each time, no caching)
db = get_session()
workflow_service = WorkflowService(db)
folder_service = FolderService(db)

# Initialize session state
if "agent" not in st.session_state:
    try:
        st.session_state.agent = MetaWorkflowAgent()
    except Exception as e:
        st.error(f"Agent 초기화 실패: {str(e)}")
        st.info("OPENAI_API_KEY가 .env 파일에 제대로 설정되어 있는지 확인하세요.")
        st.stop()

if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

if "generated_workflow" not in st.session_state:
    st.session_state.generated_workflow = None

# Sidebar - Configuration
with st.sidebar:
    st.subheader("⚙️ 설정")
    
    # Folder selection
    folders = folder_service.list_folders()
    folder_options = ["(없음)"] + [f.name for f in folders]
    selected_folder_name = st.selectbox("폴더", folder_options)
    selected_folder_id = None
    if selected_folder_name != "(없음)":
        selected_folder = next((f for f in folders if f.name == selected_folder_name), None)
        if selected_folder:
            selected_folder_id = selected_folder.id
    
    # Tags
    tags_input = st.text_input("태그 (쉼표로 구분)", "")
    tags = [t.strip() for t in tags_input.split(",") if t.strip()]
    
    # Initial status
    initial_status = st.selectbox(
        "초기 상태",
        [WorkflowStatus.DRAFT, WorkflowStatus.ACTIVE],
        format_func=lambda x: {"DRAFT": "초안", "ACTIVE": "활성"}.get(x.value, x.value)
    )
    
    st.markdown("---")
    
    if st.button("🔄 대화 초기화", use_container_width=True):
        st.session_state.agent.reset_conversation()
        st.session_state.conversation_history = []
        st.session_state.generated_workflow = None
        st.rerun()
    
    st.markdown("---")
    st.subheader("🧪 테스트")
    
    if st.button("📝 샘플 워크플로우 생성", use_container_width=True):
        # Create a sample workflow for testing
        sample_workflow = {
            "name": "샘플 데이터 처리 워크플로우",
            "description": "테스트용 샘플 워크플로우입니다",
            "tags": ["sample", "test"],
            "steps": [
                {
                    "name": "데이터 수집",
                    "step_type": "LLM_CALL",
                    "order": 0,
                    "config": {
                        "description": "샘플 데이터를 생성합니다",
                        "prompt": "샘플 데이터 10개를 JSON 형식으로 생성해주세요",
                        "system_prompt": "You are a helpful assistant."
                    },
                    "output_mapping": {"collected_data": "output"}
                },
                {
                    "name": "데이터 처리",
                    "step_type": "PYTHON_SCRIPT",
                    "order": 1,
                    "config": {
                        "description": "수집된 데이터를 처리합니다"
                    },
                    "code": """import json
import sys

# Parse variables from file
variables = {}
if '--variables-file' in sys.argv:
    idx = sys.argv.index('--variables-file')
    if idx + 1 < len(sys.argv):
        with open(sys.argv[idx + 1], 'r', encoding='utf-8') as f:
            variables = json.load(f)

print(f"Processing data: {len(variables)} variables", file=sys.stderr)

try:
    result = {
        "status": "success",
        "processed_items": len(variables),
        "message": "Data processed successfully"
    }
    print(json.dumps(result))
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    print(json.dumps({"status": "error", "error": str(e)}))
    sys.exit(1)
""",
                    "input_mapping": {"data": "collected_data"}
                },
                {
                    "name": "결과 알림",
                    "step_type": "NOTIFICATION",
                    "order": 2,
                    "config": {
                        "description": "처리 결과를 알립니다",
                        "type": "log",
                        "message": "워크플로우 완료: {processed_items}개 처리됨"
                    }
                }
            ],
            "variables": {
                "sample_var": "test_value"
            },
            "metadata": {
                "python_requirements": [],
                "step_codes": {}
            }
        }
        st.session_state.generated_workflow = sample_workflow
        st.success("샘플 워크플로우가 생성되었습니다!")
        st.rerun()

# Main content
col_chat, col_workflow = st.columns([1, 1])

with col_chat:
    st.subheader("💬 AI와 대화하기")
    
            # Display conversation history
    if st.session_state.conversation_history:
        chat_container = st.container(height=400)
        with chat_container:
            for msg in st.session_state.conversation_history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                if role == "user":
                    with st.chat_message("user"):
                        st.write(content)
                else:
                    with st.chat_message("assistant"):
                        # Parse and display AI response in a user-friendly format
                        display_content = _format_ai_response(content)
                        st.write(display_content)
    else:
        st.info("👋 안녕하세요! 만들고 싶은 워크플로우를 자유롭게 설명해주세요.")
        
        with st.expander("💡 예시 보기"):
            st.markdown("""
            **예시 1:**
            "매일 아침 9시에 특정 웹사이트에서 데이터를 수집하고 이메일로 보내줘"
            
            **예시 2:**
            "API로 받은 데이터를 가공해서 데이터베이스에 저장하는 워크플로우 만들어줘"
            
            **예시 3:**
            "주간 보고서를 자동으로 생성하고 승인 후 슬랙으로 전송하는 프로세스 필요해"
            """)

# User input - moved outside column to ensure it's always visible
st.markdown("---")
user_input = st.chat_input("업무를 설명하거나 질문에 답변해주세요...", key="chat_input_main")

if user_input:
    # Process user input
    with st.spinner("AI가 생각하고 있습니다..."):
        try:
            # Run async function
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response_message, workflow_def, is_complete, rag_info = loop.run_until_complete(
                st.session_state.agent.process_user_input(
                    user_input,
                    st.session_state.conversation_history
                )
            )
            loop.close()
            
            # Update conversation history
            st.session_state.conversation_history = st.session_state.agent.get_conversation_history()
            
            # If workflow is complete, store it
            if workflow_def and is_complete:
                # Extract the actual workflow from the response
                actual_workflow = workflow_def.get("workflow", workflow_def)
                st.session_state.generated_workflow = actual_workflow
                st.success("✅ 워크플로우가 생성되었습니다! 오른쪽에서 확인하고 저장하세요.")
                
                # Display RAG usage information
                if rag_info and rag_info.get("rag_used"):
                    st.info(f"🧠 RAG 지식 베이스 활용됨 (컨텍스트 길이: {rag_info.get('rag_context_length', 0)}자)")
                else:
                    st.info("💭 일반 AI 생성 (RAG 미사용)")
            
            st.rerun()
        
        except Exception as e:
            st.error(f"오류가 발생했습니다: {str(e)}")
            import traceback
            st.code(traceback.format_exc())

with col_workflow:
    st.subheader("📋 생성된 워크플로우")
    
    if st.session_state.generated_workflow:
        workflow_def = st.session_state.generated_workflow
        
        # Display workflow info
        st.markdown(f"**이름:** {workflow_def.get('name', 'Unnamed')}")
        st.markdown(f"**설명:** {workflow_def.get('description', 'No description')}")
        
        # Display steps
        steps = workflow_def.get("steps", [])
        st.markdown(f"**스텝 수:** {len(steps)}")
        
        # Display each step as separate expanders (no nesting)
        st.markdown("### 📋 스텝 목록")
        for i, step in enumerate(steps):
            # Validate Python code if present
            code_valid = True
            code_issues = []
            if step.get('code') and step.get('step_type') == 'PYTHON_SCRIPT':
                code_valid, code_issues = CodeValidator.validate_python_code(step['code'])
            
            # Show validation status in title
            status_icon = "✅" if (not step.get('code') or code_valid) else "⚠️"
            
            with st.expander(f"{status_icon} Step {i+1}: {step.get('name', 'Unnamed')}", expanded=(i==0)):
                st.write(f"**타입:** {step.get('step_type', 'Unknown')}")
                st.write(f"**설명:** {step.get('config', {}).get('description', 'No description')}")
                
                if step.get('input_mapping'):
                    st.write(f"**입력 매핑:** {step.get('input_mapping')}")
                if step.get('output_mapping'):
                    st.write(f"**출력 매핑:** {step.get('output_mapping')}")
                
                if step.get('code'):
                    st.markdown("**Python 코드:**")
                    
                    # Show validation results
                    if not code_valid:
                        st.error(f"❌ 코드 검증 실패: {len([i for i in code_issues if '문법 오류' in i])}개 오류")
                        for issue in code_issues:
                            if "문법 오류" in issue:
                                st.error(f"  • {issue}")
                            else:
                                st.warning(f"  • {issue}")
                        
                        # Show fix suggestions
                        fix_suggestion = CodeValidator.suggest_fix(step['code'], code_issues)
                        if fix_suggestion:
                            st.info(f"💡 수정 방법:\n{fix_suggestion}")
                    elif code_issues:
                        st.warning(f"⚠️ {len(code_issues)}개 경고")
                        for issue in code_issues:
                            st.caption(f"  • {issue}")
                    else:
                        st.success("✅ 코드 검증 통과")
                    
                    st.code(step['code'], language='python')
        
        st.markdown("---")
        
        # Display metadata
        metadata = workflow_def.get("metadata", {})
        if metadata:
            with st.expander("🔧 메타데이터"):
                if metadata.get("python_requirements"):
                    st.write("**Python 패키지:**")
                    st.write(", ".join(metadata["python_requirements"]))
                
                st.json(metadata)
        
        # Display full JSON
        with st.expander("📄 전체 워크플로우 정의 (JSON)"):
            st.json(workflow_def)
        
        st.markdown("---")
        
        # Save workflow
        col_a, col_b = st.columns(2)
        
        with col_a:
            if st.button("💾 워크플로우 저장", type="primary", use_container_width=True):
                try:
                    # Validate workflow structure
                    if "name" not in workflow_def:
                        st.error("워크플로우 이름이 없습니다. 워크플로우를 다시 생성해주세요.")
                        st.json(workflow_def)
                    elif "steps" not in workflow_def:
                        st.error("워크플로우 스텝이 없습니다. 워크플로우를 다시 생성해주세요.")
                        st.json(workflow_def)
                    else:
                        # Create workflow
                        workflow = workflow_service.create_workflow(
                            name=workflow_def["name"],
                            description=workflow_def.get("description", ""),
                            steps=workflow_def["steps"],
                            folder_id=selected_folder_id,
                            tags=tags or workflow_def.get("tags", []),
                            variables=workflow_def.get("variables", {}),
                            metadata=workflow_def.get("metadata", {}),
                            status=initial_status,
                        )
                        
                        st.success(f"✅ 워크플로우가 저장되었습니다! (ID: {workflow.id})")
                        
                        # Reset
                        st.session_state.generated_workflow = None
                        st.session_state.agent.reset_conversation()
                        st.session_state.conversation_history = []
                        
                        st.balloons()
                    
                except Exception as e:
                    st.error(f"저장 중 오류가 발생했습니다: {str(e)}")
                    import traceback
                    with st.expander("상세 오류 정보"):
                        st.code(traceback.format_exc())
                        st.write("**워크플로우 구조:**")
                        st.json(workflow_def)
        
        with col_b:
            if st.button("🔄 다시 생성", use_container_width=True):
                st.session_state.generated_workflow = None
                st.rerun()
    
    else:
        st.info("👈 왼쪽 채팅창에서 AI와 대화하며 워크플로우를 생성하세요.")

st.markdown("---")
st.caption("💡 Tip: AI가 질문하면 구체적으로 답변할수록 더 정확한 워크플로우가 생성됩니다.")
