"""Errors raised by the enricher. User-facing messages are Spanish."""


class EnricherError(Exception):
    """Fatal error: the run must stop. The old Keep note is left in place."""


class ConfigError(EnricherError):
    """Missing or unusable configuration."""


class NoteNotFound(EnricherError):
    """The configured Keep note does not exist."""


class VerificationError(EnricherError):
    """The new note was created but its text does not match. The old note is kept."""


class LookupFailure(Exception):
    """One title could not be resolved. The rest of the run continues."""


class CheckpointError(LookupFailure):
    """Stream with VPN answered with a Vercel checkpoint or a block page."""
