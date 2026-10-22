from fastapi import APIRouter

router = APIRouter(tags=['health'])


@router.get(
    '/health',
    summary='Проверка доступности API',
)
async def health_check() -> bool:
    return True
