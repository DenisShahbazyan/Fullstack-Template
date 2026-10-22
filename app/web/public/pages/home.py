from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app.models.user import User
from app.web.dependencies import optional_user
from app.web.templates import render

router = APIRouter()


@router.get('/', response_class=HTMLResponse)
async def home(
    request: Request,
    current_user: User | None = Depends(optional_user),
):
    return render(request, 'public/pages/home.html', {'current_user': current_user})
