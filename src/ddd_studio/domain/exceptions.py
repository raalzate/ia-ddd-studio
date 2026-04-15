"""Domain exceptions for the agent pipeline."""


class ServiceUnavailableError(Exception):
    """Raised when a remote AI service is unreachable."""


class TranscriptionError(Exception):
    """Raised when audio transcription fails."""


class FileTooLargeError(Exception):
    """Raised when an audio file exceeds the remote service size limit."""


class ConfigurationError(Exception):
    """Raised when LLM settings (API Key, Model) are missing or invalid."""
