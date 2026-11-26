# HTTP transport

This package owns technical request contracts, allowed HTTPS endpoints, bounded
transfer, transport evidence and explicit transport implementations.
[Contracts](contracts.py) define the provider boundary; [transport](transport.py)
implements the common exchange mechanisms.

Standard material actions adapt a prepared request to the selected provider.
Publisher URLs and publication-selection rules come from domain specifications.
Credential and deployment configuration arrive through declared runtime roles.

See [network behavior](../../../../docs/current-how/core-runtime-network.md)
and [provider resolution](../runtime/).
