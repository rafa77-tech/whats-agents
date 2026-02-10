#!/bin/bash
set -euo pipefail

# ─── Configuração ───────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_BLOCK="$SCRIPT_DIR/CLAUDE-SKILLS-BLOCK.md"
MARKER="# Skills Auto-Activation"

# ─── Cores ──────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

ok()   { echo -e "${GREEN}[ok]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
fail() { echo -e "${RED}[erro]${NC} $1"; exit 1; }

# ─── Uso ────────────────────────────────────────────────────────
usage() {
  echo "Uso: $(basename "$0") [caminho-do-projeto]"
  echo ""
  echo "  Sem argumento: usa o diretorio atual"
  echo "  Com argumento:  usa o caminho informado"
  echo ""
  echo "O que faz:"
  echo "  1. Cria symlink .claude/skills/ → coleção central de skills"
  echo "  2. Adiciona bloco de auto-ativação ao CLAUDE.md do projeto"
  exit 0
}

[[ "${1:-}" == "-h" || "${1:-}" == "--help" ]] && usage

# ─── Resolver caminho do projeto ────────────────────────────────
PROJECT_DIR="${1:-.}"
PROJECT_DIR="$(cd "$PROJECT_DIR" && pwd)"

echo ""
echo "Projeto: $PROJECT_DIR"
echo "Skills:  $SCRIPT_DIR"
echo ""

# ─── Validações ─────────────────────────────────────────────────
[[ ! -d "$PROJECT_DIR" ]] && fail "Diretorio nao encontrado: $PROJECT_DIR"
[[ ! -f "$SKILLS_BLOCK" ]] && fail "CLAUDE-SKILLS-BLOCK.md nao encontrado em $SCRIPT_DIR"

# ─── 1. Symlink das skills ──────────────────────────────────────
CLAUDE_DIR="$PROJECT_DIR/.claude"
SKILLS_LINK="$CLAUDE_DIR/skills"

mkdir -p "$CLAUDE_DIR"

if [[ -L "$SKILLS_LINK" ]]; then
  CURRENT_TARGET="$(readlink "$SKILLS_LINK")"
  if [[ "$CURRENT_TARGET" == "$SCRIPT_DIR" ]]; then
    ok "Symlink ja existe e aponta para o lugar certo"
  else
    warn "Symlink existe mas aponta para: $CURRENT_TARGET"
    read -rp "    Atualizar para $SCRIPT_DIR? [s/N] " answer
    if [[ "$answer" =~ ^[sS]$ ]]; then
      rm "$SKILLS_LINK"
      ln -s "$SCRIPT_DIR" "$SKILLS_LINK"
      ok "Symlink atualizado"
    else
      warn "Symlink mantido como estava"
    fi
  fi
elif [[ -d "$SKILLS_LINK" ]]; then
  warn "Pasta .claude/skills/ ja existe (nao e symlink)"
  read -rp "    Substituir por symlink para $SCRIPT_DIR? [s/N] " answer
  if [[ "$answer" =~ ^[sS]$ ]]; then
    rm -rf "$SKILLS_LINK"
    ln -s "$SCRIPT_DIR" "$SKILLS_LINK"
    ok "Pasta substituida por symlink"
  else
    warn "Pasta mantida como estava"
  fi
else
  ln -s "$SCRIPT_DIR" "$SKILLS_LINK"
  ok "Symlink criado: .claude/skills/ → $SCRIPT_DIR"
fi

# ─── 2. Bloco de ativação no CLAUDE.md ──────────────────────────
CLAUDE_MD="$PROJECT_DIR/CLAUDE.md"

if [[ -f "$CLAUDE_MD" ]] && grep -qF "$MARKER" "$CLAUDE_MD"; then
  ok "Bloco de auto-ativação ja existe no CLAUDE.md"
else
  if [[ -f "$CLAUDE_MD" ]]; then
    echo "" >> "$CLAUDE_MD"
  fi
  cat "$SKILLS_BLOCK" >> "$CLAUDE_MD"
  ok "Bloco de auto-ativação adicionado ao CLAUDE.md"
fi

# ─── Resultado ──────────────────────────────────────────────────
echo ""
echo -e "${GREEN}Pronto!${NC} Skills disponíveis em $PROJECT_DIR"
echo ""
echo "Skills instaladas:"
for skill_dir in "$SCRIPT_DIR"/*/; do
  skill_name="$(basename "$skill_dir")"
  [[ -f "$skill_dir/SKILL.md" ]] && echo "  - $skill_name"
done
echo ""
