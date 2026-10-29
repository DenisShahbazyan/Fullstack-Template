"""Ручной порядок списков в админке: перетаскивание строк (drag-sort.js)."""

from collections.abc import Collection, Sequence

from app.domain.admin.errors import StaleOrderError

SORT_STEP = 10
"""Шаг с запасом: между соседями остаётся место для вставки без перенумерации."""


def sort_orders(
    ordered_ids: Sequence[int], existing_ids: Collection[int]
) -> dict[int, int]:
    """Позиции по новому порядку: первый — 0, дальше с шагом SORT_STEP.

    Raises:
        StaleOrderError: прислан не тот же набор, что в базе — список успели
            поменять в другой вкладке, и применять старый порядок нельзя.
    """
    if len(ordered_ids) != len(set(ordered_ids)) or set(ordered_ids) != set(
        existing_ids
    ):
        raise StaleOrderError()
    return {item_id: index * SORT_STEP for index, item_id in enumerate(ordered_ids)}


def next_sort_order(current: Collection[int]) -> int:
    """Позиция для нового элемента — в конец списка."""
    return max(current, default=-SORT_STEP) + SORT_STEP
