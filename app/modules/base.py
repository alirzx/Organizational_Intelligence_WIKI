from typing import Protocol

from app.preprocessing.types import PreparedPage
from app.schemas.extraction import ModulePageResponse


class PageModule(Protocol):
    async def run(self, page: PreparedPage, request_id: str) -> ModulePageResponse:
        ...
