# Sprint 63 — Pipeline Grupos: Bug Fixes & Refatoracao

## Status: 📋 Planejada

**Inicio:** 2026-02-19
**Estimativa:** 1.5 semanas

## Objetivo

Corrigir dois bugs de producao que causam 0% de importacao de vagas (cache LLM retornando datas de 2023 + normalizacao falhando para hospitais abreviados) e consolidar refatoracoes estruturais identificadas na auditoria arquitetural.

**Origem:** Analise de pipeline (2026-02-19) — dashboard mostra 53 mensagens → 7 vagas extraidas → 0 importadas. Todas descartadas por "data no passado" ou "hospital_id ausente".

---

## Diagnostico

| Metrica | Valor Atual | Meta |
|---------|-------------|------|
| Vagas importadas (ultimo ciclo) | 0 de 7 | >80% |
| Bug cache LLM datas | Ativo (retorna 2023) | Corrigido |
| Bug normalizacao hospital | Ativo (nao match "H.") | Corrigido |
| Codigo morto (extrator v1) | 638 linhas | 0 |
| Funcoes batch orfas | ~250 linhas | 0 |
| God function hospital_web | 212 linhas, 7 responsabilidades | <50 linhas por funcao |
| marcar_como_descartado bypass | Nao sincroniza mensagens_grupo | Corrigido |

### Causas raiz (0 importacoes)

1. **Cache LLM ignora data_referencia** — `extrator_llm.py:266` gera chave de cache `CACHE_PREFIX + hash(texto)` sem incluir data. Mesma mensagem processada em datas diferentes retorna vagas com data 2023.
2. **Normalizacao strip parenteses** — `normalizador.py:42` remove `(IVA)` de "H. BENEDICTO MONTENEGRO (IVA)", produzindo "h benedicto montenegro" que nao bate com alias "hospital benedicto montenegro".
3. **Cascata**: hospital_id null → especialidade_id null (normalizacao nao roda) → validacao rejeita tudo.

---

## Epicos

| # | Epico | Prioridade | Foco | Dependencias |
|---|-------|-----------|------|--------------|
| 01 | Fix Cache LLM + Datas | P0 (Critico) | Bug de producao: cache retornando datas erradas | Nenhuma |
| 02 | Fix Normalizacao Hospital | P0 (Critico) | Bug de producao: hospitais abreviados nao encontrados | Nenhuma |
| 03 | Cleanup Codigo Morto | P1 (Alto) | Remover extrator v1 e funcoes batch orfas | Nenhuma |
| 04 | Fix marcar_como_descartado | P1 (Alto) | Bypass de atualizar_estagio | Nenhuma |
| 05 | Refatorar pipeline_worker | P2 (Medio) | Extrair helpers, remover duplicacao v1/v2/v3 | Epic 03 |
| 06 | Refatorar hospital_web | P2 (Medio) | Quebrar god function em funcoes menores | Epic 02 |
| 07 | Constantes e Enums | P3 (Baixo) | Magic numbers, string literals, feature flags | Epics 03-06 |

---

## Criterios de Sucesso

- [ ] Vagas com datas corretas apos reprocessamento (bug cache corrigido)
- [ ] Hospital "H. BENEDICTO MONTENEGRO (IVA)" encontrado na normalizacao
- [ ] Zero codigo morto do extrator v1 no repositorio
- [ ] marcar_como_descartado usa atualizar_estagio
- [ ] pipeline_worker.py com helper compartilhado para extracao
- [ ] hospital_web.py sem funcao >60 linhas
- [ ] Todos os testes passando
- [ ] Cobertura proporcional ao risco (P0: >90%, P1: >80%, P2: >70%)

---

## Riscos

| Risco | Impacto | Mitigacao |
|-------|---------|-----------|
| Invalidar cache LLM existente | Vagas reprocessadas com custo LLM | Migrar chave gradualmente, TTL de 24h expira naturalmente |
| Alias de hospital incompletos | Outros hospitais tambem falham | Adicionar alias "h." como padrao de expansao |
| Remover extrator v1 quebra fallback | Pipeline para se v2 e v3 falharem | Verificar que v2 tem fallback proprio |
| Refatorar hospital_web muda comportamento | Normalizacao produz resultados diferentes | Testes de regressao com dados reais |

## Dependencias

| Epico | Depende de | Status |
|-------|-----------|--------|
| Epic 05 | Epic 03 (remover v1 antes de refatorar) | Pendente |
| Epic 06 | Epic 02 (fix normalizacao antes de refatorar) | Pendente |
| Epic 07 | Epics 03-06 (constantes apos refatoracao) | Pendente |
