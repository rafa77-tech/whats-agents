# E01 - Modelo de Dados

## Objetivo

Criar todas as tabelas necessárias para o sistema de scraping de vagas de grupos WhatsApp.

## Contexto

Este épico é pré-requisito para todos os outros. Define a estrutura de dados que suportará:
- Cadastro de grupos e contatos
- Armazenamento de mensagens
- Staging de vagas extraídas
- Rastreamento de fontes e duplicatas
- Aprendizado de alias

## Stories

### S01.1 - Criar tabela `grupos_whatsapp`

**Descrição:** Tabela para cadastro dos grupos de WhatsApp monitorados.

**Critérios de Aceite:**
- [ ] Tabela criada com todos os campos especificados
- [ ] Constraint UNIQUE em `jid`
- [ ] Índice em `ativo` para queries de grupos ativos
- [ ] RLS habilitado
- [ ] Migration criada e aplicada

**Schema:**
```sql
CREATE TABLE grupos_whatsapp (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    jid TEXT UNIQUE NOT NULL,              -- "123456789-987654321@g.us"
    nome TEXT,                             -- Nome do grupo no WhatsApp
    descricao TEXT,                        -- Descrição manual do grupo
    tipo TEXT DEFAULT 'vagas',             -- "vagas", "geral", "regional", "hospital"
    regiao TEXT,                           -- "ABC", "SP Capital", "Campinas", etc
    hospital_id UUID REFERENCES hospitais(id), -- Se for grupo de hospital específico
    ativo BOOLEAN DEFAULT true,
    monitorar_ofertas BOOLEAN DEFAULT true, -- Se deve processar ofertas deste grupo

    -- Métricas
    total_mensagens INTEGER DEFAULT 0,
    total_ofertas_detectadas INTEGER DEFAULT 0,
    total_vagas_importadas INTEGER DEFAULT 0,

    -- Timestamps
    primeira_mensagem_em TIMESTAMPTZ,
    ultima_mensagem_em TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Índices
CREATE INDEX idx_grupos_whatsapp_ativo ON grupos_whatsapp(ativo) WHERE ativo = true;
CREATE INDEX idx_grupos_whatsapp_tipo ON grupos_whatsapp(tipo);
CREATE INDEX idx_grupos_whatsapp_regiao ON grupos_whatsapp(regiao);

-- RLS
ALTER TABLE grupos_whatsapp ENABLE ROW LEVEL SECURITY;
```

**Estimativa:** 0.5h

---

### S01.2 - Criar tabela `contatos_grupo`

**Descrição:** Tabela para armazenar contatos que postam vagas nos grupos.

**Critérios de Aceite:**
- [ ] Tabela criada com todos os campos especificados
- [ ] Constraint UNIQUE em `jid`
- [ ] Índice em `telefone` para busca rápida
- [ ] RLS habilitado
- [ ] Migration criada e aplicada

**Schema:**
```sql
CREATE TABLE contatos_grupo (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    jid TEXT UNIQUE NOT NULL,              -- "5511999999999@s.whatsapp.net"
    telefone TEXT,                         -- "5511999999999" (extraído do JID)
    nome TEXT,                             -- pushName do WhatsApp

    -- Identificação (preenchido manualmente ou inferido)
    empresa TEXT,                          -- "Revoluna", "MedStaff", "Hospital X"
    tipo TEXT DEFAULT 'desconhecido',      -- "escalista", "hospital", "medico", "desconhecido"

    -- Métricas
    total_mensagens INTEGER DEFAULT 0,
    total_vagas_postadas INTEGER DEFAULT 0,
    total_vagas_validas INTEGER DEFAULT 0, -- Vagas que foram importadas
    taxa_qualidade FLOAT,                  -- % de vagas válidas

    -- Relacionamento
    cliente_id UUID REFERENCES clientes(id), -- Se for um médico conhecido

    -- Timestamps
    primeiro_contato TIMESTAMPTZ,
    ultimo_contato TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Índices
CREATE INDEX idx_contatos_grupo_telefone ON contatos_grupo(telefone);
CREATE INDEX idx_contatos_grupo_empresa ON contatos_grupo(empresa);
CREATE INDEX idx_contatos_grupo_tipo ON contatos_grupo(tipo);

-- RLS
ALTER TABLE contatos_grupo ENABLE ROW LEVEL SECURITY;
```

**Estimativa:** 0.5h

---

### S01.3 - Criar tabela `mensagens_grupo`

**Descrição:** Tabela para armazenar todas as mensagens capturadas dos grupos.

**Critérios de Aceite:**
- [ ] Tabela criada com todos os campos especificados
- [ ] Constraint UNIQUE em `message_id`
- [ ] Índices para queries de processamento
- [ ] RLS habilitado
- [ ] Migration criada e aplicada

**Schema:**
```sql
CREATE TABLE mensagens_grupo (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Origem
    grupo_id UUID NOT NULL REFERENCES grupos_whatsapp(id),
    contato_id UUID REFERENCES contatos_grupo(id),

    -- Dados do WhatsApp
    message_id TEXT UNIQUE NOT NULL,       -- ID único da mensagem no WhatsApp
    sender_jid TEXT NOT NULL,              -- JID de quem enviou
    sender_nome TEXT,                      -- pushName de quem enviou

    -- Conteúdo
    texto TEXT,                            -- Texto da mensagem
    tipo_midia TEXT DEFAULT 'texto',       -- "texto", "imagem", "audio", "video", "documento", "sticker"
    tem_midia BOOLEAN DEFAULT false,       -- Se tem anexo de mídia

    -- Metadados do WhatsApp
    timestamp_msg TIMESTAMPTZ NOT NULL,    -- Timestamp da mensagem no WhatsApp
    is_forwarded BOOLEAN DEFAULT false,    -- Se é mensagem encaminhada
    is_reply BOOLEAN DEFAULT false,        -- Se é resposta a outra mensagem
    reply_to_id TEXT,                      -- ID da mensagem respondida

    -- Pipeline de processamento
    status TEXT DEFAULT 'pendente',
    -- Valores possíveis:
    -- 'pendente' - Aguardando processamento
    -- 'ignorada_midia' - Ignorada por ser mídia (não texto)
    -- 'ignorada_curta' - Ignorada por ser muito curta
    -- 'heuristica_passou' - Passou pela heurística, aguarda LLM
    -- 'heuristica_rejeitou' - Rejeitada pela heurística
    -- 'classificada_oferta' - LLM classificou como oferta
    -- 'classificada_nao_oferta' - LLM classificou como não-oferta
    -- 'extraida' - Dados extraídos com sucesso
    -- 'extracao_falhou' - Falha na extração
    -- 'erro' - Erro no processamento

    -- Resultados do processamento
    passou_heuristica BOOLEAN,
    score_heuristica FLOAT,                -- Score da heurística (0-1)
    keywords_encontradas TEXT[],           -- Keywords que matcharam

    eh_oferta BOOLEAN,
    confianca_classificacao FLOAT,         -- Confiança do LLM na classificação

    qtd_vagas_extraidas INTEGER DEFAULT 0, -- Quantas vagas foram extraídas

    -- Erros
    erro TEXT,
    tentativas INTEGER DEFAULT 0,

    -- Timestamps de processamento
    processado_em TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Índices para processamento
CREATE INDEX idx_mensagens_grupo_status ON mensagens_grupo(status);
CREATE INDEX idx_mensagens_grupo_pendentes ON mensagens_grupo(status, created_at)
    WHERE status = 'pendente';
CREATE INDEX idx_mensagens_grupo_heuristica ON mensagens_grupo(status, created_at)
    WHERE status = 'heuristica_passou';

-- Índices para consulta
CREATE INDEX idx_mensagens_grupo_grupo ON mensagens_grupo(grupo_id);
CREATE INDEX idx_mensagens_grupo_contato ON mensagens_grupo(contato_id);
CREATE INDEX idx_mensagens_grupo_timestamp ON mensagens_grupo(timestamp_msg DESC);
CREATE INDEX idx_mensagens_grupo_ofertas ON mensagens_grupo(grupo_id, timestamp_msg)
    WHERE eh_oferta = true;

-- RLS
ALTER TABLE mensagens_grupo ENABLE ROW LEVEL SECURITY;
```

**Estimativa:** 1h

---

### S01.4 - Criar tabela `vagas_grupo`

**Descrição:** Tabela de staging para vagas extraídas antes de importação.

**Critérios de Aceite:**
- [ ] Tabela criada com todos os campos especificados
- [ ] FKs para todas as tabelas relacionadas
- [ ] Índices para deduplicação e consulta
- [ ] RLS habilitado
- [ ] Migration criada e aplicada

**Schema:**
```sql
CREATE TABLE vagas_grupo (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Origem
    mensagem_id UUID NOT NULL REFERENCES mensagens_grupo(id),
    grupo_origem_id UUID NOT NULL REFERENCES grupos_whatsapp(id),
    contato_responsavel_id UUID REFERENCES contatos_grupo(id),

    -- Dados extraídos (raw do LLM) - texto original
    hospital_raw TEXT,
    especialidade_raw TEXT,
    setor_raw TEXT,
    periodo_raw TEXT,
    tipo_vaga_raw TEXT,
    forma_pagamento_raw TEXT,

    -- Dados extraídos (valores)
    data DATE,
    hora_inicio TIME,
    hora_fim TIME,
    valor INTEGER,                         -- Em reais (sem centavos)
    observacoes TEXT,

    -- Dados normalizados (FKs para tabelas existentes)
    hospital_id UUID REFERENCES hospitais(id),
    especialidade_id UUID REFERENCES especialidades(id),
    setor_id UUID REFERENCES setores(id),
    periodo_id UUID REFERENCES periodos(id),
    tipos_vaga_id UUID REFERENCES tipos_vaga(id),
    forma_recebimento_id UUID REFERENCES formas_recebimento(id),

    -- Flags de normalização
    hospital_criado BOOLEAN DEFAULT false,  -- Se o hospital foi criado automaticamente
    hospital_match_score FLOAT,             -- Score do fuzzy match
    especialidade_match_score FLOAT,

    -- Scores de confiança (0-1)
    confianca_geral FLOAT,                  -- Média ponderada
    confianca_hospital FLOAT,
    confianca_especialidade FLOAT,
    confianca_data FLOAT,
    confianca_horario FLOAT,
    confianca_valor FLOAT,
    campos_faltando TEXT[],                 -- Lista de campos não extraídos

    -- Validação
    data_valida BOOLEAN DEFAULT true,       -- Se data >= hoje
    dados_minimos_ok BOOLEAN DEFAULT false, -- Se tem hospital + especialidade

    -- Deduplicação
    hash_dedup TEXT,                        -- MD5(hospital_id + data + periodo_id + especialidade_id)
    eh_duplicada BOOLEAN DEFAULT false,
    duplicada_de UUID REFERENCES vagas_grupo(id),
    qtd_fontes INTEGER DEFAULT 1,           -- Quantos grupos postaram esta vaga

    -- Status do pipeline
    status TEXT DEFAULT 'nova',
    -- Valores possíveis:
    -- 'nova' - Recém extraída
    -- 'normalizando' - Em processo de normalização
    -- 'normalizada' - Normalização completa
    -- 'duplicada' - Identificada como duplicata
    -- 'aguardando_revisao' - Confiança média, aguarda revisão
    -- 'aprovada' - Aprovada para importação
    -- 'importada' - Já importada para tabela vagas
    -- 'rejeitada' - Rejeitada manualmente
    -- 'descartada' - Descartada automaticamente (confiança baixa)
    -- 'erro' - Erro no processamento

    motivo_status TEXT,                     -- Explicação do status

    -- Importação
    importada_para UUID REFERENCES vagas(id),
    importada_em TIMESTAMPTZ,

    -- Revisão manual
    revisada_por TEXT,
    revisada_em TIMESTAMPTZ,
    notas_revisao TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Índices para deduplicação
CREATE INDEX idx_vagas_grupo_hash ON vagas_grupo(hash_dedup) WHERE hash_dedup IS NOT NULL;
CREATE INDEX idx_vagas_grupo_dedup ON vagas_grupo(hospital_id, data, periodo_id, especialidade_id)
    WHERE eh_duplicada = false;

-- Índices para pipeline
CREATE INDEX idx_vagas_grupo_status ON vagas_grupo(status);
CREATE INDEX idx_vagas_grupo_revisao ON vagas_grupo(status, created_at)
    WHERE status = 'aguardando_revisao';
CREATE INDEX idx_vagas_grupo_aprovadas ON vagas_grupo(status, created_at)
    WHERE status = 'aprovada';

-- Índices para consulta
CREATE INDEX idx_vagas_grupo_data ON vagas_grupo(data);
CREATE INDEX idx_vagas_grupo_hospital ON vagas_grupo(hospital_id);
CREATE INDEX idx_vagas_grupo_grupo ON vagas_grupo(grupo_origem_id);
CREATE INDEX idx_vagas_grupo_mensagem ON vagas_grupo(mensagem_id);

-- RLS
ALTER TABLE vagas_grupo ENABLE ROW LEVEL SECURITY;
```

**Estimativa:** 1.5h

---

### S01.5 - Criar tabela `vagas_grupo_fontes`

**Descrição:** Tabela para rastrear múltiplas fontes de uma mesma vaga.

**Critérios de Aceite:**
- [ ] Tabela criada com todos os campos especificados
- [ ] Constraint UNIQUE para evitar duplicatas
- [ ] Índices para consulta
- [ ] RLS habilitado
- [ ] Migration criada e aplicada

**Schema:**
```sql
CREATE TABLE vagas_grupo_fontes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Relacionamentos
    vaga_grupo_id UUID NOT NULL REFERENCES vagas_grupo(id) ON DELETE CASCADE,
    mensagem_id UUID NOT NULL REFERENCES mensagens_grupo(id),
    grupo_id UUID NOT NULL REFERENCES grupos_whatsapp(id),
    contato_id UUID REFERENCES contatos_grupo(id),

    -- Ordem de descoberta
    ordem INTEGER DEFAULT 1,               -- 1 = primeira fonte, 2 = segunda, etc

    -- Dados da fonte
    texto_original TEXT,                   -- Texto da mensagem original
    valor_informado INTEGER,               -- Valor informado nesta fonte (pode variar)

    -- Timestamp
    created_at TIMESTAMPTZ DEFAULT now(),

    -- Evita duplicar mesma mensagem como fonte
    UNIQUE(vaga_grupo_id, mensagem_id)
);

-- Índices
CREATE INDEX idx_vagas_grupo_fontes_vaga ON vagas_grupo_fontes(vaga_grupo_id);
CREATE INDEX idx_vagas_grupo_fontes_grupo ON vagas_grupo_fontes(grupo_id);
CREATE INDEX idx_vagas_grupo_fontes_mensagem ON vagas_grupo_fontes(mensagem_id);

-- RLS
ALTER TABLE vagas_grupo_fontes ENABLE ROW LEVEL SECURITY;
```

**Estimativa:** 0.5h

---

### S01.6 - Criar tabela `hospitais_alias`

**Descrição:** Tabela para armazenar variações de nomes de hospitais.

**Critérios de Aceite:**
- [ ] Tabela criada com todos os campos especificados
- [ ] Constraint UNIQUE para evitar alias duplicados
- [ ] Índice para busca rápida por alias
- [ ] Migration criada e aplicada

**Schema:**
```sql
CREATE TABLE hospitais_alias (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hospital_id UUID NOT NULL REFERENCES hospitais(id) ON DELETE CASCADE,

    alias TEXT NOT NULL,                   -- "HSL", "São Luiz ABC", "HSLZ"
    alias_normalizado TEXT NOT NULL,       -- Versão lowercase sem acentos para busca

    -- Origem do alias
    origem TEXT DEFAULT 'sistema',         -- "sistema", "manual", "importacao"
    criado_por TEXT,                       -- User ID ou "sistema_auto"

    -- Confiança
    confianca FLOAT DEFAULT 1.0,           -- 1.0 = confirmado, <1.0 = inferido
    confirmado BOOLEAN DEFAULT false,      -- Se foi confirmado manualmente

    -- Uso
    vezes_usado INTEGER DEFAULT 0,         -- Quantas vezes este alias foi matchado
    ultimo_uso TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now(),

    UNIQUE(hospital_id, alias_normalizado)
);

-- Índices para busca
CREATE INDEX idx_hospitais_alias_normalizado ON hospitais_alias(alias_normalizado);
CREATE INDEX idx_hospitais_alias_hospital ON hospitais_alias(hospital_id);

-- Trigger para normalizar alias automaticamente
CREATE OR REPLACE FUNCTION normalizar_alias()
RETURNS TRIGGER AS $$
BEGIN
    NEW.alias_normalizado := lower(unaccent(NEW.alias));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_normalizar_hospital_alias
    BEFORE INSERT OR UPDATE ON hospitais_alias
    FOR EACH ROW EXECUTE FUNCTION normalizar_alias();
```

**Estimativa:** 0.5h

---

### S01.7 - Criar tabela `especialidades_alias`

**Descrição:** Tabela para armazenar variações de nomes de especialidades.

**Critérios de Aceite:**
- [ ] Tabela criada com todos os campos especificados
- [ ] Constraint UNIQUE para evitar alias duplicados
- [ ] Índice para busca rápida por alias
- [ ] Migration criada e aplicada

**Schema:**
```sql
CREATE TABLE especialidades_alias (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    especialidade_id UUID NOT NULL REFERENCES especialidades(id) ON DELETE CASCADE,

    alias TEXT NOT NULL,                   -- "cardio", "CM", "GO", "pediatra"
    alias_normalizado TEXT NOT NULL,       -- Versão lowercase sem acentos

    -- Origem
    origem TEXT DEFAULT 'sistema',
    criado_por TEXT,

    -- Confiança
    confianca FLOAT DEFAULT 1.0,
    confirmado BOOLEAN DEFAULT false,

    -- Uso
    vezes_usado INTEGER DEFAULT 0,
    ultimo_uso TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now(),

    UNIQUE(especialidade_id, alias_normalizado)
);

-- Índices
CREATE INDEX idx_especialidades_alias_normalizado ON especialidades_alias(alias_normalizado);
CREATE INDEX idx_especialidades_alias_especialidade ON especialidades_alias(especialidade_id);

-- Trigger para normalizar
CREATE TRIGGER trigger_normalizar_especialidade_alias
    BEFORE INSERT OR UPDATE ON especialidades_alias
    FOR EACH ROW EXECUTE FUNCTION normalizar_alias();
```

**Estimativa:** 0.5h

---

### S01.8 - Seed de alias comuns

**Descrição:** Popular tabelas de alias com variações conhecidas.

**Critérios de Aceite:**
- [ ] Alias de especialidades comuns cadastrados
- [ ] Script de seed criado e executado
- [ ] Documentação das abreviações

**Dados iniciais - Especialidades:**
```sql
-- Clínica Médica
INSERT INTO especialidades_alias (especialidade_id, alias, origem, confirmado)
SELECT id, 'CM', 'seed', true FROM especialidades WHERE nome ILIKE '%clínica médica%';
INSERT INTO especialidades_alias (especialidade_id, alias, origem, confirmado)
SELECT id, 'clinica', 'seed', true FROM especialidades WHERE nome ILIKE '%clínica médica%';

-- Cardiologia
INSERT INTO especialidades_alias (especialidade_id, alias, origem, confirmado)
SELECT id, 'cardio', 'seed', true FROM especialidades WHERE nome ILIKE '%cardiologia%';

-- Pediatria
INSERT INTO especialidades_alias (especialidade_id, alias, origem, confirmado)
SELECT id, 'pedi', 'seed', true FROM especialidades WHERE nome ILIKE '%pediatria%';
INSERT INTO especialidades_alias (especialidade_id, alias, origem, confirmado)
SELECT id, 'ped', 'seed', true FROM especialidades WHERE nome ILIKE '%pediatria%';

-- Ortopedia
INSERT INTO especialidades_alias (especialidade_id, alias, origem, confirmado)
SELECT id, 'orto', 'seed', true FROM especialidades WHERE nome ILIKE '%ortopedia%';

-- Ginecologia/Obstetrícia
INSERT INTO especialidades_alias (especialidade_id, alias, origem, confirmado)
SELECT id, 'GO', 'seed', true FROM especialidades WHERE nome ILIKE '%ginecologia%';
INSERT INTO especialidades_alias (especialidade_id, alias, origem, confirmado)
SELECT id, 'gine', 'seed', true FROM especialidades WHERE nome ILIKE '%ginecologia%';

-- Cirurgia Geral
INSERT INTO especialidades_alias (especialidade_id, alias, origem, confirmado)
SELECT id, 'CG', 'seed', true FROM especialidades WHERE nome ILIKE '%cirurgia geral%';

-- Anestesiologia
INSERT INTO especialidades_alias (especialidade_id, alias, origem, confirmado)
SELECT id, 'anestesio', 'seed', true FROM especialidades WHERE nome ILIKE '%anestesiologia%';

-- UTI
INSERT INTO especialidades_alias (especialidade_id, alias, origem, confirmado)
SELECT id, 'intensivista', 'seed', true FROM especialidades WHERE nome ILIKE '%terapia intensiva%';
INSERT INTO especialidades_alias (especialidade_id, alias, origem, confirmado)
SELECT id, 'UTI', 'seed', true FROM especialidades WHERE nome ILIKE '%terapia intensiva%';
```

**Estimativa:** 1h

---

### S01.9 - Criar função de busca por alias

**Descrição:** Criar funções SQL para busca eficiente por alias.

**Critérios de Aceite:**
- [ ] Função `buscar_hospital_por_alias` criada
- [ ] Função `buscar_especialidade_por_alias` criada
- [ ] Testes das funções

**Schema:**
```sql
-- Buscar hospital por alias (retorna ID e score)
CREATE OR REPLACE FUNCTION buscar_hospital_por_alias(p_texto TEXT)
RETURNS TABLE (hospital_id UUID, nome TEXT, score FLOAT) AS $$
DECLARE
    v_texto_normalizado TEXT;
BEGIN
    v_texto_normalizado := lower(unaccent(p_texto));

    -- Primeiro tenta match exato em alias
    RETURN QUERY
    SELECT ha.hospital_id, h.nome, 1.0::FLOAT as score
    FROM hospitais_alias ha
    JOIN hospitais h ON h.id = ha.hospital_id
    WHERE ha.alias_normalizado = v_texto_normalizado
    LIMIT 1;

    IF NOT FOUND THEN
        -- Se não encontrou, tenta match parcial
        RETURN QUERY
        SELECT ha.hospital_id, h.nome,
               similarity(ha.alias_normalizado, v_texto_normalizado)::FLOAT as score
        FROM hospitais_alias ha
        JOIN hospitais h ON h.id = ha.hospital_id
        WHERE ha.alias_normalizado % v_texto_normalizado
        ORDER BY score DESC
        LIMIT 1;
    END IF;

    IF NOT FOUND THEN
        -- Último recurso: busca no nome do hospital
        RETURN QUERY
        SELECT h.id, h.nome,
               similarity(lower(unaccent(h.nome)), v_texto_normalizado)::FLOAT as score
        FROM hospitais h
        WHERE lower(unaccent(h.nome)) % v_texto_normalizado
        ORDER BY score DESC
        LIMIT 1;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Mesma lógica para especialidades
CREATE OR REPLACE FUNCTION buscar_especialidade_por_alias(p_texto TEXT)
RETURNS TABLE (especialidade_id UUID, nome TEXT, score FLOAT) AS $$
DECLARE
    v_texto_normalizado TEXT;
BEGIN
    v_texto_normalizado := lower(unaccent(p_texto));

    RETURN QUERY
    SELECT ea.especialidade_id, e.nome, 1.0::FLOAT as score
    FROM especialidades_alias ea
    JOIN especialidades e ON e.id = ea.especialidade_id
    WHERE ea.alias_normalizado = v_texto_normalizado
    LIMIT 1;

    IF NOT FOUND THEN
        RETURN QUERY
        SELECT ea.especialidade_id, e.nome,
               similarity(ea.alias_normalizado, v_texto_normalizado)::FLOAT as score
        FROM especialidades_alias ea
        JOIN especialidades e ON e.id = ea.especialidade_id
        WHERE ea.alias_normalizado % v_texto_normalizado
        ORDER BY score DESC
        LIMIT 1;
    END IF;

    IF NOT FOUND THEN
        RETURN QUERY
        SELECT e.id, e.nome,
               similarity(lower(unaccent(e.nome)), v_texto_normalizado)::FLOAT as score
        FROM especialidades e
        WHERE lower(unaccent(e.nome)) % v_texto_normalizado
        ORDER BY score DESC
        LIMIT 1;
    END IF;
END;
$$ LANGUAGE plpgsql;
```

**Estimativa:** 1h

---

### S01.10 - Habilitar extensão pg_trgm

**Descrição:** Habilitar extensão para busca por similaridade.

**Critérios de Aceite:**
- [ ] Extensão `pg_trgm` habilitada
- [ ] Extensão `unaccent` habilitada
- [ ] Teste de similaridade funcionando

**Schema:**
```sql
-- Habilitar extensões necessárias
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

-- Configurar threshold de similaridade
SET pg_trgm.similarity_threshold = 0.3;
```

**Estimativa:** 0.25h

---

## Resumo

| Story | Descrição | Estimativa |
|-------|-----------|------------|
| S01.1 | Tabela grupos_whatsapp | 0.5h |
| S01.2 | Tabela contatos_grupo | 0.5h |
| S01.3 | Tabela mensagens_grupo | 1h |
| S01.4 | Tabela vagas_grupo | 1.5h |
| S01.5 | Tabela vagas_grupo_fontes | 0.5h |
| S01.6 | Tabela hospitais_alias | 0.5h |
| S01.7 | Tabela especialidades_alias | 0.5h |
| S01.8 | Seed de alias comuns | 1h |
| S01.9 | Funções de busca por alias | 1h |
| S01.10 | Extensão pg_trgm | 0.25h |

**Total:** 7.25h (~1 dia)

## Dependências

- Nenhuma (primeiro épico)

## Entregáveis

- Migration com todas as tabelas
- Seed de alias iniciais
- Funções SQL de busca
- Documentação do schema
