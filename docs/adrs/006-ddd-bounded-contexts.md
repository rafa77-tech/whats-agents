# ADR-006: Formalizar Bounded Contexts do Domínio Júlia

- Status: Proposta
- Data: 2026-02-21
- Sprint: Backlog Arquitetural (DDD)
- Decisores: Equipe de Engenharia

## Contexto

O sistema evoluiu rápido e já contém múltiplos domínios relevantes (conversa, policy, campanhas, vagas, handoff, eventos). Hoje esses contextos existem na prática, mas não estão formalizados como contrato arquitetural.

Efeitos observados:

- Fronteiras implícitas e não governadas
- Sobreposição de responsabilidades entre módulos
- Aumento de acoplamento entre camadas e contextos
- Maior risco de regressão semântica ao evoluir regras

Referências:

- `app/main.py:105`
- `app/services/policy/types.py:91`
- `app/services/campanhas/types.py:78`
- `app/services/vagas/service.py:26`

## Decisão

Formalizar oficialmente os seguintes bounded contexts e seus owners:

1. `ConversaMedica`
2. `PolicyContato`
3. `CampanhasOutbound`
4. `VagasAlocacao`
5. `HandoffSupervisao`
6. `BusinessEventsAuditoria`

Para cada contexto, manter documentação mínima obrigatória:

- Responsabilidade
- Modelo principal (entidades/VOs)
- API interna exposta
- Eventos consumidos/publicados
- Dependências permitidas

Criar e manter um **Context Map** versionado em documentação de arquitetura.

## Alternativas Consideradas

1. **Manter estado atual (fronteiras implícitas)**
   - Pros: zero custo imediato
   - Cons: acelera erosão arquitetural e custo de manutenção

2. **Refatoração grande única para domínio completo**
   - Pros: convergência rápida
   - Cons: alto risco operacional e parada de roadmap

3. **Formalização incremental por contexto (decisão escolhida)**
   - Pros: menor risco, ganho progressivo, compatível com operação contínua
   - Cons: período de transição com arquitetura híbrida

## Consequências

### Positivas

- Clareza de fronteiras e ownership
- Menor acoplamento entre domínios
- Base para evolução de produto com menos regressões
- Melhor rastreabilidade de decisões de negócio por contexto

### Negativas

- Custo inicial de documentação e alinhamento
- Necessidade de disciplina em revisão de PR

### Mitigações

- Definir checklist arquitetural por PR com validação de contexto
- Migrar contexto a contexto, sem big-bang
- Registrar desvios temporários com prazo

## Referências

- `docs/auditorias/relatorio-ddd-2026-02-21.md`
- `docs/arquitetura/visao-geral.md`
