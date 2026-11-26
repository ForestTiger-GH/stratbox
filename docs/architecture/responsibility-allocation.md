# Runtime and source responsibility

The standard layer defines what a command means, which values it consumes and produces, and how commands compose into operations, scenarios and cascades. Domain specifications supply publisher knowledge. The core supplies transport, decoding, calculation mechanisms, resource scheduling, storage, journal facts and notification delivery.

Applications own UI, schedules, deployment, credentials and destination configuration. They submit the same prepared plan through the SDK. Optional providers implement neutral contracts and are selected independently of source identity.

A successful computation, accepted output, confirmed write and channel delivery are different facts. Runtime contracts preserve each distinction through composition and recovery.
