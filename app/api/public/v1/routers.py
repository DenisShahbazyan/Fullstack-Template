from fastapi import APIRouter

from app.api.public.v1.endpoints import user

public_v1_router = APIRouter()

public_v1_router.include_router(user.router)
