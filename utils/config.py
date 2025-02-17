from pydantic_settings import BaseSettings


class Config(BaseSettings):
    ARANGO_USER: str
    ARANGO_PASS: str
    
    class Config:
        env_file = ".env"


config = Config()