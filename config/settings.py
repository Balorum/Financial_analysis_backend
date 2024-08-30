from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    sqlalchemy_database_url: str = "sqlite:///db.sqlite3"

    class Config:
        extra = "ignore"
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
