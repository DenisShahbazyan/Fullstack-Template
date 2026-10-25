"""Чистка осиротевших загрузок вручную — то же, что делает сервис uploads_sweep.

    uv run python -m scripts.uploads.sweep_orphans --dry-run   # только показать
    uv run python -m scripts.uploads.sweep_orphans             # удалить
    uv run python -m scripts.uploads.sweep_orphans --force     # без защиты от
                                                               # массового удаления

На сервере:

    sudo docker compose --env-file .env.docker exec web \\
        python -m scripts.uploads.sweep_orphans --dry-run

`--force` нужен, когда ночная чистка остановилась на ImplausibleOrphanSweepError,
а список сирот проверен глазами (`--dry-run`).
"""

from __future__ import annotations

import argparse
import asyncio

from app.core.logs import setup_logging
from app.core.s3.sweep import delete_orphans, plan_orphan_sweep
from app.domain.uploads.orphans import ensure_sweep_plausible


async def run(dry_run: bool, force: bool) -> None:
    plan = await plan_orphan_sweep()
    print(f'Файлов в папках сайта: {plan.total}, сирот: {len(plan.orphans)}')
    if dry_run:
        print('\n'.join(plan.orphans))
        return
    if not force:
        ensure_sweep_plausible(plan.total, len(plan.orphans))
    print(f'Удалено: {await delete_orphans(plan.orphans)}')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--dry-run', action='store_true', help='Только показать')
    parser.add_argument('--force', action='store_true', help='Без защиты')
    args = parser.parse_args()
    setup_logging()
    asyncio.run(run(args.dry_run, args.force))


if __name__ == '__main__':
    main()
