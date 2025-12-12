# Sprint 10: Refatoracao e Divida Tecnica

## Visao Geral

Sprint dedicada a **pagar a divida tecnica** acumulada nas sprints 0-9. O codebase cresceu organicamente de 0 para 100 arquivos Python, 46 services e 11k+ linhas. Agora precisa de consolidacao antes de continuar evoluindo.

**Objetivo:** Reduzir redundancia, padronizar padroes e quebrar arquivos monoliticos para melhorar manutenibilidade.

## Problema Atual

### Metricas de Saude do Codigo

| Metrica | Atual | Meta |
|---------|-------|------|
| Max linhas/arquivo | 1196 | < 500 |
| Max linhas/funcao | 100+ | < 50 |
| Padroes Supabase | 2 coexistem | 1 |
| Nomes inconsistentes | 5 areas | 0 |
| Formatacao duplicada | 4 arquivos | 1 |

### Problemas Identificados

1. **Redundancia de Codigo**
   - Funcoes de formatacao duplicadas em 4 arquivos
   - Queries Supabase repetidas sem helpers
   - 2 padroes de acesso ao banco coexistindo

2. **Arquivos Monoliticos**
   - `slack_tools.py`: 1196 linhas, 14 tools
   - `jobs.py`: 623 linhas, 14 endpoints
   - `agente_slack.py`: 572 linhas, classe monolitica

3. **Inconsistencias**
   - Nomes de funcoes: `get_*` vs `obter_*` vs `buscar_*`
   - Tratamento de erro: 3 padroes diferentes
   - Configuracoes espalhadas em services

## Principios da Refatoracao

1. **Nao quebrar funcionalidade existente** - Todos os testes devem passar
2. **Mudancas incrementais** - Uma story por vez, commit pequeno
3. **Backward compatible** - Deprecar antes de remover
4. **Testes primeiro** - Garantir cobertura antes de refatorar

## Epics

| Epic | Titulo | Stories | Prioridade |
|------|--------|---------|------------|
| E01 | Padronizacao Supabase | 4 | P0 - Critica |
| E02 | Consolidacao Slack | 3 | P1 - Alta |
| E03 | Quebra de Arquivos Grandes | 4 | P1 - Alta |
| E04 | Padronizacao de Nomes e Erros | 3 | P2 - Media |

## Metricas de Sucesso

| Metrica | Meta |
|---------|------|
| Testes passando | 100% |
| Max linhas/arquivo | < 500 |
| Max linhas/funcao | < 50 |
| Padroes Supabase | 1 unico |
| Cobertura de testes | > 80% |

## Riscos

| Risco | Probabilidade | Impacto | Mitigacao |
|-------|--------------|---------|-----------|
| Quebrar funcionalidade | Media | Alto | Rodar testes a cada commit |
| Introducao de bugs | Media | Medio | Code review obrigatorio |
| Demora excessiva | Baixa | Medio | Timeboxar cada story |
| Conflitos de merge | Baixa | Baixo | Branches curtas, merge frequente |

## Dependencias

- Nenhuma externa
- Sprint 9 concluida
- Ambiente de testes funcionando

## Criterios de Aceite da Sprint

- [ ] Todos os 443 testes passando
- [ ] Nenhum arquivo > 500 linhas em services/
- [ ] Padrao unico de acesso ao Supabase
- [ ] Funcoes de formatacao centralizadas
- [ ] Configuracoes em core/config.py
- [ ] Nomes de funcoes padronizados
- [ ] Tratamento de erro consistente
