from abc import ABC, abstractmethod

from fastapi import UploadFile


class IStorage(ABC):
    @abstractmethod
    async def upload(self, file: UploadFile, folder: str) -> str: ...

    @abstractmethod
    async def download(self, file_path: str) -> bytes: ...

    @abstractmethod
    async def delete(self, file_path: str) -> None: ...

    @abstractmethod
    def get_url(self, file_path: str) -> str: ...
