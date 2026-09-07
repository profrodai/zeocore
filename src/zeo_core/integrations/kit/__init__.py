"""Kit newsletters and marketing automation through API v4."""

from .client import KitClient
from .models import (
    Audience,
    BroadcastDraft,
    Exclusion,
    Page,
    PageRequest,
    Record,
    SendBroadcast,
    SequenceDraft,
    SequenceEmailDraft,
    SourceFilter,
    SubscriberCreate,
    broadcast_send_digest,
    record_digest,
)
from .service import KitIntegration, create_integration
from .transport import KitAPIError, KitTransport

__all__ = [
    "Audience",
    "BroadcastDraft",
    "Exclusion",
    "KitAPIError",
    "KitClient",
    "KitIntegration",
    "KitTransport",
    "Page",
    "PageRequest",
    "Record",
    "SendBroadcast",
    "SequenceDraft",
    "SequenceEmailDraft",
    "SourceFilter",
    "SubscriberCreate",
    "broadcast_send_digest",
    "create_integration",
    "record_digest",
]
