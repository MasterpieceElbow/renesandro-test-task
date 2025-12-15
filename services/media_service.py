from datetime import datetime
import random
import itertools
from logging import getLogger
from routers.schemas.requests import ProcessMediaSchema
from services.google_service import GoogleDriveService
from services.schemas.schemas import LogSchema
from tasks.tasks import process_video

logger = getLogger(__name__)

google_service = GoogleDriveService()


class MediaService:
    async def process_media(self, media_data: ProcessMediaSchema) -> None:
        logger.info(
            LogSchema(
                task_name=media_data.task_name,
                timestamp=datetime.now().timestamp(),
                total_time=None,
                level="INFO",
                message="Processing media started",
                error_details=None,
            ).model_dump(mode="json")
        )
        video_combinations = list(itertools.product(
            *media_data.video_blocks.values()
        ))
        audio_urls = [audio for block in media_data.audio_blocks.values() for audio in block]
        for index, combination in enumerate(video_combinations, start=1):
            audio_url = random.choice(audio_urls)
            text_to_speech = random.choice(media_data.text_to_speech)
            kwargs ={
                "task_name": media_data.task_name,
                "video_urls": combination,
                "audio_url": audio_url,
                "text_to_speech": text_to_speech.to_dict(),
                "index": index,
            }
            process_video.delay(**kwargs)
