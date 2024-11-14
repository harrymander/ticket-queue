import os
from collections.abc import Sequence
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, model_validator


class PathOrUrl(BaseModel):
    type: Literal["path", "url"]
    value: str

    @model_validator(mode="after")
    def validate_model(self) -> "PathOrUrl":
        if self.type == "url":
            url = urlparse(self.value)
            if not (url.scheme and url.netloc):
                raise ValueError("invalid URL")
        return self


class Config(BaseModel):
    urls: Sequence[str] = Field(min_length=1)
    frontend: PathOrUrl
    admin_password: str
    database: str


_config: Config | None = None


def get_config() -> Config:
    if not _config:
        raise RuntimeError("config not set")
    return _config


_CONFIG_ENV_VAR = "__TICKET_QUEUE_CONFIG"


def load_config_from_env() -> None:
    global _config

    var = os.getenv(_CONFIG_ENV_VAR)
    if not var:
        raise RuntimeError("no config stored found in environment")
    _config = Config.model_validate_json(var)


def save_config_to_env(config: Config) -> None:
    var = os.getenv(_CONFIG_ENV_VAR)
    if var:
        raise RuntimeError(f"${{{_CONFIG_ENV_VAR}}} already set: {var}")
    os.environ[_CONFIG_ENV_VAR] = config.model_dump_json()
