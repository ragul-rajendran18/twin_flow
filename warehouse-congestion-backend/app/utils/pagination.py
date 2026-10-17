from math import ceil
from typing import Any


def paginate(
    items: list[Any],
    page: int,
    page_size: int,
    total: int,
) -> dict:
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": ceil(total / page_size) if total else 0,
    }