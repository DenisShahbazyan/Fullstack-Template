from fastapi import APIRouter, Depends

from app.api.admin.v1.endpoints import audit_log, user
from app.core.admin.permissions import require_admin, require_moder_or_higher

# Модератору открыто то, что касается контента; управление людьми и журнал —
# только администратору.
admin_v1_router = APIRouter(dependencies=[Depends(require_moder_or_higher)])

_admin_only = APIRouter(dependencies=[Depends(require_admin)])
_admin_only.include_router(user.router)
_admin_only.include_router(audit_log.router)

admin_v1_router.include_router(_admin_only)
