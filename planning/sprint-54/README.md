# Sprint 54 - Insights Dashboard & Relatório Julia

**Início:** 09/02/2026
**Duração estimada:** 1 semana
**Dependências:** Sprint 53 (Extraction Pipeline) completa
**Status:** 📋 Planejado

---

## Progresso

| Epic | Status | Descrição |
|------|--------|-----------|
| Epic 1: API de Relatório Julia | 📋 Pendente | Endpoint que gera análise qualitativa |
| Epic 2: Insights na Página de Campanha | 📋 Pendente | Cards + Relatório Julia |
| Epic 3: Perfil do Médico Enriquecido | 📋 Pendente | Histórico de insights |
| Epic 4: Página de Oportunidades | 📋 Pendente | Ações pendentes por próximo passo |
| Epic 5: Dashboard Overview | 📋 Pendente | Métricas gerais de extração |

---

## Objetivo Estratégico

Transformar dados brutos de `conversation_insights` em **visualizações acionáveis** no dashboard, incluindo um **relatório qualitativo da Julia** que vai além de números e entrega análise estratégica.

### Por que agora?

Sprint 53 criou o pipeline de extração, mas os dados estão "escondidos" no banco:
- Gestores não veem os insights
- Decisões continuam baseadas em intuição
- Valor dos dados não é capturado

### Diferencial: Relatório Julia

Em vez de apenas mostrar "32% interesse positivo", a Julia vai gerar um **relatório executivo**:

```
📊 Relatório da Campanha "Discovery Cardiologia"

Olá! Analisei as 16 respostas dessa campanha e aqui está o que descobri:

**O que funcionou:**
- 5 médicos demonstraram interesse real em vagas
- Dr. Sergio e Dra. Debora estão prontos para receber ofertas
- Fins de semana apareceram como preferência comum

**Pontos de atenção:**
- 3 médicos já trabalham com outras empresas (principal objeção)
- 2 mencionaram que estão em regiões diferentes do cadastro

**Próximos passos sugeridos:**
1. Enviar vagas de fim de semana para Sergio e Debora
2. Atualizar região do Dr. Enrico (mencionou RJ, cadastrado em SP)
3. Não reabordar Cristiano e Nadia (objeção forte)

**Insight estratégico:**
Cardiologistas dessa base parecem preferir plantões de fim de semana.
Considere criar uma campanha específica para esse perfil.
```

---

## Arquitetura

### Fluxo de Dados

```
┌─────────────────────────────────────────────────────────────────────┐
│                     BACKEND (Python/FastAPI)                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────────┐     ┌──────────────────────┐              │
│  │ conversation_insights│     │   campaign_insights  │              │
│  │     (raw data)       │────▶│  (view materializada)│              │
│  └──────────────────────┘     └──────────────────────┘              │
│              │                           │                           │
│              ▼                           ▼                           │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              /extraction/campaign/{id}/report                 │   │
│  │                                                               │   │
│  │  1. Busca insights da campanha                                │   │
│  │  2. Agrega por interesse, objeção, próximo passo             │   │
│  │  3. Chama LLM (Haiku) para gerar relatório qualitativo       │   │
│  │  4. Retorna JSON com métricas + relatório                    │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     FRONTEND (Next.js/TypeScript)                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                 Página de Campanha                           │    │
│  ├─────────────────────────────────────────────────────────────┤    │
│  │                                                              │    │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │    │
│  │  │  Interesse  │ │  Objeções   │ │   Ações     │            │    │
│  │  │  Positivo   │ │  Detectadas │ │  Sugeridas  │            │    │
│  │  │    32%      │ │     5       │ │     8       │            │    │
│  │  └─────────────┘ └─────────────┘ └─────────────┘            │    │
│  │                                                              │    │
│  │  ┌──────────────────────────────────────────────────────┐   │    │
│  │  │              📊 Relatório da Julia                    │   │    │
│  │  │                                                       │   │    │
│  │  │  "Analisei as 16 respostas dessa campanha..."        │   │    │
│  │  │                                                       │   │    │
│  │  │  [Texto do relatório com markdown renderizado]        │   │    │
│  │  │                                                       │   │    │
│  │  └──────────────────────────────────────────────────────┘   │    │
│  │                                                              │    │
│  │  ┌──────────────────────────────────────────────────────┐   │    │
│  │  │              Médicos Prontos para Ação                │   │    │
│  │  │                                                       │   │    │
│  │  │  👤 Dr. Sergio - Enviar vagas    [Enviar]             │   │    │
│  │  │  👤 Dra. Debora - Enviar vagas   [Enviar]             │   │    │
│  │  │  👤 Dr. Marcos - Follow-up       [Agendar]            │   │    │
│  │  │                                                       │   │    │
│  │  └──────────────────────────────────────────────────────┘   │    │
│  │                                                              │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Épicos

### Epic 1: API de Relatório Julia (P0 - Crítico)

**Objetivo:** Criar endpoint que gera relatório qualitativo usando LLM.

**Arquivos:**
- `app/services/extraction/report_generator.py` (NOVO)
- `app/api/routes/extraction.py` (adicionar endpoint)

**Endpoint:**
```
GET /extraction/campaign/{campaign_id}/report
```

**Response:**
```json
{
  "campaign_id": 19,
  "campaign_name": "Discovery Cardiologia",
  "generated_at": "2026-02-09T18:30:00Z",

  "metrics": {
    "total_respostas": 16,
    "interesse_positivo": 5,
    "interesse_negativo": 3,
    "interesse_neutro": 6,
    "interesse_incerto": 2,
    "taxa_interesse_pct": 31.2,
    "total_objecoes": 5,
    "objecao_mais_comum": "empresa_atual",
    "prontos_para_vagas": 3,
    "para_followup": 4
  },

  "medicos_destaque": [
    {
      "cliente_id": "uuid-1",
      "nome": "Dr. Sergio",
      "interesse": "positivo",
      "proximo_passo": "enviar_vagas",
      "insight": "Mencionou interesse em fins de semana"
    }
  ],

  "objecoes_encontradas": [
    {
      "tipo": "empresa_atual",
      "quantidade": 3,
      "exemplo": "Já trabalho com outra empresa de plantões"
    }
  ],

  "relatorio_julia": "📊 **Relatório da Campanha \"Discovery Cardiologia\"**\n\nOlá! Analisei as 16 respostas dessa campanha...",

  "tokens_usados": 850,
  "cached": false
}
```

**Prompt do Relatório:**
```
Você é Julia, escalista da Revoluna. Analise os dados desta campanha e gere um relatório executivo.

DADOS DA CAMPANHA:
- Nome: {nome}
- Total de respostas: {total}
- Interesse positivo: {positivo} ({pct}%)
- Interesse negativo: {negativo}
- Objeções detectadas: {objecoes}

MÉDICOS COM INTERESSE:
{lista_interessados}

OBJEÇÕES ENCONTRADAS:
{lista_objecoes}

PREFERÊNCIAS MENCIONADAS:
{preferencias}

Gere um relatório em primeira pessoa, como se você (Julia) estivesse apresentando para o gestor.

Inclua:
1. **O que funcionou** - pontos positivos
2. **Pontos de atenção** - objeções e problemas
3. **Próximos passos sugeridos** - ações concretas
4. **Insight estratégico** - padrão ou oportunidade identificada

Use markdown para formatação. Seja concisa mas informativa.
Não invente dados - use apenas o que foi fornecido.
```

**Tarefas:**
- [ ] 1.1 Criar `report_generator.py` com lógica de agregação
- [ ] 1.2 Criar prompt para geração de relatório
- [ ] 1.3 Implementar cache (1 hora TTL por campanha)
- [ ] 1.4 Adicionar endpoint `/campaign/{id}/report`
- [ ] 1.5 Testes unitários

**DoD:**
- [ ] Endpoint retorna métricas + relatório
- [ ] Cache funcionando
- [ ] Relatório legível e útil

**Estimativa:** 3 horas

---

### Epic 2: Insights na Página de Campanha (P0 - Crítico)

**Objetivo:** Adicionar seção de insights com relatório Julia na página de campanha.

**Arquivos:**
- `dashboard/src/app/campanhas/[id]/page.tsx` (modificar)
- `dashboard/src/components/campaigns/CampaignInsights.tsx` (NOVO)
- `dashboard/src/components/campaigns/JuliaReport.tsx` (NOVO)
- `dashboard/src/components/campaigns/ActionableContacts.tsx` (NOVO)
- `dashboard/src/lib/api/extraction.ts` (NOVO)

**Layout:**

```
┌────────────────────────────────────────────────────────────────┐
│  Campanha: Discovery Cardiologia                               │
│  Status: Concluída | Enviados: 50 | Respostas: 16 (32%)       │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────── Insights da Campanha ──────────────────┐ │
│  │                                                            │ │
│  │  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐          │ │
│  │  │   👍   │  │   👎   │  │   😐   │  │   ⚠️   │          │ │
│  │  │   5    │  │   3    │  │   6    │  │   5    │          │ │
│  │  │Positivo│  │Negativo│  │ Neutro │  │Objeções│          │ │
│  │  └────────┘  └────────┘  └────────┘  └────────┘          │ │
│  │                                                            │ │
│  │  Score Médio de Interesse: ████████░░ 6.8/10              │ │
│  │                                                            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌─────────────────── 📊 Relatório da Julia ─────────────────┐ │
│  │                                                            │ │
│  │  Olá! Analisei as 16 respostas dessa campanha e aqui      │ │
│  │  está o que descobri:                                      │ │
│  │                                                            │ │
│  │  **O que funcionou:**                                      │ │
│  │  • 5 médicos demonstraram interesse real em vagas         │ │
│  │  • Dr. Sergio e Dra. Debora estão prontos para ofertas    │ │
│  │  • Fins de semana apareceram como preferência comum       │ │
│  │                                                            │ │
│  │  **Pontos de atenção:**                                    │ │
│  │  • 3 médicos já trabalham com outras empresas             │ │
│  │  • 2 mencionaram regiões diferentes do cadastro           │ │
│  │                                                            │ │
│  │  **Próximos passos sugeridos:**                            │ │
│  │  1. Enviar vagas de fim de semana para Sergio e Debora    │ │
│  │  2. Atualizar região do Dr. Enrico (RJ, não SP)           │ │
│  │  3. Não reabordar Cristiano e Nadia (objeção forte)       │ │
│  │                                                            │ │
│  │  **Insight estratégico:**                                  │ │
│  │  Cardiologistas dessa base parecem preferir plantões de   │ │
│  │  fim de semana. Considere criar campanha específica.      │ │
│  │                                                            │ │
│  │                              [🔄 Regenerar Relatório]      │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌─────────────────── Médicos para Ação ─────────────────────┐ │
│  │                                                            │ │
│  │  🎯 Prontos para Vagas (3)                                │ │
│  │  ┌──────────────────────────────────────────────────────┐ │ │
│  │  │ 👤 Dr. Sergio Silva     | Cardiologia | ⭐ 0.9       │ │ │
│  │  │    "Tenho interesse em plantões de fim de semana"    │ │ │
│  │  │                                    [Enviar Vagas]     │ │ │
│  │  ├──────────────────────────────────────────────────────┤ │ │
│  │  │ 👤 Dra. Debora Costa    | Cardiologia | ⭐ 0.85      │ │ │
│  │  │    "Disponível fins de semana"                       │ │ │
│  │  │                                    [Enviar Vagas]     │ │ │
│  │  └──────────────────────────────────────────────────────┘ │ │
│  │                                                            │ │
│  │  📅 Para Follow-up (4)                                    │ │
│  │  ┌──────────────────────────────────────────────────────┐ │ │
│  │  │ 👤 Dr. Marcos Oliveira  | Cardiologia | ⭐ 0.6       │ │ │
│  │  │    "Talvez no futuro, me liga daqui uns dias"        │ │ │
│  │  │                                    [Agendar]          │ │ │
│  │  └──────────────────────────────────────────────────────┘ │ │
│  │                                                            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

**Tarefas:**
- [ ] 2.1 Criar `extraction.ts` com client API
- [ ] 2.2 Criar componente `CampaignInsights` (cards de métricas)
- [ ] 2.3 Criar componente `JuliaReport` (renderiza markdown)
- [ ] 2.4 Criar componente `ActionableContacts` (lista de médicos)
- [ ] 2.5 Integrar na página de campanha
- [ ] 2.6 Adicionar loading states e error handling
- [ ] 2.7 Testes de componentes

**DoD:**
- [ ] Insights aparecem na página de campanha
- [ ] Relatório Julia renderizado corretamente
- [ ] Botões de ação funcionando
- [ ] Mobile responsive

**Estimativa:** 4 horas

---

### Epic 3: Perfil do Médico Enriquecido (P1)

**Objetivo:** Mostrar histórico de insights no perfil do médico.

**Arquivos:**
- `dashboard/src/app/medicos/[id]/page.tsx` (modificar)
- `dashboard/src/components/doctors/DoctorInsights.tsx` (NOVO)
- `dashboard/src/components/doctors/InsightTimeline.tsx` (NOVO)

**Layout:**

```
┌────────────────────────────────────────────────────────────────┐
│  Dr. Carlos Silva                                              │
│  Cardiologia | São Paulo | CRM 123456                         │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────── Perfil de Interesse ───────────────────┐ │
│  │                                                            │ │
│  │  Score Médio: ████████░░ 7.2/10                           │ │
│  │  Tendência: 📈 Crescente (últimos 30 dias)                │ │
│  │                                                            │ │
│  │  Interações: 8 conversas | Última: há 3 dias              │ │
│  │                                                            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌─────────────────── Preferências Detectadas ───────────────┐ │
│  │                                                            │ │
│  │  ✅ Plantões noturnos                                      │ │
│  │  ✅ Fins de semana                                         │ │
│  │  ✅ Região: Grande São Paulo                               │ │
│  │                                                            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌─────────────────── Restrições Conhecidas ─────────────────┐ │
│  │                                                            │ │
│  │  ❌ Não trabalha segundas-feiras                           │ │
│  │  ❌ Não aceita valores abaixo de R$ 2.000                  │ │
│  │                                                            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌─────────────────── Histórico de Interações ───────────────┐ │
│  │                                                            │ │
│  │  📅 05/02/2026 - Campanha Discovery                       │ │
│  │     👍 Positivo (0.85) - "Tenho interesse em vagas"       │ │
│  │                                                            │ │
│  │  📅 20/01/2026 - Follow-up                                │ │
│  │     😐 Neutro (0.5) - "Me liga depois"                    │ │
│  │                                                            │ │
│  │  📅 10/01/2026 - Oferta Vaga                              │ │
│  │     👎 Negativo (0.2) - Objeção: preço                    │ │
│  │                                                            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

**Tarefas:**
- [ ] 3.1 Criar componente `DoctorInsights` (resumo)
- [ ] 3.2 Criar componente `InsightTimeline` (histórico)
- [ ] 3.3 Mostrar preferências e restrições do doctor_context
- [ ] 3.4 Calcular tendência de interesse
- [ ] 3.5 Integrar na página do médico

**DoD:**
- [ ] Perfil mostra insights agregados
- [ ] Timeline de interações visível
- [ ] Preferências e restrições claras

**Estimativa:** 3 horas

---

### Epic 4: Página de Oportunidades (P1)

**Objetivo:** Página dedicada para ações pendentes, agrupadas por tipo.

**Arquivos:**
- `dashboard/src/app/oportunidades/page.tsx` (NOVO)
- `dashboard/src/components/opportunities/OpportunityList.tsx` (NOVO)
- `dashboard/src/components/opportunities/OpportunityCard.tsx` (NOVO)

**Endpoint necessário:**
```
GET /extraction/opportunities
```

**Response:**
```json
{
  "enviar_vagas": [
    {"cliente_id": "...", "nome": "Dr. Sergio", "score": 0.9, "insight": "..."}
  ],
  "agendar_followup": [...],
  "escalar_humano": [...],
  "total": 15
}
```

**Layout:**

```
┌────────────────────────────────────────────────────────────────┐
│  🎯 Oportunidades                                    [Filtros] │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────── Prontos para Vagas (8) ────────────────┐ │
│  │                                                            │ │
│  │  👤 Dr. Sergio Silva      | ⭐ 0.9  | Cardiologia         │ │
│  │     "Tenho interesse em plantões de fim de semana"        │ │
│  │     Campanha: Discovery Cardiologia | há 2 dias           │ │
│  │                                    [Enviar Vagas] [Ver]    │ │
│  │  ─────────────────────────────────────────────────────    │ │
│  │  👤 Dra. Ana Costa        | ⭐ 0.85 | Pediatria           │ │
│  │     "Gostaria de saber mais sobre as vagas"               │ │
│  │     Campanha: Discovery Pediatria | há 1 dia              │ │
│  │                                    [Enviar Vagas] [Ver]    │ │
│  │                                                            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌─────────────────── Para Follow-up (5) ────────────────────┐ │
│  │                                                            │ │
│  │  👤 Dr. Marcos Oliveira   | ⭐ 0.6  | Clínica Médica      │ │
│  │     "Talvez no futuro, me liga daqui uns dias"            │ │
│  │     Última interação: há 5 dias                            │ │
│  │                                    [Agendar] [Ver]         │ │
│  │                                                            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌─────────────────── Escalar para Humano (2) ───────────────┐ │
│  │                                                            │ │
│  │  👤 Dr. Paulo Santos      | ⚠️ Reclamação                 │ │
│  │     "Vocês me ligaram 3 vezes essa semana!"               │ │
│  │     Última interação: há 1 hora                            │ │
│  │                                    [Assumir] [Ver]         │ │
│  │                                                            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

**Tarefas:**
- [ ] 4.1 Criar endpoint `/extraction/opportunities`
- [ ] 4.2 Criar página `oportunidades/page.tsx`
- [ ] 4.3 Criar componentes de lista e card
- [ ] 4.4 Implementar ações (enviar vagas, agendar, assumir)
- [ ] 4.5 Adicionar à navegação do dashboard
- [ ] 4.6 Filtros por tipo, campanha, data

**DoD:**
- [ ] Página lista oportunidades agrupadas
- [ ] Ações funcionando
- [ ] Navegação atualizada

**Estimativa:** 3 horas

---

### Epic 5: Dashboard Overview (P2)

**Objetivo:** Adicionar métricas de extração ao dashboard principal.

**Arquivos:**
- `dashboard/src/app/page.tsx` (modificar)
- `dashboard/src/components/dashboard/ExtractionMetrics.tsx` (NOVO)

**Layout:**

```
┌────────────────────────────────────────────────────────────────┐
│  📊 Insights da Semana                                         │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐               │
│  │  125   │  │  42    │  │  18    │  │  95%   │               │
│  │Insights│  │Positivo│  │Objeções│  │Cobertura│              │
│  │ Novos  │  │        │  │        │  │        │               │
│  └────────┘  └────────┘  └────────┘  └────────┘               │
│                                                                 │
│  Interesse ao Longo do Tempo                                   │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │     ██                                                    │ │
│  │   ████  ██                    ██                         │ │
│  │ ██████████  ██████    ████  ████████                     │ │
│  │ Seg  Ter  Qua  Qui  Sex  Sáb  Dom                        │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
│  Top Objeções                                                  │
│  1. empresa_atual (35%)  ████████████░░░░░░░░                 │
│  2. tempo (25%)          ████████░░░░░░░░░░░░                 │
│  3. preco (20%)          ██████░░░░░░░░░░░░░░                 │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

**Tarefas:**
- [ ] 5.1 Criar endpoint `/extraction/stats/weekly`
- [ ] 5.2 Criar componente `ExtractionMetrics`
- [ ] 5.3 Gráfico de interesse por dia
- [ ] 5.4 Top objeções
- [ ] 5.5 Integrar no dashboard

**DoD:**
- [ ] Métricas aparecem no dashboard
- [ ] Gráfico renderizado
- [ ] Atualização automática

**Estimativa:** 2 horas

---

## Estimativas

| Epic | Complexidade | Tempo Estimado |
|------|--------------|----------------|
| Epic 1: API Relatório Julia | Alta | 3 horas |
| Epic 2: Insights Campanha | Alta | 4 horas |
| Epic 3: Perfil Médico | Média | 3 horas |
| Epic 4: Página Oportunidades | Média | 3 horas |
| Epic 5: Dashboard Overview | Baixa | 2 horas |
| **Total** | | **15 horas** |

---

## Stack Frontend

| Tecnologia | Uso |
|------------|-----|
| Next.js 14+ | Framework React |
| TypeScript | Tipagem estrita |
| Tailwind CSS | Estilos |
| shadcn/ui | Componentes base |
| react-markdown | Renderizar relatório Julia |
| recharts | Gráficos |
| SWR ou React Query | Data fetching |

---

## Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Relatório Julia genérico | Média | Médio | Prompt bem estruturado + exemplos |
| Latência do relatório | Média | Baixo | Cache 1 hora + loading state |
| Custo de tokens | Baixa | Baixo | Haiku + cache agressivo |
| Dados insuficientes | Média | Médio | Fallback para métricas básicas |

---

## Ordem de Implementação

### Fase 1: Backend (Dia 1)
1. **Epic 1**: API de Relatório Julia
2. Endpoint de oportunidades

### Fase 2: Frontend Core (Dia 2-3)
3. **Epic 2**: Insights na página de campanha
4. **Epic 4**: Página de oportunidades

### Fase 3: Enriquecimento (Dia 4)
5. **Epic 3**: Perfil do médico
6. **Epic 5**: Dashboard overview

---

## Definition of Done (Sprint)

### Obrigatório (P0)
- [ ] Relatório Julia gerado para campanhas
- [ ] Insights visíveis na página de campanha
- [ ] Médicos acionáveis listados
- [ ] Botões de ação funcionando

### Desejável (P1)
- [ ] Perfil do médico enriquecido
- [ ] Página de oportunidades
- [ ] Dashboard overview com métricas

### Futuro (P2)
- [ ] Gráficos de tendência
- [ ] Notificações de oportunidades
- [ ] Export de relatório (PDF)

---

## Exemplo de Relatório Julia

```markdown
📊 **Relatório da Campanha "Discovery Cardiologia"**

Olá! Analisei as 16 respostas dessa campanha e aqui está o que descobri:

---

### ✅ O que funcionou

- **5 médicos** demonstraram interesse real em vagas
- Dr. Sergio e Dra. Debora estão **prontos para receber ofertas**
- "Fins de semana" apareceu como preferência comum (3 menções)
- Taxa de resposta de 32% está acima da média (25%)

---

### ⚠️ Pontos de atenção

- **3 médicos** já trabalham com outras empresas (principal objeção)
- Dr. Enrico mencionou que atua no RJ, mas está cadastrado em SP
- 2 respostas foram de bots/sistemas automáticos

---

### 🎯 Próximos passos sugeridos

1. **Enviar vagas de fim de semana** para Dr. Sergio e Dra. Debora
2. **Atualizar cadastro** do Dr. Enrico (região: RJ)
3. **Não reabordar** Cristiano e Nadia (objeção forte)
4. **Agendar follow-up** para Dr. Marcos (disse "talvez no futuro")

---

### 💡 Insight estratégico

Cardiologistas dessa base parecem **preferir plantões de fim de semana**.
Considere criar uma campanha específica com vagas de sábado/domingo
para maximizar conversão.

Os que recusaram por "já trabalhar com outra empresa" podem ser
reabordados em 3-6 meses, quando contratos costumam renovar.
```

---

## Métricas de Sucesso

| Métrica | Antes | Meta |
|---------|-------|------|
| Tempo para analisar campanha | 30+ min (manual) | < 30 seg (automático) |
| Insights visualizados | 0% | 100% |
| Ações tomadas após campanha | Ad-hoc | Estruturadas |
| Decisões baseadas em dados | Poucas | Todas |
