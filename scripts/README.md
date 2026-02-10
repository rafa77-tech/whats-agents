# Scripts

Utility scripts for the Agente Julia project.

## Available Scripts

### check_doc_metrics.py

Documentation freshness checker that validates metrics documented in `CLAUDE.md` match actual codebase metrics.

**Usage:**

```bash
python3 scripts/check_doc_metrics.py
```

**Checks:**

- Python files in `app/` directory
- Service modules in `app/services/`
- API routers in `app/api/routes/`
- Test functions in `tests/`
- Database tables in `bootstrap/01-schema.sql`
- Markdown files in `docs/`
- Markdown files in `planning/`

**Exit codes:**

- `0` - All metrics OK (drift <= 10%)
- `1` - Drift detected (drift > 10%)

**CI Integration:**

This script runs automatically in the CI pipeline (`doc-freshness` job) on every push to `main` or `develop` branches.

**When drift is detected:**

1. Update the metrics in `CLAUDE.md` (section "Métricas do Projeto")
2. Update the "Última Atualização" date
3. Commit and push

**Example output:**

```
Documentation Freshness Check
======================================================================

Metric                    |  Documented |      Actual |      Drift | Status
----------------------------------------------------------------------
Python files (app/)       |         386 |         386 |      +0.0% | ✅
Service modules           |         267 |         267 |      +0.0% | ✅
API routers               |          28 |          28 |      +0.0% | ✅
Test functions            |        2662 |        1701 |     -36.1% | ❌
Database tables           |          64 |          64 |      +0.0% | ✅
Docs markdown             |          97 |         100 |      +3.1% | ✅
Planning docs             |         349 |         355 |      +1.7% | ✅
----------------------------------------------------------------------
```

## Adding New Scripts

When adding new scripts to this directory:

1. Add a shebang line: `#!/usr/bin/env python3`
2. Make it executable: `chmod +x scripts/your_script.py`
3. Add documentation to this README
4. Consider adding to CI pipeline if appropriate
