"""Domain management service for dynamic domain handling"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import re
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database.models import Domain
from ..database.session import get_session
from ..utils.logger import get_logger

logger = get_logger(__name__)


def normalize_collection_name(name: str) -> str:
    """
    Normalize domain name to valid ChromaDB collection name
    
    ChromaDB collection names must:
    (1) contain 3-63 characters
    (2) start and end with alphanumeric character
    (3) only contain alphanumeric characters, underscores or hyphens (-)
    (4) not contain two consecutive periods (..)
    (5) not be a valid IPv4 address
    
    Args:
        name: Original domain name (e.g., "기상청 API", "Naver-뉴스")
    
    Returns:
        Valid collection name (e.g., "collection_api_xyz")
    """
    # Convert to lowercase
    normalized = name.lower()
    
    # Replace spaces with underscores
    normalized = normalized.replace(" ", "_")
    
    # Replace Korean characters with romanized equivalents or remove
    # For now, we'll replace non-alphanumeric with underscores
    normalized = re.sub(r'[^a-z0-9_\-]', '_', normalized)
    
    # Remove consecutive underscores
    normalized = re.sub(r'_+', '_', normalized)
    
    # Remove leading/trailing underscores
    normalized = normalized.strip('_')
    
    # Ensure minimum length (3 chars)
    if len(normalized) < 3:
        # Append random suffix if too short
        normalized = f"{normalized}_" + str(uuid.uuid4())[:8]
    
    # Ensure maximum length (63 chars)
    if len(normalized) > 63:
        normalized = normalized[:59] + "_" + str(uuid.uuid4())[:4]
    
    # Prepend "collection_" prefix
    collection_name = f"collection_{normalized}"
    
    # Final check
    if len(collection_name) > 63:
        # If still too long, use hash
        hash_suffix = str(uuid.uuid4())[:8]
        collection_name = f"collection_{hash_suffix}"
    
    return collection_name


class DomainService:
    """Service for managing domains dynamically"""
    
    def __init__(self):
        """Initialize domain service"""
        self.ensure_common_domain()
    
    def ensure_common_domain(self) -> Domain:
        """
        Ensure common domain exists (system initialization)
        
        Returns:
            Common domain object
        """
        with get_session() as session:
            common = session.query(Domain).filter(Domain.name == "common").first()
            
            if not common:
                logger.info("🔧 Creating common domain...")
                common = Domain(
                    name="common",
                    display_name="공통 도메인",
                    description="모든 검색에 포함되는 공통 문서 (Python 기초, REST API 개념 등)",
                    keywords=["common", "공통", "일반", "기본"],
                    collection_name="collection_common",
                    is_common=True,
                    is_active=True
                )
                session.add(common)
                session.commit()
                session.refresh(common)
                logger.info("✅ Common domain created")
            
            return common
    
    def create_or_get_domain(
        self,
        name: str,
        keywords: List[str] = None,
        display_name: str = None,
        description: str = None
    ) -> Domain:
        """
        Create new domain or get existing one
        
        Args:
            name: Domain name (e.g., "네이버", "기상청")
            keywords: List of keywords for detection (e.g., ["네이버", "naver", "NAVER"])
            display_name: Display name (optional)
            description: Description (optional)
        
        Returns:
            Domain object
        """
        with get_session() as session:
            # ✨ Normalize domain name and keywords
            name = name.strip() if name else name
            keywords = [k.strip() for k in (keywords or []) if k and k.strip()]
            
            # Check if domain already exists
            domain = session.query(Domain).filter(Domain.name == name).first()
            
            if domain:
                logger.debug(f"📂 Domain '{name}' already exists")
                return domain
            
            # Create new domain
            collection_name = normalize_collection_name(name)
            
            domain = Domain(
                name=name,
                display_name=display_name or name,
                description=description or f"{name} 관련 문서",
                keywords=keywords or [name],
                collection_name=collection_name,
                is_common=False,
                is_active=True,
                document_count=0
            )
            
            session.add(domain)
            session.commit()
            session.refresh(domain)
            
            logger.info(f"✅ Created new domain: '{name}' (collection: {collection_name})")
            return domain
    
    def find_domain_by_keywords(self, text: str) -> Optional[Domain]:
        """
        Find domain by matching keywords in text
        
        Also matches against domain.name directly
        
        Args:
            text: Text to search for domain keywords
        
        Returns:
            Matched domain or None
        """
        with get_session() as session:
            # Get all active non-common domains
            all_domains = session.query(Domain).filter(
                Domain.is_active == True,
                Domain.is_common == False
            ).all()
            
            if not all_domains:
                logger.debug("📂 No active domains found")
                return None
            
            text_lower = text.lower()
            
            # Try to match keywords
            best_match = None
            max_matches = 0
            
            for domain in all_domains:
                match_count = 0
                matched_keywords = []
                
                # ✨ NEW: Always include domain.name as a keyword
                keywords_to_check = (domain.keywords or []) + [domain.name]
                
                for keyword in keywords_to_check:
                    if keyword.lower() in text_lower:
                        match_count += 1
                        matched_keywords.append(keyword)
                
                if match_count > max_matches:
                    max_matches = match_count
                    best_match = domain
                    logger.debug(f"  📍 Domain '{domain.name}' matched {match_count} keywords: {matched_keywords}")
            
            if best_match:
                logger.info(f"🎯 Found domain '{best_match.name}' by keywords (matches: {max_matches})")
                
                # Update last_used_at
                with get_session() as update_session:
                    domain_to_update = update_session.query(Domain).filter(
                        Domain.id == best_match.id
                    ).first()
                    if domain_to_update:
                        domain_to_update.last_used_at = datetime.utcnow()
                        update_session.commit()
            
            return best_match
    
    def get_all_domains(self, include_common: bool = True) -> List[Domain]:
        """
        Get all active domains
        
        Args:
            include_common: Include common domain in results
        
        Returns:
            List of domain objects
        """
        with get_session() as session:
            query = session.query(Domain).filter(Domain.is_active == True)
            
            if not include_common:
                query = query.filter(Domain.is_common == False)
            
            domains = query.order_by(Domain.name).all()
            logger.debug(f"📂 Found {len(domains)} active domains")
            return domains
    
    def get_common_domain(self) -> Optional[Domain]:
        """
        Get common domain
        
        Returns:
            Common domain object or None
        """
        with get_session() as session:
            return session.query(Domain).filter(Domain.is_common == True).first()
    
    def get_domain_by_name(self, name: str) -> Optional[Domain]:
        """
        Get domain by name
        
        Args:
            name: Domain name
        
        Returns:
            Domain object or None
        """
        with get_session() as session:
            return session.query(Domain).filter(Domain.name == name).first()
    
    def get_domain_by_id(self, domain_id: str) -> Optional[Domain]:
        """
        Get domain by ID
        
        Args:
            domain_id: Domain ID
        
        Returns:
            Domain object or None
        """
        with get_session() as session:
            return session.query(Domain).filter(Domain.id == domain_id).first()
    
    def update_domain_keywords(
        self,
        domain_id: str,
        keywords: List[str]
    ) -> bool:
        """
        Update domain keywords
        
        Args:
            domain_id: Domain ID
            keywords: New keywords list
        
        Returns:
            Success status
        """
        try:
            with get_session() as session:
                domain = session.query(Domain).filter(Domain.id == domain_id).first()
                
                if not domain:
                    logger.error(f"❌ Domain not found: {domain_id}")
                    return False
                
                domain.keywords = keywords
                domain.updated_at = datetime.utcnow()
                session.commit()
                
                logger.info(f"✅ Updated keywords for domain '{domain.name}': {keywords}")
                return True
        
        except Exception as e:
            logger.error(f"❌ Failed to update domain keywords: {e}")
            return False
    
    def update_document_count(self, domain_id: str, increment: int = 1) -> bool:
        """
        Update document count for domain
        
        Args:
            domain_id: Domain ID
            increment: Count increment (can be negative)
        
        Returns:
            Success status
        """
        try:
            with get_session() as session:
                domain = session.query(Domain).filter(Domain.id == domain_id).first()
                
                if not domain:
                    return False
                
                domain.document_count = max(0, domain.document_count + increment)
                session.commit()
                
                return True
        
        except Exception as e:
            logger.error(f"❌ Failed to update document count: {e}")
            return False
    
    def deactivate_domain(self, domain_id: str) -> bool:
        """
        Deactivate domain (soft delete)
        
        Args:
            domain_id: Domain ID
        
        Returns:
            Success status
        """
        try:
            with get_session() as session:
                domain = session.query(Domain).filter(Domain.id == domain_id).first()
                
                if not domain:
                    logger.error(f"❌ Domain not found: {domain_id}")
                    return False
                
                if domain.is_common:
                    logger.error(f"❌ Cannot deactivate common domain")
                    return False
                
                domain.is_active = False
                domain.updated_at = datetime.utcnow()
                session.commit()
                
                logger.info(f"✅ Deactivated domain '{domain.name}'")
                return True
        
        except Exception as e:
            logger.error(f"❌ Failed to deactivate domain: {e}")
            return False
    
    def get_domain_statistics(self) -> Dict[str, Any]:
        """
        Get domain statistics
        
        Returns:
            Statistics dictionary
        """
        with get_session() as session:
            total_domains = session.query(func.count(Domain.id)).scalar()
            active_domains = session.query(func.count(Domain.id)).filter(
                Domain.is_active == True
            ).scalar()
            
            domains = session.query(Domain).filter(Domain.is_active == True).all()
            
            domain_stats = []
            for domain in domains:
                domain_stats.append({
                    "name": domain.name,
                    "display_name": domain.display_name,
                    "document_count": domain.document_count,
                    "last_used_at": domain.last_used_at.isoformat() if domain.last_used_at else None,
                    "is_common": domain.is_common
                })
            
            return {
                "total_domains": total_domains,
                "active_domains": active_domains,
                "domains": domain_stats
            }


# Singleton instance
_domain_service = None

def get_domain_service() -> DomainService:
    """Get singleton domain service instance"""
    global _domain_service
    if _domain_service is None:
        _domain_service = DomainService()
    return _domain_service

