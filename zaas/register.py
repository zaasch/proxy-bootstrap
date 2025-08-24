import json

from .logger import Logger
from .models import ManagerConfig


class ZaaSRegister:

    def __init__(self, logger: Logger) -> None:
        self.logger = logger

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
        self.logger.log_json("Starting ZaaS registration process")
