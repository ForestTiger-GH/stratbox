"""Technical HTTP requests and explicit transport implementations."""

from stratbox.core.network.contracts import HttpFailure, HttpRequest, HttpResponse, HttpStreamResponse, HttpTransport, HttpsEndpoint, StreamingHttpTransport
from stratbox.core.network.transport import HttpsRoute, RequestsTransport, RetryPolicy, RoutedTransport, exchange, exchange_into
from stratbox.core.network.peer import PeerBoundTransport

from stratbox.core.network.shared import (AccessScope, AccessScopes, SharedClaim, SharedMaterial, SharedWorkRegistry, SessionNetwork, SharedHttpTransport, acquisition_key, request_identity, network_resources)
