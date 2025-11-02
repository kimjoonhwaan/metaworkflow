"""RAG (Retrieval-Augmented Generation) service with metadata-based search"""

import asyncio
import time
from typing import List, Dict, Any, Optional
import json
import re
from datetime import datetime

import chromadb
from chromadb.config import Settings
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
import tiktoken
import numpy as np

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_

from ..database.models import (
    KnowledgeBase, Document, DocumentMetadata, DocumentChunk, RAGQuery,
    KnowledgeBaseCategory, DocumentContentType, Domain
)
from ..database.session import get_session
from ..utils.config import get_settings
from ..utils.logger import get_logger
from ..utils.openai_client import get_openai_client
from .domain_service import get_domain_service

logger = get_logger(__name__)


class RAGService:
    """
    Metadata-based RAG service with domain-based collection separation
    - Embeds only metadata (title, keywords, technologies, description)
    - Stores full content in database
    - Retrieves full content after metadata match
    - Separates documents by domain (naver, weather, kakao, google, common)
    """
    
    # Note: Domain management is now handled dynamically via DomainService
    # No hardcoded domain lists needed!
    
    def __init__(self):
        self.settings = get_settings()
        self.openai_client = get_openai_client()
        
        # ✨ NEW: Domain service for dynamic domain management
        self.domain_service = get_domain_service()
        
        # Disable ChromaDB telemetry and logging
        import os
        import logging
        os.environ["ANONYMIZED_TELEMETRY"] = "False"
        os.environ["CHROMA_TELEMETRY_ENABLED"] = "False"
        
        # Suppress ChromaDB's telemetry logger completely
        logging.getLogger("chromadb.telemetry").setLevel(logging.CRITICAL)
        logging.getLogger("chromadb").setLevel(logging.ERROR)
        logging.getLogger("chromadb.telemetry.posthog").setLevel(logging.CRITICAL)
        
        # Initialize ChromaDB
        self.chroma_client = chromadb.PersistentClient(
            path="./data/chroma_db",
            settings=Settings(anonymized_telemetry=False)
        )
        
        # ✨ OpenAI embedding function for ChromaDB
        self.embedding_function = OpenAIEmbeddingFunction(
            api_key=self.settings.openai_api_key,
            model_name="text-embedding-3-small"
        )
        
        # Tokenizer for text processing
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        
        # Collection cache
        self._collections_cache = {}
    
    def _get_collection_name_for_domain(self, domain: str) -> str:
        """
        Get ChromaDB collection name for domain (dynamic)
        
        Args:
            domain: Domain name (from database)
        
        Returns:
            Collection name in ChromaDB (e.g., "collection_네이버")
        """
        # Get domain from database to get collection name
        domain_obj = self.domain_service.get_domain_by_name(domain)
        
        if domain_obj:
            collection_name = domain_obj.collection_name
        else:
            # Fallback: generate collection name
            collection_name = f"collection_{domain}"
            logger.warning(f"⚠️ Domain '{domain}' not found in database, using fallback: {collection_name}")
        
        logger.debug(f"📂 Collection for domain '{domain}': {collection_name}")
        return collection_name
    
    def _get_collection_for_domain(self, domain: str):
        """
        Get or create ChromaDB collection for domain
        
        Args:
            domain: Domain name
        
        Returns:
            ChromaDB Collection object
        """
        collection_name = self._get_collection_name_for_domain(domain)
        cache_key = f"domain_{domain}"
        
        if cache_key not in self._collections_cache:
            try:
                # Try to get existing collection
                collection = self.chroma_client.get_collection(
                    name=collection_name,
                    embedding_function=self.embedding_function
                )
                logger.debug(f"✅ Got existing collection: {collection_name}")
            except Exception:
                # Create new collection if doesn't exist
                collection = self.chroma_client.create_collection(
                    name=collection_name,
                    embedding_function=self.embedding_function,
                    metadata={"hnsw:space": "cosine"}
                )
                logger.info(f"✨ Created new collection: {collection_name}")
            
            self._collections_cache[cache_key] = collection
        
        return self._collections_cache[cache_key]
    
    def _get_collection_name(self, category: KnowledgeBaseCategory) -> str:
        """Get ChromaDB collection name for category"""
        return f"metadata_{category.value.lower()}"
    
    def _get_or_create_collection(self, category: KnowledgeBaseCategory):
        """Get or create ChromaDB collection with OpenAI embeddings"""
        collection_name = self._get_collection_name(category)
        
        if collection_name not in self._collections_cache:
            try:
                # Try to get existing collection first
                try:
                    collection = self.chroma_client.get_collection(collection_name)
                    logger.info(f"✅ Using existing collection: {collection_name}")
                except Exception as e:
                    # Collection doesn't exist, create new one
                    logger.info(f"✨ Creating new collection: {collection_name}")
                    collection = self.chroma_client.create_collection(
                        name=collection_name,
                        metadata={"category": category.value},
                        embedding_function=self.embedding_function
                    )
                    
            except Exception as e:
                logger.error(f"Failed to get or create collection {collection_name}: {e}")
                raise
            
            self._collections_cache[collection_name] = collection
        
        return self._collections_cache[collection_name]
    
    async def add_document(
        self,
        document: Document,
        metadata_obj: DocumentMetadata,
        domain: str = None  # ✨ NEW: Optional domain parameter
    ) -> bool:
        """
        Add document to RAG system with domain-based collection
        - Embeds metadata (searchable_text) to domain-specific collection
        - References full content in database
        
        Args:
            document: Document object with content
            metadata_obj: DocumentMetadata object
            domain: Optional domain override (default: uses document.domain)
        """
        try:
            # ✨ Step 1: Get domain (priority: parameter > document.domain > "common")
            doc_domain = domain or document.domain or "common"
            logger.info(f"📝 Adding document to domain '{doc_domain}': {document.title}")
            
            # ✨ Step 2: Update document domain if specified
            if domain and document.domain != domain:
                document.domain = domain
                logger.debug(f"📝 Updated document domain to '{domain}'")
            
            # ✨ Step 3: Get domain-specific collection
            collection = self._get_collection_for_domain(doc_domain)
            
            # ✨ Step 4: Prepare metadata for ChromaDB
            chroma_metadata = {
                "document_id": document.id,
                "title": document.title,
                "domain": doc_domain,  # ✨ Store domain for filtering
                "doc_type": metadata_obj.doc_type or "unknown",
                "content_type": document.content_type.value,
            }
            
            # ✨ Step 5: Prepare embedding text
            keywords_str = " ".join(metadata_obj.keywords or []) if metadata_obj.keywords else ""
            searchable_with_title = (
                f"{document.title}\n"
                f"{keywords_str}\n"
                f"{metadata_obj.searchable_text}"
            ).strip()
            
            # ✨ Step 6: Add to domain-specific collection
            collection.add(
                ids=[document.id],
                documents=[searchable_with_title],
                metadatas=[chroma_metadata]
            )
            
            # Log what's being embedded
            logger.info(f"📝 Embedding text (first 150 chars): {searchable_with_title[:150]}...")
            
            # Log metadata for verification
            logger.info(f"📌 Metadata stored in ChromaDB:")
            logger.info(f"   - Title: {chroma_metadata['title']}")
            logger.info(f"   - Domain: {chroma_metadata['domain']}")
            logger.info(f"   - Doc Type: {chroma_metadata['doc_type']}")
            logger.info(f"   - Document ID: {chroma_metadata['document_id']}")
            
            # ✨ Step 7: Update embedding_id and domain in database
            with get_session() as session:
                metadata = session.query(DocumentMetadata).filter(
                    DocumentMetadata.document_id == document.id
                ).first()
                if metadata:
                    metadata.embedding_id = document.id
                    metadata.domain = doc_domain  # ✨ Store domain
                    session.commit()
                    logger.debug(f"✅ Updated metadata for document {document.id}")
            
            logger.info(f"✅ Added document to {doc_domain} collection: {document.title} (ID: {document.id})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to add document {document.id}: {e}")
            raise
    
    async def search_metadata(
        self,
        query: str,
        domain: str = None,  # ✨ NEW: Domain parameter for targeted search
        category: KnowledgeBaseCategory = None,  # For backward compatibility
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for documents by metadata with domain-based collection separation
        
        Args:
            query: Search query
            domain: Domain name (None = search all domains)
            category: Legacy parameter (ignored in domain-based search)
            limit: Number of results to return
        
        Returns:
            List of search results with metadata and content
        """
        try:
            logger.info(f"🔍 Searching: '{query}' in domain: {domain or 'all'}")
            
            if domain:
                # ✨ Step 1: Specific domain + common domain search
                all_results = []
                
                # 1-1. Search specific domain collection
                try:
                    specific_collection = self._get_collection_for_domain(domain)
                    specific_results = specific_collection.query(
                        query_texts=[query],
                        n_results=limit,
                        include=["documents", "metadatas", "distances"]
                    )
                    specific_items = self._parse_search_results(specific_results)
                    all_results.extend(specific_items)
                    logger.debug(f"  📂 {domain}: {len(specific_items)} results")
                except Exception as e:
                    logger.debug(f"  ⚠️ {domain} search failed: {e}")
                
                # 1-2. Search common collection
                try:
                    common_collection = self._get_collection_for_domain("common")
                    common_results = common_collection.query(
                        query_texts=[query],
                        n_results=limit,
                        include=["documents", "metadatas", "distances"]
                    )
                    common_items = self._parse_search_results(common_results)
                    
                    # Remove duplicates (same document_id)
                    existing_ids = {r["document_id"] for r in all_results}
                    unique_common = [
                        r for r in common_items
                        if r["document_id"] not in existing_ids
                    ]
                    
                    all_results.extend(unique_common)
                    logger.debug(f"  📂 common: {len(unique_common)} unique results")
                
                except Exception as e:
                    logger.debug(f"  ⚠️ common collection search failed: {e}")
                
                # 1-3. Sort by domain (specific first) and then by similarity
                all_results.sort(key=lambda x: (
                    x["domain"] != domain,  # Specific domain first
                    -x["similarity_score"]  # Then by similarity
                ))
                
                final_results = all_results[:limit]
                logger.info(f"✅ Found {len(final_results)} results in '{domain}' + common")
            
            else:
                # ✨ Step 2: Search all domains
                all_results = []
                
                # Get all active domains dynamically
                all_domains = self.domain_service.get_all_domains()
                
                for domain_obj in all_domains:
                    domain_key = domain_obj.name
                    try:
                        collection = self._get_collection_for_domain(domain_key)
                        
                        results = collection.query(
                            query_texts=[query],
                            n_results=limit,
                            include=["documents", "metadatas", "distances"]
                        )
                        
                        domain_results = self._parse_search_results(results)
                        all_results.extend(domain_results)
                        logger.debug(f"  📂 {domain_key}: {len(domain_results)} results")
                    
                    except Exception as e:
                        logger.debug(f"  ⚠️ {domain_key} search failed: {e}")
                        continue
                
                # Sort by similarity
                all_results.sort(key=lambda x: x["similarity_score"], reverse=True)
                final_results = all_results[:limit]
                
                logger.info(f"✅ Found {len(final_results)} total results from all domains")
            
            return final_results
        
        except Exception as e:
            logger.error(f"❌ Search failed: {e}")
            return []
    
    def _parse_search_results(self, results) -> List[Dict]:
        """Parse ChromaDB search results into standardized format"""
        all_results = []
        
        if results and results["ids"] and len(results["ids"]) > 0:
            for i, doc_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i]
                distance = results["distances"][0][i]
                
                # Calculate similarity score
                if distance < 0.1:
                    similarity = 1.0 - (distance * 2)
                else:
                    similarity = max(0, 1.0 - (distance / 2.0))
                similarity = max(0, min(1, similarity))
                
                result_item = {
                    "document_id": doc_id,
                    "title": metadata.get("title", "Unknown"),
                    "domain": metadata.get("domain", "unknown"),  # ✨ Include domain
                    "doc_type": metadata.get("doc_type", "unknown"),
                    "similarity_score": similarity,
                    "distance": distance,
                    "content": ""
                }
                
                # Retrieve full content from database
                try:
                    with get_session() as session:
                        doc = session.query(Document).filter(Document.id == doc_id).first()
                        if doc:
                            result_item["content"] = doc.content[:500] if doc.content else ""
                except Exception as e:
                    logger.debug(f"⚠️ Failed to retrieve content for {doc_id}: {e}")
                
                all_results.append(result_item)
        
        return all_results
    
    async def _get_query_embedding(self, query: str) -> Optional[List[float]]:
        """Get embedding for query text"""
        try:
            response = await self.openai_client.embeddings.create(
                input=query,
                model="text-embedding-3-small"
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to create query embedding: {e}")
            return None
    
    async def get_full_content(
        self,
        document_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Get full content of documents from database
        Called after metadata search
        """
        try:
            results = []
            
            with get_session() as session:
                for doc_id in document_ids:
                    doc = session.query(Document).filter(
                        Document.id == doc_id
                    ).first()
                    
                    if doc:
                        results.append({
                            "document_id": doc.id,
                            "title": doc.title,
                            "content": doc.content,  # ✨ Full content
                            "content_type": doc.content_type.value,
                            "tags": doc.tags or [],
                            "metadata": doc.kb_metadata or {}
                        })
                    else:
                        logger.warning(f"Document not found: {doc_id}")
            
            return results
        
        except Exception as e:
            logger.error(f"Failed to get full content: {e}")
            return []
    
    async def get_document_detail(
        self,
        document_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a single document
        Includes full content and all metadata
        
        Args:
            document_id: Document ID to retrieve
        
        Returns:
            Dictionary with complete document information or None if not found
        """
        try:
            with get_session() as session:
                # Query document with related objects
                doc = session.query(Document).filter(
                    Document.id == document_id
                ).first()
                
                if not doc:
                    logger.warning(f"Document not found: {document_id}")
                    return None
                
                # Get metadata
                metadata = session.query(DocumentMetadata).filter(
                    DocumentMetadata.document_id == document_id
                ).first()
                
                # Get chunks if available
                chunks = session.query(DocumentChunk).filter(
                    DocumentChunk.document_id == document_id
                ).all()
                
                # Build response
                result = {
                    "document_id": doc.id,
                    "title": doc.title,
                    "content": doc.content,
                    "content_type": doc.content_type.value,
                    "tags": doc.tags or [],
                    "kb_metadata": doc.kb_metadata or {},
                    "created_at": doc.created_at.isoformat() if doc.created_at else None,
                    "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
                    "is_processed": doc.is_processed,
                    "processing_error": doc.processing_error,
                    "knowledge_base_id": doc.knowledge_base_id,
                }
                
                # Add metadata info if available
                if metadata:
                    result["metadata_info"] = {
                        "searchable_text": metadata.searchable_text or "",
                        "keywords": metadata.keywords or [],
                        "description": metadata.description or "",
                        "doc_type": metadata.doc_type or "unknown",
                        "embedding_id": metadata.embedding_id
                    }
                
                # Add chunks info if available
                if chunks:
                    result["chunks"] = [
                        {
                            "chunk_id": chunk.id,
                            "chunk_index": chunk.chunk_index,
                            "content": chunk.content,
                            "embedding_id": chunk.embedding_id
                        }
                        for chunk in chunks
                    ]
                
                logger.info(f"✅ Retrieved document detail: {document_id}")
                return result
        
        except Exception as e:
            logger.error(f"Failed to get document detail: {e}")
            return None
    
    async def get_relevant_context_for_workflow_generation(
        self,
        query: str,
        max_tokens: int = 30000
    ) -> str:
        """
        Get context for workflow generation
        1. Search metadata
        2. Get full content
        3. Build context
        """
        try:
            logger.info(f"📚 Getting context for workflow generation: '{query}'")
            
            # Step 1: Search metadata
            metadata_results = await self.search_metadata(
                query=query,
                limit=5
            )
            
            if not metadata_results:
                logger.warning("⚠️ No relevant documents found")
                return ""
            
            # Step 2: Get full content
            document_ids = [r["document_id"] for r in metadata_results]
            full_contents = await self.get_full_content(document_ids)
            
            # Step 3: Build context
            context = self._build_context_from_contents(
                full_contents,
                metadata_results,
                max_tokens
            )
            
            logger.info(f"✅ Context built: {len(context)} chars")
            return context
        
        except Exception as e:
            logger.error(f"Failed to get relevant context: {e}")
            return ""
    
    def _build_context_from_contents(
        self,
        full_contents: List[Dict[str, Any]],
        metadata_results: List[Dict[str, Any]],
        max_tokens: int
    ) -> str:
        """Build context string from full contents"""
        context_parts = []
        current_tokens = 0
        
        # Create mapping for quick lookup
        metadata_map = {r["document_id"]: r for r in metadata_results}
        
        for content in full_contents:
            doc_id = content["document_id"]
            metadata = metadata_map.get(doc_id, {})
            
            content_tokens = len(self.tokenizer.encode(content["content"]))
            
            if current_tokens + content_tokens > max_tokens:
                logger.info(f"Reached max_tokens limit. Included {len(context_parts)} documents.")
                break
            
            similarity = metadata.get("similarity_score", "N/A")
            if isinstance(similarity, (int, float)):
                score_str = f"{similarity:.3f}"
            else:
                score_str = "N/A"
            
            context_part = f"""
**{content['title']}**
Source: {metadata.get('category', 'Unknown')}
Doc Type: {metadata.get('doc_type', 'unknown')}
Score: {score_str}

{content['content']}

---
"""
            context_parts.append(context_part)
            current_tokens += content_tokens
            logger.debug(f"Added {doc_id}: {content_tokens} tokens (total: {current_tokens}/{max_tokens})")
        
        return "\n".join(context_parts)
    
    async def get_relevant_context_for_error_fix(
        self,
        query: str,
        error_logs: Optional[str] = None,
        max_tokens: int = 30000
    ) -> str:
        """
        Get context for error fixing
        Similar to workflow generation but focused on error solutions
        """
        try:
            # Enhance query with error information
            if error_logs:
                enhanced_query = f"{query}\n\nError: {error_logs[:500]}"
            else:
                enhanced_query = query
            
            # Get context (same process)
            return await self.get_relevant_context_for_workflow_generation(
                enhanced_query,
                max_tokens
            )
        
        except Exception as e:
            logger.error(f"Failed to get error context: {e}")
            return ""
    
    async def _decompose_query_to_subqueries(
        self, 
        query: str, 
        num_queries: int = 4
    ) -> List[str]:
        """
        LLM을 사용해서 사용자 쿼리를 여러 서브-쿼리로 분해
        
        Args:
            query: 원본 사용자 쿼리
            num_queries: 생성할 서브-쿼리 개수
        
        Returns:
            서브-쿼리 목록 및 분해 정보
        """
        try:
            decompose_prompt = f"""당신은 정보 검색 전문가입니다.
        
사용자의 워크플로우 요청을 분석하고, 필요한 정보를 검색하기 위한 여러 개의 검색 쿼리로 분해해주세요.

사용자 요청: "{query}"

다음과 같이 {num_queries}개의 구체적인 검색 쿼리를 생성해주세요:
1. 각 쿼리는 특정 관심사나 기술에 초점을 맞춥니다
2. 쿼리들은 상호 보완적이어야 합니다
3. 각 쿼리는 한 줄의 짧은 문장이어야 합니다
4. ⚠️ 중요: 일반적인 단어 (예: "API", "데이터", "코드")를 최대한 피하고 구체적인 기술이나 라이브러리명을 포함하세요
5. 예시: "Selenium으로 동적 웹 페이지 크롤링" (O) vs "웹 크롤링" (X)

JSON 형식으로 응답해주세요:
{{
    "subqueries": [
        "첫 번째 구체적인 쿼리",
        "두 번째 구체적인 쿼리",
        ...
    ]
}}"""
            
            from langchain_openai import ChatOpenAI
            from langchain.schema import HumanMessage
            
            llm = ChatOpenAI(
                model=self.settings.openai_model,
                api_key=self.settings.openai_api_key,
                temperature=1,
                reasoning_effort="minimal"
            )
            
            response = await llm.ainvoke([HumanMessage(content=decompose_prompt)])
            
            # Parse JSON response
            response_text = response.content
            try:
                # Extract JSON from response
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    subqueries = result.get("subqueries", [])
                    logger.info(f"✅ Generated {len(subqueries)} subqueries")
                    return subqueries
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse LLM response: {response_text}")
            
            # Fallback: return original query
            logger.warning("Fallback: Using original query only")
            return [query]
        
        except Exception as e:
            logger.error(f"Failed to decompose query: {e}")
            return [query]
    
    def _deduplicate_metadata_results(
        self,
        all_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        여러 검색 결과에서 중복을 제거하고 유사도 점수로 정렬
        
        Args:
            all_results: 여러 검색에서 수집한 결과들
        
        Returns:
            중복 제거된 결과 (유사도 높은 순서)
        """
        # 문서 ID로 그룹화 (가장 높은 유사도만 유지)
        seen_docs = {}
        
        for result in all_results:
            doc_id = result["document_id"]
            
            if doc_id not in seen_docs:
                seen_docs[doc_id] = result
            else:
                # 유사도가 더 높으면 업데이트
                current_score = seen_docs[doc_id].get("similarity_score", 0)
                new_score = result.get("similarity_score", 0)
                
                if isinstance(new_score, (int, float)) and isinstance(current_score, (int, float)):
                    if new_score > current_score:
                        seen_docs[doc_id] = result
        
        # 유사도 순으로 정렬
        deduped = list(seen_docs.values())
        deduped.sort(
            key=lambda x: x.get("similarity_score", 0),
            reverse=True
        )
        
        logger.info(f"📊 Deduplicated: {len(all_results)} → {len(deduped)} results")
        return deduped
    
    async def get_relevant_context_for_workflow_generation_v2(
        self,
        query: str,
        use_query_decomposition: bool = True,
        max_tokens: int = 30000
    ) -> tuple:
        """
        개선된 워크플로우 생성용 컨텍스트 검색 (쿼리 분해 포함)
        선택적 쿼리 분해를 통해 더 포괄적인 결과 제공
        
        Args:
            query: 사용자 쿼리
            use_query_decomposition: 쿼리 분해 사용 여부
            max_tokens: 최대 토큰 수
        
        Returns:
            (context_string, metadata_dict) 튜플
            metadata_dict에는 쿼리 분해 과정 정보 포함
        """
        try:
            logger.info(f"📚 Getting context (v2) for workflow: '{query}'")
            logger.info(f"Query decomposition: {'enabled' if use_query_decomposition else 'disabled'}")
            
            all_metadata_results = []
            search_queries = [query]
            subqueries_detail = []
            
            # Step 1: 쿼리 분해 (선택적)
            if use_query_decomposition:
                subqueries = await self._decompose_query_to_subqueries(query, num_queries=4)
                search_queries.extend(subqueries)
                logger.info(f"🔍 Searching with {len(search_queries)} queries total")
            
            # Step 2: 모든 쿼리로 검색
            for idx, search_query in enumerate(search_queries):
                try:
                    is_original = (idx == 0)
                    query_label = "Original Query" if is_original else f"Subquery {idx}"
                    
                    logger.debug(f"Searching ({query_label}): '{search_query}'")
                    
                    # 🆕 추가: 각 쿼리에서 도메인 감지 (Knowledge Base Smart Search 방식)
                    detected_domain_obj = self.domain_service.find_domain_by_keywords(search_query)
                    domain_for_search = detected_domain_obj.name if detected_domain_obj else None
                    
                    if domain_for_search:
                        logger.info(f"  📂 Domain detected for ({query_label}): '{domain_for_search}'")
                    else:
                        logger.debug(f"  📂 No specific domain detected for ({query_label}), searching common")
                    
                    # 🆕 변경: domain 파라미터 추가 (Search 대상 제한)
                    metadata_results = await self.search_metadata(
                        query=search_query,
                        domain=domain_for_search,  # ← 핵심 변경! 도메인 지정
                        limit=3  # 각 쿼리당 3개 (분해되므로 총 12-15개 수집)
                    )
                    
                    all_metadata_results.extend(metadata_results)
                    
                    subqueries_detail.append({
                        "query": search_query,
                        "detected_domain": domain_for_search,  # ← 도메인 정보 기록
                        "found": len(metadata_results),
                        "documents": [
                            {
                                "title": r.get("title", "Unknown"),
                                "similarity_score": r.get("similarity_score", 0),
                                "document_id": r.get("document_id"),
                                "domain": r.get("domain", "unknown")
                            }
                            for r in metadata_results
                        ]
                    })
                    
                    logger.debug(f"  Found: {len(metadata_results)} results")
                except Exception as e:
                    logger.warning(f"Search failed for '{search_query}': {e}")
            
            # Step 3: 중복 제거
            if not all_metadata_results:
                logger.warning("⚠️ No relevant documents found")
                return "", {
                    "query_decomposed": use_query_decomposition,
                    "num_subqueries": len(search_queries) - 1,
                    "total_documents_collected": 0,
                    "unique_documents": 0,
                    "subqueries_detail": subqueries_detail
                }
            
            deduped_results = self._deduplicate_metadata_results(all_metadata_results)
            logger.info(f"✅ Total unique documents: {len(deduped_results)}")
            
            # Step 4: 전체 콘텐츠 조회
            document_ids = [r["document_id"] for r in deduped_results]
            full_contents = await self.get_full_content(document_ids)
            
            # Step 5: 컨텍스트 구성
            context = self._build_context_from_contents(
                full_contents,
                deduped_results,
                max_tokens
            )
            
            logger.info(f"✅ Context built: {len(context)} chars from {len(full_contents)} documents")
            
            # 메타데이터 반환
            metadata = {
                "query_decomposed": use_query_decomposition,
                "num_subqueries": len(search_queries) - 1,
                "total_documents_collected": len(all_metadata_results),
                "unique_documents": len(deduped_results),
                "context_length": len(context),
                "subqueries_detail": subqueries_detail,
                "original_query": query,
                "domain_detection_enabled": True  # ✨ 도메인 감지 활성화 표시
            }
            
            return context, metadata
        
        except Exception as e:
            logger.error(f"Failed to get relevant context (v2): {e}")
            return "", {
                "query_decomposed": use_query_decomposition,
                "num_subqueries": 0,
                "total_documents_collected": 0,
                "unique_documents": 0,
                "error": str(e),
                "subqueries_detail": []
            }
    
    async def get_relevant_context_for_workflow_with_domain_detection(
        self,
        query: str,
        max_tokens: int = 30000
    ) -> tuple:
        """
        🆕 워크플로우 생성용 컨텍스트 검색 (도메인 감지 포함)
        Knowledge Base의 Smart Search와 동일하게 동작
        
        원본 쿼리에서 도메인 감지 후:
        1. 감지된 도메인 + common 도메인에서만 검색
        2. 결과 수집 및 컨텍스트 구성
        
        Args:
            query: 사용자 쿼리
            max_tokens: 최대 토큰 수
        
        Returns:
            (context_string, metadata_dict) 튜플
            metadata_dict에는 도메인 감지 정보 포함
        """
        try:
            logger.info(f"📚 Getting context for workflow (with smart domain detection): '{query}'")
            
            # Step 1: 원본 쿼리에서 도메인 감지
            detected_domain_obj = self.domain_service.find_domain_by_keywords(query)
            domain_for_search = detected_domain_obj.name if detected_domain_obj else None
            
            if domain_for_search:
                logger.info(f"📂 Domain detected: '{domain_for_search}'")
            else:
                logger.info(f"📂 No specific domain detected, searching all domains")
            
            # Step 2: 감지된 도메인에서 검색 (Smart Search 방식)
            metadata_results = await self.search_metadata(
                query=query,
                domain=domain_for_search,  # ← 핵심! 도메인 지정
                limit=5
            )
            
            logger.info(f"✅ Found {len(metadata_results)} results")
            
            # Step 3: 결과가 없으면 빈 결과 반환
            if not metadata_results:
                logger.warning("⚠️ No relevant documents found")
                return "", {
                    "query": query,
                    "detected_domain": domain_for_search,
                    "total_documents_collected": 0,
                    "unique_documents": 0,
                    "context_length": 0,
                    "domain_detection_enabled": True,
                    "method": "with_domain_detection"
                }
            
            # Step 4: 전체 콘텐츠 조회
            document_ids = [r["document_id"] for r in metadata_results]
            full_contents = await self.get_full_content(document_ids)
            
            # Step 5: 컨텍스트 구성
            context = self._build_context_from_contents(
                full_contents,
                metadata_results,
                max_tokens
            )
            
            logger.info(f"✅ Context built: {len(context)} chars from {len(full_contents)} documents")
            
            # 메타데이터 반환
            metadata = {
                "query": query,
                "detected_domain": domain_for_search,
                "total_documents_collected": len(metadata_results),
                "unique_documents": len(metadata_results),
                "context_length": len(context),
                "domain_detection_enabled": True,
                "method": "with_domain_detection"
            }
            
            return context, metadata
        
        except Exception as e:
            logger.error(f"Failed to get relevant context (with domain detection): {e}", exc_info=True)
            return "", {
                "error": str(e),
                "query": query,
                "domain_detection_enabled": False,
                "method": "with_domain_detection"
            }
    
    # Backward compatibility methods for old RAG interface
    async def search_documents(
        self,
        query: str,
        category = None,
        domain: str = None,  # ✨ NEW: Domain filter
        limit: int = 5,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Backward compatible search method with domain filtering"""
        logger.debug(f"Backward compat: search_documents called (domain: {domain})")
        # ✨ FIX: Pass all parameters correctly
        results = await self.search_metadata(query=query, domain=domain, category=category, limit=limit)
        
        # Convert to old format
        converted = []
        for r in results:
            doc = await self.get_full_content([r["document_id"]])
            if doc:
                converted.append({
                    "content": doc[0].get("content", ""),
                    "metadata": {
                        "document_id": r["document_id"],
                        "title": r["title"],
                        "category": r.get("category", "Unknown"),
                        "doc_type": r.get("doc_type", "unknown"),
                        "domain": r.get("domain", "common"),  # ✨ NEW: Include domain
                    },
                    "similarity_score": r["similarity_score"],
                    "distance": r.get("distance", 0)
                })
        return converted
    
    async def hybrid_search(
        self,
        query: str,
        category = None,
        domain: str = None,  # ✨ NEW: Domain filter
        limit: int = 5,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Backward compatible hybrid search with domain filtering"""
        logger.debug(f"Backward compat: hybrid_search called (domain: {domain})")
        return await self.search_documents(query, category, domain, limit)
    
    def build_context(self, search_results, max_tokens: int = 30000) -> str:
        """Backward compatible context builder"""
        if not search_results:
            return ""
        
        context_parts = []
        current_tokens = 0
        
        for content in search_results:
            content_text = content.get("content", "")
            metadata = content.get("metadata", {})
            
            content_tokens = len(self.tokenizer.encode(content_text))
            
            if current_tokens + content_tokens > max_tokens:
                logger.info(f"Reached max_tokens limit. Included {len(context_parts)} documents.")
                break
            
            similarity = content.get("similarity_score", "N/A")
            if isinstance(similarity, (int, float)):
                score_str = f"{similarity:.3f}"
            else:
                score_str = "N/A"
            
            context_part = f"""
**{metadata.get('title', 'Unknown')}**
Source: {metadata.get('category', 'Unknown')}
Score: {score_str}

{content_text}

---
"""
            context_parts.append(context_part)
            current_tokens += content_tokens
        
        return "\n".join(context_parts)
    
    async def log_query(
        self,
        query_text: str,
        results_count: int,
        category: Optional[KnowledgeBaseCategory] = None,
        used_in_generation: bool = False,
        generation_success: Optional[bool] = None,
        execution_time_ms: Optional[int] = None
    ):
        """Log RAG query for analytics"""
        try:
            with get_session() as session:
                rag_query = RAGQuery(
                    query_text=query_text,
                    query_category=category,
                    results_count=results_count,
                    execution_time_ms=execution_time_ms,
                    used_in_generation=used_in_generation,
                    generation_success=generation_success
                )
                session.add(rag_query)
                session.commit()
        except Exception as e:
            logger.error(f"Failed to log query: {e}")
    
    async def smart_search(
        self,
        query: str,
        limit: int = 5,
        min_score: float = 0.3
    ) -> Dict[str, Any]:
        """
        🎯 Smart search: Automatically detect domain and search
        
        Workflow:
        1. Detect domain from query using DomainService
        2. Search in detected domain collection (if found)
        3. Always search in common domain
        4. Merge results and remove duplicates
        5. Sort by similarity score
        
        Args:
            query: User query (natural language)
            limit: Maximum results per domain
            min_score: Minimum similarity score (0-1)
        
        Returns:
            {
                "detected_domain": "네이버" or None,
                "domain_results": [...],  # Results from specific domain
                "common_results": [...],  # Results from common domain
                "all_results": [...],     # Merged results (sorted by score)
                "total_count": int
            }
        """
        logger.info(f"🔍 Smart search: '{query}'")
        
        domain_results = []
        common_results = []
        detected_domain = None
        
        # Step 1: Detect domain from query
        detected_domain_obj = self.domain_service.find_domain_by_keywords(query)
        
        if detected_domain_obj:
            detected_domain = detected_domain_obj.name
            logger.info(f"📂 Detected domain: '{detected_domain}'")
            
            # Step 2: Search in specific domain
            try:
                collection = self._get_collection_by_name(detected_domain_obj.collection_name)
                
                results = collection.query(
                    query_texts=[query],
                    n_results=limit,
                    include=["documents", "metadatas", "distances"]
                )
                
                domain_results = self._parse_search_results(results, min_score=min_score)
                logger.info(f"  ✅ Found {len(domain_results)} results in '{detected_domain}'")
                
            except Exception as e:
                logger.error(f"  ❌ Domain search failed: {e}")
        else:
            logger.info(f"📂 No specific domain detected, searching common only")
        
        # Step 3: Always search in common domain
        try:
            common_domain = self.domain_service.get_common_domain()
            
            if common_domain:
                collection = self._get_collection_by_name(common_domain.collection_name)
                
                results = collection.query(
                    query_texts=[query],
                    n_results=limit,
                    include=["documents", "metadatas", "distances"]
                )
                
                common_results = self._parse_search_results(results, min_score=min_score)
                logger.info(f"  ✅ Found {len(common_results)} results in 'common'")
            
        except Exception as e:
            logger.error(f"  ❌ Common search failed: {e}")
        
        # Step 4: Merge results and remove duplicates
        all_results = []
        seen_ids = set()
        
        # Add domain-specific results first (higher priority)
        for result in domain_results:
            doc_id = result.get("document_id")
            if doc_id and doc_id not in seen_ids:
                result["source_domain"] = detected_domain
                all_results.append(result)
                seen_ids.add(doc_id)
        
        # Add common results
        for result in common_results:
            doc_id = result.get("document_id")
            if doc_id and doc_id not in seen_ids:
                result["source_domain"] = "common"
                all_results.append(result)
                seen_ids.add(doc_id)
        
        # Step 5: Sort by similarity score (descending)
        all_results.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)
        
        # Limit total results
        all_results = all_results[:limit]
        
        logger.info(f"✅ Smart search complete: {len(all_results)} total results")
        
        return {
            "detected_domain": detected_domain,
            "domain_results": domain_results,
            "common_results": common_results,
            "all_results": all_results,
            "total_count": len(all_results)
        }
    
    def _get_collection_by_name(self, collection_name: str):
        """
        Get ChromaDB collection by name
        
        Args:
            collection_name: Collection name (e.g., "collection_네이버")
        
        Returns:
            ChromaDB Collection object
        """
        cache_key = f"name_{collection_name}"
        
        if cache_key not in self._collections_cache:
            try:
                # Try to get existing collection
                collection = self.chroma_client.get_collection(
                    name=collection_name,
                    embedding_function=self.embedding_function
                )
                self._collections_cache[cache_key] = collection
                logger.debug(f"📂 Loaded collection: {collection_name}")
                
            except Exception as e:
                # Collection doesn't exist, create it
                logger.info(f"✨ Creating new collection: {collection_name}")
                collection = self.chroma_client.create_collection(
                    name=collection_name,
                    embedding_function=self.embedding_function,
                    metadata={"hnsw:space": "cosine"}
                )
                self._collections_cache[cache_key] = collection
        
        return self._collections_cache[cache_key]
    
    def _parse_search_results(
        self,
        results: Dict[str, Any],
        min_score: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Parse ChromaDB search results
        
        Args:
            results: ChromaDB query results
            min_score: Minimum similarity score filter
        
        Returns:
            List of parsed result dictionaries
        """
        parsed_results = []
        
        if not results or not results.get("ids"):
            return parsed_results
        
        ids = results["ids"][0] if results["ids"] else []
        metadatas = results["metadatas"][0] if results.get("metadatas") else []
        distances = results["distances"][0] if results.get("distances") else []
        documents = results["documents"][0] if results.get("documents") else []
        
        for i, doc_id in enumerate(ids):
            metadata = metadatas[i] if i < len(metadatas) else {}
            distance = distances[i] if i < len(distances) else 1.0
            document = documents[i] if i < len(documents) else ""
            
            # Convert distance to similarity score (cosine: 0=identical, 2=opposite)
            similarity_score = 1.0 - (distance / 2.0)
            
            # Filter by minimum score
            if similarity_score < min_score:
                continue
            
            parsed_results.append({
                "document_id": metadata.get("document_id", doc_id),
                "title": metadata.get("title", "Untitled"),
                "domain": metadata.get("domain", "unknown"),
                "doc_type": metadata.get("doc_type", "unknown"),
                "content_type": metadata.get("content_type", "unknown"),
                "similarity_score": similarity_score,
                "distance": distance,
                "searchable_text": document[:200] + "..." if len(document) > 200 else document
            })
        
        return parsed_results


# Global RAG service instance
_rag_service_instance = None


def get_rag_service() -> RAGService:
    """Get or create RAG service singleton"""
    global _rag_service_instance
    if _rag_service_instance is None:
        _rag_service_instance = RAGService()
    return _rag_service_instance
