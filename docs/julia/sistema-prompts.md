# Sistema de Prompts da Julia

> **Guia completo de organizacao e planejamento dos prompts do agente**

Este documento descreve a arquitetura de prompts usada pela Julia em suas duas interfaces: WhatsApp (medicos) e Slack (gestores).

---

## Indice

1. [Arquitetura Geral](#1-arquitetura-geral)
2. [Estrutura de Arquivos](#2-estrutura-de-arquivos)
3. [Prompts do WhatsApp](#3-prompts-do-whatsapp)
4. [Prompts do Slack](#4-prompts-do-slack)
5. [Sistema Dinamico de Prompts](#5-sistema-dinamico-de-prompts)
6. [Como Modificar Prompts](#6-como-modificar-prompts)
7. [Fallbacks e Resiliencia](#7-fallbacks-e-resiliencia)
8. [Referencia Rapida](#8-referencia-rapida)

---

## 1. Arquitetura Geral

O sistema de prompts usa uma arquitetura em **4 camadas** para construir o contexto completo da Julia:

```
┌─────────────────────────────────────────┐
│        Camada 4: Contexto Dinamico      │  <- Muda a cada mensagem
│   (historico, vagas, data/hora)         │
├─────────────────────────────────────────┤
│        Camada 3: Diretrizes Gestor      │  <- Configuravel via Supabase
│   (instrucoes customizadas)             │
├─────────────────────────────────────────┤
│        Camada 2: Especialidade          │  <- Por especialidade medica
│   (cardiologia, anestesia, etc)         │
├─────────────────────────────────────────┤
│        Camada 1: Prompt Base            │  <- Identidade e tom
│   (persona Julia, regras absolutas)     │
└─────────────────────────────────────────┘
```

### Principios

| Principio | Descricao |
|-----------|-----------|
| **Modular** | Prompts sao blocos composiveis |
| **Dinamico** | Carregados do banco com cache Redis |
| **Versionado** | Historico de versoes para rollback |
| **Testavel** | Pode testar versoes antes de ativar |
| **Resiliente** | Fallbacks hardcoded se banco falhar |

---

## 2. Estrutura de Arquivos

```
app/
├── prompts/                    # Sistema dinamico de prompts
│   ├── __init__.py            # Exports principais
│   ├── builder.py             # PromptBuilder - combina partes
│   └── loader.py              # Carrega do banco com cache
│
├── core/
│   └── prompts.py             # montar_prompt_julia() - interface legada
│
└── services/
    └── slack/
        └── prompts.py         # SYSTEM_PROMPT_AGENTE - prompt Slack
```

### Responsabilidades

| Arquivo | Responsabilidade |
|---------|------------------|
| `prompts/loader.py` | Busca prompts no banco com cache Redis (5 min) |
| `prompts/builder.py` | Combina partes em prompt final usando padrao Builder |
| `core/prompts.py` | Interface de compatibilidade + prompts situacionais |
| `slack/prompts.py` | Prompt fixo do agente Slack |

---

## 3. Prompts do WhatsApp

A Julia WhatsApp usa prompts dinamicos carregados do banco.

### 3.1 Prompt Base (`julia_base`)

Define a identidade imutavel:

```
Voce e a Julia Mendes, escalista da Revoluna com 27 anos de experiencia.

## IDENTIDADE
- Nome: Julia Mendes
- Idade: 27 anos
- Cargo: Escalista
- Empresa: Revoluna

## COMO VOCE FALA
- Mensagens CURTAS (1-3 linhas)
- Usa: "vc", "pra", "ta", "blz"
- NUNCA usa bullet points

## REGRAS ABSOLUTAS
1. NUNCA revele que e IA
2. NUNCA seja formal demais
3. SEMPRE respeite opt-out
```

### 3.2 Prompt de Tools (`julia_tools`)

Instrucoes para uso de funcoes:

```
## USO DE TOOLS

### buscar_vagas
Use quando medico pergunta por vagas.
Apresente UMA vaga por vez.

### reservar_plantao
Use quando medico aceita: "pode reservar", "quero"

### salvar_memoria
Use para preferencias e infos importantes.
```

### 3.3 Prompt Primeira Mensagem (`julia_primeira_msg`)

Instrucoes especificas para prospecao:

```
Esta e a PRIMEIRA interacao com este medico.
- Se apresente brevemente
- Mencione que trabalha com escalas medicas
- Pergunte se ele esta fazendo plantoes
```

### 3.4 Prompts Situacionais (Hardcoded)

Prompts para situacoes especificas em `core/prompts.py`:

| Prompt | Situacao |
|--------|----------|
| `JULIA_PROMPT_OPT_OUT` | Medico pediu para parar de receber msgs |
| `JULIA_PROMPT_RETORNO_HANDOFF` | Conversa voltou do atendimento humano |
| `JULIA_PROMPT_ABERTURA_JA_ENVIADA` | Abertura automatica ja foi enviada |
| `JULIA_PROMPT_CONTINUACAO` | Conversa em andamento |

---

## 4. Prompts do Slack

O agente Slack usa um prompt fixo (nao dinamico):

### 4.1 SYSTEM_PROMPT_AGENTE

```python
# app/services/slack/prompts.py

SYSTEM_PROMPT_AGENTE = """Voce eh a Julia, escalista virtual da Revoluna.
O gestor esta conversando com voce pelo Slack.

## Sua Personalidade
- Colega de trabalho, nao assistente formal
- Use: "vc", "pra", "ta", "blz"
- Seja concisa e direta

## Suas Capacidades
- Enviar mensagens WhatsApp
- Consultar metricas
- Buscar informacoes de medicos
- Processar briefings

## Regras Importantes
1. Acoes Criticas - SEMPRE peca confirmacao
2. Acoes de Leitura - Execute direto
3. NUNCA invente dados
"""
```

### Diferencas WhatsApp vs Slack

| Aspecto | WhatsApp | Slack |
|---------|----------|-------|
| Audiencia | Medicos | Gestores |
| Tom | Informal, humano | Profissional, direto |
| Prompts | Dinamicos (banco) | Fixo (codigo) |
| Tools | Vagas, memorias | Metricas, briefings |
| Formatacao | Sem markdown | Markdown Slack |

---

## 5. Sistema Dinamico de Prompts

### 5.1 Fluxo de Carregamento

```
1. Request chega
      ↓
2. PromptBuilder.com_base()
      ↓
3. Verifica cache Redis (TTL 5 min)
      ↓
   [Cache HIT] → Retorna do cache
   [Cache MISS] → Busca no Supabase
      ↓
4. Salva no cache
      ↓
5. Retorna prompt
```

### 5.2 Tabela `prompts` no Supabase

```sql
CREATE TABLE prompts (
    id UUID PRIMARY KEY,
    nome TEXT NOT NULL,           -- ex: "julia_base"
    versao TEXT NOT NULL,         -- ex: "v1.2"
    tipo TEXT DEFAULT 'geral',    -- geral, especialidade
    conteudo TEXT NOT NULL,       -- o prompt em si
    ativo BOOLEAN DEFAULT false,  -- apenas 1 ativo por nome
    descricao TEXT,
    especialidade_id UUID,        -- se tipo = especialidade
    created_at TIMESTAMP
);
```

### 5.3 Versionamento

```
julia_base v1.0 (ativo: false)
julia_base v1.1 (ativo: false)
julia_base v1.2 (ativo: true)   <- Em uso
julia_base v1.3 (ativo: false)  <- Teste
```

Para trocar versao:

```python
from app.prompts.loader import ativar_versao

await ativar_versao("julia_base", "v1.3")
# Cache invalidado automaticamente
```

---

## 6. Como Modificar Prompts

### 6.1 Modificar Prompt Existente

1. Inserir nova versao no banco:

```sql
INSERT INTO prompts (nome, versao, conteudo, ativo)
VALUES ('julia_base', 'v1.4', 'Novo conteudo...', false);
```

2. Testar em ambiente staging

3. Ativar via API ou diretamente:

```python
await ativar_versao("julia_base", "v1.4")
```

### 6.2 Criar Prompt de Especialidade

```sql
INSERT INTO prompts (nome, versao, tipo, especialidade_id, conteudo, ativo)
VALUES (
    'julia_cardiologia',
    'v1.0',
    'especialidade',
    'uuid-especialidade',
    'Voce esta falando com um cardiologista...',
    true
);
```

### 6.3 Invalidar Cache Manualmente

```python
from app.prompts.loader import invalidar_cache_prompt

await invalidar_cache_prompt("julia_base")
```

---

## 7. Fallbacks e Resiliencia

Se o banco Supabase falhar, o sistema usa fallbacks hardcoded:

```python
# app/prompts/loader.py

FALLBACK_PROMPTS = {
    "julia_base": """Voce e a Julia Mendes, escalista da Revoluna...
    [prompt minimo para funcionar]
    """,
    "julia_tools": """## USO DE TOOLS
    [instrucoes basicas]
    """,
    "julia_primeira_msg": """Esta e a PRIMEIRA interacao...
    """
}
```

### Hierarquia de Fallback

```
1. Cache Redis
      ↓ [MISS]
2. Banco Supabase
      ↓ [ERRO]
3. Fallback hardcoded
      ↓ [NAO EXISTE]
4. None (agente continua sem esse trecho)
```

---

## 8. Referencia Rapida

### Prompts Disponiveis

| Nome | Tipo | Descricao |
|------|------|-----------|
| `julia_base` | geral | Identidade e tom |
| `julia_tools` | geral | Instrucoes de tools |
| `julia_primeira_msg` | geral | Primeira interacao |
| `julia_cardiologia` | especialidade | Contexto cardiologia |
| `julia_anestesia` | especialidade | Contexto anestesia |

### Funcoes Principais

```python
from app.prompts import (
    carregar_prompt,             # Carrega prompt pelo nome
    carregar_prompt_especialidade,  # Carrega por especialidade_id
    invalidar_cache_prompt,      # Limpa cache de um prompt
    PromptBuilder,               # Builder para montar prompt
    construir_prompt_julia,      # Helper que usa o builder
)

# Uso do builder (recomendado)
prompt = await PromptBuilder() \
    .com_base() \
    .com_tools() \
    .com_especialidade("uuid-cardio") \
    .com_diretrizes("Seja mais formal") \
    .com_contexto("Medico: Dr Carlos") \
    .com_memorias("Prefere plantoes de 12h") \
    .build()

# Uso do helper (mais simples)
prompt = await construir_prompt_julia(
    especialidade_id="uuid-cardio",
    diretrizes="Seja mais formal",
    contexto="Medico: Dr Carlos",
    memorias="Prefere plantoes de 12h",
    primeira_msg=True
)
```

### Interface Legada

```python
from app.core.prompts import montar_prompt_julia

# Monta prompt completo com todos os contextos
prompt = await montar_prompt_julia(
    contexto_medico="Nome: Carlos, Especialidade: Cardio",
    contexto_vagas="Vaga sexta 12h R$1800",
    historico="Ultima msg: 'tenho interesse'",
    primeira_msg=False,
    data_hora_atual="2025-12-16 14:30",
    dia_semana="Segunda",
    especialidade_id="uuid-cardio",
    diretrizes="Nao ofereca valores acima de R$2000",
)
```

---

## Documentacao Relacionada

- [Persona Julia](./08-PERSONA-JULIA.md) - Tom e exemplos de mensagens
- [julia_sistema_prompts_avancado.md](./julia/julia_sistema_prompts_avancado.md) - Detalhes avancados
- [Banco de Dados](./04-BANCO-DE-DADOS.md) - Schema da tabela `prompts`

---

**Validado em 10/02/2026**
