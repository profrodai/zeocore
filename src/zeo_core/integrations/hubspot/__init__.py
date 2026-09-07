"""HubSpot marketing automation without a general CRM integration."""

from .client import HubSpotClient
from .models import (
    Audience,
    CampaignProperties,
    EmailContent,
    EmailDraft,
    EmailSequence,
    MarketingPage,
    MarketingRecord,
    PageRequest,
    PublishRequest,
    SequenceStep,
    SubscriptionChange,
)
from .service import HubSpotIntegration, create_integration
from .transport import HubSpotAPIError, HubSpotTransport

__all__ = [
    "Audience",
    "CampaignProperties",
    "EmailContent",
    "EmailDraft",
    "EmailSequence",
    "HubSpotAPIError",
    "HubSpotClient",
    "HubSpotIntegration",
    "HubSpotTransport",
    "MarketingPage",
    "MarketingRecord",
    "PageRequest",
    "PublishRequest",
    "SequenceStep",
    "SubscriptionChange",
    "create_integration",
]
