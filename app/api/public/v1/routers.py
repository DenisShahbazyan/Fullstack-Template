from fastapi import APIRouter

from app.api.public.v1.endpoints import file, user

public_v1_router = APIRouter()

public_v1_router.include_router(user.router)
public_v1_router.include_router(file.router)
