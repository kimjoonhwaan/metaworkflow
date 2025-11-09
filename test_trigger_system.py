"""Test script for trigger system

이 스크립트는 트리거 시스템이 제대로 동작하는지 테스트합니다.

사용법:
    python test_trigger_system.py
"""
import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.database.session import get_session
from src.database.models import Workflow, WorkflowStep, WorkflowStatus, TriggerType, StepType
from src.services.workflow_service import WorkflowService
from src.triggers.trigger_manager import TriggerManager
from src.utils.logger import get_logger

logger = get_logger("test_trigger_system")


def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_section(text):
    """Print formatted section"""
    print(f"\n>> {text}")
    print("-" * 60)


def test_trigger_creation():
    """Test creating a trigger"""
    print_header("TEST 1: Trigger Creation")
    
    try:
        db = get_session()
        workflow_service = WorkflowService(db)
        trigger_manager = TriggerManager(db)
        
        # Create a test workflow
        print_section("Creating test workflow...")
        workflow = workflow_service.create_workflow(
            name="Test Workflow for Trigger",
            description="This is a test workflow for trigger system",
            steps=[
                {
                    "name": "Test Step",
                    "step_type": "LLM_CALL",
                    "order": 1,
                    "config": {"model": "gpt-4", "prompt": "Hello"}
                }
            ]
        )
        print(f"OK: PASSED: Workflow created: {workflow.id}")
        print(f"   Name: {workflow.name}")
        
        # Create a SCHEDULED trigger
        print_section("Creating SCHEDULED trigger...")
        next_minute = datetime.utcnow() + timedelta(minutes=1)
        cron_expr = f"{next_minute.minute} {next_minute.hour} * * *"
        
        trigger = trigger_manager.create_trigger(
            workflow_id=workflow.id,
            name="Test Scheduled Trigger",
            trigger_type=TriggerType.SCHEDULED,
            config={
                "cron": cron_expr,
                "timezone": "UTC"
            },
            enabled=True
        )
        print(f"OK: PASSED: Trigger created: {trigger.id}")
        print(f"   Name: {trigger.name}")
        print(f"   Type: {trigger.trigger_type.value}")
        print(f"   Cron: {cron_expr}")
        print(f"   Next trigger: {trigger.next_trigger_at}")
        print(f"   Enabled: {trigger.enabled}")
        
        # Create a MANUAL trigger
        print_section("Creating MANUAL trigger...")
        manual_trigger = trigger_manager.create_trigger(
            workflow_id=workflow.id,
            name="Test Manual Trigger",
            trigger_type=TriggerType.MANUAL,
            config={},
            enabled=True
        )
        print(f"OK: PASSED: Manual trigger created: {manual_trigger.id}")
        print(f"   Name: {manual_trigger.name}")
        print(f"   Type: {manual_trigger.trigger_type.value}")
        
        db.close()
        print(f"\nOK: PASSED: TEST 1 PASSED: Trigger creation works!")
        return True
        
    except Exception as e:
        logger.error(f"FAIL: TEST 1 FAILED: {e}", exc_info=True)
        print(f"\nFAIL: TEST 1 FAILED: {e}")
        return False


def test_trigger_listing():
    """Test listing triggers"""
    print_header("TEST 2: Trigger Listing")
    
    try:
        db = get_session()
        trigger_manager = TriggerManager(db)
        
        print_section("Listing all triggers...")
        all_triggers = trigger_manager.list_triggers()
        print(f"OK: PASSED: Found {len(all_triggers)} triggers:")
        
        for i, trigger in enumerate(all_triggers, 1):
            print(f"\n   {i}. {trigger.name}")
            print(f"      ID: {trigger.id}")
            print(f"      Type: {trigger.trigger_type.value}")
            print(f"      Enabled: {trigger.enabled}")
            print(f"      Created: {trigger.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            if trigger.last_triggered_at:
                print(f"      Last triggered: {trigger.last_triggered_at.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"      Trigger count: {trigger.trigger_count}")
        
        # List scheduled triggers
        print_section("Listing SCHEDULED triggers only...")
        scheduled = trigger_manager.list_triggers(trigger_type=TriggerType.SCHEDULED)
        print(f"OK: PASSED: Found {len(scheduled)} scheduled triggers")
        
        # Check due triggers
        print_section("Checking for due triggers...")
        due = trigger_manager.get_due_triggers()
        print(f"OK: PASSED: Found {len(due)} due triggers")
        if due:
            for trigger in due:
                print(f"   - {trigger.name} (next: {trigger.next_trigger_at})")
        
        db.close()
        print(f"\nOK: PASSED: TEST 2 PASSED: Trigger listing works!")
        return True
        
    except Exception as e:
        logger.error(f"FAIL: TEST 2 FAILED: {e}", exc_info=True)
        print(f"\nFAIL: TEST 2 FAILED: {e}")
        return False


def test_trigger_update():
    """Test updating a trigger"""
    print_header("TEST 3: Trigger Update")
    
    try:
        db = get_session()
        trigger_manager = TriggerManager(db)
        
        # Get a trigger to update
        all_triggers = trigger_manager.list_triggers()
        if not all_triggers:
            print("FAIL: No triggers found to update. Skipping test.")
            db.close()
            return False
        
        trigger = all_triggers[0]
        print_section(f"Updating trigger: {trigger.name}")
        
        # Update enabled status
        new_enabled = not trigger.enabled
        updated = trigger_manager.update_trigger(
            trigger_id=trigger.id,
            enabled=new_enabled
        )
        print(f"OK: PASSED: Trigger updated:")
        print(f"   Enabled: {updated.enabled} (was {trigger.enabled})")
        
        # Update back
        trigger_manager.update_trigger(
            trigger_id=trigger.id,
            enabled=trigger.enabled
        )
        
        db.close()
        print(f"\nOK: PASSED: TEST 3 PASSED: Trigger update works!")
        return True
        
    except Exception as e:
        logger.error(f"FAIL: TEST 3 FAILED: {e}", exc_info=True)
        print(f"\nFAIL: TEST 3 FAILED: {e}")
        return False


def test_database_state():
    """Test current database state"""
    print_header("TEST 4: Database State Check")
    
    try:
        db = get_session()
        trigger_manager = TriggerManager(db)
        
        all_triggers = trigger_manager.list_triggers()
        
        print_section("Database state:")
        print(f"OK: PASSED: Total triggers: {len(all_triggers)}")
        
        # Count by type
        manual = len(trigger_manager.list_triggers(trigger_type=TriggerType.MANUAL))
        scheduled = len(trigger_manager.list_triggers(trigger_type=TriggerType.SCHEDULED))
        event = len(trigger_manager.list_triggers(trigger_type=TriggerType.EVENT))
        webhook = len(trigger_manager.list_triggers(trigger_type=TriggerType.WEBHOOK))
        
        print(f"\n   By type:")
        print(f"   - MANUAL: {manual}")
        print(f"   - SCHEDULED: {scheduled}")
        print(f"   - EVENT: {event}")
        print(f"   - WEBHOOK: {webhook}")
        
        # Count by status
        enabled = len(trigger_manager.list_triggers(enabled=True))
        disabled = len(trigger_manager.list_triggers(enabled=False))
        
        print(f"\n   By status:")
        print(f"   - Enabled: {enabled}")
        print(f"   - Disabled: {disabled}")
        
        # Check due triggers
        due = trigger_manager.get_due_triggers()
        print(f"\n   Due triggers: {len(due)}")
        
        db.close()
        print(f"\nOK: PASSED: TEST 4 PASSED: Database state check works!")
        return True
        
    except Exception as e:
        logger.error(f"FAIL: TEST 4 FAILED: {e}", exc_info=True)
        print(f"\nFAIL: TEST 4 FAILED: {e}")
        return False


def main():
    """Run all tests"""
    print("\n")
    print("[" + "=" * 58 + "]")
    print("[" + " " * 58 + "]")
    print("[" + "  TRIGGER SYSTEM TEST SUITE".center(58) + "]")
    print("[" + " " * 58 + "]")
    print("[" + "=" * 58 + "]")
    
    results = []
    
    # Run tests
    results.append(("Trigger Creation", test_trigger_creation()))
    results.append(("Trigger Listing", test_trigger_listing()))
    results.append(("Trigger Update", test_trigger_update()))
    results.append(("Database State", test_database_state()))
    
    # Summary
    print_header("TEST SUMMARY")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "OK: PASSED" if result else "FAIL: FAILED"
        print(f"{status}: {name}")
    
    print(f"\n{'=' * 60}")
    print(f"Total: {passed}/{total} tests passed")
    print(f"{'=' * 60}\n")
    
    return all(result for _, result in results)


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"FAIL: Test suite failed: {e}", exc_info=True)
        print(f"\nFAIL: Test suite failed: {e}")
        sys.exit(1)
