"""
워크플로우 관리 페이지
"""
import streamlit as st
import asyncio
import json

from src.database.session import get_session
from src.services import WorkflowService, FolderService
from src.runners import WorkflowRunner
from src.agents import WorkflowModifier
from src.database.models import WorkflowStatus

st.set_page_config(
    page_title="워크플로우 관리",
    page_icon="📂",
    layout="wide",
)

st.title("📂 워크플로우 관리")
st.markdown("---")

# Initialize (fresh session each time, no caching)
db = get_session()
workflow_service = WorkflowService(db)
folder_service = FolderService(db)

# Sidebar - Filters
with st.sidebar:
    st.subheader("🔍 필터")
    
    # Folder filter
    folders = folder_service.list_folders()
    folder_options = ["전체"] + [f.name for f in folders]
    selected_folder_filter = st.selectbox("폴더", folder_options)
    selected_folder_id_filter = None
    if selected_folder_filter != "전체":
        folder = next((f for f in folders if f.name == selected_folder_filter), None)
        if folder:
            selected_folder_id_filter = folder.id
    
    # Status filter
    status_options = ["전체"] + [s.value for s in WorkflowStatus]
    selected_status_filter = st.selectbox("상태", status_options)
    status_filter = None
    if selected_status_filter != "전체":
        status_filter = WorkflowStatus(selected_status_filter)
    
    # Search
    search_query = st.text_input("검색", "")
    
    st.markdown("---")
    
    # Folder management
    with st.expander("📁 폴더 관리"):
        new_folder_name = st.text_input("새 폴더 이름")
        new_folder_desc = st.text_area("설명")
        
        if st.button("폴더 생성"):
            if new_folder_name:
                try:
                    folder_service.create_folder(
                        name=new_folder_name,
                        description=new_folder_desc,
                    )
                    st.success(f"폴더 '{new_folder_name}' 생성됨")
                    st.rerun()
                except Exception as e:
                    st.error(f"오류: {str(e)}")
            else:
                st.warning("폴더 이름을 입력하세요")

# Main content
workflows = workflow_service.list_workflows(
    folder_id=selected_folder_id_filter,
    status=status_filter,
    search=search_query if search_query else None,
)

st.subheader(f"워크플로우 목록 ({len(workflows)}개)")

if workflows:
    for workflow in workflows:
        with st.expander(
            f"{'🟢' if workflow.status == WorkflowStatus.ACTIVE else '⚪'} "
            f"{workflow.name} (v{workflow.version})"
        ):
            col_info, col_actions = st.columns([2, 1])
            
            with col_info:
                st.write(f"**ID:** {workflow.id}")
                st.write(f"**설명:** {workflow.description}")
                st.write(f"**상태:** {workflow.status.value}")
                st.write(f"**스텝 수:** {len(workflow.steps)}")
                
                if workflow.folder:
                    st.write(f"**폴더:** {workflow.folder.name}")
                
                if workflow.tags:
                    st.write(f"**태그:** {', '.join(workflow.tags)}")
                
                st.write(f"**생성일:** {workflow.created_at.strftime('%Y-%m-%d %H:%M')}")
                st.write(f"**수정일:** {workflow.updated_at.strftime('%Y-%m-%d %H:%M')}")
                
                # Show steps directly (no nested expander)
                st.markdown(f"**스텝 목록 ({len(workflow.steps)}개):**")
                for step in sorted(workflow.steps, key=lambda s: s.order):
                    st.markdown(f"&nbsp;&nbsp;**{step.order + 1}.** {step.name} `{step.step_type.value}`")
                    st.caption(f"&nbsp;&nbsp;&nbsp;&nbsp;{step.config.get('description', 'No description')}")
            
            with col_actions:
                st.write("**작업**")
                
                # Execute
                if st.button("▶️ 실행", key=f"exec_{workflow.id}"):
                    with st.spinner("워크플로우 실행 중..."):
                        try:
                            runner = WorkflowRunner(db)
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            execution = loop.run_until_complete(
                                runner.execute_workflow(workflow.id)
                            )
                            loop.close()
                            
                            st.success(f"실행 완료! (ID: {execution.id})")
                            st.info(f"상태: {execution.status.value}")
                        except Exception as e:
                            st.error(f"실행 실패: {str(e)}")
                
                # Change status
                new_status = st.selectbox(
                    "상태 변경",
                    [s.value for s in WorkflowStatus],
                    index=[s.value for s in WorkflowStatus].index(workflow.status.value),
                    key=f"status_{workflow.id}",
                )
                
                if new_status != workflow.status.value:
                    if st.button("상태 업데이트", key=f"update_status_{workflow.id}"):
                        try:
                            workflow_service.update_workflow(
                                workflow.id,
                                status=WorkflowStatus(new_status),
                            )
                            st.success("상태 업데이트됨")
                            st.rerun()
                        except Exception as e:
                            st.error(f"오류: {str(e)}")
                
                # View JSON
                if st.button("📄 JSON 보기", key=f"json_{workflow.id}"):
                    st.json(workflow.definition)
                
                # Modify with AI
                if st.button("🤖 AI 수정", key=f"modify_{workflow.id}"):
                    st.session_state[f"modifying_{workflow.id}"] = True
                
                # Delete
                if st.button("🗑️ 삭제", key=f"delete_{workflow.id}"):
                    st.session_state[f"confirm_delete_{workflow.id}"] = True
            
            # AI Modification dialog
            if st.session_state.get(f"modifying_{workflow.id}"):
                st.markdown("---")
                st.subheader("🤖 AI 워크플로우 수정")
                
                modification_request = st.text_area(
                    "수정 요청사항을 입력하세요",
                    key=f"mod_req_{workflow.id}",
                    placeholder="예: 이메일 알림 스텝을 추가해줘"
                )
                
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("수정 실행", key=f"exec_mod_{workflow.id}"):
                        if modification_request:
                            with st.spinner("AI가 워크플로우를 수정하고 있습니다..."):
                                try:
                                    modifier = WorkflowModifier()
                                    loop = asyncio.new_event_loop()
                                    asyncio.set_event_loop(loop)
                                    
                                    modified_workflow, changes, rag_info = loop.run_until_complete(
                                        modifier.modify_workflow(
                                            current_workflow=workflow.definition,
                                            modification_request=modification_request,
                                        )
                                    )
                                    loop.close()
                                    
                                    # Update workflow
                                    workflow_service.update_workflow(
                                        workflow.id,
                                        name=modified_workflow["name"],
                                        description=modified_workflow["description"],
                                        steps=modified_workflow["steps"],
                                        variables=modified_workflow.get("variables", {}),
                                        metadata=modified_workflow.get("metadata", {}),
                                        change_summary=f"AI 수정: {modification_request[:100]}",
                                    )
                                    
                                    st.success("✅ 워크플로우가 수정되었습니다!")
                                    
                                    # Display RAG usage information
                                    if rag_info and rag_info.get("rag_used"):
                                        st.info(f"🧠 RAG 지식 베이스 활용됨 (컨텍스트 길이: {rag_info.get('rag_context_length', 0)}자)")
                                    else:
                                        st.info("💭 일반 AI 수정 (RAG 미사용)")
                                    
                                    st.write("**변경사항:**")
                                    for change in changes:
                                        st.write(f"- {change}")
                                    
                                    del st.session_state[f"modifying_{workflow.id}"]
                                    st.rerun()
                                
                                except Exception as e:
                                    st.error(f"수정 실패: {str(e)}")
                        else:
                            st.warning("수정 요청사항을 입력하세요")
                
                with col_b:
                    if st.button("취소", key=f"cancel_mod_{workflow.id}"):
                        del st.session_state[f"modifying_{workflow.id}"]
                        st.rerun()
            
            # Delete confirmation
            if st.session_state.get(f"confirm_delete_{workflow.id}"):
                st.warning("⚠️ 정말로 이 워크플로우를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.")
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("삭제 확인", key=f"confirm_del_{workflow.id}"):
                        try:
                            workflow_service.delete_workflow(workflow.id)
                            st.success("워크플로우가 삭제되었습니다")
                            del st.session_state[f"confirm_delete_{workflow.id}"]
                            st.rerun()
                        except Exception as e:
                            st.error(f"삭제 실패: {str(e)}")
                with col_b:
                    if st.button("취소", key=f"cancel_del_{workflow.id}"):
                        del st.session_state[f"confirm_delete_{workflow.id}"]
                        st.rerun()

else:
    st.info("워크플로우가 없습니다. '워크플로우 생성' 페이지에서 새로 만들어보세요!")

st.markdown("---")
st.caption(f"총 {len(workflows)}개의 워크플로우")

