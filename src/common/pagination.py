import math


def build_pagination(page: int, page_size: int, total: int) -> dict:
    """Build pagination metadata dict."""
    total_pages = math.ceil(total / page_size) if total else 0
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "has_next_page": page < total_pages,
        "has_prev_page": page > 1,
    }
