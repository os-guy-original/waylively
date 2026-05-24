from waylively.utils.service import get_service_manager


_manager = None


def _get_manager():
    global _manager
    if _manager is None:
        _manager = get_service_manager()
    return _manager


def ensure_systemd_dir() -> bool:
    """Legacy compatibility - no longer needed for OpenRC."""
    manager = _get_manager()
    if hasattr(manager, '_ensure_dir'):
        return manager._ensure_dir()
    return True


def generate_service_file() -> bool:
    return _get_manager().generate_service_file()


def is_service_enabled() -> bool:
    return _get_manager().is_enabled()


def is_service_active() -> bool:
    return _get_manager().is_active()


def start_service() -> bool:
    return _get_manager().start()


def stop_service() -> bool:
    return _get_manager().stop()


def enable_service() -> bool:
    return _get_manager().enable()


def disable_service() -> bool:
    return _get_manager().disable()


def restart_service() -> bool:
    return _get_manager().restart()
