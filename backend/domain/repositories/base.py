"""
Base repository interface.
Implements Repository Pattern following Dependency Inversion Principle.
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List
from uuid import UUID

T = TypeVar('T')


class IRepository(ABC, Generic[T]):
    """
    Abstract repository interface.
    Defines contract for data access operations.
    Concrete implementations can use different storage backends.
    """
    
    @abstractmethod
    async def create(self, entity: T) -> T:
        """Create a new entity."""
        pass
    
    @abstractmethod
    async def get_by_id(self, entity_id: UUID) -> Optional[T]:
        """Retrieve entity by ID."""
        pass
    
    @abstractmethod
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """Retrieve all entities with pagination."""
        pass
    
    @abstractmethod
    async def update(self, entity: T) -> T:
        """Update an existing entity."""
        pass
    
    @abstractmethod
    async def delete(self, entity_id: UUID) -> bool:
        """Delete an entity by ID."""
        pass
    
    @abstractmethod
    async def exists(self, entity_id: UUID) -> bool:
        """Check if entity exists."""
        pass
