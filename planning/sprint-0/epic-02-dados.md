# Epic 2: Dados

## Objetivo do Epic

> **Popular o banco de dados com os dados necessários para o MVP funcionar.**

Sem dados, a Júlia não tem médicos para contatar, nem vagas para oferecer.

---

## Stories

1. [S0.E2.1 - Seed de dados auxiliares](#s0e21---seed-de-dados-auxiliares)
2. [S0.E2.2 - Cadastrar hospitais](#s0e22---cadastrar-hospitais)
3. [S0.E2.3 - Cadastrar vagas reais](#s0e23---cadastrar-vagas-reais)
4. [S0.E2.4 - Selecionar médicos piloto](#s0e24---selecionar-médicos-piloto)

---

# S0.E2.1 - Seed de dados auxiliares

## Objetivo

> **Criar registros base nas tabelas de especialidades, setores e períodos.**

Essas tabelas são referenciadas por vagas e médicos. Precisam existir primeiro.

**Resultado esperado:** Tabelas `especialidades`, `setores` e `periodos` populadas com dados do MVP.

---

## Contexto

- Especialidades: tipos de médico (Anestesiologia é nosso foco)
- Setores: áreas do hospital (CC, SADT, UTI, etc)
- Períodos: turnos de trabalho (Diurno 12h, Noturno 12h, etc)
- Esses dados raramente mudam

---

## Responsável

**Dev**

---

## Pré-requisitos

- [x] Acesso ao Supabase (MCP ou cliente direto)
- [x] Schema do banco já executado (tabelas existem)

---

## Tarefas

### 1. Verificar se tabelas existem

```sql
-- Via MCP Supabase ou SQL Editor
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('especialidades', 'setores', 'periodos');
```

Deve retornar as 3 tabelas.

### 2. Inserir especialidades

```sql
INSERT INTO especialidades (nome, codigo, ativa) VALUES
('Anestesiologia', 'ANEST', true)
ON CONFLICT (codigo) DO NOTHING;

-- Verificar
SELECT * FROM especialidades;
```

**Nota:** Para o MVP, só precisamos de Anestesiologia.

### 3. Inserir setores

```sql
INSERT INTO setores (nome, codigo, descricao) VALUES
('Centro Cirúrgico', 'CC', 'Cirurgias eletivas e emergências'),
('SADT', 'SADT', 'Serviço de Apoio Diagnóstico e Terapêutico'),
('Hemodinâmica', 'HEMO', 'Procedimentos cardíacos'),
('Endoscopia', 'ENDO', 'Endoscopia digestiva'),
('UTI', 'UTI', 'Unidade de Terapia Intensiva')
ON CONFLICT (codigo) DO NOTHING;

-- Verificar
SELECT * FROM setores;
```

### 4. Inserir períodos

```sql
INSERT INTO periodos (nome, hora_inicio, hora_fim, duracao_horas) VALUES
('Diurno 12h', '07:00', '19:00', 12),
('Noturno 12h', '19:00', '07:00', 12),
('Manhã 6h', '07:00', '13:00', 6),
('Tarde 6h', '13:00', '19:00', 6),
('Cinderela', '19:00', '01:00', 6)
ON CONFLICT (nome) DO NOTHING;

-- Verificar
SELECT * FROM periodos;
```

### 5. Criar script de seed

Salve os comandos em um arquivo para reprodutibilidade:

```bash
cat > /Users/rafaelpivovar/Documents/Projetos/whatsapp-api/scripts/seed_auxiliares.sql << 'EOF'
-- Seed de dados auxiliares para MVP Júlia
-- Executar uma vez no Supabase

-- 1. Especialidades
INSERT INTO especialidades (nome, codigo, ativa) VALUES
('Anestesiologia', 'ANEST', true)
ON CONFLICT (codigo) DO NOTHING;

-- 2. Setores
INSERT INTO setores (nome, codigo, descricao) VALUES
('Centro Cirúrgico', 'CC', 'Cirurgias eletivas e emergências'),
('SADT', 'SADT', 'Serviço de Apoio Diagnóstico e Terapêutico'),
('Hemodinâmica', 'HEMO', 'Procedimentos cardíacos'),
('Endoscopia', 'ENDO', 'Endoscopia digestiva'),
('UTI', 'UTI', 'Unidade de Terapia Intensiva')
ON CONFLICT (codigo) DO NOTHING;

-- 3. Períodos
INSERT INTO periodos (nome, hora_inicio, hora_fim, duracao_horas) VALUES
('Diurno 12h', '07:00', '19:00', 12),
('Noturno 12h', '19:00', '07:00', 12),
('Diurno 6h', '07:00', '13:00', 6),
('Vespertino 6h', '13:00', '19:00', 6),
('Cinderela', '19:00', '01:00', 6)
ON CONFLICT (nome) DO NOTHING;

-- Verificação
SELECT 'especialidades' as tabela, COUNT(*) as registros FROM especialidades
UNION ALL
SELECT 'setores', COUNT(*) FROM setores
UNION ALL
SELECT 'periodos', COUNT(*) FROM periodos;
EOF
```

### 6. Executar e verificar

Execute o script via Supabase SQL Editor ou MCP:

```sql
-- Verificação final
SELECT 'especialidades' as tabela, COUNT(*) as registros FROM especialidades
UNION ALL
SELECT 'setores', COUNT(*) FROM setores
UNION ALL
SELECT 'periodos', COUNT(*) FROM periodos;
```

Resultado esperado:
| tabela | registros |
|--------|-----------|
| especialidades | 1 |
| setores | 5 |
| periodos | 5 |

---

## Como Testar

```sql
-- Deve retornar 1 especialidade, 5 setores, 5 períodos
SELECT
  (SELECT COUNT(*) FROM especialidades) as esp,
  (SELECT COUNT(*) FROM setores) as set,
  (SELECT COUNT(*) FROM periodos) as per;
```

---

## DoD (Definition of Done)

- [x] Tabela `especialidades` tem registros (56 importadas via CSV)
- [x] Tabela `setores` tem registros (9 importados via CSV)
- [x] Tabela `periodos` tem registros (6 importados via CSV)
- [x] Dados importados via upload CSV
- [x] Nenhum erro de constraint

**Status: COMPLETO** ✅ (07/12/2025) - Dados importados via CSV superaram expectativa inicial.

---

## Troubleshooting

| Erro | Causa | Solução |
|------|-------|---------|
| `relation does not exist` | Tabela não existe | Executar migrations primeiro |
| `duplicate key` | Dado já existe | `ON CONFLICT DO NOTHING` resolve |
| `permission denied` | Sem permissão | Usar service key |

---
---

# S0.E2.2 - Cadastrar hospitais

## Objetivo

> **Registrar os hospitais reais onde temos vagas para ofertar.**

Sem hospitais cadastrados, não conseguimos criar vagas.

**Resultado esperado:** 3-5 hospitais cadastrados com nome, endereço e características.

---

## Contexto

- Hospitais são os locais onde os médicos trabalharão
- Cada hospital tem características (estacionamento, refeitório)
- Dados devem ser reais (hospitais parceiros da Revoluna)

---

## Responsável

**Gestor**

---

## Pré-requisitos

- [x] Story S0.E2.1 completa (tabelas auxiliares populadas)
- [x] Lista de hospitais parceiros disponível

---

## Tarefas

### 1. Identificar hospitais do MVP

Gestor deve listar 3-5 hospitais onde já temos:
- Contrato ativo
- Vagas disponíveis
- Histórico de trabalho

### 2. Coletar informações de cada hospital

Para cada hospital, obter:
- Nome completo
- Endereço
- Cidade/UF
- Tem estacionamento? (sim/não)
- Tem refeitório? (sim/não)
- Observações relevantes

### 3. Inserir via SQL ou Supabase

**Opção A: Via Supabase Dashboard**
1. Acesse o Supabase
2. Vá em Table Editor → hospitais
3. Clique em "Insert row"
4. Preencha os campos

**Opção B: Via SQL**

```sql
INSERT INTO hospitais (nome, endereco, cidade, uf, tem_estacionamento, tem_refeitorio, observacoes) VALUES
('Hospital Brasil', 'Av. Industrial, 1825', 'Santo André', 'SP', true, true, 'Entrada de médicos pelo estacionamento'),
('Hospital São Luiz', 'R. Dr. Alceu de Campos Rodrigues, 95', 'São Paulo', 'SP', true, true, 'Apresentar-se na recepção médica'),
('Hospital Cruz Azul', 'Av. Lins de Vasconcelos, 356', 'São Paulo', 'SP', false, true, 'Estacionamento pago nas redondezas');

-- Verificar
SELECT id, nome, cidade FROM hospitais;
```

### 4. Anotar IDs dos hospitais

Após inserir, anote o ID de cada hospital. Será necessário para cadastrar vagas:

```sql
SELECT id, nome FROM hospitais;
```

Exemplo:
| id | nome |
|----|------|
| 1 | Hospital Brasil |
| 2 | Hospital São Luiz |
| 3 | Hospital Cruz Azul |

### 5. Documentar hospitais cadastrados

```bash
cat > /Users/rafaelpivovar/Documents/Projetos/whatsapp-api/data/hospitais_mvp.md << 'EOF'
# Hospitais do MVP

| ID | Nome | Cidade | Estacionamento | Refeitório |
|----|------|--------|----------------|------------|
| 1 | Hospital Brasil | Santo André | Sim | Sim |
| 2 | Hospital São Luiz | São Paulo | Sim | Sim |
| 3 | Hospital Cruz Azul | São Paulo | Não | Sim |

## Observações por Hospital

### Hospital Brasil
- Entrada de médicos pelo estacionamento
- Contato: [nome do contato]

### Hospital São Luiz
- Apresentar-se na recepção médica
- Contato: [nome do contato]

### Hospital Cruz Azul
- Estacionamento pago nas redondezas
- Contato: [nome do contato]
EOF
```

---

## Como Testar

```sql
-- Deve retornar 3-5 hospitais
SELECT COUNT(*) FROM hospitais;

-- Verificar dados completos
SELECT * FROM hospitais;
```

---

## DoD (Definition of Done)

- [x] 85 hospitais cadastrados (importados via CSV)
- [x] Cada hospital tem: nome, endereço, cidade, uf
- [x] Campos de características preenchidos
- [x] Dados importados via upload CSV

**Status: COMPLETO** ✅ (07/12/2025) - 85 hospitais importados via CSV.

---

## Troubleshooting

| Erro | Causa | Solução |
|------|-------|---------|
| `null value in column` | Campo obrigatório vazio | Preencher todos os campos |
| `duplicate key` | Hospital já existe | Verificar se já foi cadastrado |

---
---

# S0.E2.3 - Cadastrar vagas reais

## Objetivo

> **Registrar vagas de plantão reais para a Júlia ofertar aos médicos.**

Sem vagas, a Júlia não tem o que oferecer.

**Resultado esperado:** 10-20 vagas cadastradas com datas, valores e características reais.

---

## Contexto

- Vagas são plantões disponíveis em hospitais
- Cada vaga tem: hospital, data, período, valor, setor
- Valor tem range (min/max) para negociação
- Prioridade define urgência (normal, alta, urgente)

---

## Responsável

**Gestor**

---

## Pré-requisitos

- [x] Story S0.E2.1 completa (especialidades, setores, períodos)
- [x] Story S0.E2.2 completa (hospitais cadastrados)
- [x] Lista de vagas reais disponíveis

---

## Tarefas

### 1. Obter IDs necessários

Antes de cadastrar, obtenha os IDs:

```sql
-- IDs dos hospitais
SELECT id, nome FROM hospitais;

-- ID da especialidade (Anestesiologia)
SELECT id, nome FROM especialidades;

-- IDs dos setores
SELECT id, nome, codigo FROM setores;

-- IDs dos períodos
SELECT id, nome FROM periodos;
```

### 2. Preparar lista de vagas

Para cada vaga, defina:
- Hospital (id)
- Data do plantão
- Período (id)
- Setor (id) - opcional
- Valor mínimo
- Valor máximo
- Prioridade (normal, alta, urgente)

### 3. Inserir vagas via SQL

```sql
-- Exemplo com IDs fictícios (ajustar conforme seus IDs reais)

INSERT INTO vagas (
    hospital_id,
    especialidade_id,
    setor_id,
    data_plantao,
    periodo_id,
    valor_min,
    valor_max,
    prioridade,
    status
) VALUES
-- Hospital Brasil - SADT
(1, 1, 2, '2024-12-14', 1, 2000, 2500, 'urgente', 'aberta'),
(1, 1, 2, '2024-12-15', 1, 2000, 2500, 'alta', 'aberta'),
(1, 1, 2, '2024-12-21', 1, 2000, 2500, 'normal', 'aberta'),
(1, 1, 2, '2024-12-22', 2, 2200, 2700, 'normal', 'aberta'),

-- Hospital São Luiz - CC
(2, 1, 1, '2024-12-14', 2, 2400, 3000, 'alta', 'aberta'),
(2, 1, 1, '2024-12-15', 1, 2200, 2800, 'normal', 'aberta'),
(2, 1, 1, '2024-12-16', 1, 2200, 2800, 'normal', 'aberta'),

-- Hospital Cruz Azul - Hemodinâmica
(3, 1, 3, '2024-12-16', 1, 1800, 2200, 'normal', 'aberta'),
(3, 1, 3, '2024-12-17', 1, 1800, 2200, 'normal', 'aberta'),
(3, 1, 3, '2024-12-18', 2, 2000, 2400, 'alta', 'aberta');

-- Verificar
SELECT
    v.id,
    h.nome as hospital,
    v.data_plantao,
    p.nome as periodo,
    s.nome as setor,
    v.valor_min,
    v.valor_max,
    v.prioridade
FROM vagas v
JOIN hospitais h ON v.hospital_id = h.id
JOIN periodos p ON v.periodo_id = p.id
LEFT JOIN setores s ON v.setor_id = s.id
ORDER BY v.data_plantao, h.nome;
```

### 4. Verificar distribuição

```sql
-- Vagas por hospital
SELECT h.nome, COUNT(*) as qtd_vagas
FROM vagas v
JOIN hospitais h ON v.hospital_id = h.id
WHERE v.status = 'aberta'
GROUP BY h.nome;

-- Vagas por prioridade
SELECT prioridade, COUNT(*) as qtd
FROM vagas
WHERE status = 'aberta'
GROUP BY prioridade;

-- Vagas por período
SELECT p.nome, COUNT(*) as qtd
FROM vagas v
JOIN periodos p ON v.periodo_id = p.id
WHERE v.status = 'aberta'
GROUP BY p.nome;
```

### 5. Documentar vagas cadastradas

```bash
mkdir -p /Users/rafaelpivovar/Documents/Projetos/whatsapp-api/data

cat > /Users/rafaelpivovar/Documents/Projetos/whatsapp-api/data/vagas_mvp.md << 'EOF'
# Vagas do MVP

## Resumo
- Total de vagas: X
- Por prioridade: X urgente, X alta, X normal
- Período: DD/MM a DD/MM

## Por Hospital

### Hospital Brasil
| Data | Período | Setor | Valor | Prioridade |
|------|---------|-------|-------|------------|
| ... | ... | ... | ... | ... |

### Hospital São Luiz
| Data | Período | Setor | Valor | Prioridade |
|------|---------|-------|-------|------------|
| ... | ... | ... | ... | ... |

### Hospital Cruz Azul
| Data | Período | Setor | Valor | Prioridade |
|------|---------|-------|-------|------------|
| ... | ... | ... | ... | ... |
EOF
```

---

## Como Testar

```sql
-- Deve retornar 10-20 vagas
SELECT COUNT(*) FROM vagas WHERE status = 'aberta';

-- Verificar se todas têm os relacionamentos corretos
SELECT v.id
FROM vagas v
LEFT JOIN hospitais h ON v.hospital_id = h.id
LEFT JOIN especialidades e ON v.especialidade_id = e.id
LEFT JOIN periodos p ON v.periodo_id = p.id
WHERE h.id IS NULL OR e.id IS NULL OR p.id IS NULL;
-- Deve retornar vazio (nenhum registro com FK quebrada)
```

---

## DoD (Definition of Done)

- [x] 4.973 vagas cadastradas (importadas via CSV)
- [x] Todas as vagas têm: hospital, especialidade, período, data, valores
- [x] Mix de prioridades
- [x] Mix de hospitais (85 hospitais)
- [x] Mix de períodos
- [x] Valores realistas
- [x] Dados importados via upload CSV

**Status: COMPLETO** ✅ (07/12/2025) - 4.973 vagas importadas via CSV.

---

## Troubleshooting

| Erro | Causa | Solução |
|------|-------|---------|
| `foreign key violation` | ID de hospital/setor não existe | Verificar IDs antes |
| `invalid date` | Formato de data errado | Usar 'YYYY-MM-DD' |
| `check constraint` | Valor fora do range | Verificar constraints |

---
---

# S0.E2.4 - Selecionar médicos piloto

## Objetivo

> **Identificar e marcar os 100 médicos que participarão do piloto.**

Precisamos de um grupo controlado para testar a Júlia antes de expandir.

**Resultado esperado:** 100 médicos anestesistas selecionados e marcados para o piloto.

---

## Contexto

- Temos 1.660 anestesistas na base
- 81% têm CRM (dados mais completos)
- Queremos os 100 melhores para o piloto
- Critérios: CRM preenchido, nome completo, telefone válido

---

## Responsável

**Dev**

---

## Pré-requisitos

- [x] Acesso ao Supabase
- [x] Tabela `clientes` já tem os médicos importados

---

## Tarefas

### 1. Analisar a base de anestesistas

```sql
-- Total de anestesistas
SELECT COUNT(*) as total
FROM clientes
WHERE especialidade = 'Anestesiologia';

-- Com CRM
SELECT COUNT(*) as com_crm
FROM clientes
WHERE especialidade = 'Anestesiologia'
  AND crm IS NOT NULL;

-- Com nome completo
SELECT COUNT(*) as com_nome
FROM clientes
WHERE especialidade = 'Anestesiologia'
  AND primeiro_nome IS NOT NULL
  AND sobrenome IS NOT NULL;

-- Com telefone válido (começa com 55)
SELECT COUNT(*) as telefone_valido
FROM clientes
WHERE especialidade = 'Anestesiologia'
  AND telefone LIKE '55%'
  AND LENGTH(telefone) >= 12;
```

### 2. Query para selecionar os melhores 100

```sql
-- Selecionar médicos com dados mais completos
SELECT
    id,
    primeiro_nome,
    sobrenome,
    crm,
    telefone,
    email,
    cidade,
    estado
FROM clientes
WHERE especialidade = 'Anestesiologia'
  AND opt_out = false
  AND telefone IS NOT NULL
  AND LENGTH(telefone) >= 12
ORDER BY
    -- Priorizar quem tem mais dados
    (CASE WHEN crm IS NOT NULL THEN 1 ELSE 0 END) DESC,
    (CASE WHEN primeiro_nome IS NOT NULL THEN 1 ELSE 0 END) DESC,
    (CASE WHEN email IS NOT NULL THEN 1 ELSE 0 END) DESC,
    created_at DESC
LIMIT 100;
```

### 3. Criar campo para marcar piloto (se não existir)

```sql
-- Adicionar coluna para marcar médicos do piloto
ALTER TABLE clientes
ADD COLUMN IF NOT EXISTS grupo_piloto boolean DEFAULT false;
```

### 4. Marcar os 100 selecionados

```sql
-- Primeiro, desmarcar todos (reset)
UPDATE clientes SET grupo_piloto = false;

-- Marcar os 100 selecionados
UPDATE clientes
SET grupo_piloto = true
WHERE id IN (
    SELECT id
    FROM clientes
    WHERE especialidade = 'Anestesiologia'
      AND opt_out = false
      AND telefone IS NOT NULL
      AND LENGTH(telefone) >= 12
    ORDER BY
        (CASE WHEN crm IS NOT NULL THEN 1 ELSE 0 END) DESC,
        (CASE WHEN primeiro_nome IS NOT NULL THEN 1 ELSE 0 END) DESC,
        (CASE WHEN email IS NOT NULL THEN 1 ELSE 0 END) DESC,
        created_at DESC
    LIMIT 100
);

-- Verificar
SELECT COUNT(*) as total_piloto
FROM clientes
WHERE grupo_piloto = true;
```

### 5. Analisar o grupo selecionado

```sql
-- Perfil do grupo piloto
SELECT
    COUNT(*) as total,
    COUNT(crm) as com_crm,
    COUNT(primeiro_nome) as com_nome,
    COUNT(email) as com_email,
    COUNT(cidade) as com_cidade
FROM clientes
WHERE grupo_piloto = true;
```

### 6. Exportar lista para revisão

```sql
-- Lista completa do piloto
SELECT
    id,
    CONCAT(primeiro_nome, ' ', sobrenome) as nome_completo,
    crm,
    telefone,
    email,
    cidade,
    estado
FROM clientes
WHERE grupo_piloto = true
ORDER BY primeiro_nome;
```

### 7. Documentar seleção

```bash
cat > /Users/rafaelpivovar/Documents/Projetos/whatsapp-api/data/medicos_piloto.md << 'EOF'
# Médicos do Piloto - MVP Júlia

## Critérios de Seleção
1. Especialidade: Anestesiologia
2. Opt-out: false
3. Telefone válido (12+ dígitos)
4. Priorizados por completude dos dados

## Perfil do Grupo
- Total: 100 médicos
- Com CRM: X%
- Com nome completo: X%
- Com email: X%

## Query de Seleção
```sql
SELECT id FROM clientes
WHERE especialidade = 'Anestesiologia'
  AND opt_out = false
  AND telefone IS NOT NULL
ORDER BY completude
LIMIT 100;
```

## Próximos Passos
1. Gestor revisa lista
2. Ajustes se necessário
3. Liberação para Sprint 1
EOF
```

---

## Como Testar

```sql
-- Deve retornar 100
SELECT COUNT(*) FROM clientes WHERE grupo_piloto = true;

-- Todos devem ser anestesistas
SELECT COUNT(*) FROM clientes
WHERE grupo_piloto = true
  AND especialidade != 'Anestesiologia';
-- Deve retornar 0

-- Nenhum deve ter opt_out
SELECT COUNT(*) FROM clientes
WHERE grupo_piloto = true
  AND opt_out = true;
-- Deve retornar 0
```

---

## DoD (Definition of Done)

- [x] Coluna `grupo_piloto` existe na tabela `clientes`
- [x] Exatamente 100 médicos marcados com `grupo_piloto = true`
- [x] Todos são anestesistas com dados completos
- [x] Nenhum tem `opt_out = true`
- [x] Todos têm telefone válido
- [x] Perfil do grupo documentado
- [x] Arquivo `data/medicos_piloto.md` criado

**Status: COMPLETO** ✅ (07/12/2025) - 100 anestesistas selecionados por completude de dados.

---

## Troubleshooting

| Erro | Causa | Solução |
|------|-------|---------|
| Menos de 100 médicos | Critérios muito restritivos | Relaxar critérios |
| Coluna já existe | Executou ALTER duas vezes | Ignorar erro |
| Telefones inválidos | Formato inconsistente | Ajustar query de validação |

---

# Epic 2 Summary

**Status Geral: COMPLETO** ✅

| Story | Status | Registros |
|-------|--------|-----------|
| S0.E2.1 - Seed dados auxiliares | ✅ Completo | 56 esp, 9 set, 6 per |
| S0.E2.2 - Cadastrar hospitais | ✅ Completo | 85 hospitais |
| S0.E2.3 - Cadastrar vagas | ✅ Completo | 4.973 vagas |
| S0.E2.4 - Selecionar médicos piloto | ✅ Completo | 100 médicos |

**Nota:** Dados importados via CSV com volume superior ao planejado inicialmente para o MVP.
