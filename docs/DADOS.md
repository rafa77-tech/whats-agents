# Fonte e Estrutura de Dados - MVP Júlia

Este documento define de onde vêm os dados e como devem ser estruturados.

---

## Visão Geral dos Dados

| Entidade | Fonte | Quantidade | Status |
|----------|-------|------------|--------|
| Médicos (Total) | Supabase `clientes` | 29.645 | ✅ Importados |
| Anestesistas | Supabase `clientes` | 1.660 (81% com CRM) | ✅ Prontos |
| Hospitais | Manual | 0 | ❌ Precisa seed |
| Vagas | Manual | 0 | ❌ Precisa cadastrar |
| Especialidades | Seed | 0 | ❌ Precisa seed |
| Setores | Seed | 0 | ❌ Precisa seed |
| Períodos | Seed | 0 | ❌ Precisa seed |

### Qualidade dos Dados de Médicos

| Campo | Preenchidos | % |
|-------|-------------|---|
| telefone | 29.645 | 100% |
| primeiro_nome | 23.605 | 80% |
| especialidade | 23.441 | 79% |
| email | 23.385 | 79% |
| crm | 8.186 | 28% |
| cidade | 5 | <1% |

### Anestesistas (Foco MVP)

| Métrica | Valor |
|---------|-------|
| Total | 1.660 |
| Com CRM | 1.345 (81%) |
| Com nome | 1.533 (92%) |
| Com email | ~1.500 (est.) |
| Estado | SP (maioria) |

**Exemplo de registro completo:**
```json
{
  "primeiro_nome": "Italo",
  "sobrenome": "Pires Gomes",
  "crm": "172629",
  "especialidade": "Anestesiologia",
  "telefone": "+5511930100194",
  "email": "italopires11@hotmail.com",
  "estado": "SP",
  "titulo": "Dr.",
  "stage_jornada": "novo",
  "opt_out": false
}
```

---

## 1. Médicos

### Status: ✅ Dados Disponíveis no Supabase

Os dados de médicos já estão importados na tabela `clientes`. Não é necessário importação adicional.

**Query para selecionar anestesistas do MVP:**
```sql
SELECT * FROM clientes
WHERE especialidade = 'Anestesiologia'
  AND opt_out = false
  AND telefone IS NOT NULL
ORDER BY crm IS NOT NULL DESC, primeiro_nome
LIMIT 100;
```

### Estrutura Atual (Tabela `clientes`)

**Campos obrigatórios:**
| Campo | Tipo | Exemplo | Validação |
|-------|------|---------|-----------|
| nome | string | "Carlos Eduardo Silva" | Não vazio |
| telefone | string | "5511999998888" | Formato brasileiro, único |

**Campos opcionais:**
| Campo | Tipo | Exemplo | Default |
|-------|------|---------|---------|
| crm | string | "123456" | null |
| uf_crm | string | "SP" | null |
| email | string | "carlos@email.com" | null |
| especialidade | string | "Anestesiologia" | null |
| rqe | string | "12345" | null |
| fonte | string | "DoctorID" | "import" |

### Formato do CSV de Importação

```csv
nome,telefone,crm,uf_crm,especialidade,rqe,fonte
Carlos Eduardo Silva,5511999998888,123456,SP,Anestesiologia,12345,DoctorID
Ana Maria Santos,5511988887777,789012,SP,Anestesiologia,,Planilha
João Pedro Costa,5511977776666,,,,Manual
```

### Mapeamento para Tabela `clientes`

```sql
INSERT INTO clientes (
    nome,
    telefone,
    crm,
    especialidade_id,
    rqe,
    stage_jornada,
    source,
    created_at
) VALUES (
    'Carlos Eduardo Silva',
    '5511999998888',
    'CRM-SP 123456',
    (SELECT id FROM especialidades WHERE nome = 'Anestesiologia'),
    '12345',
    'novo',
    'import_csv',
    NOW()
);
```

### Validações na Importação

| Validação | Ação |
|-----------|------|
| Telefone formato inválido | Log erro, pula registro |
| Telefone duplicado | Log duplicado, pula registro |
| CRM inválido (formato) | Importa sem CRM, flag `crm_pendente = true` |
| Especialidade não existe | Cria nova especialidade ou mapeia |

### Script de Importação (Proposto)

```python
# scripts/importar_medicos.py

import csv
from supabase import create_client

def importar_medicos(arquivo_csv: str):
    """
    Importa médicos de arquivo CSV para o Supabase.
    """
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    resultados = {
        "importados": 0,
        "duplicados": 0,
        "erros": []
    }

    with open(arquivo_csv) as f:
        reader = csv.DictReader(f)

        for row in reader:
            # Validar telefone
            telefone = normalizar_telefone(row["telefone"])
            if not telefone:
                resultados["erros"].append(f"Telefone inválido: {row}")
                continue

            # Verificar duplicado
            existente = supabase.table("clientes").select("id").eq("telefone", telefone).execute()
            if existente.data:
                resultados["duplicados"] += 1
                continue

            # Inserir
            dados = {
                "nome": row["nome"],
                "telefone": telefone,
                "crm": row.get("crm"),
                "stage_jornada": "novo",
                "source": "import_csv"
            }

            supabase.table("clientes").insert(dados).execute()
            resultados["importados"] += 1

    return resultados
```

---

## 2. Hospitais

### Dados para MVP

Para o MVP, precisamos de 3-5 hospitais reais onde já temos vagas.

**Campos:**
| Campo | Tipo | Obrigatório |
|-------|------|-------------|
| nome | string | Sim |
| endereco | string | Sim |
| bairro | string | Não |
| cidade | string | Sim |
| uf | string | Sim |
| telefone | string | Não |
| tem_estacionamento | boolean | Não |
| tem_refeitorio | boolean | Não |
| observacoes | text | Não |

### Seed de Hospitais (Exemplo)

```sql
INSERT INTO hospitais (nome, endereco, cidade, uf, tem_estacionamento, tem_refeitorio) VALUES
('Hospital Brasil', 'Av. Industrial, 1825', 'Santo André', 'SP', true, true),
('Hospital São Luiz', 'R. Dr. Alceu de Campos Rodrigues, 95', 'São Paulo', 'SP', true, true),
('Hospital Cruz Azul', 'Av. Lins de Vasconcelos, 356', 'São Paulo', 'SP', false, true),
('Hospital Saboya', 'Av. Paes de Barros, 1000', 'São Paulo', 'SP', true, false),
('Hospital Tatuapé', 'R. Serra de Bragança, 1000', 'São Paulo', 'SP', true, true);
```

---

## 3. Especialidades

### Seed para MVP

```sql
INSERT INTO especialidades (nome, codigo, ativa) VALUES
('Anestesiologia', 'ANEST', true);

-- Para futuro (não MVP)
-- ('Cardiologia', 'CARDIO', false),
-- ('Pediatria', 'PED', false),
-- ('Cirurgia Geral', 'CIRGE', false);
```

---

## 4. Setores

### Seed para MVP

```sql
INSERT INTO setores (nome, codigo, descricao) VALUES
('Centro Cirúrgico', 'CC', 'Cirurgias eletivas e emergências'),
('SADT', 'SADT', 'Serviço de Apoio Diagnóstico e Terapêutico'),
('Hemodinâmica', 'HEMO', 'Procedimentos cardíacos'),
('Endoscopia', 'ENDO', 'Endoscopia digestiva'),
('UTI', 'UTI', 'Unidade de Terapia Intensiva');
```

---

## 5. Períodos

### Seed para MVP

```sql
INSERT INTO periodos (nome, hora_inicio, hora_fim, duracao_horas) VALUES
('Diurno 12h', '07:00', '19:00', 12),
('Noturno 12h', '19:00', '07:00', 12),
('Diurno 6h', '07:00', '13:00', 6),
('Vespertino 6h', '13:00', '19:00', 6),
('Cinderela', '19:00', '01:00', 6);
```

---

## 6. Vagas

### Estrutura

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| hospital_id | FK | Sim | Hospital da vaga |
| especialidade_id | FK | Sim | Especialidade requerida |
| setor_id | FK | Não | Setor específico |
| data_plantao | date | Sim | Data do plantão |
| periodo_id | FK | Sim | Período (diurno, noturno, etc) |
| valor_min | decimal | Sim | Valor mínimo oferecido |
| valor_max | decimal | Sim | Valor máximo (margem de negociação) |
| prioridade | enum | Sim | normal / alta / urgente |
| status | enum | Auto | aberta / reservada / preenchida / cancelada |
| exige_rqe | boolean | Não | Se exige RQE |
| observacoes | text | Não | Observações adicionais |

### Exemplo de Vagas para MVP

```sql
INSERT INTO vagas (
    hospital_id, especialidade_id, setor_id,
    data_plantao, periodo_id,
    valor_min, valor_max, prioridade, status
) VALUES
-- Hospital Brasil - Vagas SADT
(1, 1, 2, '2024-12-14', 1, 2000, 2500, 'urgente', 'aberta'),
(1, 1, 2, '2024-12-15', 1, 2000, 2500, 'alta', 'aberta'),
(1, 1, 2, '2024-12-21', 1, 2000, 2500, 'normal', 'aberta'),

-- Hospital São Luiz - CC
(2, 1, 1, '2024-12-14', 2, 2400, 3000, 'alta', 'aberta'),
(2, 1, 1, '2024-12-15', 1, 2200, 2800, 'normal', 'aberta'),

-- Hospital Cruz Azul - Hemo
(3, 1, 3, '2024-12-16', 1, 1800, 2200, 'normal', 'aberta'),
(3, 1, 3, '2024-12-17', 1, 1800, 2200, 'normal', 'aberta');
```

---

## 7. Pipeline de Dados

### Fluxo de Importação Inicial

```
┌──────────────────────────────────────────────────────────────────┐
│                     IMPORTAÇÃO INICIAL                           │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. SEED (automático)                                           │
│     ├── especialidades (1: Anestesiologia)                      │
│     ├── setores (5: CC, SADT, Hemo, Endo, UTI)                 │
│     └── periodos (5: Diurno, Noturno, etc)                     │
│                                                                  │
│  2. HOSPITAIS (manual ou seed)                                  │
│     └── 3-5 hospitais reais                                     │
│                                                                  │
│  3. MÉDICOS (script de importação)                              │
│     ├── Fonte: CSV (origem a definir)                          │
│     ├── Validação: telefone, duplicados                         │
│     └── Resultado: 100 médicos para piloto                      │
│                                                                  │
│  4. VAGAS (manual pelo gestor)                                  │
│     └── 10-20 vagas reais                                       │
│                                                                  │
│  5. FILA DE PROSPECÇÃO (script)                                │
│     ├── Seleciona médicos com stage='novo'                     │
│     └── Cria entradas na fila_prospeccao                       │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Script de Seed Completo

```sql
-- scripts/seed_mvp.sql

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

-- 4. Hospitais (ajustar com dados reais)
INSERT INTO hospitais (nome, endereco, cidade, uf, tem_estacionamento, tem_refeitorio) VALUES
('Hospital Brasil', 'Av. Industrial, 1825', 'Santo André', 'SP', true, true),
('Hospital São Luiz', 'R. Dr. Alceu de Campos Rodrigues, 95', 'São Paulo', 'SP', true, true),
('Hospital Cruz Azul', 'Av. Lins de Vasconcelos, 356', 'São Paulo', 'SP', false, true)
ON CONFLICT (nome) DO NOTHING;
```

---

## 8. Fonte da Verdade: Supabase

O Supabase é a **única fonte da verdade**. Júlia consulta o banco dinamicamente para:

| Dado | Tabela | Uso |
|------|--------|-----|
| Hospitais disponíveis | `hospitais` | Ofertar vagas |
| Vagas abertas | `vagas` | Buscar compatíveis |
| Valores (min/max) | `vagas.valor` | Margem de negociação |
| Especialidades | `especialidades` | Filtrar médicos |
| Setores | `setores` | Contexto da vaga |
| Períodos | `periodos` | Diurno, noturno, etc |

**Princípio:** O código não deve ter dados hardcoded. Tudo vem do banco.

### Questões Fechadas

| # | Pergunta | Resposta |
|---|----------|----------|
| 1 | Onde estão os médicos? | Supabase `clientes` |
| 2 | Quantos anestesistas? | 1.660 (81% com CRM) |
| 3 | Há opt-outs a respeitar? | Não, base limpa |
| 4 | De onde vêm as vagas? | Contratos + parceiros → Supabase |
| 5 | Orçamento LLM? | Até $50/mês |
| 6 | Hospitais/valores? | Supabase (gestor popula) |

---

## 9. Próximos Passos

### Para o Gestor
1. Popular tabela `hospitais` com hospitais do MVP
2. Popular tabela `especialidades` (pelo menos Anestesiologia)
3. Popular tabela `setores` (CC, SADT, Hemo, etc)
4. Popular tabela `periodos` (Diurno, Noturno, etc)
5. Cadastrar vagas reais em `vagas`

### Para o Desenvolvimento
1. Implementar agente Júlia consultando Supabase
2. Queries dinâmicas para buscar vagas compatíveis
3. Não hardcodar hospitais/valores no código

---

## 10. Estrutura Final de Arquivos

```
/scripts
├── seed_mvp.sql              # Seed de tabelas auxiliares
├── importar_medicos.py       # Script de importação CSV
├── popular_fila.py           # Popula fila de prospecção
└── verificar_dados.py        # Validação pós-importação

/data
├── medicos_piloto.csv        # 100 médicos para MVP
└── hospitais.csv             # Hospitais para seed
```
