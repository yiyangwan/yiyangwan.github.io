"""HTTP access for the pipeline (completed in Task 2)."""
from .models import SourceError


class FetchError(SourceError):
    """A request failed; the message is short and safe to publish (for example, 'HTTP 403')."""
