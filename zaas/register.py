import json

from pathlib import Path
from authlib.integrations.httpx_client import OAuth2Client

from .logger import Logger
from .models import ManagerConfig
from .config import config


class ZaaSRegister:

    logger: Logger
    config: ManagerConfig
    client: OAuth2Client

    def __init__(self, logger: Logger) -> None:

        # Logger
        self.logger = logger
        self.logger.log_json("Starting ZaaS registration process")

        # Config
        manager_config = self.read_config_file(str(Path(config.CONFIG_DIR) / Path(config.CONFIG_FILE)))
        if not manager_config:
            self.logger.fail(f"Failed to load configuration file: {config.CONFIG_FILE}")
            exit(1)
        self.config = manager_config

        # OAuth2 Client
        self.client = OAuth2Client(
            client_id=self.config.sso.client_id,
            client_secret=self.config.sso.client_secret,
            token_url=self.config.sso.provider_url + self.config.sso.token_path,
        )

    # Read configuration from file
    def read_config_file(self, path: str) -> ManagerConfig | None:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return ManagerConfig.model_validate_json(f.read())
        except FileNotFoundError:
            return None
        except json.JSONDecodeError as e:
            self.logger.fail(f"Config file {path} is not valid JSON: {e}")
        except Exception as e:
            self.logger.fail(f"Cannot read config file {path}: {e}")

    def register(self):

        # TODO: Implement registration logic here
