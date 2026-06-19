from typing import Optional

from pydantic import BaseModel, ConfigDict

from src.common.response import to_camel


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int
    has_next_page: bool
    has_prev_page: bool

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )
