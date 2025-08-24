from pydantic_settings import BaseSettings
from pydantic import Field


class Config(BaseSettings):

    LOGFILE = Field("/var/log/zaas-bootstrap.log", description="Path to the log file")
    CONFIG_DIR = Field("/etc/zaas", description="Path to the config directory")
    CONFIG_FILE = Field("zaas.json", description="Path to the config file")
    UUID_FILE = Field("uuid", description="Path to the UUID file")


config = Config()
