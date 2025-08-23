#!/usr/bin/env python3

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid as uuid_mod
import requests

from pydantic import BaseModel, Field
from typing import Optional


LOGFILE = "/var/log/zaas-bootstrap.log"
CONFIG_DIR = "/etc/zaas"
CONFIG_FILE = os.path.join(CONFIG_DIR, "zaas.json")
UUID_FILE = os.path.join(CONFIG_DIR, "uuid")


class ManagerConfig(BaseModel):

    manager_url: str = Field(...)
    uuid: uuid_mod.UUID = Field(...)
    hostname: str = Field(...)

    class SSOConfig(BaseModel):
        provider_url: str = Field(...)
        registration_path: str = Field(...)
        client_id: str = Field(...)
        token: Optional[str] = Field(None)
        client_secret: Optional[str] = Field(None)

    sso: SSOConfig = Field(...)


def is_root() -> bool:
    return os.geteuid() == 0


def log_json(message: str):
    os.makedirs(os.path.dirname(LOGFILE), exist_ok=True)
    fd = os.open(LOGFILE, os.O_WRONLY | os.O_CREAT, 0o600)
    with os.fdopen(fd, "a", buffering=1) as f:
        rec = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "message": message,
        }
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(message)


def fail(msg: str, code: int = 1):
    log_json(f"ERROR: {msg}")
    sys.exit(code)


def detect_vm() -> tuple[bool, str]:
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


def read_json_multiline_from_tty() -> ManagerConfig:
    print("****************************")
    print("Please provide the JSON configuration produced by ZaaS Manager:")
    print("(paste it here, then press Ctrl-D)")
    print("****************************")

    # Read until EOF (Ctrl-D)
    with open("/dev/tty", "rb", buffering=0) as tty:
        data = tty.read()  # bytes
    try:
        return ManagerConfig.model_validate(data.decode("utf-8"))
    except json.JSONDecodeError as e:
        fail(f"Invalid JSON provided: {e}")
    except Exception as e:
        fail(f"Failed to read from TTY: {e}")
    exit(1)


def press_enter_to_continue():

    try:
        input("Press [Enter] when you are done. ")
    except Exception as e:
        fail(f"Failed to read from TTY: {e}")


def load_json_file(path: str) -> ManagerConfig | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return ManagerConfig.model_validate(f.read())
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as e:
        fail(f"Config file {path} is not valid JSON: {e}")
    except Exception as e:
        fail(f"Cannot read config file {path}: {e}")


def atomic_write_json(path: str, payload: dict, mode: int = 0o600):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", delete=False, dir=os.path.dirname(path)
    ) as tmp:
        json.dump(payload, tmp, ensure_ascii=False, indent=2)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_name = tmp.name
    os.chmod(tmp_name, mode)
    os.replace(tmp_name, path)


def register_proxy_with_manager(config: ManagerConfig):
    pass


def main():
    if not is_root():
        print("This script must be run as root", file=sys.stderr)
        sys.exit(1)

    # Logging file perms ensured by first write
    log_json("Starting ZaaS bootstrap (python)")

    # Ensure config dir
    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.chmod(CONFIG_DIR, 0o700)

    # VM detection
    in_vm, hypervisor = detect_vm()
    if in_vm:
        log_json(f"We detected that we are running in a VM ({hypervisor}).")
    else:
        log_json("Not running in a VM")

    # Load existing config
    existing = load_json_file(CONFIG_FILE)

    # If we have a client-secret in the configuration file, the proxy has already been configured
    if existing and existing.sso.client_secret:
        log_json("Proxy has already been configured.")
        return

    # Check if we already have a UUID. If not, generate one
    if os.path.exists(UUID_FILE):
        with open(UUID_FILE, "r", encoding="utf-8") as f:
            uuid = uuid_mod.UUID(f.read().strip())
            log_json(f"Found existing UUID: {uuid}")
    else:
        uuid = uuid_mod.uuid4()
        log_json(f"Generated new UUID: {uuid}")
        with open(UUID_FILE, "w", encoding="utf-8") as f:
            f.write(str(uuid))

    # Check if we already have a token
    if not existing or not existing.sso.token:

        # Manual step when in VM: show UUID, wait Enter, then read Manager JSON
        if in_vm:
            print("****************************")
            print("Please register the following UUID in ZaaS Manager:")
            print(uuid)
            print("****************************")
            press_enter_to_continue()

        # Acquire Manager JSON
        manager_cfg = read_json_multiline_from_tty()

        # Write Manager JSON
        atomic_write_json(CONFIG_FILE, manager_cfg.model_dump())
        log_json(f"Saved ZaaS Manager configuration to: {CONFIG_FILE}")

    # Post-read logging of key fields
    final = load_json_file(CONFIG_FILE)
    if not final:
        fail(f"Failed to load configuration file: {CONFIG_FILE}")
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
        fail(f"Failed to contact SSO provider: {e}")
        exit(1)

    # Extract client-secret from response
    client_secret = response.json().get("secret")
    if not client_secret:
        fail("Missing client_secret in SSO provider response.")

    # Remove token from config and add client-secret
    final.sso.token = None
    final.sso.client_secret = client_secret
    atomic_write_json(CONFIG_FILE, final.model_dump())
    log_json(f"Updated configuration file: {CONFIG_FILE}")

    # Register the proxy with the manager
    register_proxy_with_manager(final)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        fail("Interrupted by user", code=130)
