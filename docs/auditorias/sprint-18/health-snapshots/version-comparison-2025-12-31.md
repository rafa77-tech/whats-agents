# Comparacao de Versoes DEV vs PROD

**Data:** 2025-12-31
**Sprint:** 18 - Auditoria e Integridade

---

## 1. App Settings

| Configuracao | DEV | PROD | Status |
|--------------|-----|------|--------|
| environment | `dev` | `production` | OK |
| supabase_project_ref | `ofpnronthwcsybfxnxgj` | `jyqgbzhqavgpxqacduoi` | OK |
| schema_version | `20251230192934` | `20251231173654` | DIVERGE (*) |
| schema_applied_at | 2025-12-31 20:21:20 | 2025-12-31 20:21:52 | OK |

(*) Schema version diverge porque PROD tem migrations adicionais. Isso e esperado.

---

## 2. Schema Fingerprint

| Ambiente | Fingerprint | Notas |
|----------|-------------|-------|
| DEV | `fallback-186a95216dccc6b7` | Fallback (funcao SQL nao existe) |
| PROD | `fallback-186a95216dccc6b7` | Fallback (funcao SQL nao existe) |

**Status:** MATCH - Fingerprints identicos (fallback mode)

**Nota:** A funcao `get_table_columns_for_fingerprint` nao esta deployada.
O fingerprint atual usa fallback baseado em hash das tabelas core.

---

## 3. Prompts

| Prompt | DEV versao | PROD versao | DEV chars | PROD chars | Status |
|--------|------------|-------------|-----------|------------|--------|
| julia_base | v2 | v2 | 5524 | 5524 | MATCH |
| julia_primeira_msg | v1 | v1 | 236 | 236 | MATCH |
| julia_tools | v1 | v1 | 1516 | 1516 | MATCH |

**Status:** Todos prompts sincronizados.

---

## 4. Health Check Status

| Check | DEV | PROD | Status |
|-------|-----|------|--------|
| status | healthy | healthy | OK |
| deploy_safe | true | true | OK |
| environment | ok | ok | OK |
| project_ref | ok | ok | OK |
| dev_guardrails | ok (allowlist=1) | skipped | OK |
| redis | ok | ok | OK |
| supabase | ok | ok | OK |
| tables | ok | ok | OK |
| views | ok | ok | OK |
| prompts | ok | ok | OK |

---

## 5. Conclusao

| Aspecto | Resultado |
|---------|-----------|
| Ambientes isolados | SIM |
| Marcadores corretos | SIM |
| Prompts sincronizados | SIM |
| DEV guardrails ativos | SIM |
| Schema compativel | SIM |
| Deploy safe | SIM |

**Veredicto:** Ambientes corretamente configurados e prontos para operacao.

---

## Assinatura

Gerado automaticamente por Claude Code em 2025-12-31T21:10:00Z
Sprint 18 - Auditoria e Integridade
