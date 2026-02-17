#!/usr/bin/env python3
"""
Check coverage by module for Tier 1 critical modules.

Sprint 62: Ensures critical modules maintain minimum coverage thresholds.
Run after: uv run pytest --cov=app --cov-report=json -q

Usage:
    uv run pytest --cov=app --cov-report=json -q
    python3 scripts/check-coverage-by-module.py
"""

import json
import sys
from pathlib import Path

# Tier 1 thresholds: modules where bugs = irreversible damage
TIER1_THRESHOLDS: dict[str, float] = {
    "app/services/rate_limiter.py": 85.0,
    "app/services/rate_limit.py": 80.0,
    "app/services/chips/circuit_breaker.py": 90.0,
    "app/services/handoff/flow.py": 70.0,
    "app/services/handoff/repository.py": 70.0,
    "app/services/business_events/kpis.py": 70.0,
    "app/services/business_events/audit.py": 70.0,
    "app/tools/vagas/reservar_plantao.py": 75.0,
}


def get_file_coverage(data: dict, filepath: str) -> float | None:
    """Extract coverage percentage for a specific file from coverage.json."""
    file_data = data.get("files", {}).get(filepath)
    if file_data is None:
        return None
    summary = file_data.get("summary", {})
    return summary.get("percent_covered", 0.0)


def get_directory_coverage(data: dict, dir_prefix: str) -> float | None:
    """Calculate average coverage for files in a directory."""
    files = data.get("files", {})
    total_stmts = 0
    covered_stmts = 0

    for filepath, file_data in files.items():
        if filepath.startswith(dir_prefix):
            summary = file_data.get("summary", {})
            total_stmts += summary.get("num_statements", 0)
            covered_stmts += summary.get("covered_lines", 0)

    if total_stmts == 0:
        return None

    return (covered_stmts / total_stmts) * 100


def main() -> int:
    coverage_file = Path("coverage.json")
    if not coverage_file.exists():
        print("ERROR: coverage.json not found. Run pytest with --cov-report=json first.")
        return 1

    with open(coverage_file) as f:
        data = json.load(f)

    failures: list[str] = []
    passes: list[str] = []

    print("\n=== Tier 1 Module Coverage Check ===\n")

    for module, threshold in TIER1_THRESHOLDS.items():
        if module.endswith("/"):
            coverage = get_directory_coverage(data, module)
        else:
            coverage = get_file_coverage(data, module)

        if coverage is None:
            print(f"  SKIP  {module} (not found in coverage report)")
            continue

        status = "PASS" if coverage >= threshold else "FAIL"
        symbol = "ok" if status == "PASS" else "FAIL"
        line = f"  {symbol}  {module}: {coverage:.1f}% (threshold: {threshold}%)"

        if status == "FAIL":
            failures.append(line)
        else:
            passes.append(line)

        print(line)

    print()

    if failures:
        print(f"FAILED: {len(failures)} module(s) below threshold")
        return 1

    print(f"PASSED: All {len(passes)} checked module(s) above threshold")
    return 0


if __name__ == "__main__":
    sys.exit(main())
