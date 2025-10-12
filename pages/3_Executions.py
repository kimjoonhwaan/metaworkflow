"""
실행 기록 페이지
"""
import streamlit as st
import asyncio
from datetime import datetime

from src.database.session import get_session
from src.services import ExecutionService, WorkflowService
from src.runners import WorkflowRunner
from src.database.models import ExecutionStatus

st.set_page_config(
    page_title="실행 기록",
    page_icon="📊",
    layout="wide",
)

st.title("📊 워크플로우 실행 기록")
st.markdown("---")

# Initialize (fresh session each time, no caching)
db = get_session()
execution_service = ExecutionService(db)
workflow_service = WorkflowService(db)

# Sidebar - Filters
with st.sidebar:
    st.subheader("🔍 필터")
    
    # Workflow filter
    workflows = workflow_service.list_workflows()
    workflow_options = ["전체"] + [f"{w.name} ({w.id[:8]})" for w in workflows]
    selected_workflow_filter = st.selectbox("워크플로우", workflow_options)
    
    selected_workflow_id = None
    if selected_workflow_filter != "전체":
        workflow_id = selected_workflow_filter.split("(")[-1].strip(")")
        selected_workflow_id = next((w.id for w in workflows if w.id.startswith(workflow_id)), None)
    
    # Status filter
    status_options = ["전체"] + [s.value for s in ExecutionStatus]
    selected_status_filter = st.selectbox("상태", status_options)
    status_filter = None
    if selected_status_filter != "전체":
        status_filter = ExecutionStatus(selected_status_filter)
    
    # Limit
    limit = st.slider("표시 개수", 10, 100, 50)
    
    st.markdown("---")
    
    # Statistics
    st.subheader("📈 통계")
    stats = execution_service.get_execution_stats(workflow_id=selected_workflow_id, days=7)
    
    st.metric("전체 실행", stats["total"])
    st.metric("성공률", f"{stats['success_rate']:.1f}%")
    st.metric("평균 시간", f"{stats['average_duration_seconds']:.1f}초")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("성공", stats["success"])
        st.metric("실행 중", stats["running"])
    with col2:
        st.metric("실패", stats["failed"])
        st.metric("대기", stats["pending"])

# Main content
executions = execution_service.list_executions(
    workflow_id=selected_workflow_id,
    status=status_filter,
    limit=limit,
)

st.subheader(f"실행 기록 ({len(executions)}개)")

if executions:
    for execution in executions:
        workflow = workflow_service.get_workflow(execution.workflow_id)
        workflow_name = workflow.name if workflow else "Unknown"
        
        # Status icon
        status_icon = {
            ExecutionStatus.SUCCESS: "✅",
            ExecutionStatus.FAILED: "❌",
            ExecutionStatus.RUNNING: "🔄",
            ExecutionStatus.PENDING: "⏳",
            ExecutionStatus.WAITING_APPROVAL: "⏸️",
            ExecutionStatus.CANCELLED: "🚫",
        }.get(execution.status, "❓")
        
        # Status color
        status_color = {
            ExecutionStatus.SUCCESS: "green",
            ExecutionStatus.FAILED: "red",
            ExecutionStatus.RUNNING: "blue",
            ExecutionStatus.PENDING: "gray",
            ExecutionStatus.WAITING_APPROVAL: "orange",
            ExecutionStatus.CANCELLED: "gray",
        }.get(execution.status, "gray")
        
        with st.expander(
            f"{status_icon} {workflow_name} - "
            f"{execution.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
        ):
            col_info, col_actions = st.columns([2, 1])
            
            with col_info:
                st.write(f"**실행 ID:** {execution.id}")
                st.write(f"**워크플로우:** {workflow_name}")
                st.write(f"**상태:** :{status_color}[{execution.status.value}]")
                
                if execution.started_at:
                    st.write(f"**시작 시간:** {execution.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
                
                if execution.completed_at:
                    st.write(f"**완료 시간:** {execution.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")
                    st.write(f"**소요 시간:** {execution.duration_seconds:.2f}초")
                
                if execution.input_data:
                    st.markdown("**입력 데이터:**")
                    st.json(execution.input_data)
                
                if execution.output_data:
                    st.markdown("**출력 데이터:**")
                    st.json(execution.output_data)
                
                if execution.error_message:
                    st.error(f"**오류 메시지:** {execution.error_message}")
                    if execution.error_step_id:
                        st.write(f"**오류 발생 스텝:** {execution.error_step_id}")
            
            with col_actions:
                st.write("**작업**")
                
                # View detailed logs
                if st.button("📋 상세 로그", key=f"logs_{execution.id}"):
                    st.session_state[f"show_logs_{execution.id}"] = True
                
                # Retry execution
                if execution.status == ExecutionStatus.FAILED:
                    if st.button("🔄 재시도", key=f"retry_{execution.id}"):
                        with st.spinner("재시도 중..."):
                            try:
                                runner = WorkflowRunner(db)
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                new_execution = loop.run_until_complete(
                                    runner.retry_execution(execution.id)
                                )
                                loop.close()
                                
                                st.success(f"재시도 실행 시작! (ID: {new_execution.id})")
                                st.rerun()
                            except Exception as e:
                                st.error(f"재시도 실패: {str(e)}")
                
                # Approve execution
                if execution.status == ExecutionStatus.WAITING_APPROVAL:
                    st.write("**승인 필요**")
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("✅ 승인", key=f"approve_{execution.id}"):
                            try:
                                runner = WorkflowRunner(db)
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                updated = loop.run_until_complete(
                                    runner.approve_execution(execution.id, approved=True)
                                )
                                loop.close()
                                
                                st.success("승인되었습니다")
                                st.rerun()
                            except Exception as e:
                                st.error(f"승인 실패: {str(e)}")
                    with col_b:
                        if st.button("❌ 거부", key=f"reject_{execution.id}"):
                            try:
                                runner = WorkflowRunner(db)
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                updated = loop.run_until_complete(
                                    runner.approve_execution(execution.id, approved=False)
                                )
                                loop.close()
                                
                                st.warning("거부되었습니다")
                                st.rerun()
                            except Exception as e:
                                st.error(f"거부 실패: {str(e)}")
                
                # Cancel execution
                if execution.status in [ExecutionStatus.RUNNING, ExecutionStatus.PENDING]:
                    if st.button("🚫 취소", key=f"cancel_{execution.id}"):
                        try:
                            runner = WorkflowRunner(db)
                            runner.cancel_execution(execution.id)
                            st.success("실행이 취소되었습니다")
                            st.rerun()
                        except Exception as e:
                            st.error(f"취소 실패: {str(e)}")
            
            # Show detailed logs
            if st.session_state.get(f"show_logs_{execution.id}"):
                st.markdown("---")
                st.subheader("📋 상세 실행 로그")
                
                try:
                    runner = WorkflowRunner(db)
                    logs = runner.get_execution_logs(execution.id)
                    
                    # Step executions
                    st.write("**스텝별 실행 기록:**")
                    for step_exec in logs["step_executions"]:
                        step_status_icon = {
                            "SUCCESS": "✅",
                            "FAILED": "❌",
                            "RUNNING": "🔄",
                            "PENDING": "⏳",
                            "WAITING_APPROVAL": "⏸️",
                        }.get(step_exec["status"], "❓")
                        
                        with st.expander(
                            f"{step_status_icon} Step {step_exec['step_order'] + 1}: {step_exec['step_name']}"
                        ):
                            st.write(f"**상태:** {step_exec['status']}")
                            
                            if step_exec["started_at"]:
                                st.write(f"**시작:** {step_exec['started_at']}")
                            if step_exec["completed_at"]:
                                st.write(f"**완료:** {step_exec['completed_at']}")
                            if step_exec["duration_seconds"]:
                                st.write(f"**소요 시간:** {step_exec['duration_seconds']:.2f}초")
                            
                            if step_exec["input_data"]:
                                st.markdown("**입력:**")
                                st.json(step_exec["input_data"])
                            
                            if step_exec["output_data"]:
                                st.markdown("**출력:**")
                                st.json(step_exec["output_data"])
                            
                            if step_exec["logs"]:
                                st.markdown("**로그:**")
                                st.text(step_exec["logs"])
                            
                            if step_exec["error_message"]:
                                st.error(f"**오류:** {step_exec['error_message']}")
                                if step_exec["error_traceback"]:
                                    st.markdown("**트레이스백:**")
                                    st.code(step_exec["error_traceback"])
                    
                    if st.button("닫기", key=f"close_logs_{execution.id}"):
                        del st.session_state[f"show_logs_{execution.id}"]
                        st.rerun()
                
                except Exception as e:
                    st.error(f"로그를 불러오는데 실패했습니다: {str(e)}")

else:
    st.info("실행 기록이 없습니다.")

st.markdown("---")
st.caption(f"총 {len(executions)}개의 실행 기록")

