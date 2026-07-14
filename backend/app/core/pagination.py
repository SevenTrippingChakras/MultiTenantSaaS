"""Cursor (keyset) pagination.

Keyset pagination beats offset/`skip` at scale: instead of counting past N rows
(O(N) and unstable when rows shift), it seeks straight to the row after an opaque
cursor using an indexed key. The cursor here is the last item's `_id`; a page
carries a `next_cursor` the client echoes back as `?after=`.

Repos over-fetch one row (`limit + 1`) so we can tell whether more remain without
a second count query; `build_page` trims that extra row and derives the cursor.
"""

from collections.abc import Callable

from pydantic import BaseModel

DEFAULT_LIMIT = 50
MAX_LIMIT = 100


class Page[T](BaseModel):
    """A single page of results plus the cursor to fetch the next one."""

    items: list[T]
    next_cursor: str | None = None


def clamp_limit(limit: int) -> int:
    """Bound a client-supplied limit to a sane range (defends the DB)."""
    if limit < 1:
        return DEFAULT_LIMIT
    return min(limit, MAX_LIMIT)


def build_page[T](docs: list[dict], limit: int, to_out: Callable[[dict], T]) -> Page[T]:
    """Turn `limit + 1` raw docs into a Page: trim the probe row, set the cursor.

    `docs` holds up to `limit + 1` rows (the repo over-fetches by one). If the
    extra row is present there are more results, so we drop it and expose the
    last kept row's `_id` as `next_cursor`.
    """
    has_more = len(docs) > limit
    kept = docs[:limit]
    next_cursor = str(kept[-1]["_id"]) if has_more and kept else None
    return Page(items=[to_out(d) for d in kept], next_cursor=next_cursor)
