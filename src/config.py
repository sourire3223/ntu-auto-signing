import configparser
from pathlib import Path

from pydantic import BaseModel


class UserConfig(BaseModel):
    username: str
    password: str


class MailConfig(BaseModel):
    Host: str
    TlsPort: int
    User: str
    Password: str
    SendWraningMail: bool


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
