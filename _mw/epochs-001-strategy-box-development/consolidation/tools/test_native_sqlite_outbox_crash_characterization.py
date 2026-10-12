#!/usr/bin/env python3
"""SQLite crash/transaction *characterization*, not Strategy Box host code.

Uses real disposable SQLite files and child-process os._exit crash windows.
This verifies one local SQLite profile could satisfy several Run+dispatch
outbox invariants. It does NOT select SQLite for the actual product, certify
OS power-fail durability, implement a host, or establish security/Job effects.
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

CHILD = r'''
import os, sqlite3, sys
database, mode = sys.argv[1:]
conn = sqlite3.connect(database)
conn.execute("PRAGMA synchronous=FULL")
conn.execute("PRAGMA busy_timeout=2000")
conn.execute("BEGIN IMMEDIATE")
if mode in ("precommit_exit", "commit_exit"):
    conn.execute("INSERT INTO runs VALUES (?, ?, ?)",
                 ("intent-crash", "digest-A", "run-1"))
    conn.execute("INSERT INTO outbox(dispatch_ref, run_ref, status) VALUES (?, ?, ?)",
                 ("dispatch-run-1", "run-1", "pending"))
    if mode == "commit_exit":
        conn.commit()
        os._exit(17)  # after SQL commit, before caller reply
    os._exit(18)      # before commit, force transaction rollback on restart
if mode == "job_commit_exit":
    conn.execute("INSERT OR IGNORE INTO jobs(dispatch_ref, run_ref) VALUES (?, ?)",
                 ("dispatch-run-1", "run-1"))
    conn.commit()
    os._exit(19)      # after job reservation, before scheduler ACK
raise RuntimeError("unsupported crash window")
'''


def database(path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(str(path), timeout=2, isolation_level=None)
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=FULL")
    con.execute("CREATE TABLE IF NOT EXISTS runs("
                "intention_key TEXT PRIMARY KEY, digest TEXT NOT NULL, "
                "run_ref TEXT NOT NULL UNIQUE)")
    con.execute("CREATE TABLE IF NOT EXISTS outbox("
                "dispatch_ref TEXT PRIMARY KEY, run_ref TEXT NOT NULL UNIQUE, "
                "status TEXT NOT NULL CHECK(status IN "
                "('pending','unknown','dispatched')), fence INTEGER NOT NULL DEFAULT 0, "
                "FOREIGN KEY(run_ref) REFERENCES runs(run_ref))")
    con.execute("CREATE TABLE IF NOT EXISTS jobs("
                "dispatch_ref TEXT PRIMARY KEY, run_ref TEXT NOT NULL UNIQUE)")
    return con


def child_crash(path: Path, mode: str, expected_return: int) -> None:
    result = subprocess.run([sys.executable, "-c", CHILD, str(path), mode],
                            check=False, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=8)
    assert result.returncode == expected_return, (
        mode, result.returncode, result.stderr.decode("utf-8", "replace"))


def claim(con: sqlite3.Connection):
    con.execute("BEGIN IMMEDIATE")
    row = con.execute(
        "SELECT dispatch_ref, run_ref, fence FROM outbox "
        "WHERE status IN ('pending', 'unknown') ORDER BY dispatch_ref LIMIT 1"
    ).fetchone()
    if row is None:
        con.commit()
        return None
    dispatch_ref, run_ref, old = row
    generation = old + 1
    cursor = con.execute(
        "UPDATE outbox SET fence=?, status='unknown' "
        "WHERE dispatch_ref=? AND fence=?", (generation, dispatch_ref, old))
    assert cursor.rowcount == 1
    con.commit()
    return dispatch_ref, run_ref, generation


def reserve_job(con: sqlite3.Connection, dispatch_ref: str, run_ref: str):
    con.execute("BEGIN IMMEDIATE")
    con.execute("INSERT OR IGNORE INTO jobs(dispatch_ref, run_ref) VALUES (?, ?)",
                (dispatch_ref, run_ref))
    result = con.execute(
        "SELECT run_ref FROM jobs WHERE dispatch_ref=?", (dispatch_ref,)
    ).fetchone()
    if result != (run_ref,):
        con.rollback()
        raise ValueError("same dispatch identity assigned another Run")
    con.commit()


def acknowledge(con: sqlite3.Connection, dispatch_ref: str, generation: int) -> bool:
    con.execute("BEGIN IMMEDIATE")
    changed = con.execute(
        "UPDATE outbox SET status='dispatched' "
        "WHERE dispatch_ref=? AND fence=? AND status='unknown'",
        (dispatch_ref, generation)).rowcount
    con.commit()
    return changed == 1


def main() -> dict:
    counts = {}
    with tempfile.TemporaryDirectory(prefix="strategy-box-outbox-posix-sqlite-") as tmp:
        root = Path(tmp)
        p = root / "host-candidate.sqlite"
        con = database(p)
        con.close()

        child_crash(p, "precommit_exit", 18)
        with database(p) as con:
            assert con.execute("SELECT count(*) FROM runs").fetchone() == (0,)
            assert con.execute("SELECT count(*) FROM outbox").fetchone() == (0,)
        counts["crash_precommit_rolls_back_run_and_dispatch"] = True

        child_crash(p, "commit_exit", 17)
        with database(p) as con:
            assert con.execute("SELECT intention_key,run_ref FROM runs").fetchone() == (
                "intent-crash", "run-1")
            assert con.execute("SELECT dispatch_ref,run_ref FROM outbox").fetchone() == (
                "dispatch-run-1", "run-1")
        counts["crash_postcommit_keeps_run_and_outbox"] = True

        with database(p) as con:
            try:
                con.execute("BEGIN IMMEDIATE")
                con.execute("INSERT INTO runs VALUES(?, ?, ?)",
                            ("intent-conflict", "digest-B", "run-orphan"))
                # Deliberately force unique outbox collision.
                con.execute(
                    "INSERT INTO outbox(dispatch_ref,run_ref,status) VALUES(?,?,?)",
                    ("dispatch-run-1", "run-orphan", "pending"))
            except sqlite3.IntegrityError:
                con.rollback()
            else:
                raise AssertionError("outbox collision unexpectedly admitted Run")
            assert con.execute(
                "SELECT count(*) FROM runs WHERE run_ref='run-orphan'"
            ).fetchone() == (0,)
        counts["outbox_collision_rolls_back_run"] = True

        with database(p) as con:
            first = claim(con)
            assert first == ("dispatch-run-1", "run-1", 1)
        counts["pending_outbox_can_be_reclaimed_after_caller_crash"] = True

        child_crash(p, "job_commit_exit", 19)
        with database(p) as con:
            assert con.execute("SELECT count(*) FROM jobs").fetchone() == (1,)
            reserve_job(con, "dispatch-run-1", "run-1")
            assert con.execute("SELECT count(*) FROM jobs").fetchone() == (1,)
        counts["job_reservation_postcommit_replay_is_one"] = True

        with database(p) as con:
            second = claim(con)
            assert second == ("dispatch-run-1", "run-1", 2)
            assert acknowledge(con, "dispatch-run-1", 1) is False
            assert acknowledge(con, "dispatch-run-1", 2) is True
            assert claim(con) is None
            assert con.execute("SELECT count(*) FROM jobs").fetchone() == (1,)
        counts["stale_generation_cannot_ack_reclaimed_dispatch"] = True

        with database(p) as con:
            try:
                reserve_job(con, "dispatch-run-1", "other-run")
            except ValueError:
                pass
            else:
                raise AssertionError("mismatched Run reused dispatch key")
            assert con.execute(
                "SELECT run_ref FROM jobs WHERE dispatch_ref='dispatch-run-1'"
            ).fetchone() == ("run-1",)
        counts["same_dispatch_cannot_silently_bind_other_run"] = True

        with database(p) as con:
            try:
                con.execute(
                    "INSERT INTO runs VALUES (?, ?, ?)",
                    ("intent-crash", "digest-changed", "run-new"))
            except sqlite3.IntegrityError:
                pass
            else:
                raise AssertionError("duplicate intention created a new Run")
            assert con.execute("SELECT count(*) FROM runs").fetchone() == (1,)
        counts["duplicate_intention_cannot_create_second_run"] = True

    assert len(counts) == 8 and all(counts.values())
    return {
        "status": "SQLITE_PROCESS_EXIT_OUTBOX_PROBE_PASS",
        "synthetic_native_sqlite_cases": len(counts),
        "cases": counts,
        "evidence": "sqlite3 real disposable WAL/FULL transactions and subprocess os._exit; generic example only",
        "explicit_limits": [
            "no Strategy Box installed host, ledger or scheduler used",
            "no real bank data or real external file mutation",
            "no power-loss, network filesystem, SQLite deployment policy or platform choice",
            "no actual multi-worker lease timeout, authentication or effect permission",
            "no independent product acceptance or original-source semantic verification",
        ],
    }


if __name__ == "__main__":
    print(json.dumps(main(), ensure_ascii=False, sort_keys=True))
