from fastapi import APIRouter

from app.web.admin.pages.audit import router as admin_audit_router
from app.web.admin.pages.dashboard import router as admin_dashboard_router
from app.web.admin.pages.users import router as admin_users_router
from app.web.public.pages.auth import router as public_auth_router
from app.web.public.pages.home import router as public_home_router

web_router = APIRouter(include_in_schema=False)

web_router.include_router(public_home_router)
web_router.include_router(public_auth_router)
web_router.include_router(admin_dashboard_router)
web_router.include_router(admin_users_router)
web_router.include_router(admin_audit_router)
