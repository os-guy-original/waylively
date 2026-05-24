from waylively.utils.service.base import BaseServiceManager
from waylively.utils.service.systemd import SystemdManager
from waylively.utils.service.openrc import OpenRCManager


def get_service_manager() -> BaseServiceManager:
    """Detect and return the appropriate service manager for the system."""
    if SystemdManager.is_available():
        return SystemdManager()
    if OpenRCManager.is_available():
        return OpenRCManager()
    raise RuntimeError("No supported service manager found (systemd or openrc required)")


__all__ = ["BaseServiceManager", "SystemdManager", "OpenRCManager", "get_service_manager"]
