from pydantic_settings import BaseSettings
from pydantic import Field


class Config(BaseSettings):

    LOGFILE: str = Field("/var/log/zaas-bootstrap.log", description="Path to the log file")
    CONFIG_DIR: str = Field("/etc/zaas", description="Path to the config directory")
    CONFIG_FILE: str = Field("zaas.json", description="Path to the config file")
    UUID_FILE: str = Field("uuid", description="Path to the UUID file")


config = Config()  # type: ignore
