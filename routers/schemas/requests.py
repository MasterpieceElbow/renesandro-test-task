from typing import TypedDict
from pydantic import BaseModel, Field, model_validator


class TestToSpeechDict(TypedDict):
    text: str
    voice: str

class TextToSpeechSchema(BaseModel):
    text: str
    voice: str

    def to_dict(self) -> TestToSpeechDict:
        return TestToSpeechDict(
            text=self.text,
            voice=self.voice,
        )


class ProcessMediaSchema(BaseModel):
    task_name: str
    video_blocks: dict[str, list[str]] = Field(min_length=1, max_length=10)
    audio_blocks: dict[str, list[str]] = Field(min_length=1)
    text_to_speech: list[TextToSpeechSchema] = Field(min_length=1)

    # All video and audio blocks must not be empty
    @model_validator(mode="after")
    def check_video_audio_blocks(self):
        for list_url in list(self.video_blocks.values()) + list(self.audio_blocks.values()):
            if len(list_url) == 0:
                raise ValueError("Video and audio URL blocks must not be empty")
        return self
