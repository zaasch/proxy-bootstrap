import os
import shutil
import subprocess
import json
import sys
import tempfile
import requests
import uuid as uuid_mod

from pathlib import Path

from .models import ManagerConfig
from .logger import Logger
from .config import config


class ZaaSBootstrap:

    logger: Logger

    def __init__(self, logger: Logger) -> None:
        self.logger = logger

    def is_root(self) -> bool:
        return os.geteuid() == 0

    def detect_vm(self) -> tuple[bool, str]:
        """Use systemd-detect-virt if available."""
        if shutil.which("systemd-detect-virt"):
            try:
                out = subprocess.run(
                    ["systemd-detect-virt"], check=False, capture_output=True, text=True
                )
                if out.returncode == 0:
                    return True, (out.stdout.strip() or "unknown")
                return False, ""
            except Exception:
                return False, ""
        # Fallback: consider 'not in VM' if tool isn't present
        return False, ""

    def read_json_multiline_from_tty(self) -> ManagerConfig:
        print("****************************")
        print("Please provide the JSON configuration produced by ZaaS Manager:")
        print("(paste it here, then press Ctrl-D)")
        print("****************************")

        # Read until EOF (Ctrl-D)
        with open("/dev/tty", "rb", buffering=0) as tty:
            data = tty.read()  # bytes
        try:
            return ManagerConfig.model_validate_json(data.decode("utf-8"))
        except json.JSONDecodeError as e:
            self.logger.fail(f"Invalid JSON provided: {e}")
        except Exception as e:
            self.logger.fail(f"Failed to read from TTY: {e}")
        exit(1)

    def press_enter_to_continue(self):

        try:
            input("Press [Enter] when you are done. ")
        except Exception as e:
            self.logger.fail(f"Failed to read from TTY: {e}")

    def load_json_file(self, path: str) -> ManagerConfig | None:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return ManagerConfig.model_validate_json(f.read())
        except FileNotFoundError:
            return None
        except json.JSONDecodeError as e:
            self.logger.fail(f"Config file {path} is not valid JSON: {e}")
        except Exception as e:
            self.logger.fail(f"Cannot read config file {path}: {e}")

    def atomic_write_json(self, path: str, payload: ManagerConfig, mode: int = 0o600):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", delete=False, dir=os.path.dirname(path)
        ) as tmp:
            tmp.write(payload.model_dump_json())
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp_name = tmp.name
        os.chmod(tmp_name, mode)
        os.replace(tmp_name, path)

    def run(self):

        if not self.is_root():
            print("This script must be run as root", file=sys.stderr)
            sys.exit(1)

        # Logging file perms ensured by first write
        self.logger.log_json("Starting ZaaS bootstrap (python)")

        # Ensure config dir
        os.makedirs(config.CONFIG_DIR, exist_ok=True)
        os.chmod(config.CONFIG_DIR, 0o700)

        # VM detection
        in_vm, hypervisor = self.detect_vm()
        if in_vm:
            self.logger.log_json(f"We detected that we are running in a VM ({hypervisor}).")
        else:
            self.logger.log_json("Not running in a VM")

        # Load existing config
        existing = self.load_json_file(str(Path(config.CONFIG_DIR) / Path(config.CONFIG_FILE)))

        # If we have a client-secret in the configuration file, the proxy has already been configured
        if existing and existing.sso.client_secret:
            self.logger.log_json("Proxy has already been configured.")
            return

        # Check if we already have a UUID. If not, generate one
        if Path(config.CONFIG_DIR, config.UUID_FILE).is_file():
            with open(Path(config.CONFIG_DIR) / Path(config.UUID_FILE), "r", encoding="utf-8") as f:
                uuid = uuid_mod.UUID(f.read().strip())
                self.logger.log_json(f"Found existing UUID: {uuid}")
        else:
            uuid = uuid_mod.uuid4()
            self.logger.log_json(f"Generated new UUID: {uuid}")
            with open(Path(config.CONFIG_DIR) / Path(config.UUID_FILE), "w", encoding="utf-8") as f:
                f.write(str(uuid))

        # Check if we already have a token
        if not existing or not existing.sso.token:

            # Manual step when in VM: show UUID, wait Enter, then read Manager JSON
            if in_vm:
                print("****************************")
                print("Please register the following UUID in ZaaS Manager:")
                print(uuid)
                print("****************************")
                self.press_enter_to_continue()

            # Acquire Manager JSON
            manager_cfg = self.read_json_multiline_from_tty()

            # Write Manager JSON
            self.atomic_write_json(str(Path(config.CONFIG_DIR) / Path(config.CONFIG_FILE)), manager_cfg)
            self.logger.log_json(f"Saved ZaaS Manager configuration to: {config.CONFIG_FILE}")

        # Post-read logging of key fields
        final = self.load_json_file(str(Path(config.CONFIG_DIR) / Path(config.CONFIG_FILE)))
        if not final:
            self.logger.fail(f"Failed to load configuration file: {config.CONFIG_FILE}")
            exit(1)

        # Query SSO provider for token
        try:
            response = requests.get(
                final.sso.provider_url
                + final.sso.registration_path
                + "/"
                + final.sso.client_id,
                headers={"Authorization": f"Bearer {final.sso.token}"},
            )
            response.raise_for_status()
        except Exception as e:
            self.logger.fail(f"Failed to contact SSO provider: {e}")
            exit(1)

        # Extract client-secret from response
        client_secret = response.json().get("secret")
        if not client_secret:
            self.logger.fail("Missing client_secret in SSO provider response.")

        # Remove token from config and add client-secret
        final.sso.token = None
        final.sso.client_secret = client_secret
        self.atomic_write_json(str(Path(config.CONFIG_DIR) / Path(config.CONFIG_FILE)), final)
        self.logger.log_json(f"Updated configuration file: {config.CONFIG_FILE}")
