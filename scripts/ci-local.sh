#!/usr/bin/env bash
# ci-local.sh — Replica os gates do GitHub CI localmente.
# Uso: ./scripts/ci-local.sh
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

step() { echo -e "\n${YELLOW}▶ $1${NC}"; }
pass() { echo -e "${GREEN}✔ $1${NC}"; }
fail() { echo -e "${RED}✘ $1${NC}"; exit 1; }

step "Ruff linter (ruff check)"
uv run ruff check app/ && pass "Lint OK" || fail "Lint failed"

step "Ruff formatter (ruff format --check)"
uv run ruff format --check app/ && pass "Format OK" || fail "Format failed — run: uv run ruff format app/"

step "Pytest"
uv run pytest -v --tb=short "$@" && pass "Tests OK" || fail "Tests failed"

echo -e "\n${GREEN}═══ CI local passed ═══${NC}"
