"""
애플리케이션 초기화 스크립트
데이터베이스 생성 및 샘플 데이터 추가
"""
import os
import sys

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.database.session import init_db, get_session
from src.services import FolderService, WorkflowService
from src.database.models import WorkflowStatus

def main():
    print("=" * 60)
    print("AI-Powered Workflow Management System")
    print("애플리케이션 초기화")
    print("=" * 60)
    print()
    
    # Initialize database
    print("1. 데이터베이스 초기화 중...")
    init_db()
    print("   ✅ 데이터베이스 초기화 완료")
    print()
    
    # Create sample folders
    print("2. 샘플 폴더 생성 중...")
    db = get_session()
    folder_service = FolderService(db)
    
    try:
        folder_service.create_folder(
            name="일반",
            description="일반 워크플로우",
        )
        print("   ✅ '일반' 폴더 생성 완료")
    except Exception as e:
        print(f"   ⚠️  폴더 생성 건너뛰기: {str(e)}")
    
    print()
    print("=" * 60)
    print("초기화 완료!")
    print("=" * 60)
    print()
    print("다음 명령으로 애플리케이션을 실행하세요:")
    print("  streamlit run app.py")
    print()
    print("환경 변수 설정을 잊지 마세요 (.env 파일):")
    print("  OPENAI_API_KEY=your_api_key_here")
    print()

if __name__ == "__main__":
    main()

