# Public invocation facade

`StrategyBox` is the caller entry point. Use `discover()` and `describe()` for
standard callables, and `sources` for continuing source declarations.
`prepare()` selects and binds a graph without executing it; `run()` executes
that plan, while `invoke()` combines those steps.

`submit()` returns a handle for waiting, cancellation and status inspection.
Use a context manager for the box and close results when their library-owned
outputs are no longer needed. Supply provider implementations, execution
settings and a journal when constructing the box.

The facade delegates graph construction to [capabilities](../capabilities/)
and lifecycle management to [core execution](../core/execution/).
[Machine projection](machine.py) provides bounded descriptions for external clients.

See [calls, plans and result lifetime](../../../docs/current-how/capability-session.md).
