import os
import tempfile
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
from routers.schemas.requests import TextToSpeechSchema
from services.google_service import GoogleDriveService
from services.elevenlabs_service import ElevenLabsService

google_service = GoogleDriveService()
elevenlabs_service = ElevenLabsService()


@celery.shared_task(name="process_video")
def process_video(
    task_name: str,
    video_urls: list[str],
    audio_url: str,
    text_to_speech: TextToSpeechSchema,
    index: int,
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        video_filename = f"output_{index}.mp4"
        video_filepath = os.path.join(tmpdir, video_filename)
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

        voiceover_filename = os.path.join(
            tmpdir, 
            f"{text_to_speech.voice}_{abs(hash(text_to_speech.text)) % (10 ** 16)}.mp3",
        )
        elevenlabs_service.create_voiceover(
            filename=voiceover_filename,
            text=text_to_speech.text,
            author=text_to_speech.voice,
        )

        video = create_video(video_files)
        audio = get_video_audio(
            video_duration=video.duration,
            background_filename=background_filename,
            voiceover_filename=voiceover_filename,
        )
        video = video.with_audio(audio)
        video.write_videofile(
            video_filepath,
            codec="libx264",
            audio_codec="aac"
        )
        save_to_google_drive(
            folder_name=task_name,
            file_path=video_filepath,
            file_name=video_filename,
        )

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

def save_to_google_drive(folder_name: str, file_path: str, file_name: str) -> None:
    google_service.upload_video(
        folder_name=folder_name,
        file_path=file_path,
        file_name=file_name,
    )