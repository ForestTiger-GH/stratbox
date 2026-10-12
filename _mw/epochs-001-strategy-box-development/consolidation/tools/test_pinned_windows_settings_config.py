#!/usr/bin/env python3
"""Execute pinned stratbox-windows config code against temporary synthetic files.

This characterizes CURRENT behavior; it does not qualify target Settings LCD,
authorize product implementation, or claim installed-platform behavior.
Requires PYTHONPATH=windows-pinned/src and the exact checkout in CI.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from stratbox_windows.runtime.config import (
    AppUserConfig, load_user_config, save_user_config,
)
from stratbox_windows.runtime.errors import AppConfigError


def assert_raises(cls, fn):
    try:
        fn()
    except cls:
        return
    raise AssertionError(f"Expected {cls.__name__}")


def main() -> dict[str, object]:
    assertions = []
    with tempfile.TemporaryDirectory(prefix="sb-config-observed-") as d:
        root = Path(d)

        # 1. A new config load has a write side effect, even during reading.
        p = root / "absent" / "app.json"
        cfg = load_user_config(p)
        assert p.is_file() and cfg.window.width == 1440
        assertions.append("missing file creates config on load")

        # 2. Syntactically invalid JSON raises typed AppConfigError.
        p.write_text("{ broken", encoding="utf-8")
        assert_raises(AppConfigError, lambda: load_user_config(p))
        assertions.append("malformed JSON typed error")

        # 3. A syntactically correct JSON with invalid integer propagates a
        #    plain ValueError from _coerce_config rather than AppConfigError.
        p.write_text(json.dumps({"window": {"width": "not-an-int"}}), encoding="utf-8")
        assert_raises(ValueError, lambda: load_user_config(p))
        assertions.append("invalid numeric field leaks ValueError")

        # 4. Current coercion treats a nonempty string 'false' as bool True.
        p.write_text(json.dumps({"shell": {"right_inspector_open": "false"}}), encoding="utf-8")
        actual = load_user_config(p)
        assert actual.shell.right_inspector_open is True
        assertions.append("nonempty false string accepted as True")

        # 5. Current config allows nonsense physical geometry (no range check).
        p.write_text(json.dumps({"window": {"width": -7, "height": 0}}), encoding="utf-8")
        actual = load_user_config(p)
        assert actual.window.width == -7 and actual.window.height == 0
        assertions.append("nonpositive window geometry accepted")

        # 6. Current writer stores opaque scenario form values verbatim.
        p2 = root / "values.json"
        cfg = AppUserConfig()
        cfg.scenario_form_values["scenario.atomic.synthetic"] = {
            "example_sensitive_input": "TEST_SENTINEL_DO_NOT_USE_AS_SECRET"
        }
        save_user_config(p2, cfg)
        written = p2.read_text(encoding="utf-8")
        assert "TEST_SENTINEL_DO_NOT_USE_AS_SECRET" in written
        assertions.append("scenario form values persisted without field sensitivity filtering")

        # 7. A fake short write+exception inside the actual writer leaves a
        #    partially replaced file. This deliberately injects a fake
        #    Path.write_text failure: it proves lack of rollback in wrapper,
        #    NOT that a particular real filesystem fails this way.
        p3 = root / "write-failure.json"
        p3.write_text('{"old_value":"intact"}', encoding="utf-8")
        original = Path.write_text
        def partial_then_raise(self, text, *args, **kwargs):
            if self == p3:
                original(self, '{"truncated":', encoding="utf-8")
                raise OSError("simulated write interrupted")
            return original(self, text, *args, **kwargs)
        with patch.object(Path, "write_text", partial_then_raise):
            assert_raises(OSError, lambda: save_user_config(p3, AppUserConfig()))
        assert p3.read_text(encoding="utf-8") == '{"truncated":'
        assertions.append("injected partial writer destroys earlier config without recovery")

        # 8. Save has no schema_version and is ordinary direct JSON.
        p4 = root / "fresh.json"
        save_user_config(p4, AppUserConfig())
        raw = json.loads(p4.read_text(encoding="utf-8"))
        assert "schema_version" not in raw and "window" in raw and "scenario_form_values" in raw
        assertions.append("unversioned mixed UI/draft JSON current writer")

    return {
        "evidence": "exact checked-in pinned Windows config functions executed with synthetic temporary files",
        "observed_cases": len(assertions),
        "cases": assertions,
        "status": "BOUNDED_CURRENT_CODE_CHARACTERIZATION_PASS",
        "not_claimed": ["target implementation", "real user-data incident",
                        "native Windows filesystem crash durability", "independent release verification"],
    }


if __name__ == "__main__":
    print(json.dumps(main(), ensure_ascii=False, indent=2))
