from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")


class IRepository(ABC, Generic[T]):
    @abstractmethod
    async def get_by_id(self, id: int) -> T | None: ...

    @abstractmethod
    async def get_all(self, skip: int = 0, limit: int = 100) -> list[T]: ...

    @abstractmethod
    async def create(self, obj: T) -> T: ...

    @abstractmethod
    async def update(self, obj: T) -> T: ...

    @abstractmethod
    async def delete(self, id: int) -> None: ...

    @abstractmethod
    async def exists(self, id: int) -> bool: ...
