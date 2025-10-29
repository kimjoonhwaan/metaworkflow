#!/usr/bin/env python3
"""
기존 문서를 새 RAG 설정으로 재처리하는 스크립트
"""
import sys
import os
from pathlib import Path

# 경로 설정
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import asyncio
from src.database.session import get_session
from src.database.models import Document, DocumentChunk
from src.services.rag_service import RAGService
from src.utils.config import get_settings
from src.utils.logger import get_logger

logger = get_logger("reprocess_documents")

async def cleanup_chroma_db():
    """ChromaDB 디렉토리 정리"""
    chroma_path = Path("./data/chroma_db")
    
    if chroma_path.exists():
        print(f"\n🗑️  ChromaDB 정리 중: {chroma_path}")
        try:
            # 백업 생성
            backup_path = Path("./data/chroma_db.backup")
            if backup_path.exists():
                shutil.rmtree(backup_path)
            shutil.move(str(chroma_path), str(backup_path))
            print(f"   ✅ 백업 생성: {backup_path}")
        except Exception as e:
            logger.error(f"ChromaDB 정리 실패: {e}")
            return False
    
    return True

async def clear_document_chunks():
    """데이터베이스에서 기존 청크 삭제"""
    print(f"\n🗑️  기존 청크 삭제 중...")
    
    with get_session() as session:
        try:
            chunk_count = session.query(DocumentChunk).count()
            print(f"   삭제할 청크: {chunk_count}개")
            
            session.query(DocumentChunk).delete()
            session.commit()
            
            print(f"   ✅ 모든 청크 삭제됨")
            return True
        except Exception as e:
            logger.error(f"청크 삭제 실패: {e}")
            session.rollback()
            return False

async def reprocess_documents():
    """모든 문서를 새로운 설정으로 재임베딩"""
    print(f"\n📚 문서 재임베딩 시작...")
    print(f"   설정: chunk_size=1500, overlap=300")
    print("=" * 80)
    
    rag_service = RAGService()
    
    with get_session() as session:
        # 임베딩할 모든 문서 조회
        documents = session.query(Document).filter(
            Document.is_processed == True
        ).all()
        
        print(f"\n재임베딩할 문서: {len(documents)}개")
        
        if not documents:
            print("   ⚠️  처리할 문서가 없습니다")
            return True
        
        success_count = 0
        failed_count = 0
        
        for idx, doc in enumerate(documents, 1):
            doc_name = doc.title[:40] + "..." if len(doc.title) > 40 else doc.title
            
            try:
                print(f"\n[{idx}/{len(documents)}] 📄 {doc_name}")
                print(f"   ID: {doc.id}")
                
                # 1단계: 기존 청크 삭제
                session.query(DocumentChunk).filter(
                    DocumentChunk.document_id == doc.id
                ).delete()
                session.commit()
                print(f"   ✅ 기존 청크 삭제됨")
                
                # 2단계: 새로운 설정으로 재임베딩
                # add_document는 내부적으로 chunk_text를 사용하므로
                # 새로운 chunk_size(1500)와 overlap(300)이 자동 적용됨
                print(f"   ⏳ 재임베딩 중...")
                
                # 문서의 청크를 새로운 설정으로 다시 생성
                chunks = rag_service.chunk_text(
                    doc.content,
                    chunk_size=1500,  # 새로운 크기
                    overlap=300        # 새로운 오버랩
                )
                
                print(f"   ✅ 청크 생성: {len(chunks)}개 (이전보다 적을 것임)")
                
                # 3단계: 임베딩 생성 및 저장
                collection = rag_service._get_or_create_collection(doc.knowledge_base.category)
                
                embedding_count = 0
                for i, chunk_content in enumerate(chunks):
                    # 임베딩 생성
                    embedding = await rag_service.create_embedding(chunk_content)
                    
                    # ChromaDB에 저장
                    chunk_id = f"{doc.id}_chunk_{i}"
                    collection.add(
                        ids=[chunk_id],
                        embeddings=[embedding],
                        documents=[chunk_content],
                        metadatas=[{
                            "document_id": doc.id,
                            "chunk_index": i,
                            "title": doc.title,
                            "content_type": doc.content_type.value,
                            "category": doc.knowledge_base.category.value,
                            "has_previous": i > 0,
                            "has_next": i < len(chunks) - 1
                        }]
                    )
                    
                    # DocumentChunk 레코드 생성
                    chunk = DocumentChunk(
                        document_id=doc.id,
                        chunk_index=i,
                        content=chunk_content,
                        embedding_id=chunk_id,
                        start_char=i * (1500 - 300),
                        end_char=min((i + 1) * 1500, len(doc.content)),
                        token_count=len(rag_service.tokenizer.encode(chunk_content))
                    )
                    session.add(chunk)
                    embedding_count += 1
                
                session.commit()
                print(f"   ✅ 임베딩 저장: {embedding_count}개")
                
                # 4단계: 문서 메타데이터 업데이트
                doc.vector_count = len(chunks)
                doc.is_processed = True
                session.commit()
                
                success_count += 1
                print(f"   ✅ 완료!")
                
                # 진행률 표시
                if idx % 5 == 0:
                    print(f"\n   📊 진행률: {idx}/{len(documents)} ({idx*100//len(documents)}%)")
                
            except Exception as e:
                failed_count += 1
                print(f"   ❌ 오류: {str(e)[:100]}")
                logger.error(f"재임베딩 실패 {doc.id}: {e}", exc_info=True)
                session.rollback()
        
        print("\n" + "=" * 80)
        print(f"✅ 재임베딩 완료!")
        print(f"   성공: {success_count}개")
        print(f"   실패: {failed_count}개")
        
        return failed_count == 0

async def main():
    print("=" * 80)
    print("🔄 문서 재임베딩 시작")
    print("=" * 80)
    print("\n⚠️  주의:")
    print("   - 모든 기존 청크가 삭제되고 새로 생성됩니다")
    print("   - ChromaDB가 재생성됩니다")
    print("   - 시간이 소요됩니다 (문서 수에 따라 5-30분)")
    print()
    
    # 자동 실행 (대화형 제외)
    print("🚀 진행 중...\n")
    
    # 1단계: ChromaDB 정리
    if not await cleanup_chroma_db():
        print("❌ ChromaDB 정리 실패")
        return
    
    # 2단계: 데이터베이스 청크 삭제
    if not await clear_document_chunks():
        print("❌ 청크 삭제 실패")
        return
    
    # 3단계: 문서 재임베딩
    if await reprocess_documents():
        print("\n🎉 재임베딩 성공!")
        print("\n다음 단계:")
        print("   1. Streamlit 앱 재시작")
        print("   2. 워크플로우 생성 페이지에서 새 쿼리 시도")
        print("   3. RAG 컨텍스트가 더 많은 청크를 포함하는지 확인")
    else:
        print("\n⚠️  일부 문서 재임베딩 실패")
        print("   로그 파일 확인: ./logs/")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n❌ 사용자에 의해 중단됨")
    except Exception as e:
        print(f"\n\n❌ 예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()
