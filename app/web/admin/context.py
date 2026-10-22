"""Общий контекст страниц админки: текущий пользователь и активный пункт меню."""

from dataclasses import dataclass

from fastapi import Depends

from app.models.user import User
from app.web.dependencies import web_require_moder


@dataclass(frozen=True)
class AdminContext:
    """То, что нужно каждому админскому шаблону независимо от страницы."""

    user: User

    def as_template_context(self, active_nav: str) -> dict[str, object]:
        return {'current_user': self.user, 'active_nav': active_nav}


async def admin_context(user: User = Depends(web_require_moder)) -> AdminContext:
    return AdminContext(user=user)
