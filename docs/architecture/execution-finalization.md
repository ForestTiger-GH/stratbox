# Output acceptance and execution completion

A named output becomes available only after its actual type, source context and semantic predicates pass. Composite output guards preserve additional result promises before downstream consumption. Required checks and effect obligations determine enclosing completion; a useful output does not prove that its whole scenario completed.

Terminal outcomes preserve failed, cancelled, partial and unknown work. An unconfirmed external mutation stays unknown until evidence reconciles it. Cancellation stops future admission and requests cooperative interruption; it does not undo confirmed writes.

`RunResult.close()` releases result ownership. A result that remains open counts against the service retention budget. Journal facts distinguish output acceptance, command completion, effect confirmation and run completion.
