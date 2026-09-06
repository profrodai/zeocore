"""Supabase Database, Auth, Storage, Functions, and Realtime integration."""

from .auth import SupabaseAuthProvider, classify_key
from .client import SupabaseClient
from .config import SupabaseConfigProvider
from .errors import SupabaseAPIError
from .models import (
    SupabaseBucket,
    SupabaseFilter,
    SupabaseFilterOperator,
    SupabaseFunctionResult,
    SupabaseKeyKind,
    SupabaseOAuthStart,
    SupabaseOrder,
    SupabaseRealtimeChange,
    SupabaseRealtimeEvent,
    SupabaseRealtimeSubscription,
    SupabaseRowPage,
    SupabaseSessionStatus,
    SupabaseUser,
)
from .protocols import (
    SupabaseDatabaseProtocol,
    SupabaseFunctionsProtocol,
    SupabaseIntegrationProtocol,
    SupabaseRealtimeProtocol,
    SupabaseStorageProtocol,
    SupabaseUserAuthProtocol,
)
from .realtime import SupabaseRealtimeClient
from .service import SupabaseIntegration, create_integration

__all__ = [
    "SupabaseAPIError",
    "SupabaseAuthProvider",
    "SupabaseBucket",
    "SupabaseClient",
    "SupabaseConfigProvider",
    "SupabaseDatabaseProtocol",
    "SupabaseFilter",
    "SupabaseFilterOperator",
    "SupabaseFunctionResult",
    "SupabaseFunctionsProtocol",
    "SupabaseIntegration",
    "SupabaseIntegrationProtocol",
    "SupabaseKeyKind",
    "SupabaseOAuthStart",
    "SupabaseOrder",
    "SupabaseRealtimeChange",
    "SupabaseRealtimeClient",
    "SupabaseRealtimeEvent",
    "SupabaseRealtimeProtocol",
    "SupabaseRealtimeSubscription",
    "SupabaseRowPage",
    "SupabaseSessionStatus",
    "SupabaseStorageProtocol",
    "SupabaseUser",
    "SupabaseUserAuthProtocol",
    "classify_key",
    "create_integration",
]
