"""CLI for running campaigns autonomously.

Exit codes: 0 success, 1 campaign failed, 2 could not initialize or execute.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from .engine import Campaign, Harness


def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point."""
    # GENERATED doctor intercept (gen_aw_doctor.py) -- do not edit
    _dv = locals().get("argv")
    if (_dv if _dv is not None else __import__("sys").argv[1:])[:1] == ["doctor"]:
        from ._doctor import report
        return report()
    # Check for --self-test before parsing (needs no other args)
    test_argv = argv if argv is not None else sys.argv[1:]
    if "--self-test" in test_argv:
        return self_test()

    ap = argparse.ArgumentParser(
        prog="gobbonet-agentic",
        description="Run one GobboNet campaign where the harness keeps the notes.",
    )
    ap.add_argument(
        "--name",
        required=True,
        help="Campaign name",
    )
    ap.add_argument(
        "--endpoint",
        default=None,
        help="External service endpoint (optional; None means offline mode)",
    )
    ap.add_argument(
        "--notes-dir",
        default=".",
        help="Directory where notes are written (default: current directory)",
    )
    ap.add_argument(
        "--steps",
        nargs="*",
        default=[],
        help="Step names to execute in order",
    )
    ap.add_argument(
        "--json",
        action="store_true",
        help="Output result as JSON",
    )

    args = ap.parse_args(argv)

    # Validate campaign name
    if not args.name or not args.name.strip():
        print("ERROR: campaign name is required", file=sys.stderr)
        return 2

    # Initialize harness
    try:
        harness = Harness(notes_dir=args.notes_dir)
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    # Create campaign
    try:
        campaign = Campaign(
            name=args.name,
            endpoint=args.endpoint,
            harness=harness,
            steps=args.steps,
        )
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    # Run campaign
    try:
        result = campaign.run()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    # Output result
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(f"Campaign: {result.name}")
        print(f"Status: {'SUCCESS' if result.success else 'FAILED'}")
        print(f"Notes: {result.notes_path}")
        print(f"Steps: {len(result.steps)}")
        if result.errors:
            print(f"Errors: {len(result.errors)}")
            for error in result.errors:
                print(f"  - {error}")

    return 0 if result.success else 1


def self_test() -> int:
    """Run self-tests to verify the brick works.

    Tests:
    1. Harness can be created and write notes
    2. Campaign can be instantiated with valid config
    3. Campaign can run and record notes
    4. Notes file is created and contains valid JSON
    5. Offline mode works without endpoint
    6. Campaign with no steps completes

    Returns 0 if all tests pass, 1 if any test fails.
    """
    tests_passed = 0
    tests_failed = 0

    # Test 1: Harness creation and notes directory
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            harness = Harness(notes_dir=tmpdir)
            assert Path(tmpdir).exists()
            tests_passed += 1
            print("[PASS] Harness can be created and manages notes directory")
    except Exception as e:
        tests_failed += 1
        print(f"[FAIL] Harness creation failed: {e}")

    # Test 2: Campaign instantiation
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            harness = Harness(notes_dir=tmpdir)
            campaign = Campaign(
                name="test_campaign",
                endpoint="http://localhost:8080",
                harness=harness,
            )
            assert campaign.name == "test_campaign"
            assert campaign.endpoint == "http://localhost:8080"
            tests_passed += 1
            print("[PASS] Campaign can be instantiated with valid config")
    except Exception as e:
        tests_failed += 1
        print(f"[FAIL] Campaign instantiation failed: {e}")

    # Test 3: Campaign runs successfully
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            harness = Harness(notes_dir=tmpdir)
            campaign = Campaign(
                name="test_run",
                harness=harness,
                steps=["step1", "step2"],
            )
            result = campaign.run()
            assert result.success is True, f"Expected success, got {result.success}"
            assert result.notes_path.exists()
            tests_passed += 1
            print("[PASS] Campaign can run and record notes")
    except Exception as e:
        tests_failed += 1
        print(f"[FAIL] Campaign execution failed: {e}")

    # Test 4: Notes file contains valid JSON
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            harness = Harness(notes_dir=tmpdir)
            campaign = Campaign(
                name="json_test",
                harness=harness,
            )
            result = campaign.run()
            with open(result.notes_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert isinstance(data, list)
            assert len(data) > 0
            tests_passed += 1
            print("[PASS] Notes file contains valid JSON")
    except Exception as e:
        tests_failed += 1
        print(f"[FAIL] Notes JSON validation failed: {e}")

    # Test 5: Offline mode without endpoint
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            harness = Harness(notes_dir=tmpdir)
            campaign = Campaign(
                name="offline_test",
                endpoint=None,
                harness=harness,
            )
            result = campaign.run()
            assert result.success is True
            tests_passed += 1
            print("[PASS] Offline mode works without endpoint")
    except Exception as e:
        tests_failed += 1
        print(f"[FAIL] Offline mode failed: {e}")

    # Test 6: Campaign with no steps completes
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            harness = Harness(notes_dir=tmpdir)
            campaign = Campaign(
                name="no_steps_test",
                harness=harness,
                steps=[],
            )
            result = campaign.run()
            assert result.success is True
            assert len(result.steps) == 0
            tests_passed += 1
            print("[PASS] Campaign with no steps completes successfully")
    except Exception as e:
        tests_failed += 1
        print(f"[FAIL] No-steps campaign failed: {e}")

    # Summary
    print(f"\nSelf-test results: {tests_passed} passed, {tests_failed} failed")
    return 0 if tests_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
