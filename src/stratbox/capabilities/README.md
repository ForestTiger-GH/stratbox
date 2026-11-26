# Standard action language

This package owns commands, operations, scenarios and cascades. A command declares
an action's ports, acceptance, resource demands, providers, effects and reuse
policy. The other callable kinds compose these actions into purposeful graphs.

Use the [model](model/) when authoring contracts, the [catalog](catalog/) to
resolve standard definitions and domain records, and [preparation](preparation/)
to bind methods and select the required graph closure. The resulting
[plan](plan/) retains logical acceptance scopes alongside executable work.

The [route](route/) defines processing roles and legal transitions. Publisher
facts and scientific methods come from [domains](../domains/); the
[execution service](../core/execution/) runs an already prepared plan.

See [composition](../../../docs/current-how/executable-composition.md) and
[capability execution](../../../docs/architecture/capability-execution.md).
