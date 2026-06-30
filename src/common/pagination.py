import math


def build_pagination(page: int, page_size: int, total: int) -> dict:
    """Build pagination metadata dict (camelCase keys for frontend contract)."""
    total_pages = math.ceil(total / page_size) if total else 0
    return {
        "page": page,
        "pageSize": page_size,
        "total": total,
        "totalPages": total_pages,
        "hasNextPage": page < total_pages,
        "hasPrevPage": page > 1,
    }
