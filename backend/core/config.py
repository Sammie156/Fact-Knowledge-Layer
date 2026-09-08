from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    gemini_api_key: str
    gemini_model: str = "gemini-3.5-flash"
    groq_api_key: str | None = None
    groq_model: str = "llama-3.1-8b-instant"
    llm_provider: str = "gemini"  # "gemini" | "groq"

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()  # type: ignore
