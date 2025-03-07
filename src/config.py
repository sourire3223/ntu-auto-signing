import configparser
from pathlib import Path

from pydantic import BaseModel, model_validator, Field
from typing import Any


class UserConfig(BaseModel):
    username: str
    password: str


class MailConfig(BaseModel):
    host: str
    tls_port: int
    from_: str = Field(alias="from")
    password: str
    to: str

    @model_validator(mode="before")
    @classmethod
    def get_address(cls, values: dict[str, Any]) -> dict[str, Any]:
        values.setdefault("to", values["from"])
        return values


class Config(BaseModel):
    """Configuration data class"""

    user: UserConfig
    mail: MailConfig


def load_config(config_path: str) -> Config:
    """Load configuration from ini file"""
    if not Path(config_path).is_file():
        msg = f"Config file not found: {config_path}"
        raise FileNotFoundError(msg)

    config = configparser.ConfigParser()
    config.read(config_path)

    return Config(
        user=config["USER"],
        mail=config["MAIL"],
    )
