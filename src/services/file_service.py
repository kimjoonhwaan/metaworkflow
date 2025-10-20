"""File service for managing uploaded files and integrating with RAG system"""

import asyncio
import os
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from ..database.models import KnowledgeBase, Document, DocumentContentType, KnowledgeBaseCategory
from ..database.session import get_session
from ..services.rag_service import get_rag_service
from ..services.file_parser import get_file_parser
from ..utils.logger import get_logger

logger = get_logger(__name__)


class FileService:
    """Service for managing file uploads and processing"""
    
    def __init__(self):
        self.rag_service = get_rag_service()
        self.file_parser = get_file_parser()
        
        # File upload directory
        self.upload_dir = Path("./uploads")
        self.upload_dir.mkdir(exist_ok=True)
    
    async def upload_file(
        self,
        file_content: bytes,
        filename: str,
        knowledge_base_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        tags: List[str] = None
    ) -> Dict[str, Any]:
        """Upload and process a file, adding it to the knowledge base"""
        try:
            # Generate unique filename
            file_id = str(uuid.uuid4())
            file_ext = Path(filename).suffix
            unique_filename = f"{file_id}{file_ext}"
            file_path = self.upload_dir / unique_filename
            
            # Save file to disk
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            # Parse file content
            parse_result = self.file_parser.parse_file(file_content, filename)
            
            if not parse_result['success']:
                # Clean up saved file
                if file_path.exists():
                    file_path.unlink()
                
                return {
                    'success': False,
                    'error': f"Failed to parse file: {parse_result['error']}",
                    'file_info': parse_result.get('file_info', {})
                }
            
            # Determine content type based on file type
            content_type = self._determine_content_type(parse_result['file_info']['mime_type'])
            
            # Create document title
            document_title = title or f"{Path(filename).stem} ({parse_result['file_info']['mime_type']})"
            
            # Add document to knowledge base
            doc_id = await self.rag_service.add_document(
                knowledge_base_id=knowledge_base_id,
                title=document_title,
                content=parse_result['content'],
                content_type=content_type,
                metadata={
                    'original_filename': filename,
                    'file_id': file_id,
                    'file_path': str(file_path),
                    'file_info': parse_result['file_info'],
                    'parsed_metadata': parse_result.get('metadata', {}),
                    'description': description
                },
                tags=tags or []
            )
            
            logger.info(f"File uploaded successfully: {filename} -> {doc_id}")
            
            return {
                'success': True,
                'document_id': doc_id,
                'file_id': file_id,
                'file_path': str(file_path),
                'title': document_title,
                'content_type': content_type.value,
                'file_info': parse_result['file_info'],
                'content_length': len(parse_result['content'])
            }
            
        except Exception as e:
            logger.error(f"Failed to upload file {filename}: {e}")
            
            # Clean up saved file if it exists
            try:
                file_path = self.upload_dir / f"{file_id}{Path(filename).suffix}"
                if file_path.exists():
                    file_path.unlink()
            except:
                pass
            
            return {
                'success': False,
                'error': str(e)
            }
    
    def _determine_content_type(self, mime_type: str) -> DocumentContentType:
        """Determine document content type based on MIME type"""
        if mime_type == 'application/pdf':
            return DocumentContentType.EXAMPLE
        elif mime_type in ['application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/msword']:
            return DocumentContentType.EXAMPLE
        elif mime_type in ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/vnd.ms-excel']:
            return DocumentContentType.EXAMPLE
        elif mime_type == 'text/plain':
            return DocumentContentType.TEXT
        elif mime_type == 'text/csv':
            return DocumentContentType.EXAMPLE
        elif mime_type.startswith('image/'):
            return DocumentContentType.EXAMPLE
        else:
            return DocumentContentType.TEXT
    
    async def get_uploaded_files(self, knowledge_base_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of uploaded files"""
        try:
            with get_session() as session:
                query = session.query(Document)
                
                if knowledge_base_id:
                    query = query.filter(Document.knowledge_base_id == knowledge_base_id)
                
                # Filter for uploaded files (those with file_id in metadata)
                documents = query.all()
                
                uploaded_files = []
                for doc in documents:
                    if doc.kb_metadata and 'file_id' in doc.kb_metadata:
                        file_info = doc.kb_metadata.get('file_info', {})
                        uploaded_files.append({
                            'document_id': doc.id,
                            'title': doc.title,
                            'original_filename': doc.kb_metadata.get('original_filename', ''),
                            'file_id': doc.kb_metadata.get('file_id', ''),
                            'file_path': doc.kb_metadata.get('file_path', ''),
                            'content_type': doc.content_type.value,
                            'mime_type': file_info.get('mime_type', ''),
                            'file_size': file_info.get('size', 0),
                            'is_processed': doc.is_processed,
                            'created_at': doc.created_at.isoformat(),
                            'knowledge_base_id': doc.knowledge_base_id,
                            'description': doc.kb_metadata.get('description', '')
                        })
                
                return uploaded_files
                
        except Exception as e:
            logger.error(f"Failed to get uploaded files: {e}")
            return []
    
    async def delete_uploaded_file(self, document_id: str) -> bool:
        """Delete an uploaded file and its associated document"""
        try:
            with get_session() as session:
                # Get document
                document = session.query(Document).filter(Document.id == document_id).first()
                
                if not document:
                    return False
                
                # Get file path from metadata
                file_path = None
                if document.kb_metadata and 'file_path' in document.kb_metadata:
                    file_path = document.kb_metadata['file_path']
                
                # Delete document from database
                session.delete(document)
                session.commit()
                
                # Delete physical file
                if file_path and os.path.exists(file_path):
                    os.unlink(file_path)
                
                logger.info(f"Deleted uploaded file: {document_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete uploaded file {document_id}: {e}")
            return False
    
    async def get_file_content(self, document_id: str) -> Optional[bytes]:
        """Get file content by document ID"""
        try:
            with get_session() as session:
                document = session.query(Document).filter(Document.id == document_id).first()
                
                if not document or not document.kb_metadata:
                    return None
                
                file_path = document.kb_metadata.get('file_path')
                if not file_path or not os.path.exists(file_path):
                    return None
                
                with open(file_path, 'rb') as f:
                    return f.read()
                
        except Exception as e:
            logger.error(f"Failed to get file content for {document_id}: {e}")
            return None
    
    def get_supported_file_types(self) -> Dict[str, Any]:
        """Get information about supported file types"""
        return {
            'supported_extensions': self.file_parser.get_supported_extensions(),
            'supported_mime_types': self.file_parser.get_supported_mime_types(),
            'max_file_size': 50 * 1024 * 1024,  # 50MB
            'upload_directory': str(self.upload_dir)
        }
    
    async def create_file_knowledge_base(self, name: str, description: str = None) -> str:
        """Create a knowledge base specifically for uploaded files"""
        try:
            kb_id = await self.rag_service.create_knowledge_base(
                name=name,
                description=description or f"Knowledge base for uploaded files: {name}",
                category=KnowledgeBaseCategory.INTEGRATION_EXAMPLES
            )
            
            logger.info(f"Created file knowledge base: {kb_id}")
            return kb_id
            
        except Exception as e:
            logger.error(f"Failed to create file knowledge base: {e}")
            raise
    
    async def search_files(
        self,
        query: str,
        knowledge_base_id: Optional[str] = None,
        file_types: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search uploaded files"""
        try:
            # Get uploaded files
            uploaded_files = await self.get_uploaded_files(knowledge_base_id)
            
            # Filter by file types if specified
            if file_types:
                uploaded_files = [
                    f for f in uploaded_files 
                    if f['mime_type'] in file_types or Path(f['original_filename']).suffix.lower() in file_types
                ]
            
            # Search in RAG system
            search_results = await self.rag_service.hybrid_search(
                query=query,
                category=None,
                limit=limit
            )
            
            # Combine results with file information
            results = []
            for result in search_results:
                doc_id = result['metadata'].get('document_id')
                if doc_id:
                    # Find corresponding uploaded file
                    uploaded_file = next(
                        (f for f in uploaded_files if f['document_id'] == doc_id),
                        None
                    )
                    
                    if uploaded_file:
                        results.append({
                            'search_result': result,
                            'file_info': uploaded_file
                        })
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to search files: {e}")
            return []


# Global file service instance
_file_service = None

def get_file_service() -> FileService:
    """Get global file service instance"""
    global _file_service
    if _file_service is None:
        _file_service = FileService()
    return _file_service
