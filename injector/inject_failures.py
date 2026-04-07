#!/usr/bin/env python3
"""
Inject failure modes into the testbed repo, commit, push, restore.

Requires the testbed directory to be its own git clone with `origin` set.
Configure paths via TESTBED_PATH (default: ../testbed relative to repo root).
"""

from __future__ import annotations

import argparse
import os
import random
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = Path(__file__).resolve().parent / "failure_configs"
DEFAULT_TESTBED = ROOT / "testbed"

FAILURE_MODES = ["flaky_test", "dep_conflict", "missing_env", "assertion_error"]


def _testbed() -> Path:
    return Path(os.environ.get("TESTBED_PATH", DEFAULT_TESTBED)).resolve()


def _run_git(args: list[str], cwd: Path, check: bool = True) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=check)


def inject_flaky_test(tb: Path) -> None:
    shutil.copy(CONFIG_DIR / "flaky_test.py", tb / "tests" / "test_flaky.py")


def inject_dep_conflict(tb: Path) -> None:
    shutil.copy(CONFIG_DIR / "dep_conflict.txt", tb / "requirements.txt")


def inject_missing_env(tb: Path) -> None:
    main = tb / "app" / "main.py"
    text = main.read_text(encoding="utf-8")
    extra = '\nimport os\nSECRET = os.environ["MISSING_VAR"]\n'
    if "MISSING_VAR" not in text:
        main.write_text(text + extra, encoding="utf-8")


def inject_assertion_error(tb: Path) -> None:
    shutil.copy(CONFIG_DIR / "assertion_error.py", tb / "tests" / "test_assertions.py")


INJECTORS = {
    "flaky_test": inject_flaky_test,
    "dep_conflict": inject_dep_conflict,
    "missing_env": inject_missing_env,
    "assertion_error": inject_assertion_error,
}


def ensure_branch(tb: Path, branch: str) -> None:
    _run_git(["checkout", "main"], tb)
    try:
        subprocess.run(
            ["git", "rev-parse", "--verify", branch],
            cwd=tb,
            check=True,
            capture_output=True,
        )
        _run_git(["checkout", branch], tb)
    except subprocess.CalledProcessError:
        _run_git(["checkout", "-b", branch], tb)


def commit_and_push(tb: Path, message: str, branch: str) -> None:
    _run_git(["add", "."], tb)
    _run_git(["commit", "-m", message], tb)
    _run_git(["push", "-u", "origin", branch], tb)


def restore_clean_state(tb: Path, branch: str) -> None:
    _run_git(["checkout", "main", "--", "."], tb)
    _run_git(["add", "."], tb)
    _run_git(["commit", "-m", "restore: clean state"], tb)
    _run_git(["push", "origin", branch], tb)


def main() -> None:
    parser = argparse.ArgumentParser(description="Inject CI failure modes into testbed.")
    parser.add_argument(
        "--iterations",
        type=int,
        default=int(os.environ.get("INJECTION_COUNT", "75")),
        help="Number of inject/restore cycles (default 75).",
    )
    parser.add_argument(
        "--branch",
        default=os.environ.get("INJECTION_BRANCH", "failure-injection"),
        help="Branch to push (default failure-injection).",
    )
    parser.add_argument(
        "--sleep-after-push",
        type=float,
        default=30.0,
        help="Seconds to wait after push for Actions to start.",
    )
    parser.add_argument(
        "--sleep-after-restore",
        type=float,
        default=15.0,
        help="Seconds to wait after restore before next iteration.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for failure mode selection.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print chosen modes only; do not modify git.",
    )
    args = parser.parse_args()

    tb = _testbed()
    if not (tb / ".git").is_dir():
        print(f"ERROR: {tb} is not a git repository (missing .git).", file=sys.stderr)
        sys.exit(1)

    if args.seed is not None:
        random.seed(args.seed)

    if not args.dry_run:
        ensure_branch(tb, args.branch)

    for i in range(args.iterations):
        mode = random.choice(FAILURE_MODES)
        print(f"[{i + 1}/{args.iterations}] mode={mode}")
        if args.dry_run:
            continue
        INJECTORS[mode](tb)
        commit_and_push(tb, f"inject: {mode} failure mode", args.branch)
        print(f"Injected {mode} — waiting for CI run ({args.sleep_after_push}s)...")
        time.sleep(args.sleep_after_push)
        restore_clean_state(tb, args.branch)
        time.sleep(args.sleep_after_restore)


if __name__ == "__main__":
    main()
