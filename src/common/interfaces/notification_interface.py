from abc import ABC, abstractmethod


class INotifier(ABC):
    @abstractmethod
    async def notify(self, user_id: int, event: str, message: str, metadata: dict) -> None: ...

    @abstractmethod
    async def notify_bulk(self, user_ids: list[int], event: str, message: str) -> None: ...
