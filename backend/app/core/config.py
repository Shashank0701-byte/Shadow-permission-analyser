from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    neo4j_uri: str = "neo4j://127.0.0.1:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""
    allowed_origins: str = "http://localhost:5173"

    model_config = {"env_file": ".env"}


settings = Settings()
