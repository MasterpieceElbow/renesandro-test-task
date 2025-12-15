from main.settings import settings
from elevenlabs.client import ElevenLabs
from elevenlabs import save


class ElevenLabsService:
    def __init__(self):
        self.api_key = settings.elevenlabs_api_key

    def create_voiceover(
        self, 
        filename: str,
        text: str, 
        author: str,
    ) -> str:
        client = ElevenLabs(api_key=self.api_key)
        voices = client.voices.search(search=author)
        if not voices.voices:
            raise ValueError(f"Voice '{author}' not found")

        voice_id = voices.voices[0].voice_id
        audio_bytes = client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
        )
        save(audio_bytes, filename)
