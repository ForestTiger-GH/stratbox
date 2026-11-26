# Commands, operations, scenarios and cascades

A command performs one declared action. An operation composes reusable transformations. A scenario owns a purpose and its completion obligations. A cascade coordinates scenarios. Each kind can be discovered, prepared and invoked independently.

`GraphBody` declares calls, named output references, dependencies, conditions, bounded maps and bounded iteration. Domain targets specialize commands through direct static maps. Preparation validates references and semantic port compatibility before execution.

Temporary definitions use the same catalog overlay and preparation path; they create no second executor or mutable global registry. See [the standard execution model](../architecture/capability-execution.md).
