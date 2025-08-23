#!/usr/bin/env python3

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid


LOGFILE = "/var/log/zaas-bootstrap.log"
CONFIG_DIR = "/etc/zaas"
CONFIG_FILE = os.path.join(CONFIG_DIR, "zaas.json")


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


def read_json_multiline_from_tty() -> dict:
    print("****************************")
    print("Please provide the JSON configuration produced by ZaaS Manager:")
    print("(paste it here, then press Ctrl-D)")
    print("****************************")

    # Read until EOF (Ctrl-D)
    with open("/dev/tty", "rb", buffering=0) as tty:
        data = tty.read()  # bytes
    try:
        return json.loads(data.decode("utf-8"))
    except json.JSONDecodeError as e:
        fail(f"Invalid JSON provided: {e}")


def press_enter_to_continue():

    try:
        input("Press [Enter] when you are done. ")
    except Exception as e:
        fail(f"Failed to read from TTY: {e}")


def load_json_file(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
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
    os.replace(tmp_name, path)  # atomic


def merge_preferring_manager(existing: dict, manager: dict) -> dict:
    """Keep existing serial if manager JSON doesn’t provide one; otherwise prefer manager."""
    merged = dict(existing)
    merged.update(manager or {})
    if "serial" not in (manager or {}) and "serial" in existing:
        merged["serial"] = existing["serial"]
    return merged


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

    # Ensure serial
    serial = existing.get("serial")
    if not serial:
        serial = str(uuid.uuid4())
        existing["serial"] = serial
        log_json(f"Generated new serial number: {serial}")
    else:
        log_json(f"Found existing serial number: {serial}")

    # Save (at least) the serial early
    atomic_write_json(CONFIG_FILE, {"serial": serial})
    log_json(f"Updated configuration file: {CONFIG_FILE}")

    # Manual step when in VM: show serial, wait Enter, then read Manager JSON
    if in_vm:
        print("****************************")
        print("Please register the following serial number in ZaaS Manager:")
        print(serial)
        print("****************************")
        press_enter_to_continue()

    # Acquire Manager JSON
    manager_cfg = read_json_multiline_from_tty()

    # Merge and save if we have Manager JSON
    if manager_cfg:
        merged = merge_preferring_manager(existing, manager_cfg)
        atomic_write_json(CONFIG_FILE, merged)
        log_json(f"Saved ZaaS Manager configuration to: {CONFIG_FILE}")
    else:
        log_json("No Manager JSON provided.")

    # Post-read logging of key fields
    final = load_json_file(CONFIG_FILE)
    for key in ["serial", "hostname", "sso_provider", "registration_url", "token"]:
        val = final.get(key)
        if val:
            log_json(f"Found {key} in the configuration file: {val}")
        else:
            log_json(f"No {key} found in the configuration file.")

    # TODO: Register the proxy to the SSO provider (HTTP call) if needed.

    log_json("Bootstrap finished successfully.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        fail("Interrupted by user", code=130)
