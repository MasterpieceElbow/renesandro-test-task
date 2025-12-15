from fastapi import APIRouter

from routers.schemas.requests import ProcessMediaSchema
from services.media_service import MediaService


router = APIRouter()
media_service = MediaService()


@router.post("/process_media/")
async def process_media(
    media_data: ProcessMediaSchema,
):
    await media_service.process_media(media_data=media_data)
    return
