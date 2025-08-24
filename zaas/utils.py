import json
import os
import subprocess
import shutil
import platform
import psutil


class ZaasUtils:

    @staticmethod
    def is_root() -> bool:
        return os.geteuid() == 0

    @staticmethod
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
    
    @staticmethod
    def get_system_info() -> dict:
        """Get system information."""
        return {
            "os": platform.system(),
            "os_version": platform.version(),
            "platform": platform.platform(),
            "hostname": platform.node(),
            "uptime": psutil.boot_time(),
        }

    @staticmethod
    def get_cpu_info() -> dict:
        """Get CPU information."""
        return {
            "cpu_count": psutil.cpu_count(logical=True),
            "cpu_cores": psutil.cpu_count(logical=False),
            "cpu_freq": {
                "min": psutil.cpu_freq().min,
                "max": psutil.cpu_freq().max,
            }
        }
        
    @staticmethod
    def get_memory_info() -> dict:
        """Get memory information."""
        vm = psutil.virtual_memory()
        return {
            "total": vm.total,
            "available": vm.available,
            "used": vm.used,
            "free": vm.free,
        }

    @staticmethod
    def get_swap_info() -> dict:
        """Get swap memory information."""
        swap = psutil.swap_memory()
        return {
            "total": swap.total,
            "used": swap.used,
            "free": swap.free,
            "percent": swap.percent,
        }
    
    @staticmethod
    def get_disk_info() -> dict:
        """Get disk information."""
        partitions = psutil.disk_partitions()
        disk_info = {}
        for partition in partitions:
            usage = psutil.disk_usage(partition.mountpoint)
            disk_info[partition.mountpoint] = {
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
                "percent": usage.percent,
            }
        return disk_info

    @staticmethod
    def get_io_info() -> dict:
        """Get I/O information."""
        disk_io = psutil.disk_io_counters()
        if not disk_io:
            return {}
        return {
            "read_count": disk_io.read_count,
            "write_count": disk_io.write_count,
            "read_bytes": disk_io.read_bytes,
            "write_bytes": disk_io.write_bytes,
        }

utils = ZaasUtils()
