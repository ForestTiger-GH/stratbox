Strategy Box app refactor notes

Canonical app layers after this update:
- src/app/platform/...
- src/app/state/session_runtime.py
- src/app/product/catalog/...
- src/app/product/forms/...
- src/app/product/execution/...

Thin compatibility facades intentionally remain in place so existing imports inside the repository do not break during staged cleanup:
- src/app/integrations/...
- src/app/core/session_env.py
- src/app/product/models.py
- src/app/product/catalog.py
- src/app/product/composer.py
- src/app/product/registry.py
- src/app/product/runner.py

Standalone developer route now keeps app-owned storage under:
<dev-root>/.strategy_box/system/

