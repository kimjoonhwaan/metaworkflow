"""Knowledge Base Management Page"""

import streamlit as st
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List

from src.database.session import get_session
from src.database.models import (
    KnowledgeBase, Document, KnowledgeBaseCategory, DocumentContentType
)
from src.services.rag_service import get_rag_service
from src.services.file_service import get_file_service
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Page configuration
st.set_page_config(
    page_title="Knowledge Base Management",
    page_icon="🧠",
    layout="wide"
)

st.title("🧠 Knowledge Base Management")
st.markdown("Manage your RAG knowledge base for enhanced AI workflow generation")

# Initialize services
@st.cache_resource
def get_rag():
    return get_rag_service()

@st.cache_resource
def get_file():
    return get_file_service()

rag_service = get_rag()
file_service = get_file()


# Helper function to display search results
def _display_search_result(result: Dict[str, Any], index: int, key_suffix: str):
    """Display a single search result"""
    title = result.get('title', 'Untitled')
    score = result.get('similarity_score', 0.0)
    
    with st.expander(f"📄 Result {index+1}: {title} (Score: {score:.3f})"):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Domain information
            domain_badge = result.get('domain', 'unknown')
            source_domain = result.get('source_domain', domain_badge)
            
            # Dynamic emoji based on domain type
            if domain_badge == 'common':
                domain_emoji = '✨'
            elif domain_badge == 'all':
                domain_emoji = '🌐'
            else:
                domain_emoji = '📂'
            
            st.write(f"**Domain:** {domain_emoji} {domain_badge} (from: {source_domain})")
            
            st.write(f"**Type:** {result.get('doc_type', 'unknown')}")
            st.write(f"**Content Type:** {result.get('content_type', 'unknown')}")
            
            # Get full content from database
            doc_id = result.get('document_id')
            if doc_id:
                try:
                    with get_session() as session:
                        doc = session.query(Document).filter(Document.id == doc_id).first()
                        if doc:
                            full_content = doc.content
                            st.text_area(
                                "Full Content",
                                full_content,
                                height=300,
                                disabled=True,
                                key=f"content_{key_suffix}",
                                label_visibility="collapsed"
                            )
                        else:
                            st.warning("Document not found in database")
                except Exception as e:
                    st.error(f"Failed to load content: {e}")
            else:
                # Fallback to searchable_text
                st.text_area(
                    "Content Preview",
                    result.get('searchable_text', 'No content available'),
                    height=150,
                    disabled=True,
                    key=f"preview_{key_suffix}",
                    label_visibility="collapsed"
                )
        
        with col2:
            st.metric("Similarity", f"{score:.3f}")
            st.metric("Distance", f"{result.get('distance', 0):.4f}")
            st.write(f"**Doc ID:** {doc_id[:8]}..." if doc_id else "N/A")


# Sidebar for navigation
st.sidebar.title("📚 Knowledge Base")
tab = st.sidebar.radio(
    "Select Action",
    ["📖 View Knowledge Bases", "➕ Add Document", "📁 Upload Files", "🔍 Search Documents", "📊 Analytics"]
)

# Main content area
if tab == "📖 View Knowledge Bases":
    st.header("📖 Knowledge Bases")
    
    # ✅ FORCE REFRESH: Always get fresh domains from database
    from src.services.domain_service import get_domain_service
    domain_service = get_domain_service()
    all_domains = domain_service.get_all_domains()
    
    # Create unique key to force Streamlit re-render
    import hashlib
    domain_hash = hashlib.md5(str([d.name for d in all_domains]).encode()).hexdigest()[:8]
    
    # Debug: Always show current state
    if True:  # Force display
        debug_col1, debug_col2 = st.columns([3, 1])
        with debug_col1:
            st.info(f"✅ **Database domains:** {', '.join([d.name for d in all_domains])}")
        with debug_col2:
            if st.button("🔄 Refresh"):
                st.rerun()
    
    # Domain filter
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        # Debug: Show all domains in the database
        logger.debug(f"Domain Statistics - Available domains: {[d.name for d in all_domains]}")
        
        domain_options = ["All Domains"] + [d.name for d in all_domains]
        selected_domain_filter = st.selectbox(
            "Filter by Domain",
            options=domain_options,
            index=0,
            key=f"view_domain_filter_{domain_hash}"  # Unique key with hash
        )
        
        # Show debug info if needed
        if st.checkbox("Show debug info", value=False, key=f"show_domain_debug_{domain_hash}"):
            st.write(f"**Domains in database:** {len(all_domains)}")
            for d in all_domains:
                status = "✅ Active" if d.is_active else "❌ Inactive"
                common = " (COMMON)" if d.is_common else ""
                st.write(f"- {d.name} ({d.display_name}) - {status}{common}")
    
    with col2:
        # Category filter
        category_options = ["All Categories"] + [cat.value for cat in KnowledgeBaseCategory]
        selected_category_filter = st.selectbox(
            "Filter by Category",
            options=category_options,
            key="view_category_filter"
        )
    
    with col3:
        st.write("")  # Spacer
        st.write("")  # Spacer
        show_inactive = st.checkbox("Show Inactive", value=False)
    
    # Get knowledge bases
    try:
        with get_session() as session:
            # Use eager loading to avoid lazy loading issues
            from sqlalchemy.orm import joinedload
            knowledge_bases = session.query(KnowledgeBase).options(joinedload(KnowledgeBase.documents)).all()
            
            # Get domain statistics
            domain_stats = {}
            for domain in all_domains:
                doc_count = session.query(Document).filter(Document.domain == domain.name).count()
                domain_stats[domain.name] = doc_count
            
            if not knowledge_bases:
                st.info("No knowledge bases found. Create one by adding a document.")
            else:
                # Display domain statistics
                st.markdown("### 📊 Domain Statistics")
                stat_cols = st.columns(len(all_domains))
                for idx, domain in enumerate(all_domains):
                    with stat_cols[idx]:
                        # Use common emoji for common domain, generic for others
                        emoji = '✨' if domain.is_common else '📂'
                        st.metric(
                            f"{emoji} {domain.display_name or domain.name}",
                            domain_stats.get(domain.name, 0)
                        )
                
                st.markdown("---")
                
                # Display knowledge bases
                for kb in knowledge_bases:
                    # Filter by category
                    if selected_category_filter != "All Categories" and kb.category.value != selected_category_filter:
                        continue
                    
                    # Filter by active status
                    if not show_inactive and not kb.is_active:
                        continue
                    
                    # Filter documents by domain
                    filtered_docs = kb.documents
                    if selected_domain_filter != "All Domains":
                        filtered_docs = [doc for doc in kb.documents if doc.domain == selected_domain_filter]
                    
                    # Skip KB if no documents match filter
                    if selected_domain_filter != "All Domains" and not filtered_docs:
                        continue
                    
                    with st.expander(f"📁 {kb.name} ({kb.category.value}) - {len(filtered_docs)} documents"):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.write(f"**Description:** {kb.description or 'No description'}")
                            st.write(f"**Category:** {kb.category.value}")
                            st.write(f"**Total Documents:** {len(kb.documents)}")
                            if selected_domain_filter != "All Domains":
                                st.write(f"**Filtered Documents:** {len(filtered_docs)}")
                            st.write(f"**Created:** {kb.created_at.strftime('%Y-%m-%d %H:%M')}")
                            st.write(f"**Status:** {'✅ Active' if kb.is_active else '❌ Inactive'}")
                        
                        with col2:
                            if st.button(f"🗑️ Delete", key=f"delete_kb_{kb.id}"):
                                # Delete knowledge base
                                try:
                                    with get_session() as session:
                                        kb_to_delete = session.query(KnowledgeBase).filter(
                                            KnowledgeBase.id == kb.id
                                        ).first()
                                        session.delete(kb_to_delete)
                                        session.commit()
                                    st.success("Knowledge base deleted successfully!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Failed to delete knowledge base: {e}")
                            
                            if st.button(f"🔄 Toggle Status", key=f"toggle_kb_{kb.id}"):
                                try:
                                    with get_session() as session:
                                        kb_to_update = session.query(KnowledgeBase).filter(
                                            KnowledgeBase.id == kb.id
                                        ).first()
                                        kb_to_update.is_active = not kb_to_update.is_active
                                        session.commit()
                                    st.success("Status updated successfully!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Failed to update status: {e}")
                        
                        # Show documents in this knowledge base
                        if filtered_docs:
                            st.subheader("📄 Documents")
                            
                            # Group documents by domain
                            docs_by_domain = {}
                            for doc in filtered_docs:
                                domain = doc.domain or "unknown"
                                if domain not in docs_by_domain:
                                    docs_by_domain[domain] = []
                                docs_by_domain[domain].append(doc)
                            
                            # Display documents grouped by domain
                            for domain_name, docs in sorted(docs_by_domain.items()):
                                # Dynamic emoji based on domain type
                                emoji = '✨' if domain_name == 'common' else '📂'
                                
                                st.markdown(f"**{emoji} {domain_name.upper()}** ({len(docs)} documents)")
                                
                                for doc in docs:
                                    with st.container():
                                        col1, col2 = st.columns([4, 1])
                                        
                                        with col1:
                                            st.write(f"**{doc.title}** ({doc.content_type.value})")
                                            st.write(f"Processed: {'✅' if doc.is_processed else '❌'} | Domain: {emoji} {doc.domain}")
                                            if doc.processing_error:
                                                st.error(f"Error: {doc.processing_error}")
                                        
                                        with col2:
                                            if st.button("🗑️", key=f"delete_doc_{doc.id}"):
                                                try:
                                                    with get_session() as session:
                                                        doc_to_delete = session.query(Document).filter(
                                                            Document.id == doc.id
                                                        ).first()
                                                        session.delete(doc_to_delete)
                                                        session.commit()
                                                    st.success("Document deleted successfully!")
                                                    st.rerun()
                                                except Exception as e:
                                                    st.error(f"Failed to delete document: {e}")
                                
                                st.markdown("---")
    
    except Exception as e:
        st.error(f"Failed to load knowledge bases: {e}")
        logger.error(f"Error loading knowledge bases: {e}")

elif tab == "➕ Add Document":
    st.header("➕ Add Document to Knowledge Base")
    
    # Get services
    from src.services.domain_service import get_domain_service
    domain_service = get_domain_service()
    all_domains = domain_service.get_all_domains()
    
    # ✨ NEW: Quick domain creation section (OUTSIDE form)
    st.markdown("### 📌 Quick Add Domain")
    col_quick1, col_quick2, col_quick3 = st.columns([2, 2, 1])
    
    with col_quick1:
        quick_domain_name = st.text_input(
            "Domain Name",
            placeholder="e.g., 테스트, 샘플",
            key="quick_domain_name"
        )
    
    with col_quick2:
        quick_domain_keywords = st.text_input(
            "Keywords (comma-separated)",
            placeholder="e.g., 테스트, test",
            key="quick_domain_keywords"
        )
    
    with col_quick3:
        st.write("")  # Spacer
        if st.button("✅ Create Domain", key="create_domain_btn"):
            if quick_domain_name:
                try:
                    keywords = [k.strip() for k in quick_domain_keywords.split(",") if k.strip()] if quick_domain_keywords else [quick_domain_name]
                    domain_obj = domain_service.create_or_get_domain(
                        name=quick_domain_name,
                        keywords=keywords,
                        display_name=quick_domain_name
                    )
                    st.success(f"✅ Domain created: **{domain_obj.name}** (collection: {domain_obj.collection_name})")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Failed to create domain: {e}")
            else:
                st.error("❌ Domain name is required")
    
    st.divider()
    
    # Now refresh domains list
    all_domains = domain_service.get_all_domains()
    
    # Document form (simplified - no domain creation inside form)
    with st.form("add_document_form"):
        st.markdown("### 📄 Document Details")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Document title (입력하면 KB 이름도 자동 설정)
            doc_title = st.text_input(
                "Document Title",
                placeholder="e.g., Naver News API Guide",
                help="Title of the document (will also be used for KB name if creating new)"
            )
            
            # Knowledge base selection - default to "Create New Knowledge Base"
            with get_session() as session:
                existing_kbs = session.query(KnowledgeBase).all()
                kb_options = {kb.name: kb.id for kb in existing_kbs}
                kb_options["Create New Knowledge Base"] = "new"
                
                # Find index of "Create New Knowledge Base"
                kb_list = list(kb_options.keys())
                default_index = kb_list.index("Create New Knowledge Base") if "Create New Knowledge Base" in kb_list else 0
                
                selected_kb = st.selectbox(
                    "Select Knowledge Base",
                    options=kb_list,
                    index=default_index,
                    key="kb_selection"
                )
            
            # Initialize KB input variables
            new_kb_name = None
            new_kb_description = None
            new_kb_category = None
            
            if selected_kb == "Create New Knowledge Base":
                st.info("📝 **New Knowledge Base will be created automatically**")
                # Auto-fill KB name with document title
                new_kb_name = doc_title if doc_title else "Untitled Knowledge Base"
                
                new_kb_description = st.text_area(
                    "Description (Optional)",
                    placeholder="e.g., Documentation for Naver News API",
                    height=60,
                    key="new_kb_description"
                )
                new_kb_category = st.selectbox(
                    "Category",
                    options=[cat.value for cat in KnowledgeBaseCategory],
                    key="new_kb_category",
                    index=0
                )
            else:
                st.info(f"✅ Using Knowledge Base: **{selected_kb}**")
        
        with col2:
            # Document details
            doc_content_type = st.selectbox(
                "Content Type",
                options=[ct.value for ct in DocumentContentType],
                key="doc_content_type"
            )
            
            # Tags
            tags_input = st.text_input(
                "Tags (comma-separated)",
                placeholder="e.g., api, naver, news",
                help="Tags to help organize and search documents"
            )
            tags = [tag.strip() for tag in tags_input.split(",") if tag.strip()]
        
        # Document content
        doc_content = st.text_area(
            "Document Content",
            height=300,
            placeholder="Enter your document content here...",
            key="doc_content_input",
            help="Full content of the document (code, documentation, etc.)"
        )
        
        # ✨ NEW: Domain selection (dynamic from database)
        st.markdown("**Document Domain** (for collection separation)")
        
        # Build domain options with display names
        domain_options = ["📝 Enter Custom Domain"]  # Always add custom option first
        domain_help_text = ["- **Custom**: Enter your own domain name"]
        
        for domain in all_domains:
            domain_options.append(domain.name)
            if domain.is_common:
                domain_help_text.append(f"- **{domain.name}**: {domain.description or 'Searchable from all domains (shared documents)'}")
            else:
                domain_help_text.append(f"- **{domain.name}**: {domain.description or f'{domain.display_name} documents'}")
        
        selected_domain = st.selectbox(
            "Select domain for this document",
            options=domain_options,
            index=0,  # Default: first option (custom input)
            help="\n".join(domain_help_text),
            key="add_doc_domain_select"
        )
        
        # Handle custom domain input
        custom_domain_name = None
        custom_domain_keywords = None
        
        if selected_domain == "📝 Enter Custom Domain":
            st.info("💡 **You can create a new domain directly here**")
            col_custom1, col_custom2 = st.columns(2)
            
            with col_custom1:
                custom_domain_name = st.text_input(
                    "Domain Name",
                    placeholder="e.g., 테스트, 샘플, 커스텀도메인",
                    key="custom_domain_name"
                )
            
            with col_custom2:
                custom_domain_keywords = st.text_input(
                    "Keywords (comma-separated, optional)",
                    placeholder="e.g., 테스트, test, 커스텀",
                    key="custom_domain_keywords"
                )
        
        # ✨ NEW: Auto-detect option
        auto_detect_domain = st.checkbox(
            "🔍 Auto-detect domain from document title/content",
            value=False,
            help="If enabled, domain will be automatically detected from the document"
        )
        
        # Metadata
        with st.expander("📋 Additional Metadata"):
            metadata_input = st.text_area(
                "Metadata (JSON format)",
                value="{}",
                help="Enter additional metadata as JSON",
                key="metadata_json_input"
            )
        
        submitted = st.form_submit_button("📤 Add Document")
        
        if submitted and doc_content:
            try:
                with st.spinner("📤 Adding document..."):
                    import asyncio
                    
                    # ✨ NEW: Parse metadata JSON
                    metadata = {}
                    try:
                        metadata = json.loads(metadata_input)
                    except json.JSONDecodeError:
                        st.error("❌ Invalid JSON format for metadata. Please enter a valid JSON object.")
                        metadata = {}
                    
                    # ✨ NEW: Create domain if needed (before processing document)
                    domain_to_use = selected_domain
                    if selected_domain == "📝 Enter Custom Domain":
                        if not custom_domain_name:
                            st.error(f"❌ Domain name is required")
                        else:
                            # Parse keywords
                            keywords = [k.strip() for k in custom_domain_keywords.split(",") if k.strip()] if 'custom_domain_keywords' in locals() and custom_domain_keywords else [custom_domain_name]
                            
                            # Create domain with user input name (no normalization)
                            try:
                                domain_obj = domain_service.create_or_get_domain(
                                    name=custom_domain_name,
                                    keywords=keywords,
                                    display_name=custom_domain_name,
                                    description=f"{custom_domain_name} 관련 문서"
                                )
                                domain_to_use = domain_obj.name
                                st.success(f"✅ Created/using domain: **{domain_obj.display_name}**")
                            except Exception as e:
                                st.error(f"❌ Failed to create domain: {e}")
                                logger.error(f"Domain creation error: {e}", exc_info=True)
                    
                    # ✨ Auto-detect domain if enabled
                    elif auto_detect_domain:
                        from src.utils.domain_detector import DomainDetector
                        detected_domain = DomainDetector.detect_domain(
                            title=doc_title or "Untitled Document",
                            content=doc_content
                        )
                        domain_to_use = detected_domain
                        st.info(f"🔍 Auto-detected domain: **{domain_to_use}**")
                    
                    # Initialize kb_id
                    kb_id = None
                    
                    # Create knowledge base if needed
                    if selected_kb == "Create New Knowledge Base":
                        if not new_kb_name:
                            st.error("❌ Please provide a name for the new knowledge base.")
                        else:
                            try:
                                from src.database.models import KnowledgeBase
                                from src.database.session import get_session
                                
                                with get_session() as session:
                                    # ✅ CHECK: See if KB with same name already exists
                                    existing_kb = session.query(KnowledgeBase).filter(
                                        KnowledgeBase.name == new_kb_name
                                    ).first()
                                    
                                    if existing_kb:
                                        # ✅ Use existing KB instead of creating duplicate
                                        kb_id = existing_kb.id
                                        st.info(f"✅ Knowledge Base **'{new_kb_name}'** already exists. Using existing KB.")
                                    else:
                                        # Create new KB only if it doesn't exist
                                        kb = KnowledgeBase(
                                            name=new_kb_name,
                                            description=new_kb_description or "",
                                            category=KnowledgeBaseCategory(new_kb_category) if new_kb_category else KnowledgeBaseCategory.WORKFLOW_PATTERNS
                                        )
                                        session.add(kb)
                                        session.commit()
                                        kb_id = kb.id
                                        st.success(f"✅ Created Knowledge Base: **{new_kb_name}**")
                            except Exception as e:
                                st.error(f"❌ Failed to create knowledge base: {e}")
                                logger.error(f"Knowledge base creation error: {e}")
                    else:
                        if selected_kb in kb_options:
                            kb_id = kb_options[selected_kb]
                            st.info(f"✅ Using Knowledge Base: **{selected_kb}**")
                        else:
                            st.error(f"❌ Invalid knowledge base selection")
                    
                    # Add document if KB ID is set
                    if kb_id:
                        try:
                            from src.database.models import Document, DocumentMetadata, DocumentContentType
                            from src.database.session import get_session
                            
                            with get_session() as session:
                                # Create and save document
                                document = Document(
                                    knowledge_base_id=kb_id,
                                    title=doc_title or "Untitled Document",
                                    content=doc_content,
                                    content_type=DocumentContentType(doc_content_type),
                                    tags=tags or [],
                                    kb_metadata=metadata,
                                    domain=domain_to_use
                                )
                                session.add(document)
                                session.flush()
                                doc_id = document.id
                                
                                # Create metadata
                                doc_metadata = DocumentMetadata(
                                    document_id=doc_id,
                                    searchable_text=f"{doc_title}\n{doc_content[:500]}",
                                    keywords=tags or [],
                                    description=doc_title or "Untitled",
                                    summary=doc_content[:200] if doc_content else "",
                                    doc_type="document",
                                    domain=domain_to_use
                                )
                                session.add(doc_metadata)
                                session.commit()
                            
                            # Add to RAG
                            with get_session() as session:
                                document = session.query(Document).filter(Document.id == doc_id).first()
                                doc_metadata = session.query(DocumentMetadata).filter(
                                    DocumentMetadata.document_id == doc_id
                                ).first()
                                
                                if document and doc_metadata:
                                    asyncio.run(rag_service.add_document(document, doc_metadata, domain=domain_to_use))
                            
                            st.success(f"✅ Document **'{doc_title or 'Untitled'}'** added successfully!")
                            st.balloons()
                        
                        except Exception as e:
                            st.error(f"❌ Failed to add document: {e}")
                            logger.error(f"Document addition error: {e}", exc_info=True)
                    else:
                        st.error("❌ Unable to create or select a knowledge base")
            
            except Exception as e:
                st.error(f"❌ Error: {e}")
                logger.error(f"Error: {e}", exc_info=True)
    
    # Display uploaded files
    st.subheader("📂 Uploaded Files")
    
    try:
        import asyncio
        uploaded_files_list = asyncio.run(file_service.get_uploaded_files())
        
        if not uploaded_files_list:
            st.info("No files have been uploaded yet.")
        else:
            for file_info in uploaded_files_list:
                with st.container():
                    col1, col2, col3 = st.columns([4, 1, 1])
                    
                    with col1:
                        st.write(f"**{file_info['title']}**")
                        st.write(f"Original: {file_info['original_filename']}")
                        st.write(f"Type: {file_info['mime_type']} ({file_info['file_size']} bytes)")
                        st.write(f"Uploaded: {file_info['created_at'][:19]}")
                        if file_info['description']:
                            st.write(f"Description: {file_info['description']}")
                        st.write(f"Status: {'✅ Processed' if file_info['is_processed'] else '⏳ Processing'}")
                    
                    with col2:
                        if st.button("🔍 View", key=f"view_file_{file_info['document_id']}"):
                            # Show file content preview
                            with st.expander(f"Content Preview: {file_info['title']}"):
                                try:
                                    import asyncio
                                    file_content = asyncio.run(file_service.get_file_content(file_info['document_id']))
                                    if file_content:
                                        # Parse and show preview
                                        parse_result = file_service.file_parser.parse_file(file_content, file_info['original_filename'])
                                        if parse_result['success']:
                                            content_preview = parse_result['content'][:500]
                                            if len(parse_result['content']) > 500:
                                                content_preview += "..."
                                            st.text_area("Content Preview", content_preview, height=200, disabled=True, key=f"file_preview_{file_info['document_id']}")
                                        else:
                                            st.error(f"Failed to parse content: {parse_result['error']}")
                                    else:
                                        st.error("Could not retrieve file content")
                                except Exception as e:
                                    st.error(f"Error retrieving file content: {e}")
                    
                    with col3:
                        if st.button("🗑️ Delete", key=f"delete_file_{file_info['document_id']}"):
                            try:
                                import asyncio
                                success = asyncio.run(file_service.delete_uploaded_file(file_info['document_id']))
                                if success:
                                    st.success("File deleted successfully!")
                                    st.rerun()
                                else:
                                    st.error("Failed to delete file")
                            except Exception as e:
                                st.error(f"Error deleting file: {e}")
    
    except Exception as e:
        st.error(f"Failed to load uploaded files: {e}")
        logger.error(f"Error loading uploaded files: {e}")

elif tab == "🔍 Search Documents":
    st.header("🔍 Smart Search")
    st.markdown("💡 **Tip:** Just ask naturally! We'll automatically detect the domain from your query.")
    
    # Search mode selection
    search_mode = st.radio(
        "Search Mode",
        ["🎯 Smart Search (Auto-detect domain)", "🔧 Manual Search (Select domain)"],
        horizontal=True
    )
    
    # Get available domains from DomainService (outside form for caching)
    from src.services.domain_service import get_domain_service
    domain_service = get_domain_service()
    all_domains = domain_service.get_all_domains()
    
    # Search form
    with st.form("search_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            query = st.text_input(
                "Your Question",
                placeholder="e.g., 네이버 뉴스에서 경제분야 최신뉴스 3개를 뽑아서...",
                help="Enter your question in natural language"
            )
            
            # Initialize search_domain
            search_domain = None
            
            if search_mode == "🔧 Manual Search (Select domain)":
                # Show domain selector only in manual mode
                domain_options = ["All Domains"] + [d.name for d in all_domains]
                search_domain = st.selectbox(
                    "Document Domain",
                    options=domain_options,
                    index=0,
                    help="Select which domain to search in",
                    key="search_domain"
                )
            else:
                # Show available domains info in smart mode
                domain_names = [d.name for d in all_domains]
                st.info(f"📂 Available domains: {', '.join(domain_names)}")
        
        with col2:
            limit = st.slider("Max Results", min_value=1, max_value=20, value=5)
            min_score = st.slider("Min Score", min_value=0.0, max_value=1.0, value=0.3, step=0.1)
            include_files = st.checkbox("Include Uploaded Files", value=False)
        
        search_submitted = st.form_submit_button("🔍 Search")
        
        if search_submitted and query:
            try:
                with st.spinner("🔍 Analyzing and searching..."):
                    import asyncio
                    
                    # Choose search method based on mode
                    if search_mode == "🎯 Smart Search (Auto-detect domain)":
                        # Use smart_search (auto-detect domain)
                        search_result = asyncio.run(rag_service.smart_search(
                            query=query,
                            limit=limit,
                            min_score=min_score
                        ))
                        
                        # Extract results
                        detected_domain = search_result["detected_domain"]
                        domain_results = search_result["domain_results"]
                        common_results = search_result["common_results"]
                        all_results = search_result["all_results"]
                        
                        # Show detected domain
                        if detected_domain:
                            st.success(f"🎯 Detected Domain: **{detected_domain}**")
                            st.write(f"**Domain Results:** {len(domain_results)} found")
                            st.write(f"**Common Results:** {len(common_results)} found")
                        else:
                            st.info("📂 No specific domain detected, searching common only")
                        
                        # Debug: Show all domains for reference
                        with st.expander("Available domains (debug)"):
                            for d in all_domains:
                                st.write(f"- {d.name} (keywords: {d.keywords})")
                    
                    else:
                        # Manual search mode (legacy)
                        domain_filter = None if search_domain == "All Domains" else search_domain
                        results = asyncio.run(rag_service.hybrid_search(
                            query=query,
                            category=None,
                            domain=domain_filter,
                            limit=limit
                        ))
                        
                        # Convert to smart_search format
                        all_results = []
                        for r in results:
                            all_results.append({
                                "document_id": r['metadata'].get('document_id'),
                                "title": r['metadata'].get('title', 'Untitled'),
                                "domain": r['metadata'].get('domain', 'unknown'),
                                "doc_type": r['metadata'].get('doc_type', 'unknown'),
                                "content_type": r['metadata'].get('content_type', 'unknown'),
                                "similarity_score": r['similarity_score'],
                                "distance": r.get('distance', 0),
                                "content": r.get('content', ''),
                                "source_domain": domain_filter or "all"
                            })
                        
                        detected_domain = None
                        domain_results = []
                        common_results = []
                    
                    # If including files, also search uploaded files
                    file_results = []
                    if include_files:
                        file_results = asyncio.run(file_service.search_files(
                            query=query,
                            limit=limit
                        ))
                
                # Combine and display results
                total_results = len(all_results) + len(file_results)
                
                if total_results == 0:
                    st.info("No documents found matching your query.")
                else:
                    st.success(f"Found {total_results} documents ({len(all_results)} knowledge base, {len(file_results)} files)")
                    
                    # Display results in tabs if smart search detected a domain
                    if search_mode == "🎯 Smart Search (Auto-detect domain)" and detected_domain:
                        tab1, tab2, tab3 = st.tabs([
                            f"🎯 {detected_domain} ({len(domain_results)})",
                            f"✨ Common ({len(common_results)})",
                            f"📊 All ({len(all_results)})"
                        ])
                        
                        with tab1:
                            st.markdown(f"### Results from **{detected_domain}** domain")
                            for i, result in enumerate(domain_results):
                                _display_search_result(result, i, f"domain_{i}")
                        
                        with tab2:
                            st.markdown("### Results from **common** domain")
                            for i, result in enumerate(common_results):
                                _display_search_result(result, i, f"common_{i}")
                        
                        with tab3:
                            st.markdown("### All results (sorted by similarity)")
                            for i, result in enumerate(all_results):
                                _display_search_result(result, i, f"all_{i}")
                    
                    else:
                        # Display all results in single list
                        for i, result in enumerate(all_results):
                            _display_search_result(result, i, f"result_{i}")
                    
                    # Display file search results
                    if file_results:
                        st.subheader("📁 File Search Results")
                        for i, file_result in enumerate(file_results):
                            search_result = file_result['search_result']
                            file_info = file_result['file_info']
                            
                            with st.expander(f"📄 File {i+1}: {file_info['title']} (Score: {search_result['final_score']:.3f})"):
                                col1, col2 = st.columns([3, 1])
                                
                                with col1:
                                    st.write(f"**File:** {file_info['original_filename']}")
                                    st.write(f"**Type:** {file_info['mime_type']}")
                                    st.write(f"**Size:** {file_info['file_size']} bytes")
                                    st.write(f"**Uploaded:** {file_info['created_at'][:19]}")
                                    
                                    if file_info['description']:
                                        st.write(f"**Description:** {file_info['description']}")
                                    
                                    # Show content snippet
                                    content = search_result.get('content', '')
                                    if content:
                                        st.write("**Content:**")
                                        st.text_area("", content, height=150, disabled=True, key=f"file_search_content_{i}")
                                
                                with col2:
                                    st.metric("Final Score", f"{search_result['final_score']:.3f}")
                                    if 'similarity_score' in search_result:
                                        st.metric("Semantic Score", f"{search_result['similarity_score']:.3f}")
                                    if 'keyword_score' in search_result:
                                        st.metric("Keyword Score", f"{search_result['keyword_score']:.3f}")
            
            except Exception as e:
                st.error(f"Search failed: {e}")
                logger.error(f"Search error: {e}")

elif tab == "📊 Analytics":
    st.header("📊 Knowledge Base Analytics")
    
    # Get analytics data
    try:
        with get_session() as session:
            # Knowledge base stats
            total_kbs = session.query(KnowledgeBase).count()
            active_kbs = session.query(KnowledgeBase).filter(KnowledgeBase.is_active == True).count()
            
            # Document stats
            total_docs = session.query(Document).count()
            processed_docs = session.query(Document).filter(Document.is_processed == True).count()
            
            # File upload stats
            import asyncio
            uploaded_files = asyncio.run(file_service.get_uploaded_files())
            total_files = len(uploaded_files)
            processed_files = len([f for f in uploaded_files if f['is_processed']])
            
            # File type breakdown
            file_types = {}
            total_file_size = 0
            for file_info in uploaded_files:
                mime_type = file_info['mime_type']
                if mime_type not in file_types:
                    file_types[mime_type] = {"count": 0, "size": 0}
                file_types[mime_type]["count"] += 1
                file_types[mime_type]["size"] += file_info['file_size']
                total_file_size += file_info['file_size']
            
            # Category breakdown
            from sqlalchemy.orm import joinedload
            kb_categories = {}
            for kb in session.query(KnowledgeBase).options(joinedload(KnowledgeBase.documents)).all():
                category = kb.category.value
                if category not in kb_categories:
                    kb_categories[category] = {"count": 0, "docs": 0}
                kb_categories[category]["count"] += 1
                kb_categories[category]["docs"] += len(kb.documents)
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Knowledge Bases", total_kbs)
        
        with col2:
            st.metric("Active Knowledge Bases", active_kbs)
        
        with col3:
            st.metric("Total Documents", total_docs)
        
        with col4:
            st.metric("Processed Documents", processed_docs)
        
        # RAG Usage Statistics
        st.subheader("🧠 RAG Usage Statistics")
        
        # Get RAG usage stats from database (if available)
        try:
            with get_session() as session:
                from ..database.models import RAGQuery
                total_rag_queries = session.query(RAGQuery).count()
                recent_queries = session.query(RAGQuery).order_by(RAGQuery.created_at.desc()).limit(10).all()
        except Exception as e:
            total_rag_queries = 0
            recent_queries = []
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total RAG Queries", total_rag_queries)
        
        with col2:
            st.metric("Active Knowledge Bases", active_kbs)
        
        with col3:
            st.metric("Processed Documents", processed_docs)
        
        with col4:
            if total_docs > 0:
                st.metric("Processing Rate", f"{(processed_docs / total_docs * 100):.1f}%")
            else:
                st.metric("Processing Rate", "N/A")
        
        # File upload statistics
        st.subheader("📁 File Upload Statistics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Files", total_files)
        
        with col2:
            st.metric("Processed Files", processed_files)
        
        with col3:
            st.metric("Total File Size", f"{total_file_size / (1024*1024):.1f} MB")
        
        with col4:
            if total_files > 0:
                st.metric("Processing Rate", f"{(processed_files / total_files * 100):.1f}%")
            else:
                st.metric("Processing Rate", "N/A")
        
        # File type breakdown
        if file_types:
            st.subheader("📊 File Type Breakdown")
            
            for mime_type, stats in file_types.items():
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        st.write(f"**{mime_type}**")
                    
                    with col2:
                        st.write(f"Count: {stats['count']}")
                    
                    with col3:
                        st.write(f"Size: {stats['size'] / (1024*1024):.1f} MB")
        
        # Category breakdown
        st.subheader("📈 Category Breakdown")
        
        if kb_categories:
            for category, stats in kb_categories.items():
                with st.container():
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.write(f"**{category}**")
                    
                    with col2:
                        st.write(f"Knowledge Bases: {stats['count']}")
                    
                    with col3:
                        st.write(f"Documents: {stats['docs']}")
        
        # Recent activity
        st.subheader("🕒 Recent Activity")
        
        with get_session() as session:
            recent_docs = session.query(Document).order_by(
                Document.created_at.desc()
            ).limit(10).all()
        
        if recent_docs:
            for doc in recent_docs:
                st.write(f"📄 **{doc.title}** - {doc.created_at.strftime('%Y-%m-%d %H:%M')} ({doc.content_type.value})")
        else:
            st.info("No recent activity.")
    
    except Exception as e:
        st.error(f"Failed to load analytics: {e}")
        logger.error(f"Analytics error: {e}")

# Footer
st.markdown("---")
st.markdown("💡 **Tip:** Use the knowledge base to store workflow patterns, error solutions, and best practices for better AI-generated workflows!")
