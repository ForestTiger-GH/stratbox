"""Offline, reproducible Stratbox release regression and distribution check.

Run using each desired Python interpreter (3.10, 3.11, 3.12). Nothing in this
script starts GitHub Actions or performs a network fetch. Dependencies (pytest,
build, optional dataframe and format engines) must be installed beforehand.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def _run(label: str, args: list[str], report: dict, *, cwd: Path = ROOT) -> None:
    process = subprocess.run(args, cwd=cwd, check=False)
    report["steps"].append({
        "name": label, "command": args, "exit_code": process.returncode,
        "result": "passed" if process.returncode == 0 else "failed",
    })
    if process.returncode:
        raise RuntimeError(f"{label} failed with exit code {process.returncode}")


def _git_sha() -> str | None:
    try:
        process = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"], cwd=ROOT,
            capture_output=True, text=True, check=True,
        )
        return process.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def check(*, report_path: Path, full_pytest: bool = True) -> dict:
    interpreter = sys.executable
    report: dict = {
        "schema": "stratbox.local_release_check.v1",
        "sha": _git_sha(),
        "python": sys.version,
        "interpreter": interpreter,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "steps": [],
        "result": "incomplete",
    }
    try:
        _run("release_paths", [interpreter, "-B", "scripts/check_release_integrity.py"], report)
        _run("owner_imports", [interpreter, "-B", "scripts/check_internal_imports.py"], report)
        _run("reference_editions", [
            interpreter, "-B", "scripts/reference_editions.py", "verify",
            "--reference", "all",
        ], report)
        _run("shared_tests", [
            interpreter, "-B", "-m", "pytest", "-q", "tests/unit/shared",
            "tests/cbr_sors_restoration/test_identity_provenance.py",
        ], report)
        if full_pytest:
            _run("complete_pytest", [interpreter, "-B", "-m", "pytest", "-q"], report)
        with tempfile.TemporaryDirectory(prefix="stratbox-release-") as temporary:
            root = Path(temporary)
            dist = root / "dist"
            _run("build_distributions", [
                interpreter, "-B", "-m", "build", "--no-isolation",
                "--sdist", "--wheel", "--outdir", str(dist),
            ], report)
            wheels = list(dist.glob("stratbox-*.whl"))
            source_dist = list(dist.glob("stratbox-*.tar.gz"))
            if len(wheels) != 1 or len(source_dist) != 1:
                raise RuntimeError("Expected one wheel and one source distribution")
            for name, archive in (("wheel_assets", wheels[0]), ("sdist_assets", source_dist[0])):
                _run(name, [
                    interpreter, "-B", "scripts/inspect_reference_wheel.py", str(archive),
                ], report)
            installed = root / "installed"
            _run("isolated_wheel_install", [
                interpreter, "-B", "-m", "pip", "install", "--no-deps",
                "--disable-pip-version-check", "--target", str(installed), str(wheels[0]),
            ], report)
            check_code = (
                "import importlib.metadata, sys; "
                "sys.path.insert(0, sys.argv[1]); "
                "import stratbox; "
                "from stratbox.shared.identity import ByteIdentity; "
                "from stratbox.shared.evidence import SourcePayload; "
                "from stratbox.shared.reference.assets import load_reference; "
                "from stratbox.shared.reference.geography import RegionNameResolver; "
                "assert stratbox.__version__ == importlib.metadata.version('stratbox'); "
                "assert RegionNameResolver().resolve('Москва').subject.id == 'RU-MOW'; "
                "[load_reference('stratbox.shared.reference.' + family).validate_all() "
                "for family in ('banks', 'okved2', 'geography')]"
            )
            _run("isolated_base_imports", [
                interpreter, "-I", "-S", "-B", "-c", check_code, str(installed),
            ], report)
        report["result"] = "passed" if full_pytest else "partial"
    except (RuntimeError, OSError) as error:
        report["result"] = "failed"
        report["error"] = str(error)
        raise
    finally:
        report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
        print(f"Release check report: {report_path}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path,
                        default=Path(tempfile.gettempdir()) / "stratbox-shared-release-check.json")
    parser.add_argument("--skip-full-pytest", action="store_true",
                        help="Diagnostic only: full acceptance requires complete pytest")
    args = parser.parse_args()
    try:
        check(report_path=args.report, full_pytest=not args.skip_full_pytest)
        return 0
    except (RuntimeError, OSError) as error:
        print(f"LOCAL RELEASE CHECK FAILED: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
