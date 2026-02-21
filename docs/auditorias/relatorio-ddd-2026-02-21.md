# Relatório DDD (Domain-Driven Design) - Projeto Júlia

**Data:** 2026-02-21  
**Base conceitual:** Eric Evans, *Domain-Driven Design*  
**Escopo analisado:** backend (`app/`), arquitetura e rotas principais

## 1. Sumário executivo

O projeto já possui sinais fortes de modelagem de domínio em partes críticas (especialmente `policy`, `campanhas`, `vagas`, `handoff`), mas ainda opera com fronteiras de contexto parcialmente difusas e com acoplamento relevante entre API, regras de negócio e persistência.

Diagnóstico DDD (visão geral):

- **Maturidade estratégica (Bounded Context / Context Map):** média
- **Maturidade tática (Entidades, VOs, Agregados, Repositórios):** média-baixa
- **Linguagem ubíqua no código:** média (boa no domínio médico/comercial, inconsistente em nomes técnicos e status)
- **Risco principal:** erosão de fronteiras por acesso direto a `supabase.table(...)` em camadas de interface e serviços heterogêneos

## 2. Método de análise

Foram avaliados:

- Arquitetura e composição da app: `app/main.py:78`, `app/main.py:105`
- Pipeline inbound principal: `app/api/routes/webhook.py:14`, `app/api/routes/webhook.py:158`, `app/pipeline/processor.py:12`
- Núcleos de domínio explícitos:
  - Policy: `app/services/policy/types.py:15`, `app/services/policy/rules.py:27`, `app/services/policy/rules.py:363`
  - Campanhas: `app/services/campanhas/types.py:13`, `app/services/campanhas/repository.py:25`, `app/services/campanhas/executor.py:35`
  - Vagas: `app/services/vagas/service.py:26`, `app/services/vagas/service.py:104`
  - Handoff: `app/services/handoff/flow.py:31`, `app/services/external_handoff/repository.py:15`
  - Eventos de negócio: `app/services/business_events/types.py:12`, `app/services/business_events/repository.py:17`
- Pontos de acoplamento e “vazamento de contexto”:
  - `app/api/routes/campanhas.py:259`
  - `app/api/routes/group_entry.py:200`
  - `app/api/routes/policy.py:602`
  - `app/api/routes/incidents.py:61`

## 3. Domínio central e subdomínios

## 3.1 Core Domain (diferenciação competitiva)

1. **Orquestração conversacional de staffing médico**
- Conversão de contato frio para relacionamento ativo com médicos
- Personalização contextual + decisão de ação/tom
- Evidências: `app/services/agente/orchestrator.py:121`, `app/pipeline/core.py:29`

2. **Decisão de contato e segurança operacional (Policy/Guardrails)**
- Modelo explícito de estado do médico (`DoctorState`) e regras determinísticas
- Evidências: `app/services/policy/types.py:91`, `app/services/policy/rules.py:27`, `app/services/policy/rules.py:302`

3. **Oferta e fechamento de plantões**
- Busca compatível, reserva, conflitos e ciclo de vida da vaga
- Evidências: `app/services/vagas/service.py:26`, `app/services/vagas/service.py:104`, `app/services/vagas/service.py:188`

## 3.2 Supporting Subdomains

1. **Campanhas e segmentação**
- Seleção de audiência, dedupe, cooldown e enfileiramento
- Evidências: `app/services/campanhas/executor.py:38`, `app/services/segmentacao.py:63`

2. **Handoff interno/externo**
- Transferência IA->humano e confirmação externa de plantão
- Evidências: `app/services/handoff/flow.py:31`, `app/services/external_handoff/repository.py:15`

3. **Discovery e group-entry**
- Ingestão e validação de grupos para ampliar supply-side intelligence
- Evidências: `app/api/routes/group_entry.py:38`

## 3.3 Generic Subdomains

- Infra de mensageria/filas, observabilidade, incidentes, integrações (Slack, providers WhatsApp, Meta)
- Evidências: `app/services/fila.py:18`, `app/api/routes/incidents.py:61`

## 4. Bounded Contexts propostos (as-is mapeado)

## 4.1 Contexto: Conversa Médica

**Responsabilidade:** ciclo de interação com médico, estado da conversa, direção IA/humano.  
**Modelo dominante:** `medico/cliente`, `conversa`, `interacao`, `stage_jornada`.  
**Pontos de entrada:** webhook/pipeline.  
**Evidências:** `app/services/medico.py:97`, `app/services/conversa.py:75`, `app/pipeline/processors/entities.py:16`.

## 4.2 Contexto: Policy de Contato

**Responsabilidade:** decidir “pode/não pode”, “o que fazer”, “com qual tom”, com rastreabilidade.  
**Modelo dominante:** `DoctorState`, `PolicyDecision`, regras ordenadas.  
**Evidências:** `app/services/policy/types.py:91`, `app/services/policy/types.py:163`, `app/services/policy/rules.py:363`, `app/services/policy/repository.py:106`.

## 4.3 Contexto: Campanhas Outbound

**Responsabilidade:** criação, segmentação, execução e medição de campanhas.  
**Modelo dominante:** `CampanhaData`, `AudienceFilters`, status de campanha, touch history.  
**Evidências:** `app/services/campanhas/types.py:78`, `app/services/campanhas/repository.py:25`, `app/services/campanhas/executor.py:35`.

## 4.4 Contexto: Vagas e Alocação

**Responsabilidade:** disponibilidade, reserva, conflito, conclusão de plantão.  
**Modelo dominante:** `vaga`, `status`, `reserva`, `criticidade`.  
**Evidências:** `app/services/vagas/service.py:26`, `app/services/vagas/service.py:104`, `app/services/vagas/service.py:220`.

## 4.5 Contexto: Handoff e Supervisão

**Responsabilidade:** escalonamento para humano e confirmação operacional.  
**Modelo dominante:** `handoff`, `external_handoff`, estados de confirmação.  
**Evidências:** `app/services/handoff/flow.py:31`, `app/services/external_handoff/repository.py:15`.

## 4.6 Contexto: Auditoria/Eventos de Negócio

**Responsabilidade:** trilha de eventos para analytics, compliance e automações.  
**Modelo dominante:** `BusinessEvent`, `EventType`, dedupe por chave.  
**Evidências:** `app/services/business_events/types.py:12`, `app/services/business_events/repository.py:17`.

## 5. Context Map (relações atuais)

- **Conversa Médica** consome **Policy** para decisão (`orchestrator -> PolicyDecide`): `app/services/agente/orchestrator.py:217`
- **Conversa Médica** invoca **Vagas** e pode acionar **Handoff**
- **Campanhas** usa **Segmentação** e **Fila**, e afeta state conversacional por toques
- **Handoff** publica em **Business Events**
- **Policy** publica decisão/efeitos para auditoria de policy events

Leitura DDD: há um **núcleo forte em policy + conversa**, mas o mapa não está formalizado como contratos entre contextos (ACLs/interfaces versionadas).

## 6. Linguagem ubíqua (Ubiquitous Language)

Termos de domínio bem estabelecidos:

- Médico/Cliente, Vaga/Plantão, Campanha, Handoff, Opt-out, Cooling-off, Stage/Jornada

Pontos de inconsistência:

- Mistura português/inglês em estados e campos (`active`, `pending`, `concluida`, `opted_out`)
- Termos próximos com semântica diferente (ex.: `status` vs `stage_jornada` vs `lifecycle_stage`)
- “Cliente” e “Médico” coexistem em camadas diferentes (repositório vs serviço), o que aumenta ambiguidade conceitual

## 7. Padrões táticos DDD: aderência atual

## 7.1 Entidades e Value Objects

Sinais positivos:

- Objetos explícitos em policy (`DoctorState`, `PolicyDecision`)
- Tipos fortes de campanhas (`CampanhaData`, `AudienceFilters`)
- Evidências: `app/services/policy/types.py:91`, `app/services/campanhas/types.py:35`

Lacuna:

- Grande parte dos fluxos ainda trafega `dict` solto, enfraquecendo invariantes

## 7.2 Serviços de domínio

Boas implementações:

- `PolicyDecide` e `StateUpdate` modelam regras de domínio de forma clara
- `CampanhaExecutor` encapsula regras anti-spam/cooldown
- Evidências: `app/services/policy/decide.py:25`, `app/services/policy/state_update.py:20`, `app/services/campanhas/executor.py:38`

Lacuna:

- Alguns serviços misturam domínio + infraestrutura + orquestração externa no mesmo fluxo

## 7.3 Repositórios

Sinais positivos:

- Existe abstração base e `ClienteRepository`
- Evidências: `app/repositories/base.py:28`, `app/repositories/cliente.py:79`

Lacuna estrutural:

- A maioria dos módulos continua acessando `supabase.table(...)` diretamente
- Isso reduz isolamento do domínio e testabilidade por contexto

## 7.4 Agregados e consistência transacional

Estado atual:

- Agregados não estão explicitamente modelados como unidades transacionais
- Atualizações multi-entidade frequentemente ocorrem por sequência de comandos

Impacto DDD:

- Invariantes críticos podem ficar distribuídos por vários pontos de código
- Dificulta identificar “aggregate root” formal por contexto

## 8. Principais desvios em relação ao Evans

1. **Bounded contexts implícitos, não explicitamente governados**
- Estrutura de pacotes por serviço técnico, não por contexto de domínio

2. **Domain model parcialmente anêmico em áreas amplas**
- Uso intensivo de `dict` e acesso direto ao banco fora de repositórios

3. **Camada de aplicação/interface com vazamento de regra e persistência**
- Rotas com query direta em contextos que já possuem serviços/repositórios
- Evidências: `app/api/routes/campanhas.py:259`, `app/api/routes/group_entry.py:200`

4. **Ausência de anti-corruption layer formal entre contextos e integrações externas**
- Existem wrappers/adapters em alguns pontos, mas sem padrão uniforme por contexto

## 9. Riscos arquiteturais de domínio

1. **Risco de regressão semântica**
- Mudança de regra em um ponto não propaga para todos os caminhos que operam via SQL direto

2. **Risco de inconsistência de estado**
- Invariantes de jornada/policy/campanha podem divergir entre fluxos inbound/outbound/jobs

3. **Risco de crescimento com fricção**
- Novos produtos/contextos (ex.: multi-tenant ou novas linhas de serviço) tendem a aumentar acoplamento

## 10. Recomendações (roadmap DDD pragmático)

## Fase 1 (2-4 semanas): explicitar fronteiras

1. Definir oficialmente os bounded contexts acima em documentação viva (context map + ownership)
2. Padronizar linguagem ubíqua (dicionário de termos e estados canônicos)
3. Proibir novos acessos `supabase.table(...)` em routers onde já exista serviço de domínio

## Fase 2 (4-8 semanas): reforçar tático

1. Introduzir **Application Services** por contexto (ex.: `campanhas/application.py`, `policy/application.py`)
2. Consolidar repositórios por contexto e mover queries de rotas para essa camada
3. Substituir `dict` críticos por modelos de domínio/VOs nos fluxos centrais

## Fase 3 (8-12 semanas): invariantes e integração

1. Definir agregados formais e suas invariantes (ex.: `DoctorEngagement`, `CampaignExecution`, `ShiftAllocation`)
2. Implementar contrato de eventos de domínio estável (versão + schema) entre contextos
3. Criar ACL explícita para integrações externas (providers WhatsApp, Slack, Meta) para desacoplar mudanças

## 11. Proposta de score DDD atual

- **Strategic Design:** 6/10  
- **Tactical Design:** 5/10  
- **Linguagem Ubíqua:** 6/10  
- **Isolamento de Contextos:** 5/10  
- **Evolutividade de Domínio:** 6/10

**Score geral sugerido:** **5.6/10** (boa base, mas com dívida de fronteira/contexto)

## 12. Conclusão

O projeto está em um ponto comum de produtos que escalaram rápido: já construiu capacidades de domínio sofisticadas (especialmente no coração `conversa + policy + campanhas + vagas`), porém precisa formalizar o desenho DDD para evitar erosão progressiva.

Com um ciclo de 2 a 3 meses de refatoração orientada a contexto, é possível:

- reduzir acoplamento entre interface e domínio,
- aumentar previsibilidade de regras,
- e preparar o sistema para evolução de produto sem perda de coerência de modelo.
