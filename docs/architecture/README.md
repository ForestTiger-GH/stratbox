# Engineering Product Architecture — Strategy Box

**Status:** `PA-SB-2026-10-09-CANDIDATE-1`, bounded cross-repository responsibility-allocation candidate. The independent architecture role is warranted by distinct implementation owners; a physical service, repository split and distributed guarantees require their own Product Decisions.

- [System context and boundaries](system-context.md).
- [Responsibility allocation](responsibility-allocation.md).
- [Dependency direction and failure semantics](dependency-direction.md).
- [Application authority and portability placement options](application-authority-placement.md) — explicit `stratbox-application` logical hypothesis, competing locations, pilots and decision gates.

Architecture determines which implementation role owns product meaning, interfaces and failure authority. Target HOW owns executable mechanisms, operational recovery and correct use. These documents intentionally do not establish parallel wire protocols. The current `stratbox` domain core and `stratbox-windows` Windows implementation remain independent owners, while AppDock remains an external managed-platform owner.

**Important:** documenting a candidate does not create a package, service, remote host, Android/Web release, adopted API or new AppDock manifest. Confirmed current behavior belongs to Current HOW, and Product Decisions belong to their actual authority.
