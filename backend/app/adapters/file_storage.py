from typing import Protocol
from fastapi.concurrency import run_in_threadpool
from app.utils import file_storage as _fs

class AbstractFileStorage(Protocol):
    async def put(self, key: str, content: bytes, content_type: str) -> None: ...
    async def delete(self, key: str) -> None: ...
    def url_for(self, key: str | None) -> str | None: ...


class MinioFileStorage:
    async def put(self, key: str, content: bytes, content_type: str) -> None:
        await run_in_threadpool(_fs.put_object, key, content, content_type)

    async def delete(self, key: str) -> None:
        await run_in_threadpool(_fs.delete_object, key)

    def url_for(self, key: str | None) -> str | None:
        return _fs.presigned_url(key)