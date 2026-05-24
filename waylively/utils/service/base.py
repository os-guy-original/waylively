from abc import ABC, abstractmethod


class BaseServiceManager(ABC):
    """Abstract base class for service managers."""

    @classmethod
    @abstractmethod
    def is_available(cls) -> bool:
        """Check if this service manager is available on the system."""
        pass

    @abstractmethod
    def generate_service_file(self) -> bool:
        """Generate and write the service file."""
        pass

    @abstractmethod
    def is_enabled(self) -> bool:
        """Check if the service is enabled to start on boot."""
        pass

    @abstractmethod
    def is_active(self) -> bool:
        """Check if the service is currently running."""
        pass

    @abstractmethod
    def start(self) -> bool:
        """Start the service."""
        pass

    @abstractmethod
    def stop(self) -> bool:
        """Stop the service."""
        pass

    @abstractmethod
    def enable(self) -> bool:
        """Enable and start the service."""
        pass

    @abstractmethod
    def disable(self) -> bool:
        """Disable and stop the service."""
        pass

    @abstractmethod
    def restart(self) -> bool:
        """Restart the service."""
        pass
