"""RAG (Retrieval-Augmented Generation) service for enhanced workflow generation"""

import asyncio
import time
from typing import List, Dict, Any, Optional, Tuple
import json
import re
from datetime import datetime

import chromadb
from chromadb.config import Settings
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
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
        
        # ✨ Create OpenAI embedding function for ChromaDB
        self.embedding_function = OpenAIEmbeddingFunction(
            api_key=self.settings.openai_api_key,
            model_name="text-embedding-3-small"
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
        """Get or create ChromaDB collection with OpenAI embeddings"""
        collection_name = self._get_collection_name(category)
        
        if collection_name not in self._collections_cache:
            try:
                collection = self.chroma_client.get_collection(collection_name)
            except Exception:
                collection = self.chroma_client.create_collection(
                    name=collection_name,
                    metadata={"category": category.value},
                    embedding_function=self.embedding_function
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
    
    def chunk_text(self, text: str, chunk_size: int = 1500, overlap: int = 300) -> List[str]:
        """Split text into chunks with overlap for better context preservation
        
        Args:
            text: Text to chunk
            chunk_size: Size of each chunk in tokens (increased to 1500 for better context)
            overlap: Overlap between chunks in tokens (increased to 300 for stronger coherence)
            
        Returns:
            List of text chunks
        """
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
                            "category": kb.category.value,
                            "has_previous": i > 0,  # ← 신규: 이전 청크 존재 여부
                            "has_next": i < len(chunks) - 1  # ← 신규: 다음 청크 존재 여부
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
                        include=["documents", "metadatas", "distances", "embeddings"]
                    )
                    
                    # Process results
                    for i, (doc, metadata, distance, embedding) in enumerate(zip(
                        semantic_results["documents"][0],
                        semantic_results["metadatas"][0],
                        semantic_results["distances"][0],
                        semantic_results["embeddings"][0]
                    )):
                        # For normalized vectors (OpenAI embeddings), compute cosine similarity directly
                        # cosine_similarity = dot_product(normalized_vec1, normalized_vec2)
                        cosine_sim = np.dot(query_embedding, embedding)
                        
                        # Clamp to [0, 1] range
                        similarity_score = max(0, min(1, cosine_sim))
                        
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
        """Search documents using improved keyword matching with Korean support"""
        try:
            with get_session() as session:
                q = session.query(DocumentChunk).join(Document).join(KnowledgeBase)
                
                if category:
                    q = q.filter(KnowledgeBase.category == category)
                
                # Extract keywords with Korean support
                # \w matches [a-zA-Z0-9_], add Korean characters (가-힣)
                keywords = re.findall(r'[\w가-힣]+', query.lower())
                
                # Remove stop words (English and Korean)
                stop_words = {
                    # English
                    'the', 'a', 'an', 'is', 'are', 'was', 'be', 'have', 'has', 
                    'do', 'does', 'did', 'to', 'of', 'in', 'on', 'at', 'by', 'or', 'and',
                    'this', 'that', 'these', 'those', 'what', 'which', 'who',
                    # Korean (common particles and prepositions)
                    '이', '그', '저', '것', '수', '등', '및', '등등', '들', '만',
                    '으로', '로', '에', '에서', '와', '과', '나', '이나', '거나',
                    '도', '까지', '부터', '같이', '처럼', '대로', '대해', '한테'
                }
                keywords = [k for k in keywords if k not in stop_words and len(k) > 1]
                
                if not keywords:
                    return []
                
                conditions = []
                for keyword in keywords:
                    conditions.append(DocumentChunk.content.ilike(f"%{keyword}%"))
                
                if conditions:
                    q = q.filter(or_(*conditions))
                
                chunks = q.limit(limit * 3).all()
                
                results = []
                for chunk in chunks:
                    content_lower = chunk.content.lower()
                    title_lower = chunk.document.title.lower()
                    tags = [tag.lower() for tag in (chunk.document.tags or [])]
                    
                    # Improved scoring: count keyword occurrences
                    score = 0
                    keyword_matches = {}
                    
                    for keyword in keywords:
                        # Count occurrences of each keyword
                        occurrences = content_lower.count(keyword)
                        if occurrences > 0:
                            keyword_matches[keyword] = occurrences
                            # Weight by occurrence count (cap at 3)
                            score += min(occurrences, 3)
                    
                    # Normalize by total possible score
                    max_possible_score = len(keywords) * 3
                    normalized_score = score / max_possible_score if max_possible_score > 0 else 0
                    
                    # Boost score if multiple keywords appear close together
                    if len(keyword_matches) > 1:
                        keywords_in_content = list(keyword_matches.keys())
                        for i in range(len(keywords_in_content) - 1):
                            k1, k2 = keywords_in_content[i], keywords_in_content[i+1]
                            idx1 = content_lower.find(k1)
                            idx2 = content_lower.find(k2)
                            if idx1 >= 0 and idx2 >= 0 and abs(idx2 - idx1) < 100:
                                normalized_score *= 1.15  # Boost by 15%
                    
                    # Boost if matched keywords appear early in content
                    if normalized_score > 0:
                        first_match_pos = min(
                            (content_lower.find(k) for k in keyword_matches if content_lower.find(k) >= 0),
                            default=len(content_lower)
                        )
                        if first_match_pos < 200:  # First 200 characters
                            normalized_score *= 1.2  # Boost by 20%
                    
                    # ✨ Boost score for title matches (high weight!)
                    title_match_count = sum(1 for keyword in keywords if keyword in title_lower)
                    if title_match_count > 0:
                        # Title match boost: 50-100% depending on match count
                        title_boost = 1.5 + (0.3 * min(title_match_count, 3))  # 1.5 ~ 2.4
                        normalized_score *= title_boost
                    
                    # ✨ Boost score for tag matches (medium weight)
                    tag_match_count = 0
                    for tag in tags:
                        for keyword in keywords:
                            if keyword in tag or tag in keyword:
                                tag_match_count += 1
                                break
                    
                    if tag_match_count > 0:
                        # Tag match boost: 25-60% depending on match count
                        tag_boost = 1.25 + (0.15 * min(tag_match_count, 3))  # 1.25 ~ 1.7
                        normalized_score *= tag_boost
                    
                    normalized_score = min(normalized_score, 1.0)  # Cap at 1.0
                    
                    if normalized_score > 0:
                        results.append({
                            "content": chunk.content,
                            "metadata": {
                                "document_id": chunk.document_id,
                                "chunk_index": chunk.chunk_index,
                                "title": chunk.document.title,
                                "content_type": chunk.document.content_type.value,
                                "category": chunk.document.knowledge_base.category.value
                            },
                            "similarity_score": normalized_score,
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
        semantic_weight: float = 0.3,
        include_context: bool = True,
        context_radius: int = 1
    ) -> List[Dict[str, Any]]:
        """Hybrid search combining semantic and keyword search with optional context expansion
        
        Args:
            query: Search query
            category: Knowledge base category to search
            limit: Number of results to return
            semantic_weight: Weight for semantic search (0.0-1.0)
            include_context: Whether to include adjacent chunks
            context_radius: Number of adjacent chunks to include (before and after)
            
        Returns:
            List of search results with optional expanded context
        """
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
            final_results = final_results[:limit]
            
            # 🌟 Expand context if requested
            if include_context:
                final_results = await self._expand_with_context(final_results, context_radius)
            
            return final_results
            
        except Exception as e:
            logger.error(f"Failed to perform hybrid search: {e}")
            raise
    
    async def _expand_with_context(
        self,
        results: List[Dict[str, Any]],
        context_radius: int = 1
    ) -> List[Dict[str, Any]]:
        """Expand results to include adjacent chunks for better context
        
        Args:
            results: Search results with chunk metadata
            context_radius: Number of adjacent chunks to include
            
        Returns:
            Results with expanded context
        """
        try:
            expanded_results = []
            
            with get_session() as session:
                for result in results:
                    doc_id = result["metadata"].get("document_id")
                    chunk_idx = result["metadata"].get("chunk_index", 0)
                    
                    # Get the document with all its chunks
                    document = session.query(Document).get(doc_id)
                    if not document or not document.chunks:
                        expanded_results.append(result)
                        continue
                    
                    # Sort chunks by index
                    sorted_chunks = sorted(document.chunks, key=lambda c: c.chunk_index)
                    
                    # Calculate context range
                    start_idx = max(0, chunk_idx - context_radius)
                    end_idx = min(len(sorted_chunks), chunk_idx + context_radius + 1)
                    
                    # Combine chunks in context range
                    context_chunks = sorted_chunks[start_idx:end_idx]
                    combined_content = "\n\n".join([
                        f"[Chunk {chunk.chunk_index}] {chunk.content}"
                        for chunk in context_chunks
                    ])
                    
                    # Add original chunk reference
                    result["original_chunk"] = result["content"]
                    result["original_chunk_index"] = chunk_idx
                    result["content"] = combined_content
                    result["context_chunks_count"] = len(context_chunks)
                    result["context_range"] = f"{start_idx}~{end_idx-1}"
                    
                    expanded_results.append(result)
            
            return expanded_results
            
        except Exception as e:
            logger.warning(f"Failed to expand context: {e}")
            # Return original results if context expansion fails
            return results
    
    def build_context(self, search_results, max_tokens: int = 30000):
        """Build context string from search results with proper token counting"""
        if not search_results:
            return ""
        
        context_parts = []
        current_tokens = 0
        seen_results = set()  # Track which search results we've seen (by index/id)
        
        for i, result in enumerate(search_results):
            # Create unique key for this search result
            result_id = f"{result.get('metadata', {}).get('document_id')}_{i}"
            
            if result_id in seen_results:
                continue
            seen_results.add(result_id)
            
            content = result.get("content", "")
            metadata = result.get("metadata", {})
            
            # Estimate tokens for this result
            content_tokens = len(self.tokenizer.encode(content))
            
            # Check if adding this would exceed limit
            if current_tokens + content_tokens > max_tokens:
                logger.info(f"Reached max_tokens limit ({current_tokens + content_tokens} > {max_tokens}). "
                           f"Included {len(seen_results)} results so far.")
                break
            
            # Build context part
            # Extract and format score outside f-string to avoid formatting issues
            final_score = result.get('final_score', 'N/A')
            if isinstance(final_score, (int, float)):
                score_str = f"{final_score:.3f}"
            else:
                score_str = 'N/A'
            
            # Check if this is expanded context (multiple chunks combined)
            context_chunks_count = result.get('context_chunks_count', 1)
            chunk_range = result.get('context_range', 'N/A')
            
            if context_chunks_count and context_chunks_count > 1:
                chunk_info = f"Chunks: {chunk_range} ({context_chunks_count}개)"
            else:
                chunk_idx = metadata.get('chunk_index', 'N/A')
                chunk_info = f"Chunk: {chunk_idx}"
            
            context_part = f"""
**{metadata.get('title', 'Unknown')}**
Source: {metadata.get('category', 'Unknown')}
{chunk_info}
Score: {score_str}

{content}

---
"""
            context_parts.append(context_part)
            current_tokens += content_tokens
            
            logger.debug(f"Added result {i}: {content_tokens} tokens (total: {current_tokens}/{max_tokens})")
        
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
    
    async def get_relevant_context_for_workflow_generation(self, user_input: str):
        """Get relevant context for workflow generation with improved hybrid search and context expansion"""
        try:
            logger.info(f"Getting RAG context for workflow generation: '{user_input[:50]}...'")
            
            # Try specific categories first
            categories_to_search = [
                KnowledgeBaseCategory.WORKFLOW_PATTERNS,
                KnowledgeBaseCategory.BEST_PRACTICES,
                KnowledgeBaseCategory.CODE_TEMPLATES,
            ]
            
            all_results = []
            for category in categories_to_search:
                try:
                    # Use hybrid_search with context expansion (context_radius=1 = 1 chunk before + 1 chunk after)
                    results = await self.hybrid_search(
                        query=user_input,
                        category=category,
                        limit=5,  # ⬆️ Increased from 3 to 5 per category
                        semantic_weight=0.3,  # 30% semantic, 70% keyword
                        include_context=True,  # ✨ Enable context expansion
                        context_radius=1       # ✨ Include 1 adjacent chunk before and after
                    )
                    logger.debug(f"Category {category.value}: {len(results)} results")
                    all_results.extend(results)
                except Exception as e:
                    logger.warning(f"Failed to search category {category.value}: {e}")
                    continue
            
            logger.info(f"Total RAG results from primary categories: {len(all_results)}")
            
            # If no results from primary categories, try all categories
            if not all_results:
                logger.info("No results from primary categories, trying all categories...")
                
                all_categories = [cat for cat in KnowledgeBaseCategory]
                for category in all_categories:
                    if category in categories_to_search:
                        continue  # Already tried
                    
                    try:
                        results = await self.hybrid_search(
                            query=user_input,
                            category=category,
                            limit=5,  # ⬆️ Increased from 3 to 5 per category
                            semantic_weight=0.3,
                            include_context=True,
                            context_radius=1
                        )
                        logger.debug(f"Fallback category {category.value}: {len(results)} results")
                        all_results.extend(results)
                    except Exception as e:
                        logger.debug(f"Failed to search fallback category {category.value}: {e}")
                        continue
            
            logger.info(f"Total RAG results after fallback: {len(all_results)}")
            
            if not all_results:
                logger.warning(f"No RAG results found for query: '{user_input}'")
                return ""
            
            # Sort by final_score and take top results
            all_results.sort(key=lambda x: x.get("final_score", x.get("similarity_score", 0)), reverse=True)
            top_results = all_results[:10]  # ⬆️ Increased from 5 to 10 top results
            
            logger.info(f"Top {len(top_results)} RAG results selected for context")
            
            # Build context from results (now with expanded content)
            context = self.build_context(top_results, max_tokens=30000)
            
            logger.info(f"Built context: {len(context)} chars")
            
            if context:
                # Add header to indicate RAG context
                formatted_context = f"""
## 📚 Relevant Knowledge Base Context
(최고 관련성 우선 - 인접 청크 포함하여 전체 문맥 제공)

{context}

Use this context to generate a more accurate and complete workflow.
"""
                logger.info(f"Returning formatted context: {len(formatted_context)} chars")
                return formatted_context
            else:
                logger.warning("Context is empty after build_context")
                return ""
            
        except Exception as e:
            logger.error(f"Failed to get context for workflow generation: {e}", exc_info=True)
            return ""
    
    async def get_relevant_context_for_error_fix(
        self,
        error_message: str,
        workflow_context: str = None
    ) -> str:
        """Get relevant context for error fixing with context expansion"""
        try:
            # Search for error solutions with context expansion
            results = await self.hybrid_search(
                query=error_message,
                category=KnowledgeBaseCategory.ERROR_SOLUTIONS,
                limit=5,
                include_context=True,  # ✨ Enable context expansion
                context_radius=1       # ✨ Include adjacent chunks
            )
            
            # Also search for related workflow patterns if context provided
            if workflow_context:
                pattern_results = await self.hybrid_search(
                    query=workflow_context,
                    category=KnowledgeBaseCategory.WORKFLOW_PATTERNS,
                    limit=5,  # ⬆️ Increased from 3 to 5
                    include_context=True,  # ✨ Enable context expansion
                    context_radius=1       # ✨ Include adjacent chunks
                )
                results.extend(pattern_results)
            
            # Build context from expanded results
            context = self.build_context(results, max_tokens=30000)  # 15000 → 30000 (더 긴 컨텍스트 수용)
            
            if context:
                context = f"""
## Error Resolution Context
(인접 청크 포함하여 전체 문맥 제공)

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
