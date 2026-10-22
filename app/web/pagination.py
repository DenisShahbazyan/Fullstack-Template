"""Пагинация списков: одинаковая для админских и публичных страниц."""

from dataclasses import dataclass

PAGE_SIZE = 20


@dataclass(frozen=True)
class Pagination:
    """Готовые к рендеру ссылки постраничной навигации."""

    page: int
    pages: int
    total: int
    self_url: str
    prev_url: str | None
    next_url: str | None


def build_pagination(
    base_url: str,
    page: int,
    total: int,
    page_size: int = PAGE_SIZE,
) -> Pagination:
    """Считает границы страниц и ссылки «назад/вперёд» для готового URL."""
    pages = max(1, -(-total // page_size))
    separator = '&' if '?' in base_url else '?'
    return Pagination(
        page=page,
        pages=pages,
        total=total,
        self_url=f'{base_url}{separator}page={page}' if page > 1 else base_url,
        prev_url=f'{base_url}{separator}page={page - 1}' if page > 1 else None,
        next_url=f'{base_url}{separator}page={page + 1}' if page < pages else None,
    )
