from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import itertools
from logging import getLogger
import os
import random
import tempfile
from celery import chord, group
import requests
from moviepy import (
    VideoFileClip, 
    concatenate_videoclips, 
    AudioFileClip, 
    VideoClip, 
    CompositeAudioClip
)
from moviepy.audio import fx
from routers.schemas.requests import TextToSpeechDict
from services.google_service import GoogleDriveService
from services.elevenlabs_service import ElevenLabsService
from services.schemas.schemas import LogSchema
from main.celery_app import celery_app

google_service = GoogleDriveService()
elevenlabs_service = ElevenLabsService()
logger = getLogger(__name__)


# Process the entire media task
@celery_app.task()
def process_media(
    task_name: str,
    video_blocks: dict[str, list[str]],
    audio_blocks: dict[str, list[str]],
    text_to_speech: list[TextToSpeechDict],
) -> None:
    start_time = datetime.now().timestamp()
    video_combinations = list(itertools.product(
        *video_blocks.values()
    ))
    audio_urls = [audio for block in audio_blocks.values() for audio in block]
    tasks = []

    # Create a Celery task for each video combination
    for index, combination in enumerate(video_combinations, start=1):
        kwargs ={
            "task_name": task_name,
            "video_urls": combination,
            "audio_url": random.choice(audio_urls),
            "text_to_speech": random.choice(text_to_speech),
            "index": index,
        }
        tasks.append(process_video.s(**kwargs))

    logger.info(
        LogSchema(
            task_name=task_name,
            timestamp=start_time,
            total_time=None,
            level="INFO",
            message="Media processing started",
            details={
                "total_videos": len(video_combinations),
            },
            error_details=None,
        ).model_dump(mode="json")
    )

    # Call a callback task to finalize the media processing after all videos are done
    return chord(
        group(tasks),
        finalize_media_process.s(
            task_name=task_name,
            start_time=start_time
        )
    ).apply_async()


# Log the media processing results after all videos are processed
@celery_app.task
def finalize_media_process(results, task_name: str, start_time: float) -> None:
    total_time = datetime.now().timestamp() - start_time

    success = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] == "failed"]

    logger.info(
        LogSchema(
            task_name=task_name,
            timestamp=datetime.now().timestamp(),
            total_time=total_time,
            level="INFO",
            message="Media processing finished",
            details={
                "success_count": len(success),
                "failed_count": len(failed),
            }
        ).model_dump(mode="json")
    )


# Process each video separately
@celery_app.task()
def process_video(
    task_name: str,
    video_urls: list[str],
    audio_url: str,
    text_to_speech: TextToSpeechDict,
    index: int,
) -> None:
    logger.info(
        LogSchema(
            task_name=task_name,
            timestamp=datetime.now().timestamp(),
            total_time=None,
            level="INFO",
            message=f"Processing video started",
            details={
                "video_number": index,
                "video_urls": video_urls,
                "audio_url": audio_url,
                "text_to_speech": text_to_speech,
            },
            error_details=None,
        ).model_dump(mode="json")
    )
    start_time = datetime.now().timestamp()
    try:
        # Use a temporary directory to store downloaded media and intermediate files
        # to delete them automatically after processing
        with tempfile.TemporaryDirectory() as tmpdir:
            video_filename = f"output_{index}.mp4"
            video_filepath = os.path.join(tmpdir, video_filename)
            video_files, background_filename = download_media(
                task_name=task_name,
                index=index,
                video_urls=video_urls,
                tmpdir=tmpdir,
                audio_url=audio_url,
            )

            voiceover_filename = create_voiceover(
                task_name=task_name,
                index=index,
                tmpdir=tmpdir,
                text_to_speech=text_to_speech,
            )

            video = create_video(video_files)
            audio = get_video_audio(
                video_duration=video.duration,
                background_filename=background_filename,
                voiceover_filename=voiceover_filename,
            )
            video = video.with_audio(audio)
            save_video(
                task_name=task_name, 
                index=index,
                video=video,
                video_filepath=video_filepath
            )
            save_to_google_drive(
                task_name=task_name,
                index=index,
                folder_name=task_name,
                file_path=video_filepath,
                file_name=video_filename,
            )
    # Catch all exceptions to log them properly
    except Exception as e:
        logger.error(
            LogSchema(
                task_name=task_name,
                timestamp=datetime.now().timestamp(),
                total_time=datetime.now().timestamp() - start_time,
                level="ERROR",
                message=f"Processing video failed",
                details={
                    "video_number": index,
                },
                error_details=str(e),
            ).model_dump(mode="json")
        )
        return {
            "status": "failed",
            "index": index,
            "error": str(e),
        }
    # If everything went fine log success
    else:
        logger.info(
            LogSchema(
                task_name=task_name,
                timestamp=datetime.now().timestamp(),
                total_time=datetime.now().timestamp() - start_time,
                level="INFO",
                message=f"Processing video finished successfully",
                details={
                    "video_number": index,
                },
                error_details=None,
            ).model_dump(mode="json")
        )
        return {
            "status": "success",
            "index": index,
            "error": None,
        }

def create_voiceover(
    task_name: str,
    index: int,
    tmpdir: str,
    text_to_speech: TextToSpeechDict,
) -> str:
    start_time = datetime.now().timestamp()
    voiceover_filename = os.path.join(
        tmpdir, 
        f"{text_to_speech['voice']}_{abs(hash(text_to_speech['text'])) % (10 ** 16)}.mp3",
    )
    elevenlabs_service.create_voiceover(
        filename=voiceover_filename,
        text=text_to_speech["text"],
        author=text_to_speech["voice"],
    )
    logger.info(
        LogSchema(
            task_name=task_name,
            timestamp=datetime.now().timestamp(),
            total_time=datetime.now().timestamp() - start_time,
            level="INFO",
            message=f"Voiceover created",
            details={
                "video_number": index,
            },
        ).model_dump(mode="json")
    )
    return voiceover_filename

def _download_file(url: str, target_dir: str) -> str:
    filename = os.path.join(target_dir, url.split("/")[-1])
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(filename, "wb") as f:
            for chunk in r.iter_content(1024 * 1024):
                f.write(chunk)
    return filename

def download_media(
    task_name: str,
    index: int,
    video_urls: list[str],
    tmpdir: str,
    audio_url: str,
) -> tuple[list[str], str]:
    start_time = datetime.now().timestamp()
    urls = video_urls + [audio_url]
    video_files = []
    background_filename = None

    # Download video and audio files concurrently
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_map = {
            executor.submit(_download_file, url, tmpdir): url
            for url in urls
        }

        for future in as_completed(future_map):
            url = future_map[future]
            filename = future.result()
            if url == audio_url:
                background_filename = filename
            else:
                video_files.append(filename)
    logger.info(
        LogSchema(
            task_name=task_name,
            timestamp=datetime.now().timestamp(),
            total_time=datetime.now().timestamp() - start_time,
            level="INFO",
            message=f"Media for video downloaded",
            details={
                "video_number": index,
            },
        ).model_dump(mode="json")
    )
    return video_files, background_filename


def get_video_audio(
    video_duration: float, 
    background_filename: str,
    voiceover_filename: str,
):
    background_audio = AudioFileClip(background_filename)
    background_audio = background_audio.with_effects(
        [
            fx.AudioLoop(duration=video_duration),
            fx.MultiplyVolume(0.2),
        ]
    )
    voiceover_audio = AudioFileClip(voiceover_filename)
    final_audio = CompositeAudioClip(
        [
            background_audio,
            voiceover_audio,
        ]
    )
    return final_audio

def create_video(
    video_files: list[str],
) -> VideoClip:
    clips = [
        VideoFileClip(file) for file in video_files
    ]
    final_video = concatenate_videoclips(clips, method="chain")
    return final_video

def save_video(
    task_name: str, 
    index: int,
    video: VideoClip,
    video_filepath: str
) -> None:
    start_time = datetime.now().timestamp()
    video.write_videofile(
        video_filepath,
        codec="libx264",
        audio_codec="aac",
        logger=None,
    )
    logger.info(
        LogSchema(
            task_name=task_name,
            timestamp=datetime.now().timestamp(),
            total_time=datetime.now().timestamp() - start_time,
            level="INFO",
            message=f"Video saved locally",
            details={
                "video_number": index,
            },
        ).model_dump(mode="json")
    )

def save_to_google_drive(
    task_name: str, 
    index: int,
    folder_name: str, 
    file_path: str, 
    file_name: str
) -> None:
    start_time = datetime.now().timestamp()
    google_service.upload_video(
        folder_name=folder_name,
        file_path=file_path,
        file_name=file_name,
    )
    logger.info(
        LogSchema(
            task_name=task_name,
            timestamp=datetime.now().timestamp(),
            total_time=datetime.now().timestamp() - start_time,
            level="INFO",
            message=f"Video uploaded to Google Drive",
            details={
                "video_number": index,
            },
        ).model_dump(mode="json")
    )
