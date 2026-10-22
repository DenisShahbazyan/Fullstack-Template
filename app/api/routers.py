from fastapi import APIRouter

from app.api.admin.v1.routers import admin_v1_router
from app.api.public.v1.endpoints import health
from app.api.public.v1.routers import public_v1_router

main_router = APIRouter()

main_router.include_router(health.router)
main_router.include_router(public_v1_router, prefix='/api/public/v1')
main_router.include_router(admin_v1_router, prefix='/api/admin/v1')
