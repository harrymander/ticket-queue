import os
from collections.abc import Sequence
from enum import Enum
from typing import ClassVar
from urllib.parse import urlparse

from pydantic import BaseModel, Field, model_validator


class _PathOrUrlType(Enum):
    Path = "path"
    Url = "url"


def is_url(val: str) -> bool:
    url = urlparse(val)
    return bool(url.scheme) and bool(url.netloc)


class PathOrUrl(BaseModel):
    Path: ClassVar = _PathOrUrlType.Path
    Url: ClassVar = _PathOrUrlType.Url

    type: _PathOrUrlType
    value: str

    @model_validator(mode="after")
    def validate_model(self) -> "PathOrUrl":
        if self.type == self.Url and not is_url(self.value):
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
        raise RuntimeError(f"no config found in ${{{_CONFIG_ENV_VAR}}}")
    _config = Config.model_validate_json(var)


def save_config_to_env(config: Config) -> None:
    var = os.getenv(_CONFIG_ENV_VAR)
    if var:
        raise RuntimeError(f"${{{_CONFIG_ENV_VAR}}} already set: {var}")
    os.environ[_CONFIG_ENV_VAR] = config.model_dump_json()
