import json

from pathlib import Path
from authlib.integrations.httpx_client import OAuth2Client

from .logger import Logger
from .models import ManagerConfig
from .config import config
from .utils import utils


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
            token_endpoint=self.config.sso.provider_url + self.config.sso.token_path,
            base_url=self.config.manager_url + self.config.api_path
        )
        self.client.fetch_token()

        # Log
        self.logger.log_json("SSO authentication successful")

    def read_config_file(self, path: str) -> ManagerConfig | None:
        """
        Read configuration from a JSON file and return a ManagerConfig object.
        """
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
        """
        Register the ZaaS instance with the manager.
        """

        # Build the extra_data dict
        extra_data = {}

        # VM Detection
        in_vm, hypervisor = utils.detect_vm()
        if in_vm:
            extra_data["vm"] = True
            extra_data["hypervisor"] = hypervisor

        # System Information
        sys_info = utils.get_system_info()
        extra_data["system"] = sys_info

        # Number of CPUs and Cores
        cpu_info = utils.get_cpu_info()
        extra_data["cpu"] = cpu_info

        # Memory Information
        mem_info = utils.get_memory_info()
        extra_data["memory"] = mem_info

        # Swap Information
        swap_info = utils.get_swap_info()
        extra_data["swap"] = swap_info

        # Disk Information
        disk_info = utils.get_disk_info()
        extra_data["disk"] = disk_info

        # I/O Information
        io_info = utils.get_io_info()
        extra_data["io"] = io_info

        # Call the registration API
        response = self.client.post(f"/{self.config.uuid}/register", json=extra_data)
        if response.status_code == 200:
            self.logger.log_json("ZaaS instance registered successfully")
        elif response.status_code == 400:
            self.logger.fail(f"Failed to register ZaaS instance. Bad request: {response.text}")
        elif response.status_code == 302:
            self.logger.fail(f"Failed to register ZaaS instance. Redirected to {response.headers.get('Location')}")
        else:
            self.logger.fail(f"Failed to register ZaaS instance. Get status code {response.status_code} with error: {response.text}")
