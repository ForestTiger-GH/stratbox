# Windows application — bounded component Target WHAT

**Implementation owner:** `ForestTiger-GH/stratbox-windows`. **Admission:** separate application ownership `BOUNDARY_ACCEPTED`; proposed shared-node execution capabilities and future client APIs `CANDIDATE`.

**User purpose:** provide approachable interaction with workspaces, domain operation catalogs, scenarios, execution cases, progress and diagnostics, results, artifacts and authorized follow-on actions. Concrete observed behavior and current omissions belong to [the pinned Windows Current HOW](../../current-how/windows-application.md).

**Observed baseline:** Qt desktop presentation, managed activation context, scenario/chat/inspector structures, locally persisted JSON history and a bounded sequential execution coordinator. UI labels such as 'Background', 'Assignments' or 'Participants' do **not** themselves prove a durable job scheduler, network collaboration or real server-side permissions.

**Target candidates:** share typed semantic definitions for forms, operations, scenario projections and meaningful status with future clients; prevent the UI from reporting success before an authoritative Run/Effect has been verified; maintain clear diagnostics and source/result visibility; assign durable shared execution truth to a real active application owner rather than an isolated Qt window; keep user settings minimal and behaviorally meaningful.

**Separation from core and other clients:** the Windows client may keep its native presentation toolkit while portable application semantics remain reusable by Web and prospective Android clients. A specific backend API, durable schema, device capability matrix, scheduling policy and host-mode lifecycle require separate Product and implementation admission.

The Windows owner cannot guarantee remote-host background execution, cross-device synchronization or release-quality recovery simply by displaying corresponding navigation elements.
