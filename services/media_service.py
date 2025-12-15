from logging import getLogger
from routers.schemas.requests import ProcessMediaSchema
from tasks.tasks import process_media

logger = getLogger(__name__)


class MediaService:
    async def process_media(self, media_data: ProcessMediaSchema) -> None:
        """
        Process media data asynchronously without blocking the main thread
        Main celery task is triggered here
        It spawns group of subtasks for each video combination, launches them 
        At the end, logs the total time and the number 
        of successful/unsuccessful executions of all processes
        """
        process_media.delay(**media_data.to_dict())
