"""Domain detector for automatic domain classification (DEPRECATED - Use DomainService instead)"""
from typing import Optional
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DomainDetector:
    """
    Automatically detect domain from document title and content
    
    NOTE: This class is deprecated. Use DomainService.find_domain_by_keywords() instead.
    DomainService uses dynamic keywords from the database.
    """
    
    @staticmethod
    def detect_domain(title: str, content: str = "") -> str:
        """
        Detect domain from document title and content (DEPRECATED)
        
        Use DomainService.find_domain_by_keywords() instead for dynamic detection.
        
        Args:
            title: Document title
            content: Document content (optional)
        
        Returns:
            Detected domain name or "common"
        """
        logger.warning("⚠️ DomainDetector.detect_domain() is deprecated. Use DomainService.find_domain_by_keywords() instead.")
        
        # Import here to avoid circular dependency
        from src.services.domain_service import get_domain_service
        
        domain_service = get_domain_service()
        text = f"{title} {content[:500]}"
        
        # Use DomainService for detection
        detected_domain_obj = domain_service.find_domain_by_keywords(text)
        
        if detected_domain_obj:
            return detected_domain_obj.name
        
        return "common"
    
    @staticmethod
    def get_available_domains() -> list:
        """
        Get list of available domains (DEPRECATED)
        
        Use DomainService.get_all_domains() instead.
        """
        logger.warning("⚠️ DomainDetector.get_available_domains() is deprecated. Use DomainService.get_all_domains() instead.")
        
        from src.services.domain_service import get_domain_service
        
        domain_service = get_domain_service()
        all_domains = domain_service.get_all_domains()
        
        return [d.name for d in all_domains]
