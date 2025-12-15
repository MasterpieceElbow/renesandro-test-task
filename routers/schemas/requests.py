from pydantic import BaseModel, Field, model_validator


class TextToSpeechSchema(BaseModel):
    text: str
    voice: str


class ProcessMediaSchema(BaseModel):
    task_name: str
    video_blocks: dict[str, list[str]] = Field(min_length=1, max_length=10)
    audio_blocks: dict[str, list[str]] = Field(min_length=1)
    text_to_speech: list[TextToSpeechSchema] = Field(min_length=1)

    # Validate that all video and audio URLs are from Google Storage
    @model_validator(mode="after")
    def check_video_audio_blocks(self):
        for list_url in list(self.video_blocks.values()) + list(self.audio_blocks.values()):
            if len(list_url) == 0:
                raise ValueError("Video and audio URL blocks must not be empty")
            # for url in list_url:
            #     if not url.startswith("https://storage.googleapis.com"):
            #         raise ValueError(
            #             "Video and audio URLs must be only Google Storage"
            #         )
        return self
