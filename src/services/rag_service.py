"""RAG (Retrieval-Augmented Generation) service for enhanced workflow generation"""

import asyncio
import time
from typing import List, Dict, Any, Optional, Tuple
import json
import re
from datetime import datetime

import chromadb
from chromadb.config import Settings
import tiktoken
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..database.models import (
    KnowledgeBase, Document, DocumentChunk, RAGQuery,
    KnowledgeBaseCategory, DocumentContentType
)
from ..database.session import get_session
from ..utils.config import get_settings
from ..utils.logger import get_logger
from ..utils.openai_client import get_openai_client

logger = get_logger(__name__)


class RAGService:
    """RAG service for document retrieval and context building"""
    
    def __init__(self):
        self.settings = get_settings()
        self.openai_client = get_openai_client()
        
        # Disable ChromaDB telemetry
        import os
        os.environ["ANONYMIZED_TELEMETRY"] = "False"
        
        # Initialize ChromaDB
        self.chroma_client = chromadb.PersistentClient(
            path="./data/chroma_db",
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Tokenizer for text processing
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        
        # TF-IDF vectorizer for keyword search
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        
        # Collection cache
        self._collections_cache = {}
    
    def _get_collection_name(self, category: KnowledgeBaseCategory) -> str:
        """Get ChromaDB collection name for category"""
        return f"knowledge_base_{category.value.lower()}"
    
    def _get_or_create_collection(self, category: KnowledgeBaseCategory):
        """Get or create ChromaDB collection"""
        collection_name = self._get_collection_name(category)
        
        if collection_name not in self._collections_cache:
            try:
                collection = self.chroma_client.get_collection(collection_name)
            except Exception:
                collection = self.chroma_client.create_collection(
                    name=collection_name,
                    metadata={"category": category.value}
                )
            self._collections_cache[collection_name] = collection
        
        return self._collections_cache[collection_name]
    
    async def create_embedding(self, text: str) -> List[float]:
        """Create embedding for text using OpenAI API"""
        try:
            response = await self.openai_client.embeddings.create(
                input=text,
                model="text-embedding-3-small"
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to create embedding: {e}")
            raise
    
    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Split text into chunks with overlap"""
        tokens = self.tokenizer.encode(text)
        chunks = []
        
        for i in range(0, len(tokens), chunk_size - overlap):
            chunk_tokens = tokens[i:i + chunk_size]
            chunk_text = self.tokenizer.decode(chunk_tokens)
            chunks.append(chunk_text)
            
            if i + chunk_size >= len(tokens):
                break
        
        return chunks
    
    async def add_document(
        self,
        knowledge_base_id: str,
        title: str,
        content: str,
        content_type: DocumentContentType,
        metadata: Dict[str, Any] = None,
        tags: List[str] = None
    ) -> str:
        """Add document to knowledge base"""
        try:
            with get_session() as session:
                # Get knowledge base
                kb = session.query(KnowledgeBase).filter(
                    KnowledgeBase.id == knowledge_base_id
                ).first()
                
                if not kb:
                    raise ValueError(f"Knowledge base {knowledge_base_id} not found")
                
                # Create document
                document = Document(
                    knowledge_base_id=knowledge_base_id,
                    title=title,
                    content=content,
                    content_type=content_type,
                    kb_metadata=metadata or {},
                    tags=tags or []
                )
                session.add(document)
                session.flush()
                
                # Process document into chunks
                chunks = self.chunk_text(content, kb.chunk_size, kb.chunk_overlap)
                
                # Create embeddings and store in ChromaDB
                collection = self._get_or_create_collection(kb.category)
                embedding_ids = []
                
                for i, chunk_content in enumerate(chunks):
                    # Create embedding
                    embedding = await self.create_embedding(chunk_content)
                    
                    # Store in ChromaDB
                    chunk_id = f"{document.id}_chunk_{i}"
                    collection.add(
                        ids=[chunk_id],
                        embeddings=[embedding],
                        documents=[chunk_content],
                        metadatas=[{
                            "document_id": document.id,
                            "chunk_index": i,
                            "title": title,
                            "content_type": content_type.value,
                            "category": kb.category.value
                        }]
                    )
                    
                    # Create document chunk record
                    chunk = DocumentChunk(
                        document_id=document.id,
                        chunk_index=i,
                        content=chunk_content,
                        embedding_id=chunk_id,
                        start_char=i * (kb.chunk_size - kb.chunk_overlap),
                        end_char=min((i + 1) * kb.chunk_size, len(content)),
                        token_count=len(self.tokenizer.encode(chunk_content))
                    )
                    session.add(chunk)
                    
                    embedding_ids.append(chunk_id)
                
                # Update document
                document.embedding_id = f"doc_{document.id}"
                document.vector_count = len(chunks)
                document.is_processed = True
                
                session.commit()
                
                logger.info(f"Added document {document.id} with {len(chunks)} chunks")
                return document.id
                
        except Exception as e:
            logger.error(f"Failed to add document: {e}")
            raise
    
    async def search_documents(
        self,
        query: str,
        category: KnowledgeBaseCategory = None,
        limit: int = 5,
        min_score: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Search documents using hybrid search (semantic + keyword)"""
        start_time = time.time()
        
        try:
            # Create query embedding
            query_embedding = await self.create_embedding(query)
            
            results = []
            
            # Search in specific category or all categories
            categories_to_search = [category] if category else list(KnowledgeBaseCategory)
            
            for cat in categories_to_search:
                try:
                    collection = self._get_or_create_collection(cat)
                    
                    # Semantic search
                    semantic_results = collection.query(
                        query_embeddings=[query_embedding],
                        n_results=min(limit * 2, 20),
                        include=["documents", "metadatas", "distances"]
                    )
                    
                    # Process results
                    for i, (doc, metadata, distance) in enumerate(zip(
                        semantic_results["documents"][0],
                        semantic_results["metadatas"][0],
                        semantic_results["distances"][0]
                    )):
                        # Convert distance to similarity score
                        similarity_score = 1 - distance
                        
                        if similarity_score >= min_score:
                            results.append({
                                "content": doc,
                                "metadata": metadata,
                                "similarity_score": similarity_score,
                                "search_type": "semantic",
                                "category": cat.value
                            })
                
                except Exception as e:
                    logger.warning(f"Failed to search in category {cat}: {e}")
                    continue
            
            # Sort by similarity score
            results.sort(key=lambda x: x["similarity_score"], reverse=True)
            
            # Take top results
            top_results = results[:limit]
            
            # Log query for analytics
            execution_time = int((time.time() - start_time) * 1000)
            await self._log_query(query, category, len(top_results), execution_time)
            
            return top_results
            
        except Exception as e:
            logger.error(f"Failed to search documents: {e}")
            raise
    
    async def search_with_keywords(
        self,
        query: str,
        category: KnowledgeBaseCategory = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search documents using keyword matching"""
        try:
            with get_session() as session:
                # Build query
                q = session.query(DocumentChunk).join(Document).join(KnowledgeBase)
                
                if category:
                    q = q.filter(KnowledgeBase.category == category)
                
                # Simple keyword search
                keywords = re.findall(r'\b\w+\b', query.lower())
                conditions = []
                
                for keyword in keywords:
                    conditions.append(DocumentChunk.content.ilike(f"%{keyword}%"))
                
                if conditions:
                    q = q.filter(or_(*conditions))
                
                # Get results
                chunks = q.limit(limit * 3).all()
                
                # Calculate TF-IDF scores (simplified)
                results = []
                for chunk in chunks:
                    # Simple keyword match scoring
                    score = sum(1 for keyword in keywords if keyword in chunk.content.lower())
                    score = score / len(keywords) if keywords else 0
                    
                    if score > 0:
                        results.append({
                            "content": chunk.content,
                            "metadata": {
                                "document_id": chunk.document_id,
                                "chunk_index": chunk.chunk_index,
                                "title": chunk.document.title,
                                "content_type": chunk.document.content_type.value,
                                "category": chunk.document.knowledge_base.category.value
                            },
                            "similarity_score": score,
                            "search_type": "keyword",
                            "category": chunk.document.knowledge_base.category.value
                        })
                
                # Sort by score
                results.sort(key=lambda x: x["similarity_score"], reverse=True)
                
                return results[:limit]
                
        except Exception as e:
            logger.error(f"Failed to search with keywords: {e}")
            raise
    
    async def hybrid_search(
        self,
        query: str,
        category: KnowledgeBaseCategory = None,
        limit: int = 5,
        semantic_weight: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Hybrid search combining semantic and keyword search"""
        try:
            # Run both searches in parallel
            semantic_task = self.search_documents(query, category, limit * 2)
            keyword_task = self.search_with_keywords(query, category, limit * 2)
            
            semantic_results, keyword_results = await asyncio.gather(
                semantic_task, keyword_task
            )
            
            # Combine and deduplicate results
            combined_results = {}
            
            # Add semantic results
            for result in semantic_results:
                doc_id = result["metadata"].get("document_id")
                if doc_id not in combined_results:
                    combined_results[doc_id] = result
                    combined_results[doc_id]["final_score"] = result["similarity_score"] * semantic_weight
            
            # Add keyword results
            keyword_weight = 1 - semantic_weight
            for result in keyword_results:
                doc_id = result["metadata"].get("document_id")
                if doc_id in combined_results:
                    # Combine scores
                    combined_results[doc_id]["final_score"] += result["similarity_score"] * keyword_weight
                else:
                    combined_results[doc_id] = result
                    combined_results[doc_id]["final_score"] = result["similarity_score"] * keyword_weight
            
            # Sort by final score and return top results
            final_results = list(combined_results.values())
            final_results.sort(key=lambda x: x["final_score"], reverse=True)
            
            return final_results[:limit]
            
        except Exception as e:
            logger.error(f"Failed to perform hybrid search: {e}")
            raise
    
    def build_context(
        self,
        search_results: List[Dict[str, Any]],
        max_tokens: int = 2000
    ) -> str:
        """Build context string from search results"""
        if not search_results:
            return ""
        
        context_parts = []
        current_tokens = 0
        
        for result in search_results:
            content = result["content"]
            metadata = result["metadata"]
            
            # Estimate tokens
            content_tokens = len(self.tokenizer.encode(content))
            
            if current_tokens + content_tokens > max_tokens:
                break
            
            # Format context
            context_part = f"""
**{metadata.get('title', 'Unknown')}** ({metadata.get('category', 'Unknown')})
Score: {result['similarity_score']:.3f}

{content}

---
"""
            context_parts.append(context_part)
            current_tokens += content_tokens
        
        return "\n".join(context_parts)
    
    async def _log_query(
        self,
        query: str,
        category: KnowledgeBaseCategory,
        results_count: int,
        execution_time_ms: int
    ):
        """Log query for analytics"""
        try:
            with get_session() as session:
                rag_query = RAGQuery(
                    query_text=query,
                    query_category=category,
                    results_count=results_count,
                    execution_time_ms=execution_time_ms
                )
                session.add(rag_query)
                session.commit()
        except Exception as e:
            logger.warning(f"Failed to log query: {e}")
    
    async def get_relevant_context_for_workflow_generation(
        self,
        user_input: str,
        workflow_type: str = None
    ) -> str:
        """Get relevant context for workflow generation"""
        try:
            # Determine search categories based on input
            categories_to_search = [
                KnowledgeBaseCategory.WORKFLOW_PATTERNS,
                KnowledgeBaseCategory.BEST_PRACTICES
            ]
            
            if "error" in user_input.lower() or "fail" in user_input.lower():
                categories_to_search.append(KnowledgeBaseCategory.ERROR_SOLUTIONS)
            
            if "code" in user_input.lower() or "script" in user_input.lower():
                categories_to_search.append(KnowledgeBaseCategory.CODE_TEMPLATES)
            
            # Search in multiple categories
            all_results = []
            for category in categories_to_search:
                results = await self.hybrid_search(
                    query=user_input,
                    category=category,
                    limit=3
                )
                all_results.extend(results)
            
            # Sort by score and take top results
            all_results.sort(key=lambda x: x["final_score"], reverse=True)
            top_results = all_results[:5]
            
            # Build context
            context = self.build_context(top_results)
            
            if context:
                context = f"""
## Relevant Knowledge Base Context

{context}

Use this context to generate a more accurate and complete workflow.
"""
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to get context for workflow generation: {e}")
            return ""
    
    async def get_relevant_context_for_error_fix(
        self,
        error_message: str,
        workflow_context: str = None
    ) -> str:
        """Get relevant context for error fixing"""
        try:
            # Search for error solutions
            results = await self.hybrid_search(
                query=error_message,
                category=KnowledgeBaseCategory.ERROR_SOLUTIONS,
                limit=5
            )
            
            # Also search for related workflow patterns if context provided
            if workflow_context:
                pattern_results = await self.hybrid_search(
                    query=workflow_context,
                    category=KnowledgeBaseCategory.WORKFLOW_PATTERNS,
                    limit=3
                )
                results.extend(pattern_results)
            
            # Build context
            context = self.build_context(results)
            
            if context:
                context = f"""
## Error Resolution Context

Based on the error and similar cases in the knowledge base:

{context}

Use this context to fix the error and improve the workflow.
"""
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to get context for error fix: {e}")
            return ""
    
    async def create_knowledge_base(
        self,
        name: str,
        description: str,
        category: KnowledgeBaseCategory,
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ) -> str:
        """Create a new knowledge base"""
        try:
            with get_session() as session:
                kb = KnowledgeBase(
                    name=name,
                    description=description,
                    category=category,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap
                )
                session.add(kb)
                session.commit()
                
                logger.info(f"Created knowledge base: {kb.id}")
                return kb.id
                
        except Exception as e:
            logger.error(f"Failed to create knowledge base: {e}")
            raise
    
    async def list_knowledge_bases(self) -> List[Dict[str, Any]]:
        """List all knowledge bases"""
        try:
            with get_session() as session:
                kbs = session.query(KnowledgeBase).all()
                
                return [
                    {
                        "id": kb.id,
                        "name": kb.name,
                        "description": kb.description,
                        "category": kb.category.value,
                        "is_active": kb.is_active,
                        "document_count": len(kb.documents),
                        "created_at": kb.created_at.isoformat()
                    }
                    for kb in kbs
                ]
                
        except Exception as e:
            logger.error(f"Failed to list knowledge bases: {e}")
            raise


# Global RAG service instance
_rag_service = None

def get_rag_service() -> RAGService:
    """Get global RAG service instance"""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
