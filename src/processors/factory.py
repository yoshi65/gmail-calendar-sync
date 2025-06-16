"""Email processor factory."""


from ..models.email_types import EmailMessage
from ..utils.config import Settings
from .base import BaseEmailProcessor
from .carshare_processor import CarShareEmailProcessor
from .flight_processor import FlightEmailProcessor


class EmailProcessorFactory:
    """Factory for creating email processors."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._processors: list[BaseEmailProcessor] = []
        self._initialize_processors()

    def _initialize_processors(self) -> None:
        """Initialize all available processors."""
        # Add flight processor
        self._processors.append(FlightEmailProcessor(self.settings))

        # Add car sharing processor
        self._processors.append(CarShareEmailProcessor(self.settings))

        # Future processors can be added here:
        # self._processors.append(RestaurantProcessor(self.settings))

    def get_processor(self, email: EmailMessage) -> BaseEmailProcessor | None:
        """Get appropriate processor for the given email."""
        for processor in self._processors:
            if processor.can_process(email):
                return processor

        return None

    def get_all_processors(self) -> list[BaseEmailProcessor]:
        """Get all available processors."""
        return self._processors.copy()
