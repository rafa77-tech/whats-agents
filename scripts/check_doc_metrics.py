#!/usr/bin/env python3
"""
Documentation Freshness Check

Verifies that documented metrics in CLAUDE.md match actual codebase metrics.
Warns if drift exceeds 10%.

Exit codes:
  0 - All metrics OK (drift <= 10%)
  1 - Drift detected (drift > 10%)
"""

import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple


def get_project_root() -> Path:
    """Get absolute path to project root."""
    return Path(__file__).parent.parent.absolute()


def count_python_files() -> int:
    """Count Python files in app/ directory."""
    root = get_project_root()
    app_dir = root / "app"
    if not app_dir.exists():
        return 0
    return len(list(app_dir.rglob("*.py")))


def count_service_modules() -> int:
    """Count Python files in app/services/ directory."""
    root = get_project_root()
    services_dir = root / "app" / "services"
    if not services_dir.exists():
        return 0
    return len(list(services_dir.rglob("*.py")))


def count_router_files() -> int:
    """Count Python files in app/api/routes/ directory."""
    root = get_project_root()
    routes_dir = root / "app" / "api" / "routes"
    if not routes_dir.exists():
        return 0
    return len(list(routes_dir.rglob("*.py")))


def count_test_functions() -> int:
    """Count test functions in tests/ directory."""
    root = get_project_root()
    tests_dir = root / "tests"
    if not tests_dir.exists():
        return 0

    count = 0
    for test_file in tests_dir.rglob("test_*.py"):
        with open(test_file, "r", encoding="utf-8") as f:
            content = f.read()
            count += len(re.findall(r"^\s*def test_", content, re.MULTILINE))

    return count


def count_tables_in_schema() -> int:
    """Count CREATE TABLE statements in bootstrap/01-schema.sql."""
    root = get_project_root()
    schema_file = root / "bootstrap" / "01-schema.sql"
    if not schema_file.exists():
        return 0

    with open(schema_file, "r", encoding="utf-8") as f:
        content = f.read()
        return len(re.findall(r"^CREATE TABLE", content, re.MULTILINE))


def count_docs_markdown() -> int:
    """Count markdown files in docs/ directory."""
    root = get_project_root()
    docs_dir = root / "docs"
    if not docs_dir.exists():
        return 0
    return len(list(docs_dir.rglob("*.md")))


def count_planning_docs() -> int:
    """Count markdown files in planning/ directory."""
    root = get_project_root()
    planning_dir = root / "planning"
    if not planning_dir.exists():
        return 0
    return len(list(planning_dir.rglob("*.md")))


def parse_documented_metrics() -> Dict[str, int]:
    """Parse documented metrics from CLAUDE.md."""
    root = get_project_root()
    claude_md = root / "CLAUDE.md"

    if not claude_md.exists():
        print(f"ERROR: CLAUDE.md not found at {claude_md}")
        sys.exit(1)

    with open(claude_md, "r", encoding="utf-8") as f:
        content = f.read()

    metrics = {}

    # Find the metrics table (lines between "### Métricas do Projeto" and next ###)
    metrics_section = re.search(
        r"### Métricas do Projeto.*?\n\n(.*?)(?=\n###|\n---|\Z)",
        content,
        re.DOTALL
    )

    if not metrics_section:
        print("ERROR: Could not find 'Métricas do Projeto' section in CLAUDE.md")
        sys.exit(1)

    section_text = metrics_section.group(1)

    # Parse table rows (format: | Arquivos Python | ~386 | ... |)
    patterns = {
        "python_files": r"\|\s*Arquivos Python\s*\|\s*~?(\d+)",
        "service_modules": r"\|\s*Módulos de serviço\s*\|\s*~?(\d+)",
        "routers": r"\|\s*Routers API\s*\|\s*~?(\d+)",
        "tests": r"\|\s*Testes\s*\|\s*~?(\d+)",
        "tables": r"\|\s*Tabelas no banco\s*\|\s*~?(\d+)",
        "docs_markdown": r"\|\s*Docs Markdown\s*\|\s*~?(\d+)",
        "planning_docs": r"\|\s*Planning Docs\s*\|\s*~?(\d+)",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, section_text)
        if match:
            metrics[key] = int(match.group(1))
        else:
            print(f"WARNING: Could not find metric '{key}' in CLAUDE.md")

    return metrics


def calculate_drift(documented: int, actual: int) -> Tuple[float, str]:
    """
    Calculate drift percentage and status.

    Returns:
        (drift_percent, status_emoji)
    """
    if documented == 0:
        return 0.0, "⚠️"

    drift = ((actual - documented) / documented) * 100

    if abs(drift) <= 10:
        return drift, "✅"
    else:
        return drift, "❌"


def main():
    """Main entry point."""
    print("Documentation Freshness Check")
    print("=" * 70)
    print()

    # Get documented metrics
    documented = parse_documented_metrics()

    # Get actual metrics
    actual = {
        "python_files": count_python_files(),
        "service_modules": count_service_modules(),
        "routers": count_router_files(),
        "tests": count_test_functions(),
        "tables": count_tables_in_schema(),
        "docs_markdown": count_docs_markdown(),
        "planning_docs": count_planning_docs(),
    }

    # Metric labels
    labels = {
        "python_files": "Python files (app/)",
        "service_modules": "Service modules",
        "routers": "API routers",
        "tests": "Test functions",
        "tables": "Database tables",
        "docs_markdown": "Docs markdown",
        "planning_docs": "Planning docs",
    }

    # Print header
    print(f"{'Metric':<25} | {'Documented':>11} | {'Actual':>11} | {'Drift':>10} | Status")
    print("-" * 70)

    # Track overall status
    has_drift = False

    # Print each metric
    for key in labels:
        doc_val = documented.get(key, 0)
        act_val = actual.get(key, 0)
        drift_pct, status = calculate_drift(doc_val, act_val)

        label = labels[key]
        drift_str = f"{drift_pct:+.1f}%" if doc_val > 0 else "N/A"

        print(f"{label:<25} | {doc_val:>11} | {act_val:>11} | {drift_str:>10} | {status}")

        if status == "❌":
            has_drift = True

    print("-" * 70)
    print()

    if has_drift:
        print("❌ DRIFT DETECTED (>10%) - Please update CLAUDE.md metrics")
        print()
        print("To update:")
        print("  1. Edit CLAUDE.md")
        print("  2. Update the 'Métricas do Projeto' table with actual values")
        print("  3. Update 'Última Atualização' date")
        print()
        sys.exit(1)
    else:
        print("✅ All metrics OK (drift <= 10%)")
        print()
        sys.exit(0)


if __name__ == "__main__":
    main()
