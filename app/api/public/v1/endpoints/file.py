from fastapi import APIRouter, Depends, File, UploadFile

from app.core.auth.users import current_user
from app.core.constants import AUTH_REQUIRED
from app.core.s3.claim import store_tmp_upload
from app.core.s3.links import signed_url
from app.core.s3.store import read_upload
from app.models.user import User
from app.schemas.public.v1.file import FileUploadSchema

router = APIRouter(prefix='/files', tags=['file'])


@router.post('/upload', summary=AUTH_REQUIRED + 'Временная загрузка файла')
async def upload_file(
    file: UploadFile = File(...),
    user: User = Depends(current_user),
) -> FileUploadSchema:
    """Кладёт файл во временную папку пользователя на ORPHAN_TTL_HOURS.

    Ключ принимает только запись того же пользователя (`claim_uploads`).
    """
    key = await store_tmp_upload(await read_upload(file), user.id)
    return FileUploadSchema(key=key, url=await signed_url(key) or '')
