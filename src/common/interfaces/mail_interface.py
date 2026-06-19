from abc import ABC, abstractmethod


class IMail(ABC):
    @abstractmethod
    async def send(self, to: str, subject: str, body: str, html: str | None = None) -> None: ...

    @abstractmethod
    async def send_bulk(self, recipients: list[str], subject: str, body: str) -> None: ...
