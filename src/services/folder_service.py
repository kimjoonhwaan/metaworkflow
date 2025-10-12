"""Folder Service - Manages workflow folders"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from src.database.models import Folder
from src.utils import get_logger

logger = get_logger("folder_service")


class FolderService:
    """Service for managing workflow folders"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def create_folder(
        self,
        name: str,
        description: Optional[str] = None,
        parent_id: Optional[str] = None,
    ) -> Folder:
        """Create a new folder
        
        Args:
            name: Folder name
            description: Folder description
            parent_id: Parent folder ID (for nested folders)
            
        Returns:
            Created Folder record
        """
        logger.info(f"Creating folder: {name}")
        
        # Check if name already exists
        existing = self.db.query(Folder).filter(Folder.name == name).first()
        if existing:
            raise ValueError(f"Folder with name '{name}' already exists")
        
        # Validate parent folder exists if specified
        if parent_id:
            parent = self.db.query(Folder).filter(Folder.id == parent_id).first()
            if not parent:
                raise ValueError(f"Parent folder not found: {parent_id}")
        
        folder = Folder(
            name=name,
            description=description,
            parent_id=parent_id,
        )
        
        self.db.add(folder)
        self.db.commit()
        self.db.refresh(folder)
        
        logger.info(f"Folder created: {folder.id}")
        
        return folder
    
    def get_folder(self, folder_id: str) -> Optional[Folder]:
        """Get folder by ID"""
        return self.db.query(Folder).filter(Folder.id == folder_id).first()
    
    def list_folders(self, parent_id: Optional[str] = None) -> List[Folder]:
        """List folders, optionally filtered by parent"""
        query = self.db.query(Folder)
        
        if parent_id is not None:
            query = query.filter(Folder.parent_id == parent_id)
        
        return query.all()
    
    def update_folder(
        self,
        folder_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Folder:
        """Update folder"""
        folder = self.get_folder(folder_id)
        if not folder:
            raise ValueError(f"Folder not found: {folder_id}")
        
        if name is not None:
            # Check name uniqueness
            existing = self.db.query(Folder).filter(
                Folder.name == name,
                Folder.id != folder_id
            ).first()
            if existing:
                raise ValueError(f"Folder with name '{name}' already exists")
            
            folder.name = name
        
        if description is not None:
            folder.description = description
        
        self.db.commit()
        self.db.refresh(folder)
        
        logger.info(f"Folder updated: {folder_id}")
        
        return folder
    
    def delete_folder(self, folder_id: str, force: bool = False) -> bool:
        """Delete folder
        
        Args:
            folder_id: Folder ID
            force: If True, delete even if folder has workflows
            
        Returns:
            True if deleted
        """
        folder = self.get_folder(folder_id)
        if not folder:
            raise ValueError(f"Folder not found: {folder_id}")
        
        # Check if folder has workflows
        if not force and folder.workflows:
            raise ValueError(
                f"Folder has {len(folder.workflows)} workflows. "
                "Use force=True to delete anyway."
            )
        
        self.db.delete(folder)
        self.db.commit()
        
        logger.info(f"Folder deleted: {folder_id}")
        
        return True

