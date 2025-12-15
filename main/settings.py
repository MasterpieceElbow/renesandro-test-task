from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    elevenlabs_api_key: str = ""
    google_application_credentials: str = ""
    google_drive_root_folder_id: str = ""
    redis_port: int = 6379
    redis_host: str = ""

    model_config = SettingsConfigDict(
        env_file = ".env",
        env_file_encoding = "utf-8",
        validate_assignment = True,
    )

settings = Settings()
