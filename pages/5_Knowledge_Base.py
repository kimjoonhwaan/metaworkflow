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

# Sidebar for navigation
st.sidebar.title("📚 Knowledge Base")
tab = st.sidebar.radio(
    "Select Action",
    ["📖 View Knowledge Bases", "➕ Add Document", "📁 Upload Files", "🔍 Search Documents", "📊 Analytics"]
)

# Main content area
if tab == "📖 View Knowledge Bases":
    st.header("📖 Knowledge Bases")
    
    # Get knowledge bases
    try:
        with get_session() as session:
            # Use eager loading to avoid lazy loading issues
            from sqlalchemy.orm import joinedload
            knowledge_bases = session.query(KnowledgeBase).options(joinedload(KnowledgeBase.documents)).all()
            
            if not knowledge_bases:
                st.info("No knowledge bases found. Create one by adding a document.")
            else:
                for kb in knowledge_bases:
                    with st.expander(f"📁 {kb.name} ({kb.category.value})"):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.write(f"**Description:** {kb.description or 'No description'}")
                            st.write(f"**Category:** {kb.category.value}")
                            st.write(f"**Documents:** {len(kb.documents)}")
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
                    if kb.documents:
                        st.subheader("📄 Documents")
                        for doc in kb.documents:
                            with st.container():
                                col1, col2 = st.columns([4, 1])
                                
                                with col1:
                                    st.write(f"**{doc.title}** ({doc.content_type.value})")
                                    st.write(f"Processed: {'✅' if doc.is_processed else '❌'}")
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
    
    except Exception as e:
        st.error(f"Failed to load knowledge bases: {e}")
        logger.error(f"Error loading knowledge bases: {e}")

elif tab == "➕ Add Document":
    st.header("➕ Add Document to Knowledge Base")
    
    # Create new knowledge base or select existing
    with st.form("add_document_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            # Knowledge base selection
            with get_session() as session:
                existing_kbs = session.query(KnowledgeBase).all()
                kb_options = {kb.name: kb.id for kb in existing_kbs}
                kb_options["Create New Knowledge Base"] = "new"
                
                selected_kb = st.selectbox(
                    "Select Knowledge Base",
                    options=list(kb_options.keys()),
                    key="kb_selection"
                )
            
            if selected_kb == "Create New Knowledge Base":
                new_kb_name = st.text_input("New Knowledge Base Name")
                new_kb_description = st.text_area("Description", key="new_kb_description")
                new_kb_category = st.selectbox(
                    "Category",
                    options=[cat.value for cat in KnowledgeBaseCategory],
                    key="new_kb_category"
                )
        
        with col2:
            # Document details
            doc_title = st.text_input("Document Title")
            doc_content_type = st.selectbox(
                "Content Type",
                options=[ct.value for ct in DocumentContentType],
                key="doc_content_type"
            )
            
            # Tags
            tags_input = st.text_input("Tags (comma-separated)")
            tags = [tag.strip() for tag in tags_input.split(",") if tag.strip()]
        
        # Document content
        doc_content = st.text_area(
            "Document Content",
            height=300,
            placeholder="Enter your document content here...",
            key="doc_content_input"
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
        
        if submitted:
            if not doc_title or not doc_content:
                st.error("Please provide both title and content.")
            else:
                try:
                    # Parse metadata
                    try:
                        metadata = json.loads(metadata_input) if metadata_input else {}
                    except json.JSONDecodeError:
                        st.error("Invalid JSON in metadata field.")
                        metadata = {}
                    
                    # Create knowledge base if needed
                    if selected_kb == "Create New Knowledge Base":
                        if not new_kb_name:
                            st.error("Please provide a name for the new knowledge base.")
                        else:
                            # Create knowledge base using asyncio
                            import asyncio
                            kb_id = asyncio.run(rag_service.create_knowledge_base(
                                name=new_kb_name,
                                description=new_kb_description,
                                category=KnowledgeBaseCategory(new_kb_category)
                            ))
                    else:
                        kb_id = kb_options[selected_kb]
                    
                    # Add document
                    with st.spinner("Processing document..."):
                        import asyncio
                        doc_id = asyncio.run(rag_service.add_document(
                            knowledge_base_id=kb_id,
                            title=doc_title,
                            content=doc_content,
                            content_type=DocumentContentType(doc_content_type),
                            metadata=metadata,
                            tags=tags
                        ))
                    
                    st.success(f"Document added successfully! ID: {doc_id}")
                    
                except Exception as e:
                    st.error(f"Failed to add document: {e}")
                    logger.error(f"Error adding document: {e}")

elif tab == "📁 Upload Files":
    st.header("📁 Upload Files")
    st.markdown("Upload PDF, Word, Excel, images, and text files to your knowledge base")
    
    # Get supported file types
    supported_types = file_service.get_supported_file_types()
    
    # Display supported file types
    with st.expander("📋 Supported File Types"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Supported Extensions:**")
            st.write(", ".join(supported_types['supported_extensions']))
        
        with col2:
            st.write(f"**Max File Size:** {supported_types['max_file_size'] // (1024*1024)}MB")
    
    # File upload form
    with st.form("file_upload_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            # Knowledge base selection
            with get_session() as session:
                existing_kbs = session.query(KnowledgeBase).all()
                kb_options = {kb.name: kb.id for kb in existing_kbs}
                kb_options["Create New Knowledge Base"] = "new"
                
                selected_kb = st.selectbox(
                    "Select Knowledge Base",
                    options=list(kb_options.keys()),
                    key="file_kb_selection"
                )
            
            if selected_kb == "Create New Knowledge Base":
                new_kb_name = st.text_input("New Knowledge Base Name", key="file_new_kb_name")
                new_kb_description = st.text_area("Description", key="file_new_kb_description")
        
        with col2:
            # Document details
            doc_title = st.text_input("Document Title (Optional)", key="file_doc_title")
            doc_description = st.text_area("Description (Optional)", key="file_doc_description")
            
            # Tags
            tags_input = st.text_input("Tags (comma-separated)", key="file_tags_input")
            tags = [tag.strip() for tag in tags_input.split(",") if tag.strip()]
        
        # File upload
        uploaded_files = st.file_uploader(
            "Choose files to upload",
            type=supported_types['supported_extensions'],
            accept_multiple_files=True,
            help="Upload PDF, Word, Excel, images, and text files"
        )
        
        uploaded = st.form_submit_button("📤 Upload Files")
        
        if uploaded and uploaded_files:
            if not uploaded_files:
                st.error("Please select at least one file to upload.")
            else:
                # Process each uploaded file
                success_count = 0
                error_count = 0
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for i, uploaded_file in enumerate(uploaded_files):
                    status_text.text(f"Processing {uploaded_file.name}...")
                    
                    try:
                        # Get file content
                        file_content = uploaded_file.read()
                        
                        # Create knowledge base if needed
                        if selected_kb == "Create New Knowledge Base":
                            if not new_kb_name:
                                st.error("Please provide a name for the new knowledge base.")
                                break
                            
                            import asyncio
                            kb_id = asyncio.run(file_service.create_file_knowledge_base(
                                name=new_kb_name,
                                description=new_kb_description
                            ))
                        else:
                            kb_id = kb_options[selected_kb]
                        
                        # Upload file
                        import asyncio
                        result = asyncio.run(file_service.upload_file(
                            file_content=file_content,
                            filename=uploaded_file.name,
                            knowledge_base_id=kb_id,
                            title=doc_title or None,
                            description=doc_description or None,
                            tags=tags
                        ))
                        
                        if result['success']:
                            success_count += 1
                            st.success(f"✅ {uploaded_file.name} uploaded successfully!")
                        else:
                            error_count += 1
                            st.error(f"❌ Failed to upload {uploaded_file.name}: {result['error']}")
                    
                    except Exception as e:
                        error_count += 1
                        st.error(f"❌ Error processing {uploaded_file.name}: {e}")
                    
                    # Update progress
                    progress_bar.progress((i + 1) / len(uploaded_files))
                
                # Final status
                status_text.text(f"Upload complete! ✅ {success_count} successful, ❌ {error_count} failed")
                
                if success_count > 0:
                    st.success(f"Successfully uploaded {success_count} file(s)!")
                    st.info("Files have been processed and added to your knowledge base. You can now search for content within these files.")
    
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
    st.header("🔍 Search Documents")
    
    # Search form
    with st.form("search_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            query = st.text_input("Search Query", placeholder="Enter your search query...")
            search_category = st.selectbox(
                "Category Filter",
                options=["All"] + [cat.value for cat in KnowledgeBaseCategory],
                key="search_category"
            )
        
        with col2:
            limit = st.slider("Max Results", min_value=1, max_value=20, value=5)
            min_score = st.slider("Min Score", min_value=0.0, max_value=1.0, value=0.7, step=0.1)
            include_files = st.checkbox("Include Uploaded Files", value=True)
        
        search_submitted = st.form_submit_button("🔍 Search")
        
        if search_submitted and query:
            try:
                with st.spinner("Searching..."):
                    # Perform search
                    category_filter = None
                    if search_category != "All":
                        category_filter = KnowledgeBaseCategory(search_category)
                    
                    import asyncio
                    results = asyncio.run(rag_service.hybrid_search(
                        query=query,
                        category=category_filter,
                        limit=limit
                    ))
                    
                    # If including files, also search uploaded files
                    file_results = []
                    if include_files:
                        file_results = asyncio.run(file_service.search_files(
                            query=query,
                            limit=limit
                        ))
                
                # Combine and display results
                total_results = len(results) + len(file_results)
                
                if total_results == 0:
                    st.info("No documents found matching your query.")
                else:
                    st.success(f"Found {total_results} documents ({len(results)} knowledge base, {len(file_results)} files)")
                    
                    for i, result in enumerate(results):
                        with st.expander(f"📄 Result {i+1}: {result['metadata'].get('title', 'Untitled')} (Score: {result['final_score']:.3f})"):
                            col1, col2 = st.columns([3, 1])
                            
                            with col1:
                                st.write(f"**Category:** {result['category']}")
                                st.write(f"**Content Type:** {result['metadata'].get('content_type', 'Unknown')}")
                                st.write(f"**Search Type:** {result.get('search_type', 'hybrid')}")
                                
                                # Show content preview
                                content_preview = result['content'][:500]
                                if len(result['content']) > 500:
                                    content_preview += "..."
                                st.text_area("Content Preview", content_preview, height=100, disabled=True, key=f"kb_search_preview_{i}")
                            
                            with col2:
                                st.metric("Similarity Score", f"{result['final_score']:.3f}")
                                if 'similarity_score' in result:
                                    st.metric("Semantic Score", f"{result['similarity_score']:.3f}")
                    
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
