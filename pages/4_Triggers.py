"""
트리거 관리 페이지
"""
import streamlit as st
import asyncio
from datetime import datetime

from src.database.session import get_session
from src.services import WorkflowService
from src.triggers import TriggerManager, TriggerScheduler
from src.database.models import TriggerType

st.set_page_config(
    page_title="트리거 관리",
    page_icon="⏰",
    layout="wide",
)

st.title("⏰ 트리거 관리")
st.markdown("워크플로우를 자동으로 실행하는 트리거를 설정합니다.")
st.markdown("---")

# Initialize (fresh session each time, no caching)
db = get_session()
workflow_service = WorkflowService(db)
trigger_manager = TriggerManager(db)

# Main tabs
tab_list, tab_create = st.tabs(["📋 트리거 목록", "➕ 트리거 생성"])

with tab_create:
    st.subheader("새 트리거 생성")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Basic info
        trigger_name = st.text_input("트리거 이름", placeholder="예: 매일 아침 9시 실행")
        
        # Workflow selection
        workflows = workflow_service.list_workflows()
        workflow_options = [f"{w.name} ({w.id[:8]})" for w in workflows]
        selected_workflow = st.selectbox("워크플로우", workflow_options if workflows else ["워크플로우가 없습니다"])
        
        if not workflows:
            st.warning("먼저 워크플로우를 생성해주세요")
            selected_workflow_id = None
        else:
            workflow_id = selected_workflow.split("(")[-1].strip(")")
            selected_workflow_id = next((w.id for w in workflows if w.id.startswith(workflow_id)), None)
        
        # Trigger type
        trigger_type = st.selectbox(
            "트리거 유형",
            [TriggerType.MANUAL, TriggerType.SCHEDULED, TriggerType.EVENT, TriggerType.WEBHOOK],
            format_func=lambda x: {
                TriggerType.MANUAL: "수동 실행",
                TriggerType.SCHEDULED: "스케줄 (시간 기반)",
                TriggerType.EVENT: "이벤트 기반",
                TriggerType.WEBHOOK: "웹훅",
            }.get(x, str(x))
        )
        
        enabled = st.checkbox("활성화", value=True)
    
    with col2:
        st.subheader("트리거 설정")
        
        config = {}
        
        if trigger_type == TriggerType.SCHEDULED:
            st.write("**스케줄 설정 (Cron 표현식)**")
            
            # Cron helper
            cron_preset = st.selectbox(
                "프리셋",
                ["사용자 정의", "매일 오전 9시", "매주 월요일 오전 9시", "매시간", "매 5분"],
            )
            
            cron_presets = {
                "매일 오전 9시": "0 9 * * *",
                "매주 월요일 오전 9시": "0 9 * * 1",
                "매시간": "0 * * * *",
                "매 5분": "*/5 * * * *",
            }
            
            if cron_preset == "사용자 정의":
                cron_expr = st.text_input("Cron 표현식", "0 9 * * *")
            else:
                cron_expr = cron_presets[cron_preset]
                st.code(cron_expr)
            
            timezone = st.selectbox(
                "타임존",
                ["UTC", "Asia/Seoul", "America/New_York", "Europe/London"],
            )
            
            config = {
                "cron": cron_expr,
                "timezone": timezone,
            }
            
            st.info(f"다음 실행 시간은 생성 후 자동 계산됩니다")
        
        elif trigger_type == TriggerType.EVENT:
            st.write("**이벤트 설정**")
            
            event_type = st.text_input(
                "이벤트 유형",
                placeholder="예: data_received, threshold_exceeded"
            )
            
            condition = st.text_area(
                "조건 (Python 표현식, 선택사항)",
                placeholder="예: value > 100",
                key="event_condition_input"
            )
            
            config = {
                "event_type": event_type,
            }
            
            if condition:
                config["condition"] = condition
        
        elif trigger_type == TriggerType.WEBHOOK:
            st.write("**웹훅 설정**")
            
            endpoint = st.text_input(
                "엔드포인트 경로",
                placeholder="/webhook/my-trigger"
            )
            
            secret = st.text_input(
                "비밀 키 (선택사항)",
                type="password",
                placeholder="웹훅 검증용"
            )
            
            config = {
                "endpoint": endpoint,
            }
            
            if secret:
                config["secret"] = secret
        
        else:  # MANUAL
            st.info("수동 트리거는 사용자가 직접 실행합니다")
            config = {}
    
    st.markdown("---")
    
    if st.button("트리거 생성", type="primary"):
        if not trigger_name:
            st.error("트리거 이름을 입력하세요")
        elif not selected_workflow_id:
            st.error("워크플로우를 선택하세요")
        else:
            try:
                trigger = trigger_manager.create_trigger(
                    workflow_id=selected_workflow_id,
                    name=trigger_name,
                    trigger_type=trigger_type,
                    config=config,
                    enabled=enabled,
                )
                
                st.success(f"✅ 트리거가 생성되었습니다! (ID: {trigger.id})")
                
                if trigger.next_trigger_at:
                    st.info(f"다음 실행: {trigger.next_trigger_at.strftime('%Y-%m-%d %H:%M:%S')} UTC")
                
                st.rerun()
            
            except Exception as e:
                st.error(f"트리거 생성 실패: {str(e)}")

with tab_list:
    st.subheader("트리거 목록")
    
    # Filters
    col1, col2 = st.columns([2, 1])
    
    with col1:
        trigger_type_filter = st.selectbox(
            "유형 필터",
            ["전체"] + [t.value for t in TriggerType],
            key="trigger_type_filter",
        )
    
    with col2:
        enabled_filter = st.selectbox(
            "상태 필터",
            ["전체", "활성", "비활성"],
            key="enabled_filter",
        )
    
    # Get triggers
    type_filter = None if trigger_type_filter == "전체" else TriggerType(trigger_type_filter)
    enabled_bool = None if enabled_filter == "전체" else (enabled_filter == "활성")
    
    triggers = trigger_manager.list_triggers(
        trigger_type=type_filter,
        enabled=enabled_bool,
    )
    
    if triggers:
        for trigger in triggers:
            workflow = workflow_service.get_workflow(trigger.workflow_id)
            workflow_name = workflow.name if workflow else "Unknown"
            
            status_icon = "🟢" if trigger.enabled else "⚪"
            
            with st.expander(f"{status_icon} {trigger.name} - {workflow_name}"):
                col_info, col_actions = st.columns([2, 1])
                
                with col_info:
                    st.write(f"**ID:** {trigger.id}")
                    st.write(f"**워크플로우:** {workflow_name}")
                    st.write(f"**유형:** {trigger.trigger_type.value}")
                    st.write(f"**활성화:** {'예' if trigger.enabled else '아니오'}")
                    
                    # Type-specific info
                    if trigger.trigger_type == TriggerType.SCHEDULED:
                        st.write(f"**Cron:** {trigger.config.get('cron', 'N/A')}")
                        st.write(f"**타임존:** {trigger.config.get('timezone', 'UTC')}")
                        
                        if trigger.next_trigger_at:
                            st.write(f"**다음 실행:** {trigger.next_trigger_at.strftime('%Y-%m-%d %H:%M:%S')} UTC")
                    
                    elif trigger.trigger_type == TriggerType.EVENT:
                        st.write(f"**이벤트 유형:** {trigger.config.get('event_type', 'N/A')}")
                        if trigger.config.get('condition'):
                            st.write(f"**조건:** {trigger.config['condition']}")
                    
                    elif trigger.trigger_type == TriggerType.WEBHOOK:
                        st.write(f"**엔드포인트:** {trigger.config.get('endpoint', 'N/A')}")
                    
                    if trigger.last_triggered_at:
                        st.write(f"**마지막 실행:** {trigger.last_triggered_at.strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    st.write(f"**총 실행 횟수:** {trigger.trigger_count}")
                    st.write(f"**생성일:** {trigger.created_at.strftime('%Y-%m-%d %H:%M')}")
                
                with col_actions:
                    st.write("**작업**")
                    
                    # Manual execution
                    if st.button("▶️ 지금 실행", key=f"exec_{trigger.id}"):
                        with st.spinner("트리거 실행 중..."):
                            try:
                                scheduler = TriggerScheduler()
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                execution_id = loop.run_until_complete(
                                    scheduler.execute_trigger_once(trigger.id)
                                )
                                loop.close()
                                
                                st.success(f"실행 완료! (실행 ID: {execution_id})")
                            except Exception as e:
                                st.error(f"실행 실패: {str(e)}")
                    
                    # Toggle enabled
                    new_enabled = not trigger.enabled
                    button_text = "비활성화" if trigger.enabled else "활성화"
                    
                    if st.button(button_text, key=f"toggle_{trigger.id}"):
                        try:
                            trigger_manager.update_trigger(
                                trigger.id,
                                enabled=new_enabled,
                            )
                            st.success(f"{'활성화' if new_enabled else '비활성화'}되었습니다")
                            st.rerun()
                        except Exception as e:
                            st.error(f"업데이트 실패: {str(e)}")
                    
                    # Delete
                    if st.button("🗑️ 삭제", key=f"delete_{trigger.id}"):
                        st.session_state[f"confirm_delete_{trigger.id}"] = True
                
                # Delete confirmation
                if st.session_state.get(f"confirm_delete_{trigger.id}"):
                    st.warning("⚠️ 정말로 이 트리거를 삭제하시겠습니까?")
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("삭제 확인", key=f"confirm_del_{trigger.id}"):
                            try:
                                trigger_manager.delete_trigger(trigger.id)
                                st.success("트리거가 삭제되었습니다")
                                del st.session_state[f"confirm_delete_{trigger.id}"]
                                st.rerun()
                            except Exception as e:
                                st.error(f"삭제 실패: {str(e)}")
                    with col_b:
                        if st.button("취소", key=f"cancel_del_{trigger.id}"):
                            del st.session_state[f"confirm_delete_{trigger.id}"]
                            st.rerun()
    
    else:
        st.info("트리거가 없습니다. 새 트리거를 생성해보세요!")

st.markdown("---")
st.caption(f"총 {len(triggers) if triggers else 0}개의 트리거")

