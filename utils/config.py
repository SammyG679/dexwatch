from pydantic_settings import BaseSettings


class Config(BaseSettings):
    ARANGO_USER: str
    ARANGO_PASS: str
    PROXY_USERNAME: str = ""
    PROXY_PASSWORD: str = ""

    class Config:
        env_file = ".env"


# Instantiate a Config object to use in your application
config = Config()
