# ADR-008: Linguagem Ubíqua e Estados Canônicos de Domínio

- Status: Proposta
- Data: 2026-02-21
- Sprint: Backlog Arquitetural (DDD)
- Decisores: Equipe de Engenharia + Produto

## Contexto

O código e os dados usam termos próximos com semânticas diferentes e mistura de idiomas em estados de domínio (`active`, `pending`, `concluida`, `opted_out`, etc.).

Também coexistem modelos paralelos de ciclo de vida:

- `stage_jornada`
- `lifecycle_stage`
- `status` em múltiplas entidades com significados distintos

Referências:

- `app/services/policy/types.py:59`
- `app/services/medico.py:42`
- `app/services/conversa.py:24`
- `app/services/campanhas/types.py:23`

## Decisão

Estabelecer um **vocabulário ubíquo oficial** e um **catálogo de estados canônicos** por contexto.

Entregáveis obrigatórios:

1. Dicionário de termos de domínio (negócio + engenharia)
2. Tabela de estados canônicos por entidade/contexto
3. Mapeamento de aliases/legados
4. Política de naming para novos campos/status (idioma, padrão e semântica)

Diretrizes:

- Evitar estados livres em string quando houver enum de domínio disponível.
- Novos fluxos usam nomes canônicos; legados entram em plano de convergência.
- Toda mudança de estado crítica deve citar contexto e significado.

## Alternativas Consideradas

1. **Não padronizar linguagem**
   - Pros: sem esforço curto prazo
   - Cons: aumenta ambiguidade e erros de interpretação

2. **Padronizar apenas documentação, sem refletir no código**
   - Pros: baixo custo
   - Cons: baixa efetividade prática

3. **Padronização documental + convergência incremental de código e dados (decisão escolhida)**
   - Pros: equilíbrio entre governança e viabilidade
   - Cons: transição parcial por um período

## Consequências

### Positivas

- Menos ambiguidade entre negócio e engenharia
- Decisões de policy/campanha/vaga mais previsíveis
- Melhora de onboarding e revisão de PR
- Base para testes orientados a regra de domínio

### Negativas

- Necessidade de migração gradual de termos/status legados
- Possível esforço de compatibilidade em integrações

### Mitigações

- Mapa de aliases compatível durante transição
- Migração por contexto com feature flag quando necessário
- Critérios de aceite exigindo uso de termos canônicos

## Referências

- `docs/auditorias/relatorio-ddd-2026-02-21.md`
- `docs/arquitetura/logica-negocio.md`
