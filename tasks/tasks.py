from datetime import datetime
from logging import getLogger
import os
import tempfile
import time
import celery
import requests
import requests
from moviepy import (
    VideoFileClip, 
    concatenate_videoclips, 
    AudioFileClip, 
    VideoClip, 
    CompositeAudioClip
)
from moviepy.audio import fx
from routers.schemas.requests import TestToSpeechDict
from services.google_service import GoogleDriveService
from services.elevenlabs_service import ElevenLabsService
from services.schemas.schemas import LogSchema

google_service = GoogleDriveService()
elevenlabs_service = ElevenLabsService()
logger = getLogger(__name__)


@celery.shared_task(name="process_video")
def process_video(
    task_name: str,
    video_urls: list[str],
    audio_url: str,
    text_to_speech: TestToSpeechDict,
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
    start_time = time.time()
    try:
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
    except Exception as e:
        logger.error(
            LogSchema(
                task_name=task_name,
                timestamp=datetime.now().timestamp(),
                total_time=time.time() - start_time,
                level="ERROR",
                message=f"Processing video failed",
                details={
                    "video_number": index,
                },
                error_details=str(e),
            ).model_dump(mode="json")
        )
        return
    else:
        logger.info(
            LogSchema(
                task_name=task_name,
                timestamp=datetime.now().timestamp(),
                total_time=time.time() - start_time,
                level="INFO",
                message=f"Processing video finished successfully",
                details={
                    "video_number": index,
                },
                error_details=None,
            ).model_dump(mode="json")
        )

def create_voiceover(
    task_name: str,
    index: int,
    tmpdir: str,
    text_to_speech: TestToSpeechDict,
) -> str:
    start_time = time.time()
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
            total_time=time.time() - start_time,
            level="INFO",
            message=f"Voiceover created",
            details={
                "video_number": index,
            },
        ).model_dump(mode="json")
    )
    return voiceover_filename

def download_media(
    task_name: str,
    index: int,
    video_urls: list[str],
    tmpdir: str,
    audio_url: str,
) -> tuple[list[str], str]:
    start_time = time.time()
    video_files = []
    for video_url in video_urls:
        filename = os.path.join(tmpdir, video_url.split("/")[-1])
        with requests.get(video_url, stream=True) as r:
            r.raise_for_status()
            with open(filename, "wb") as f:
                for chunk in r.iter_content(1024 * 1024):
                    f.write(chunk)
        video_files.append(filename)

    background_filename = os.path.join(tmpdir, audio_url.split("/")[-1])
    with requests.get(audio_url, stream=True) as r:
        r.raise_for_status()
        with open(background_filename, "wb") as f:
            for chunk in r.iter_content(1024 * 1024):
                f.write(chunk)
    logger.info(
        LogSchema(
            task_name=task_name,
            timestamp=datetime.now().timestamp(),
            total_time=time.time() - start_time,
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
    start_time = time.time()
    video.write_videofile(
        video_filepath,
        codec="libx264",
        audio_codec="aac"
    )
    logger.info(
        LogSchema(
            task_name=task_name,
            timestamp=datetime.now().timestamp(),
            total_time=time.time() - start_time,
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
    start_time = time.time()
    google_service.upload_video(
        folder_name=folder_name,
        file_path=file_path,
        file_name=file_name,
    )
    logger.info(
        LogSchema(
            task_name=task_name,
            timestamp=datetime.now().timestamp(),
            total_time=time.time() - start_time,
            level="INFO",
            message=f"Video uploaded to Google Drive",
            details={
                "video_number": index,
            },
        ).model_dump(mode="json")
    )
