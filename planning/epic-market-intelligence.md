# Epic: Market Intelligence - Grupos WhatsApp

## Visao Geral

Transformar o modulo de Grupos de uma ferramenta operacional (entrada de links) em uma plataforma de **Market Intelligence** para o mercado de staffing medico, gerando insights estrategicos a partir das vagas captadas nos grupos WhatsApp.

## Objetivo de Negocio

> Ter visibilidade completa do mercado de plantoes medicos: quem esta oferecendo, onde, quanto, quando, e identificar oportunidades antes da concorrencia.

## Estado Atual

### Dados Disponiveis (PROD)

| Tabela | Registros | Descricao |
|--------|-----------|-----------|
| `grupos_whatsapp` | 174 | Grupos monitorados |
| `mensagens_grupo` | 22,396 | Mensagens coletadas |
| `vagas_grupo` | 56,443 | Vagas extraidas (raw) |
| `vagas` | 6,979 | Vagas importadas (processadas) |
| `metricas_grupos_diarias` | - | Metricas de pipeline por dia |

### Campos Estrategicos Disponiveis

**Localizacao:**
- `cidade`, `estado`, `endereco_raw`
- `hospital_id` → `hospitais.cidade/estado`

**Valor:**
- `valor`, `valor_minimo`, `valor_maximo`, `valor_tipo`

**Classificacao:**
- `especialidade_id`, `especialidade_raw`
- `setor_id`, `setor_raw`
- `periodo_id`, `periodo_raw`
- `tipos_vaga_id`

**Fonte:**
- `grupo_origem_id` → grupo de origem
- `contato_responsavel_id` → quem postou
- `contato_nome`, `contato_whatsapp`

**Qualidade:**
- `confianca_geral`, `confianca_hospital`, `confianca_especialidade`
- `eh_duplicada`, `qtd_fontes`

---

## Arquitetura da Solucao

```
┌─────────────────────────────────────────────────────────────────────┐
│                        MARKET INTELLIGENCE                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐│
│  │   VISAO     │  │  MERCADO    │  │  PLAYERS    │  │  INSIGHTS   ││
│  │   GERAL     │  │             │  │             │  │             ││
│  ├─────────────┤  ├─────────────┤  ├─────────────┤  ├─────────────┤│
│  │ KPIs        │  │ Por Regiao  │  │ Hospitais   │  │ Tendencias  ││
│  │ Volume      │  │ Por Espec.  │  │ Empresas    │  │ Alertas     ││
│  │ Pipeline    │  │ Por Valor   │  │ Escalistas  │  │ Predicoes   ││
│  │ Qualidade   │  │ Timeline    │  │ Ranking     │  │ Oportunid.  ││
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘│
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                      DADOS BASE                                 ││
│  │  grupos_whatsapp → mensagens_grupo → vagas_grupo → vagas        ││
│  └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

---

## Sprints Propostas

### Sprint 46: Fundacao Analytics (Visibilidade Basica)

**Objetivo:** Dashboard de KPIs e metricas de volume

#### Epicos:

**E1: API de Analytics**
- [ ] Endpoint `/api/market-intelligence/overview`
- [ ] Endpoint `/api/market-intelligence/volume`
- [ ] Endpoint `/api/market-intelligence/pipeline`
- [ ] Cache com Redis (TTL 5min)

**E2: Dashboard Overview**
- [ ] KPI Cards: vagas/dia, grupos ativos, taxa conversao
- [ ] Grafico de volume (ultimos 30 dias)
- [ ] Funil do pipeline (mensagens → ofertas → vagas)
- [ ] Health score dos grupos

**E3: Metricas de Pipeline**
- [ ] Taxa de extracao (mensagens → vagas detectadas)
- [ ] Taxa de importacao (vagas extraidas → importadas)
- [ ] Taxa de duplicatas
- [ ] Qualidade media (confianca_geral)

#### Entregaveis:
- Tab "Analytics" no modulo Grupos
- 4 KPI cards principais
- 2 graficos de tendencia
- Tabela de grupos mais ativos

---

### Sprint 47: Analise de Mercado (Segmentacao)

**Objetivo:** Visao segmentada por regiao, especialidade e valor

#### Epicos:

**E1: Analise Regional**
- [ ] Mapa de calor por estado/cidade
- [ ] Ranking de regioes por volume
- [ ] Comparativo entre regioes
- [ ] Evolucao temporal por regiao

**E2: Analise por Especialidade**
- [ ] Ranking de especialidades mais demandadas
- [ ] Valor medio por especialidade
- [ ] Tendencia de demanda por especialidade
- [ ] Gap analysis (demanda vs oferta Julia)

**E3: Analise de Valores**
- [ ] Distribuicao de valores por faixa
- [ ] Valor medio por especialidade/regiao
- [ ] Evolucao de valores no tempo
- [ ] Deteccao de outliers (valores muito altos/baixos)

**E4: Analise Temporal**
- [ ] Padrao de postagem por hora do dia
- [ ] Padrao por dia da semana
- [ ] Sazonalidade mensal
- [ ] Heatmap dia/hora

#### Entregaveis:
- Tab "Mercado" no modulo Grupos
- Filtros interativos (periodo, regiao, especialidade)
- 6+ visualizacoes de dados
- Export para CSV/Excel

---

### Sprint 48: Analise de Players (Competidores)

**Objetivo:** Identificar e analisar principais players do mercado

#### Epicos:

**E1: Analise de Hospitais**
- [ ] Ranking de hospitais por volume de vagas
- [ ] Hospitais com alta demanda recorrente
- [ ] Hospitais novos (primeira vez postando)
- [ ] Perfil de hospital (especialidades, valores, frequencia)

**E2: Analise de Empresas/Escalistas**
- [ ] Identificacao de empresas de staffing concorrentes
- [ ] Ranking por volume de postagens
- [ ] Padroes de atuacao (regioes, especialidades)
- [ ] Deteccao de novos players

**E3: Analise de Contatos**
- [ ] Contatos mais ativos (escalistas)
- [ ] Rede de relacionamento (quem posta onde)
- [ ] Contatos estrategicos (alto volume, boa qualidade)

**E4: Qualidade dos Grupos**
- [ ] Score de qualidade por grupo
- [ ] Relacao sinal/ruido
- [ ] Grupos com melhor taxa de vagas validas
- [ ] Recomendacao de grupos para monitorar

#### Entregaveis:
- Tab "Players" no modulo Grupos
- Perfil detalhado de hospital
- Ranking de competidores
- Score de qualidade de grupos

---

### Sprint 49: Insights Inteligentes (Algoritmos)

**Objetivo:** Gerar insights automaticos e predicoes

#### Epicos:

**E1: Sistema de Alertas**
- [ ] Alerta: Hospital com pico de demanda
- [ ] Alerta: Nova empresa no mercado
- [ ] Alerta: Valor de plantao fora do padrao
- [ ] Alerta: Grupo de alto valor descoberto

**E2: Deteccao de Tendencias**
- [ ] Especialidades em alta/baixa
- [ ] Regioes aquecendo/esfriando
- [ ] Valores subindo/descendo
- [ ] Sazonalidades identificadas

**E3: Oportunidades**
- [ ] Hospitais com demanda nao atendida
- [ ] Especialidades com gap de oferta
- [ ] Regioes subexploradas
- [ ] Contatos estrategicos para abordar

**E4: Predicoes (ML)**
- [ ] Previsao de volume de vagas (proximo periodo)
- [ ] Probabilidade de vaga por grupo
- [ ] Score de prioridade de grupo
- [ ] Deteccao de anomalias

#### Entregaveis:
- Tab "Insights" no modulo Grupos
- Centro de alertas
- Dashboard de oportunidades
- Modelo preditivo basico

---

## Modelo de Dados (Novas Tabelas)

### `market_intelligence_snapshots`
Snapshots diarios para analise historica.

```sql
CREATE TABLE market_intelligence_snapshots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  data DATE NOT NULL,

  -- Volume
  total_grupos_ativos INTEGER,
  total_mensagens INTEGER,
  total_vagas_extraidas INTEGER,
  total_vagas_importadas INTEGER,

  -- Taxas
  taxa_extracao NUMERIC(5,2),
  taxa_importacao NUMERIC(5,2),
  taxa_duplicatas NUMERIC(5,2),
  confianca_media NUMERIC(5,2),

  -- Breakdown
  por_estado JSONB,
  por_especialidade JSONB,
  por_faixa_valor JSONB,
  por_periodo JSONB,

  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(data)
);
```

### `hospital_intelligence`
Perfil de inteligencia por hospital.

```sql
CREATE TABLE hospital_intelligence (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  hospital_id UUID REFERENCES hospitais(id),

  -- Metricas
  total_vagas_historico INTEGER,
  vagas_ultimo_30d INTEGER,
  valor_medio INTEGER,
  valor_mediano INTEGER,

  -- Perfil
  especialidades_principais JSONB,
  periodos_principais JSONB,
  frequencia_postagem TEXT, -- 'diaria', 'semanal', 'esporadica'

  -- Scores
  score_volume INTEGER, -- 0-100
  score_recorrencia INTEGER, -- 0-100
  score_valor INTEGER, -- 0-100
  score_geral INTEGER, -- 0-100

  -- Flags
  eh_novo BOOLEAN,
  demanda_alta BOOLEAN,

  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### `player_profiles`
Perfil de empresas/escalistas.

```sql
CREATE TABLE player_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- Identificacao
  tipo TEXT, -- 'empresa', 'escalista', 'hospital'
  nome TEXT,
  telefones TEXT[],

  -- Metricas
  total_postagens INTEGER,
  grupos_atuacao TEXT[],
  regioes_atuacao TEXT[],
  especialidades TEXT[],

  -- Classificacao
  eh_concorrente BOOLEAN,
  nivel_atividade TEXT, -- 'alto', 'medio', 'baixo'

  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### `market_alerts`
Alertas de mercado.

```sql
CREATE TABLE market_alerts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  tipo TEXT, -- 'demanda_alta', 'novo_player', 'valor_anomalo', 'grupo_valioso'
  severidade TEXT, -- 'info', 'atencao', 'importante', 'critico'

  titulo TEXT,
  descricao TEXT,
  dados JSONB,

  entidade_tipo TEXT, -- 'hospital', 'grupo', 'player', 'regiao'
  entidade_id UUID,

  visualizado BOOLEAN DEFAULT FALSE,
  visualizado_em TIMESTAMPTZ,
  visualizado_por TEXT,

  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Metricas de Sucesso

### Sprint 46 (Fundacao)
- [ ] Dashboard carrega em < 2s
- [ ] Dados atualizados a cada 5 min
- [ ] 100% dos KPIs funcionando

### Sprint 47 (Mercado)
- [ ] Todos os segmentos com dados
- [ ] Filtros funcionando corretamente
- [ ] Export funcionando

### Sprint 48 (Players)
- [ ] Top 20 hospitais identificados
- [ ] Competidores mapeados
- [ ] Score de grupos implementado

### Sprint 49 (Insights)
- [ ] Alertas gerando automaticamente
- [ ] Modelo preditivo com > 70% acuracia
- [ ] Oportunidades sendo detectadas

---

## Estimativa de Esforco

| Sprint | Complexidade | Backend | Frontend | Total |
|--------|--------------|---------|----------|-------|
| 46 | Media | 3d | 3d | 6d |
| 47 | Alta | 4d | 4d | 8d |
| 48 | Alta | 4d | 3d | 7d |
| 49 | Muito Alta | 5d | 3d | 8d |
| **Total** | | **16d** | **13d** | **29d** |

---

## Proximos Passos

1. **Validar escopo** - Revisar com stakeholders
2. **Priorizar features** - O que traz mais valor primeiro?
3. **Criar Sprint 46** - Detalhar tasks e subtasks
4. **Setup de infra** - Views materializadas, indices, cache

---

## Notas Tecnicas

### Performance
- Usar views materializadas para agregacoes pesadas
- Refresh incremental diario (via worker)
- Cache agressivo no frontend (React Query)
- Indices otimizados para queries de analytics

### Arquitetura Frontend
- Nova tab "Analytics" em `/chips?tab=analytics`
- Sub-tabs: Overview, Mercado, Players, Insights
- Componentes reutilizaveis de graficos (Recharts)
- Skeleton loading para UX

### Integracao com Pipeline Existente
- Aproveitar `metricas_grupos_diarias` existente
- Enriquecer no processamento (nao pos-facto)
- Worker diario para snapshots
