# Sprint 14: Scraping de Vagas de Grupos WhatsApp

## Objetivo

Implementar sistema de captura, classificação e extração de ofertas de plantão de grupos de WhatsApp, com deduplicação inteligente e importação automática para o banco de vagas.

## Problema que Resolve

A Julia participa de ~300 grupos de WhatsApp onde são postadas ofertas de plantão de diversas fontes (Revoluna e terceiros). Hoje essas mensagens são ignoradas. Este sistema vai:

1. **Capturar** todas as mensagens de grupos
2. **Classificar** quais são ofertas de plantão (vs conversas gerais)
3. **Extrair** dados estruturados (hospital, data, valor, etc)
4. **Normalizar** para entidades conhecidas (hospitais, especialidades)
5. **Deduplicar** vagas repetidas em múltiplos grupos
6. **Importar** automaticamente vagas de alta confiança
7. **Rastrear** todas as fontes de cada vaga

## Contexto

| Aspecto | Valor |
|---------|-------|
| Grupos monitorados | ~300 |
| Volume estimado | 500-2000 msgs/dia |
| Fonte das vagas | Maioria terceiros |
| Formato das mensagens | Texto livre |
| Critério de dedup | Hospital + Data + Período + Especialidade |
| Modo de importação | Automático com regras |
| Rastreamento | Completo (todas as fontes) |

## Decisões de Escopo

| Decisão | Escolha | Motivo |
|---------|---------|--------|
| **Imagens/prints** | Ignorar no MVP | Complexidade de OCR, foco em texto primeiro |
| **Vagas em lote** | Suportar | Uma mensagem pode conter 3-5 vagas, extrair todas |
| **Hospital desconhecido** | Criar novo + busca web | Enriquecer com dados da web (endereço, cidade, etc) |
| **Vagas passadas** | Descartar | Se data < hoje, não importar |
| **Mensagens editadas** | Ignorar edições | Processar apenas mensagem original |

## Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                     WEBHOOK EVOLUTION API                        │
│                  (já recebe msgs de grupo)                       │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. INGESTAO (E01)                                              │
│  ─────────────────────────────────────────────────────────────  │
│  • Salvar TODAS as mensagens de grupo em `mensagens_grupo`      │
│  • Campos: grupo_jid, sender, texto, timestamp, status          │
│  • Cadastro de grupos em `grupos_whatsapp`                      │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. CLASSIFICACAO (E02) - Filtro de 2 estágios                  │
│  ─────────────────────────────────────────────────────────────  │
│  ESTÁGIO 1: Regex/Heurística (custo zero)                       │
│  • Descarta: "bom dia", "obrigado", áudios, stickers            │
│  • Passa: mensagens com keywords (plantão, vaga, R$, hospital)  │
│  • Objetivo: eliminar ~70% do volume                            │
│                                                                 │
│  ESTÁGIO 2: LLM Haiku (custo baixo)                             │
│  • Classifica: é oferta de plantão? (sim/não)                   │
│  • Só roda nos ~30% que passaram do estágio 1                   │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. EXTRACAO (E03) - Parsing estruturado                        │
│  ─────────────────────────────────────────────────────────────  │
│  • LLM Haiku extrai campos:                                     │
│    - hospital (texto bruto)                                     │
│    - data (YYYY-MM-DD)                                          │
│    - horário início/fim                                         │
│    - período (manhã/tarde/noturno/12h/24h)                      │
│    - especialidade                                              │
│    - valor (R$)                                                 │
│    - contato (telefone/nome)                                    │
│    - observações                                                │
│  • Confiança: score 0-1 em cada campo                           │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. NORMALIZACAO + MATCH (E04)                                  │
│  ─────────────────────────────────────────────────────────────  │
│  • Hospital: fuzzy match com tabela `hospitais`                 │
│    - "HSL ABC" → Hospital São Luiz ABC (85% match)              │
│    - Se < 70%: candidato para revisão/cadastro                  │
│                                                                 │
│  • Especialidade: match com `especialidades`                    │
│  • Período: normalizar para IDs existentes                      │
│                                                                 │
│  • Tabela `hospitais_alias` para aprender variações             │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  5. DEDUPLICACAO (E05)                                          │
│  ─────────────────────────────────────────────────────────────  │
│  • Chave: hash(hospital_id + data + periodo_id)                 │
│  • Janela: 48h (mesma vaga vista em 48h = duplicada)            │
│                                                                 │
│  • Se NOVA: insere em `vagas_grupo`                             │
│  • Se DUPLICADA: atualiza contador, registra fonte              │
│                                                                 │
│  • Rastreamento completo de todas as fontes                     │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  6. IMPORTACAO (E06)                                            │
│  ─────────────────────────────────────────────────────────────  │
│  AUTOMÁTICA (regras):                                           │
│  • Confiança > 90% + hospital conhecido → auto-importa          │
│  • Confiança 70-90% → fila de revisão                           │
│  • Confiança < 70% → descartada (log mantido)                   │
│                                                                 │
│  MANUAL (Slack):                                                │
│  • Gestor pode revisar fila e aprovar/rejeitar                  │
│  • "listar vagas pendentes" / "importar vaga X"                 │
└─────────────────────────────────────────────────────────────────┘
```

## Épicos

| Épico | Nome | Stories | Estimativa | Descrição |
|-------|------|---------|------------|-----------|
| E01 | Modelo de Dados | 10 | 7.25h | Schema, índices, RLS, seeds de alias |
| E02 | Ingestão de Mensagens | 7 | 7.25h | Captura e armazenamento de mensagens |
| E03 | Heurística de Classificação | 6 | 7.5h | Filtro rápido por keywords/regex |
| E04 | Classificação LLM | 5 | 8h | Classificação binária com Claude Haiku |
| E05 | Extração de Dados | 5 | 10h | Parsing estruturado (suporta múltiplas vagas) |
| E06 | Fuzzy Match de Entidades | 7 | 9.5h | Normalização de hospital/especialidade |
| E07 | Criação de Hospital via Web | 6 | 8h | Auto-criar hospitais com busca web |
| E08 | Deduplicação | 6 | 7h | Identificar vagas repetidas entre grupos |
| E09 | Importação Automática | 7 | 10h | Regras de confiança e importação |
| E10 | Interface Slack | 9 | 13h | Tools para revisão e gestão manual |
| E11 | Worker e Orquestração | 8 | 13.5h | Pipeline assíncrono com retry |
| E12 | Métricas e Monitoramento | 8 | 12.5h | Dashboard, alertas, custos |

**Total:** 84 stories | **~113.5h** (~14 dias)

### Detalhamento dos Épicos

**E01 - Modelo de Dados** ([epic-01-modelo-dados.md](epic-01-modelo-dados.md))
- Criar tabelas: `grupos_whatsapp`, `contatos_grupo`, `mensagens_grupo`, `vagas_grupo`
- Tabelas de rastreamento: `vagas_grupo_fontes`
- Tabelas de alias: `hospitais_alias`, `especialidades_alias`
- Fila de processamento: `fila_processamento_grupos`
- Índices, triggers, RLS, seeds de alias comuns

**E02 - Ingestão de Mensagens** ([epic-02-ingestao-mensagens.md](epic-02-ingestao-mensagens.md))
- Salvar mensagens de grupo (não mais ignorar)
- Criar/atualizar registros de grupos e contatos
- Integração com parser.py existente
- Enfileirar para processamento

**E03 - Heurística de Classificação** ([epic-03-heuristica-classificacao.md](epic-03-heuristica-classificacao.md))
- Keywords positivas: plantão, vaga, R$, hospitais
- Keywords negativas: bom dia, obrigado, perguntas
- Score de 0-1 baseado em matches
- Filtrar ~70% das mensagens (custo zero)

**E04 - Classificação LLM** ([epic-04-classificacao-llm.md](epic-04-classificacao-llm.md))
- Prompt binário: "É oferta de plantão?"
- Claude Haiku para custo baixo
- Cache em Redis para mensagens repetidas
- Só processa ~30% que passou da heurística

**E05 - Extração de Dados** ([epic-05-extracao-dados.md](epic-05-extracao-dados.md))
- Prompt de extração estruturada
- Suporte a múltiplas vagas por mensagem
- Validação de data (descarta passadas)
- Scores de confiança por campo

**E06 - Fuzzy Match de Entidades** ([epic-06-fuzzy-match.md](epic-06-fuzzy-match.md))
- Busca em alias primeiro (match exato)
- pg_trgm para similaridade
- Normalização de texto (acentos, lowercase)
- Match de período, setor, tipo_vaga

**E07 - Criação de Hospital via Web** ([epic-07-criacao-hospital-web.md](epic-07-criacao-hospital-web.md))
- Se fuzzy match < 70%: buscar na web
- Extrair: nome oficial, endereço, cidade
- Criar hospital + alias automaticamente
- Fallback para dados mínimos

**E08 - Deduplicação** ([epic-08-deduplicacao.md](epic-08-deduplicacao.md))
- Hash: hospital_id + data + período + especialidade
- Janela temporal de 48h
- Rastreamento de múltiplas fontes
- Incremento de contador

**E09 - Importação Automática** ([epic-09-importacao-automatica.md](epic-09-importacao-automatica.md))
- Confiança >= 90%: auto-importa
- Confiança 70-90%: fila de revisão
- Confiança < 70%: descarta
- Cálculo de confiança ponderado

**E10 - Interface Slack** ([epic-10-interface-slack.md](epic-10-interface-slack.md))
- Listar vagas para revisão
- Aprovar/rejeitar vagas
- Ver detalhes de vaga
- Estatísticas de captura
- Gerenciar aliases de hospital

**E11 - Worker e Orquestração** ([epic-11-worker-orquestracao.md](epic-11-worker-orquestracao.md))
- Fila com retry e backoff exponencial
- Pipeline com 6 estágios
- Workers paralelos (semaphore)
- Health check e reprocessamento

**E12 - Métricas e Monitoramento** ([epic-12-metricas-monitoramento.md](epic-12-metricas-monitoramento.md))
- Métricas agregadas por dia/grupo
- Dashboard no Slack
- Alertas automáticos (fila grande, erros, custo)
- Endpoint de métricas API

## Modelo de Dados

### Dependências da Tabela `vagas`

A tabela `vagas` possui os seguintes campos obrigatórios que precisamos preencher:

| Campo | Tabela FK | Obrigatório | Extração |
|-------|-----------|-------------|----------|
| `hospital_id` | `hospitais` | **SIM** | Fuzzy match do nome |
| `especialidade_id` | `especialidades` | **SIM** | Fuzzy match |
| `setor_id` | `setores` | Não | PA, RPA, Hospital, C. Cirúrgico, SADT |
| `periodo_id` | `periodos` | Não | Vespertino, Noturno, Diurno, Cinderela |
| `tipos_vaga_id` | `tipos_vaga` | Não | Cobertura, Fixo, Ambulatorial, Mensal |
| `forma_recebimento_id` | `formas_recebimento` | Não | PF, PJ, CLT, SCP |
| `data` | - | Não | Extrair da mensagem |
| `hora_inicio` | - | Não | Extrair da mensagem |
| `hora_fim` | - | Não | Extrair da mensagem |
| `valor` | - | Não | Extrair da mensagem |
| `observacoes` | - | Não | Texto adicional |

### Dados Críticos a Capturar

1. **Origem (Grupo WhatsApp):** De qual grupo veio a oferta
2. **Responsável (Quem postou):** Nome e telefone de quem publicou a vaga
3. **Hospital:** Nome do hospital/clínica
4. **Especialidade:** Qual especialidade médica
5. **Data/Horário:** Quando é o plantão
6. **Valor:** Quanto paga

### Novas Tabelas

```sql
-- Cadastro dos grupos monitorados
CREATE TABLE grupos_whatsapp (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    jid TEXT UNIQUE NOT NULL,              -- "123456@g.us"
    nome TEXT,
    descricao TEXT,
    tipo TEXT DEFAULT 'vagas',             -- "vagas", "geral", "regional"
    regiao TEXT,                           -- "ABC", "SP Capital", etc
    ativo BOOLEAN DEFAULT true,
    total_mensagens INTEGER DEFAULT 0,
    total_ofertas INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Contatos que postam vagas nos grupos (responsáveis)
CREATE TABLE contatos_grupo (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    jid TEXT UNIQUE NOT NULL,              -- "5511999999999@s.whatsapp.net"
    telefone TEXT,                         -- "5511999999999"
    nome TEXT,                             -- Nome do pushName
    empresa TEXT,                          -- Se identificável (outro staffing, hospital)
    total_vagas_postadas INTEGER DEFAULT 0,
    primeiro_contato TIMESTAMPTZ,
    ultimo_contato TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Todas as mensagens capturadas
CREATE TABLE mensagens_grupo (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    grupo_id UUID REFERENCES grupos_whatsapp(id),

    -- Quem enviou (responsável pela vaga)
    contato_id UUID REFERENCES contatos_grupo(id),
    sender_jid TEXT,
    sender_nome TEXT,

    -- Conteúdo
    texto TEXT,
    tipo_midia TEXT DEFAULT 'texto',       -- "texto", "imagem", "audio", "documento"
    message_id TEXT UNIQUE,                -- ID do WhatsApp
    timestamp_msg TIMESTAMPTZ,

    -- Processamento
    status TEXT DEFAULT 'pendente',        -- pendente, classificando, descartado_heuristica,
                                           -- classificado_oferta, classificado_nao_oferta,
                                           -- extraindo, extraido, erro
    passou_heuristica BOOLEAN,
    eh_oferta BOOLEAN,
    confianca_classificacao FLOAT,
    motivo_descarte TEXT,
    processado_em TIMESTAMPTZ,
    erro TEXT,

    created_at TIMESTAMPTZ DEFAULT now()
);

-- Vagas extraídas dos grupos (staging antes de ir para `vagas`)
CREATE TABLE vagas_grupo (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mensagem_id UUID REFERENCES mensagens_grupo(id),

    -- Origem (de onde veio a vaga)
    grupo_origem_id UUID REFERENCES grupos_whatsapp(id),
    contato_responsavel_id UUID REFERENCES contatos_grupo(id),

    -- Dados extraídos (raw do LLM)
    hospital_raw TEXT,
    especialidade_raw TEXT,
    setor_raw TEXT,
    periodo_raw TEXT,
    tipo_vaga_raw TEXT,
    forma_pagamento_raw TEXT,
    data DATE,
    hora_inicio TIME,
    hora_fim TIME,
    valor INTEGER,
    observacoes TEXT,

    -- Dados normalizados (após match com tabelas existentes)
    hospital_id UUID REFERENCES hospitais(id),
    especialidade_id UUID REFERENCES especialidades(id),
    setor_id UUID REFERENCES setores(id),
    periodo_id UUID REFERENCES periodos(id),
    tipos_vaga_id UUID REFERENCES tipos_vaga(id),
    forma_recebimento_id UUID REFERENCES formas_recebimento(id),

    -- Scores de confiança (0-1)
    confianca_geral FLOAT,                 -- Média ponderada
    confianca_hospital FLOAT,
    confianca_especialidade FLOAT,
    confianca_data FLOAT,
    confianca_valor FLOAT,
    campos_faltando TEXT[],                -- Lista de campos que não conseguiu extrair

    -- Deduplicação
    hash_dedup TEXT,                       -- hash(hospital_id+data+periodo_id+especialidade_id)
    eh_duplicada BOOLEAN DEFAULT false,
    duplicada_de UUID REFERENCES vagas_grupo(id),

    -- Rastreamento de múltiplas fontes
    qtd_fontes INTEGER DEFAULT 1,          -- Quantos grupos postaram esta vaga

    -- Status e importação
    status TEXT DEFAULT 'nova',            -- nova, duplicada, importada, descartada, revisao, erro
    importada_para UUID REFERENCES vagas(id),
    motivo_status TEXT,

    -- Auditoria
    revisada_por TEXT,
    revisada_em TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Rastreamento de fontes (uma vaga pode vir de múltiplos grupos)
CREATE TABLE vagas_grupo_fontes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vaga_grupo_id UUID REFERENCES vagas_grupo(id) ON DELETE CASCADE,
    mensagem_id UUID REFERENCES mensagens_grupo(id),
    grupo_id UUID REFERENCES grupos_whatsapp(id),
    contato_id UUID REFERENCES contatos_grupo(id),
    ordem INTEGER DEFAULT 1,               -- 1 = primeira fonte, 2 = segunda, etc
    created_at TIMESTAMPTZ DEFAULT now(),

    UNIQUE(vaga_grupo_id, mensagem_id)     -- Evita duplicar mesma mensagem
);

-- Alias de hospitais (para normalização aprender variações de nome)
CREATE TABLE hospitais_alias (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hospital_id UUID REFERENCES hospitais(id) ON DELETE CASCADE,
    alias TEXT NOT NULL,                   -- "HSL", "São Luiz ABC", "HSLZ"
    confianca FLOAT DEFAULT 1.0,           -- 1.0 = confirmado manual, <1.0 = inferido
    criado_por TEXT,                       -- "sistema", "importacao", ou user_id
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(hospital_id, alias)
);

-- Alias de especialidades (mesma lógica)
CREATE TABLE especialidades_alias (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    especialidade_id UUID REFERENCES especialidades(id) ON DELETE CASCADE,
    alias TEXT NOT NULL,                   -- "cardio", "CM", "GO"
    confianca FLOAT DEFAULT 1.0,
    criado_por TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(especialidade_id, alias)
);

-- Índices para performance
CREATE INDEX idx_mensagens_grupo_status ON mensagens_grupo(status);
CREATE INDEX idx_mensagens_grupo_timestamp ON mensagens_grupo(timestamp_msg);
CREATE INDEX idx_mensagens_grupo_grupo ON mensagens_grupo(grupo_id);
CREATE INDEX idx_vagas_grupo_status ON vagas_grupo(status);
CREATE INDEX idx_vagas_grupo_hash ON vagas_grupo(hash_dedup);
CREATE INDEX idx_vagas_grupo_data ON vagas_grupo(data);
CREATE INDEX idx_vagas_grupo_grupo ON vagas_grupo(grupo_origem_id);
CREATE INDEX idx_vagas_grupo_hospital ON vagas_grupo(hospital_id);
CREATE INDEX idx_hospitais_alias_alias ON hospitais_alias(alias);
CREATE INDEX idx_especialidades_alias_alias ON especialidades_alias(alias);
```

### Fluxo de Importação para Tabela `vagas`

Quando uma vaga é aprovada para importação:

```sql
-- Exemplo de INSERT na tabela vagas a partir de vagas_grupo
INSERT INTO vagas (
    hospital_id,
    especialidade_id,
    setor_id,
    periodo_id,
    tipos_vaga_id,
    forma_recebimento_id,
    data,
    hora_inicio,
    hora_fim,
    valor,
    observacoes,
    status,
    created_at
)
SELECT
    vg.hospital_id,
    vg.especialidade_id,
    vg.setor_id,
    vg.periodo_id,
    vg.tipos_vaga_id,
    vg.forma_recebimento_id,
    vg.data,
    vg.hora_inicio,
    vg.hora_fim,
    vg.valor,
    CONCAT(
        'Origem: Grupo WhatsApp (', g.nome, '). ',
        'Contato: ', c.nome, ' (', c.telefone, '). ',
        vg.observacoes
    ),
    'aberta',
    now()
FROM vagas_grupo vg
JOIN grupos_whatsapp g ON g.id = vg.grupo_origem_id
JOIN contatos_grupo c ON c.id = vg.contato_responsavel_id
WHERE vg.id = :vaga_grupo_id
  AND vg.hospital_id IS NOT NULL      -- Obrigatório
  AND vg.especialidade_id IS NOT NULL -- Obrigatório
RETURNING id;
```

## Estimativa de Custos LLM

| Etapa | Volume/dia | Modelo | Tokens/msg | Custo/dia |
|-------|------------|--------|------------|-----------|
| Classificação | ~600 msgs | Haiku | ~200 | ~$0.15 |
| Extração | ~150 ofertas | Haiku | ~400 | ~$0.06 |
| **Total** | | | | **~$0.20/dia** |

**Nota:** Custo muito baixo porque:
1. Heurística filtra 70% antes do LLM
2. Haiku é o modelo mais barato ($0.25/1M tokens input)

## Dependências

- Webhook Evolution API (já implementado)
- Parser de mensagens (já identifica grupos)
- Tabelas `hospitais`, `especialidades`, `periodos` (já existem)
- Embeddings Voyage AI (para fuzzy match - opcional)
- Redis (para cache de alias)

## Ordem de Execução

```
                           FASE 1: FUNDAÇÃO
┌──────────────────────────────────────────────────────────┐
│  E01 (Modelo de Dados) ──► E02 (Ingestão)                │
└──────────────────────────────────────────────────────────┘
                              │
                              ▼
                        FASE 2: CLASSIFICAÇÃO
┌──────────────────────────────────────────────────────────┐
│  E03 (Heurística) ──► E04 (Classificação LLM)            │
└──────────────────────────────────────────────────────────┘
                              │
                              ▼
                        FASE 3: EXTRAÇÃO
┌──────────────────────────────────────────────────────────┐
│  E05 (Extração de Dados)                                 │
└──────────────────────────────────────────────────────────┘
                              │
                              ▼
                        FASE 4: NORMALIZAÇÃO
┌──────────────────────────────────────────────────────────┐
│  E06 (Fuzzy Match) ──► E07 (Criação Hospital Web)        │
└──────────────────────────────────────────────────────────┘
                              │
                              ▼
                        FASE 5: PROCESSAMENTO
┌──────────────────────────────────────────────────────────┐
│  E08 (Deduplicação) ──► E09 (Importação Automática)      │
└──────────────────────────────────────────────────────────┘
                              │
                              ▼
                        FASE 6: OPERAÇÃO
┌──────────────────────────────────────────────────────────┐
│  E10 (Interface Slack)                                   │
│  E11 (Worker e Orquestração)                             │
│  E12 (Métricas e Monitoramento)                          │
└──────────────────────────────────────────────────────────┘
```

## Critérios de Aceite da Sprint

- [ ] Mensagens de grupo sendo salvas (não mais ignoradas)
- [ ] Heurística filtrando >60% das mensagens não-ofertas
- [ ] LLM classificando ofertas com >85% precisão
- [ ] Extração capturando hospital, data, valor em >80% dos casos
- [ ] Fuzzy match de hospitais funcionando com >75% precisão
- [ ] Deduplicação identificando vagas repetidas
- [ ] Importação automática para vagas de alta confiança
- [ ] Rastreamento completo de fontes
- [ ] Métricas de pipeline disponíveis (volume, conversão, confiança)

## Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Volume maior que esperado | Média | Médio | Rate limiting no worker, batching |
| Precisão baixa de extração | Média | Alto | Prompt engineering iterativo, exemplos |
| Muitos hospitais desconhecidos | Alta | Médio | Fila de revisão, aprendizado de alias |
| Latência do pipeline | Baixa | Médio | Workers assíncronos, não bloqueia webhook |

## Métricas de Sucesso

| Métrica | Meta |
|---------|------|
| Mensagens capturadas/dia | 100% do volume |
| Taxa filtro heurístico | >60% descartadas |
| Precisão classificação LLM | >85% |
| Precisão extração (campos críticos) | >80% |
| Precisão fuzzy match hospital | >75% |
| Taxa deduplicação | Medir (sem meta inicial) |
| Taxa importação automática | >50% das vagas válidas |
| Latência média do pipeline | <5 min (não real-time) |

## Arquivos a Criar

```
app/
├── services/
│   ├── grupos/
│   │   ├── __init__.py
│   │   ├── ingestor.py           # E01: Salva mensagens
│   │   ├── classificador.py      # E02: Heurística + LLM
│   │   ├── extrator.py           # E03: Parsing com LLM
│   │   ├── normalizador.py       # E04: Fuzzy match
│   │   ├── deduplicador.py       # E05: Hash + janela temporal
│   │   ├── importador.py         # E06: Regras de importação
│   │   └── worker.py             # Orquestra o pipeline
│   │
│   └── parser.py                 # Modificar para não ignorar grupos
│
├── tools/
│   └── slack/
│       └── grupos.py             # E06: Tools de gestão via Slack
│
├── api/
│   └── routes/
│       └── grupos.py             # Endpoints de métricas/admin
│
tests/
├── grupos/
│   ├── test_ingestor.py
│   ├── test_classificador.py
│   ├── test_extrator.py
│   ├── test_normalizador.py
│   ├── test_deduplicador.py
│   └── test_importador.py

scripts/
└── backfill_grupos.py            # Importar grupos existentes
```

## Timeline Sugerido

| Fase | Épicos | Estimativa |
|------|--------|------------|
| Fase 1: Fundação | E01, E02 | 2 dias |
| Fase 2: Classificação | E03, E04 | 2 dias |
| Fase 3: Extração | E05 | 1.5 dias |
| Fase 4: Normalização | E06, E07 | 2.5 dias |
| Fase 5: Processamento | E08, E09 | 2 dias |
| Fase 6: Operação | E10, E11, E12 | 4 dias |

**Total estimado:** 14 dias (~3 semanas)

## Notas de Implementação

### Heurística de Classificação (E02)

Keywords positivas (indica oferta):
- `plantão`, `plantao`, `vaga`, `escala`
- `R$`, `reais`, `pago`, `valor`
- Nomes de hospitais conhecidos
- Especialidades médicas
- Datas (dd/mm, dia XX)

Keywords negativas (indica conversa normal):
- `bom dia`, `boa tarde`, `boa noite`
- `obrigado`, `obrigada`, `valeu`
- `?` no final (pergunta)
- Mensagens muito curtas (<10 chars)

### Prompt de Extração (E03)

**IMPORTANTE:** Uma mensagem pode conter MÚLTIPLAS vagas. O prompt retorna um ARRAY.

```
Você é um extrator de dados de ofertas de plantão médico.
Analise a mensagem abaixo e extraia os dados estruturados.

IMPORTANTE: Uma mensagem pode conter MÚLTIPLAS vagas (ex: lista de escalas).
Retorne um ARRAY de vagas, mesmo que seja apenas uma.

Data de hoje: {data_hoje}

Para CADA VAGA encontrada, extraia:

OBRIGATÓRIOS (sem estes a vaga não pode ser importada):
- hospital: nome do hospital/clínica/UPA
- especialidade: especialidade médica requerida

IMPORTANTES:
- data: data no formato YYYY-MM-DD (se "amanhã", "segunda", calcule a data real)
- hora_inicio: horário de início HH:MM
- hora_fim: horário de fim HH:MM
- valor: valor em reais (apenas número inteiro, sem centavos)

OPCIONAIS:
- periodo: um de [Diurno, Vespertino, Noturno, Cinderela, Meio período (manhã), Meio período (tarde)]
- setor: um de [Pronto atendimento, RPA, Hospital, C. Cirúrgico, SADT]
- tipo_vaga: um de [Cobertura, Fixo, Ambulatorial, Mensal]
- forma_pagamento: um de [Pessoa fisica, Pessoa jurídica, CLT, SCP, Sócio cotista]
- observacoes: outras informações relevantes (exigências, benefícios, etc)

REGRAS:
1. Se a data da vaga for ANTERIOR a hoje, marque data_valida: false
2. Se não conseguir identificar hospital OU especialidade, não inclua a vaga
3. Campos compartilhados (ex: mesmo hospital para várias datas) devem ser repetidos em cada vaga

CONFIANÇA (0 a 1):
- 1.0: Informação explícita e clara
- 0.7-0.9: Inferida com alta certeza
- 0.4-0.6: Inferida com incerteza
- null: Não extraído

Formato de resposta:
{
  "vagas": [
    {
      "dados": {
        "hospital": "Hospital São Luiz ABC",
        "especialidade": "Clínica Médica",
        "data": "2024-12-28",
        "hora_inicio": "19:00",
        "hora_fim": "07:00",
        "valor": 1800,
        "periodo": "Noturno",
        "forma_pagamento": "Pessoa jurídica"
      },
      "confianca": {
        "hospital": 0.95,
        "especialidade": 0.90,
        "data": 1.0,
        "valor": 0.95
      },
      "data_valida": true,
      "campos_faltando": ["setor"]
    }
  ],
  "total_vagas": 1,
  "tem_vaga_passada": false
}

Mensagem do grupo:
{texto}

Contexto adicional:
- Grupo: {nome_grupo}
- Região: {regiao_grupo}
- Quem postou: {nome_contato}
```

### Exemplos de Mensagens Reais (para calibrar)

**Exemplo 1 - Completa:**
```
🚨 VAGA URGENTE 🚨
Hospital São Luiz ABC
Clínica Médica
Dia 28/12 - Noturno (19h às 7h)
Valor: R$ 1.800,00 PJ
Interessados chamar: (11) 99999-8888
```

**Exemplo 2 - Parcial:**
```
Pessoal, preciso de cardio pro HU Santo André amanhã de manhã
Pago 2k, quem topa?
```

**Exemplo 3 - Vaga em lote:**
```
Escalas disponíveis São Camilo Pompéia:
- 26/12 Diurno CM
- 27/12 Noturno Pediatria
- 28/12 24h Ortopedia
Valores a combinar. Ligar 11 98765-4321
```

### Fuzzy Match de Hospital (E04)

1. Normalizar texto (lowercase, remover acentos)
2. Buscar match exato em `hospitais_alias`
3. Se não encontrar, calcular similaridade com todos hospitais
4. Se similaridade > 70%, usar match
5. Se < 70%, **criar novo hospital** (ver abaixo)
6. Salvar alias em `hospitais_alias` para aprendizado futuro

### Criação de Hospital Desconhecido (E04)

Quando não encontrar match para um hospital, o sistema deve:

1. **Buscar na web** informações sobre o hospital
   - Usar WebSearch para encontrar dados
   - Buscar: "{nome_hospital} hospital endereço cidade"

2. **Extrair dados** do resultado:
   - Nome completo oficial
   - Endereço (logradouro, número, bairro)
   - Cidade e Estado
   - CEP (se disponível)

3. **Criar registro** na tabela `hospitais`:
   ```sql
   INSERT INTO hospitais (nome, logradouro, numero, bairro, cidade, estado, cep)
   VALUES (...);
   ```

4. **Criar alias** automaticamente:
   ```sql
   INSERT INTO hospitais_alias (hospital_id, alias, criado_por)
   VALUES (novo_id, 'nome_original_da_mensagem', 'sistema_auto');
   ```

5. **Fallback** se busca web falhar:
   - Criar hospital apenas com nome
   - Marcar `cidade` e `estado` baseado na região do grupo (se disponível)
   - Marcar para revisão manual posterior

**Prompt para enriquecimento via web:**
```
Busque informações sobre o hospital/clínica: "{nome_hospital}"
Região provável: {regiao_grupo}

Retorne JSON com:
{
  "nome_oficial": "Nome completo do hospital",
  "logradouro": "Rua/Av...",
  "numero": "123",
  "bairro": "...",
  "cidade": "...",
  "estado": "SP",
  "cep": "00000-000",
  "confianca": 0.85,
  "fonte": "URL de onde veio a informação"
}

Se não encontrar, retorne: {"encontrado": false}
```
