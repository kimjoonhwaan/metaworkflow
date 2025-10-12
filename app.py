"""
AI-Powered Workflow Management System
메인 대시보드
"""
import streamlit as st
from datetime import datetime, timedelta
import asyncio

from src.database.session import get_session
from src.services import WorkflowService, ExecutionService, FolderService
from src.database.models import WorkflowStatus, ExecutionStatus

# Page configuration
st.set_page_config(
    page_title="Workflow Manager",
    page_icon="🔄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Title
st.title("🔄 AI-Powered Workflow Management System")
st.markdown("---")

# Initialize database session (fresh session each time, no caching)
db = get_session()

# Services
workflow_service = WorkflowService(db)
execution_service = ExecutionService(db)
folder_service = FolderService(db)

# Dashboard layout
col1, col2, col3, col4 = st.columns(4)

# Get statistics
workflows = workflow_service.list_workflows()
active_workflows = [w for w in workflows if w.status == WorkflowStatus.ACTIVE]
recent_executions = execution_service.list_executions(limit=10)
stats = execution_service.get_execution_stats(days=7)

# Display metrics
with col1:
    st.metric(
        label="전체 워크플로우",
        value=len(workflows),
        delta=f"{len(active_workflows)} 활성",
    )

with col2:
    st.metric(
        label="최근 7일 실행",
        value=stats["total"],
        delta=f"{stats['success_rate']:.1f}% 성공률",
    )

with col3:
    st.metric(
        label="현재 실행 중",
        value=stats["running"],
    )

with col4:
    st.metric(
        label="평균 실행 시간",
        value=f"{stats['average_duration_seconds']:.1f}초",
    )

st.markdown("---")

# Recent Workflows
col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("📋 최근 워크플로우")
    
    if workflows:
        for workflow in workflows[:5]:
            with st.expander(f"{'🟢' if workflow.status == WorkflowStatus.ACTIVE else '⚪'} {workflow.name}"):
                st.write(f"**설명:** {workflow.description}")
                st.write(f"**상태:** {workflow.status.value}")
                st.write(f"**스텝 수:** {len(workflow.steps)}")
                st.write(f"**태그:** {', '.join(workflow.tags) if workflow.tags else '없음'}")
                st.write(f"**생성일:** {workflow.created_at.strftime('%Y-%m-%d %H:%M')}")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("실행", key=f"exec_{workflow.id}"):
                        st.info("실행 페이지로 이동하세요")
                with col_b:
                    if st.button("수정", key=f"edit_{workflow.id}"):
                        st.info("관리 페이지로 이동하세요")
    else:
        st.info("아직 워크플로우가 없습니다. '워크플로우 생성' 페이지에서 새로 만들어보세요!")

with col_right:
    st.subheader("📊 최근 실행 기록")
    
    if recent_executions:
        for execution in recent_executions[:5]:
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
            
            with st.expander(f"{status_icon} {workflow_name} - {execution.created_at.strftime('%Y-%m-%d %H:%M')}"):
                st.write(f"**상태:** {execution.status.value}")
                st.write(f"**실행 ID:** {execution.id}")
                
                if execution.started_at:
                    st.write(f"**시작 시간:** {execution.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
                
                if execution.completed_at:
                    st.write(f"**완료 시간:** {execution.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")
                    st.write(f"**소요 시간:** {execution.duration_seconds:.2f}초")
                
                if execution.error_message:
                    st.error(f"**오류:** {execution.error_message}")
                
                if st.button("상세보기", key=f"view_{execution.id}"):
                    st.info("실행 기록 페이지로 이동하세요")
    else:
        st.info("최근 실행 기록이 없습니다.")

st.markdown("---")

# Quick Actions
st.subheader("⚡ 빠른 작업")

col_a, col_b, col_c, col_d = st.columns(4)

with col_a:
    if st.button("🤖 새 워크플로우 생성", use_container_width=True):
        st.switch_page("pages/1_Create_Workflow.py")

with col_b:
    if st.button("📂 워크플로우 관리", use_container_width=True):
        st.switch_page("pages/2_Manage_Workflows.py")

with col_c:
    if st.button("📊 실행 기록", use_container_width=True):
        st.switch_page("pages/3_Executions.py")

with col_d:
    if st.button("⏰ 트리거 관리", use_container_width=True):
        st.switch_page("pages/4_Triggers.py")

# Footer
st.markdown("---")
st.caption(f"© 2025 AI-Powered Workflow Management System | Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

