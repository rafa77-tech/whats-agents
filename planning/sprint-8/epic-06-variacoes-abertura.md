# Epic 06: Variacoes de Abertura

## Prioridade: P2 (Melhoria)

## Objetivo

> **Criar sistema de variacoes para mensagens de abertura, evitando que Julia pareca robotica por repetir sempre o mesmo texto.**

Medicos que recebem mensagens identicas percebem padrao. Precisamos de variacao natural.

---

## Problema

Atualmente, Julia sempre abre com algo como:
```
"Oi Dr Carlos! Tudo bem?
Sou a Julia da Revoluna, trabalho com escalas medicas"
```

Depois de 100 medicos receberem a mesma abertura, o padrao fica obvio.

---

## Arquitetura Proposta

```
┌─────────────────────────────────────────────────────────────────┐
│                    VARIACOES DE ABERTURA                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  BANCO DE TEMPLATES (15+ variacoes)                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ • "Oi Dr {nome}! Tudo bem?"                             │   │
│  │ • "E ai Dr {nome}, td certo?"                           │   │
│  │ • "Opa Dr {nome}! Como vai?"                            │   │
│  │ • "Dr {nome}, tudo tranquilo?"                          │   │
│  │ • "Oi! Fala Dr {nome}, blz?"                            │   │
│  │ • ...                                                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│        │                                                         │
│        ▼                                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              SELETOR                                     │   │
│  │  • Evita repetir para mesmo medico                      │   │
│  │  • Evita repetir em sequencia                           │   │
│  │  • Considera horario (manha/tarde/noite)                │   │
│  │  • Considera dia da semana                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│        │                                                         │
│        ▼                                                         │
│  ABERTURA PERSONALIZADA                                         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Stories

---

# S8.E6.1 - Criar banco de templates de abertura

## Objetivo

> **Criar arquivo com 15+ variacoes de mensagens de abertura.**

## Codigo Esperado

**Arquivo:** `app/templates/aberturas.py`

```python
"""
Templates de mensagens de abertura.

Variacoes para evitar que Julia pareca robotica.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class TemplateAbertura:
    """Template de abertura com metadata."""
    id: str
    saudacao: str                  # Primeira linha
    apresentacao: str              # Segunda linha (quem sou)
    contexto: Optional[str] = None  # Terceira linha opcional
    periodo: Optional[str] = None   # manha, tarde, noite, qualquer
    dia_semana: Optional[str] = None  # seg, sex, fds, qualquer
    tom: str = "padrao"            # padrao, casual, profissional


# Saudacoes (primeira linha)
SAUDACOES = [
    ("s1", "Oi Dr {nome}! Tudo bem?", None),
    ("s2", "E ai Dr {nome}, td certo?", None),
    ("s3", "Opa Dr {nome}! Como vai?", None),
    ("s4", "Dr {nome}, tudo tranquilo?", None),
    ("s5", "Oi! Fala Dr {nome}", None),
    ("s6", "Oi Dr {nome}!", None),
    ("s7", "Bom dia Dr {nome}!", "manha"),
    ("s8", "Boa tarde Dr {nome}!", "tarde"),
    ("s9", "Boa noite Dr {nome}!", "noite"),
    ("s10", "E ai Dr {nome}! Tudo joia?", None),
    ("s11", "Oi Dr {nome}, td bem?", None),
    ("s12", "Fala Dr {nome}! Blz?", None),
    ("s13", "Dr {nome}! Tudo certo ai?", None),
    ("s14", "Opa! Dr {nome}, tudo bem?", None),
    ("s15", "Oi Dr {nome}, como vai?", None),
]

# Apresentacoes (segunda linha)
APRESENTACOES = [
    ("a1", "Sou a Julia da Revoluna"),
    ("a2", "Aqui e a Julia, da Revoluna"),
    ("a3", "Julia aqui, da Revoluna"),
    ("a4", "Meu nome e Julia, sou da Revoluna"),
    ("a5", "Sou Julia, escalista da Revoluna"),
    ("a6", "Aqui e Julia da equipe Revoluna"),
    ("a7", "Julia da Revoluna aqui"),
    ("a8", "Oi! Julia da Revoluna"),
]

# Contextos (terceira linha - o que faz)
CONTEXTOS = [
    ("c1", "Trabalho com escalas medicas aqui na regiao"),
    ("c2", "A gente trabalha com plantoes medicos"),
    ("c3", "Cuido das escalas medicas aqui"),
    ("c4", "Trabalho conectando medicos com plantoes"),
    ("c5", "Ajudo medicos a encontrar plantoes"),
    ("c6", "Trabalho com oportunidades de plantao"),
    ("c7", "Cuido da parte de escalas e plantoes"),
]

# Ganchos (quarta linha - pergunta/interesse)
GANCHOS = [
    ("g1", "Vc ta fazendo plantoes?"),
    ("g2", "Ta aceitando plantao?"),
    ("g3", "Tem interesse em plantoes?"),
    ("g4", "Vc faz plantao avulso?"),
    ("g5", "Ta com disponibilidade pra plantao?"),
    ("g6", "Procurando plantao?"),
    ("g7", "Surgiu umas vagas boas, tem interesse?"),
]


def montar_abertura_completa(
    nome: str,
    saudacao_id: str = None,
    apresentacao_id: str = None,
    contexto_id: str = None,
    gancho_id: str = None
) -> list[str]:
    """
    Monta abertura completa com IDs especificos ou aleatorios.

    Args:
        nome: Nome do medico
        saudacao_id: ID da saudacao (ou None para aleatorio)
        apresentacao_id: ID da apresentacao
        contexto_id: ID do contexto
        gancho_id: ID do gancho

    Returns:
        Lista de strings (cada uma e uma mensagem separada)
    """
    import random

    mensagens = []

    # Saudacao
    if saudacao_id:
        saudacao = next((s for s in SAUDACOES if s[0] == saudacao_id), None)
    else:
        saudacao = random.choice(SAUDACOES)

    if saudacao:
        mensagens.append(saudacao[1].format(nome=nome))

    # Apresentacao
    if apresentacao_id:
        apresentacao = next((a for a in APRESENTACOES if a[0] == apresentacao_id), None)
    else:
        apresentacao = random.choice(APRESENTACOES)

    if apresentacao:
        mensagens.append(apresentacao[1])

    # Contexto (opcional - 70% das vezes)
    if contexto_id or random.random() < 0.7:
        if contexto_id:
            contexto = next((c for c in CONTEXTOS if c[0] == contexto_id), None)
        else:
            contexto = random.choice(CONTEXTOS)

        if contexto:
            mensagens.append(contexto[1])

    # Gancho (sempre)
    if gancho_id:
        gancho = next((g for g in GANCHOS if g[0] == gancho_id), None)
    else:
        gancho = random.choice(GANCHOS)

    if gancho:
        mensagens.append(gancho[1])

    return mensagens
```

## Criterios de Aceite

1. **15+ saudacoes:** Variacoes suficientes
2. **8+ apresentacoes:** Formas de se apresentar
3. **7+ contextos:** O que Julia faz
4. **7+ ganchos:** Perguntas de interesse
5. **Periodos:** Saudacoes especificas para manha/tarde/noite

## DoD

- [ ] Arquivo `app/templates/aberturas.py` criado
- [ ] Pelo menos 15 saudacoes
- [ ] Pelo menos 8 apresentacoes
- [ ] Pelo menos 7 contextos
- [ ] Pelo menos 7 ganchos
- [ ] Funcao `montar_abertura_completa()` implementada
- [ ] Suporte a variaveis ({nome})

---

# S8.E6.2 - Criar seletor inteligente

## Objetivo

> **Criar logica para selecionar variacao sem repetir.**

## Codigo Esperado

**Arquivo:** `app/services/abertura.py`

```python
"""
Servico de selecao de aberturas.
"""
import logging
import random
from datetime import datetime
from typing import Optional

from app.templates.aberturas import (
    SAUDACOES,
    APRESENTACOES,
    CONTEXTOS,
    GANCHOS,
    montar_abertura_completa
)
from app.services.redis import cache_get, cache_set
from app.services.supabase import get_supabase

logger = logging.getLogger(__name__)

# Cache de ultima abertura usada por medico
CACHE_TTL_ABERTURA = 86400 * 30  # 30 dias


async def obter_abertura(
    cliente_id: str,
    nome: str,
    hora_atual: datetime = None
) -> list[str]:
    """
    Obtem abertura personalizada para medico.

    Evita repetir a mesma abertura para o mesmo medico.
    Considera horario do dia para saudacao.

    Args:
        cliente_id: ID do medico
        nome: Nome do medico
        hora_atual: Hora atual (para saudacao contextual)

    Returns:
        Lista de mensagens de abertura
    """
    hora_atual = hora_atual or datetime.now()

    # Buscar ultima abertura usada
    ultima_abertura = await _get_ultima_abertura(cliente_id)

    # Selecionar saudacao baseada no horario
    saudacao = _selecionar_saudacao(hora_atual, ultima_abertura)

    # Selecionar demais componentes evitando repeticao
    apresentacao = _selecionar_sem_repetir(
        APRESENTACOES,
        ultima_abertura.get("apresentacao") if ultima_abertura else None
    )

    contexto = _selecionar_sem_repetir(
        CONTEXTOS,
        ultima_abertura.get("contexto") if ultima_abertura else None
    )

    gancho = _selecionar_sem_repetir(
        GANCHOS,
        ultima_abertura.get("gancho") if ultima_abertura else None
    )

    # Montar abertura
    mensagens = montar_abertura_completa(
        nome=nome,
        saudacao_id=saudacao[0],
        apresentacao_id=apresentacao[0],
        contexto_id=contexto[0] if random.random() < 0.7 else None,
        gancho_id=gancho[0]
    )

    # Salvar para evitar repeticao
    await _salvar_abertura_usada(
        cliente_id,
        saudacao[0],
        apresentacao[0],
        contexto[0],
        gancho[0]
    )

    return mensagens


async def _get_ultima_abertura(cliente_id: str) -> Optional[dict]:
    """Busca ultima abertura usada para este medico."""
    cache_key = f"abertura:ultima:{cliente_id}"

    cached = await cache_get(cache_key)
    if cached:
        import json
        return json.loads(cached)

    # Buscar no banco
    try:
        supabase = get_supabase()
        response = (
            supabase.table("clientes")
            .select("ultima_abertura")
            .eq("id", cliente_id)
            .limit(1)
            .execute()
        )

        if response.data and response.data[0].get("ultima_abertura"):
            return response.data[0]["ultima_abertura"]

    except Exception as e:
        logger.warning(f"Erro ao buscar ultima abertura: {e}")

    return None


async def _salvar_abertura_usada(
    cliente_id: str,
    saudacao_id: str,
    apresentacao_id: str,
    contexto_id: str,
    gancho_id: str
):
    """Salva abertura usada para evitar repeticao."""
    import json

    abertura = {
        "saudacao": saudacao_id,
        "apresentacao": apresentacao_id,
        "contexto": contexto_id,
        "gancho": gancho_id,
        "timestamp": datetime.utcnow().isoformat()
    }

    # Cache
    cache_key = f"abertura:ultima:{cliente_id}"
    await cache_set(cache_key, json.dumps(abertura), CACHE_TTL_ABERTURA)

    # Banco (async, nao bloqueia)
    try:
        supabase = get_supabase()
        supabase.table("clientes").update({
            "ultima_abertura": abertura
        }).eq("id", cliente_id).execute()
    except Exception as e:
        logger.warning(f"Erro ao salvar abertura no banco: {e}")


def _selecionar_saudacao(
    hora: datetime,
    ultima: dict = None
) -> tuple:
    """
    Seleciona saudacao baseada no horario.

    6-12h: bom dia
    12-18h: boa tarde
    18-24h/0-6h: boa noite
    """
    hora_int = hora.hour

    # Filtrar por periodo
    if 6 <= hora_int < 12:
        periodo = "manha"
    elif 12 <= hora_int < 18:
        periodo = "tarde"
    else:
        periodo = "noite"

    # Buscar saudacoes do periodo ou genericas
    candidatas = [
        s for s in SAUDACOES
        if s[2] == periodo or s[2] is None
    ]

    # Evitar repetir
    if ultima and ultima.get("saudacao"):
        candidatas = [s for s in candidatas if s[0] != ultima["saudacao"]]

    # Se sobrou algo, escolher aleatorio
    if candidatas:
        return random.choice(candidatas)

    # Fallback
    return random.choice(SAUDACOES)


def _selecionar_sem_repetir(
    opcoes: list[tuple],
    ultimo_id: str = None
) -> tuple:
    """Seleciona opcao evitando a ultima usada."""
    if ultimo_id:
        candidatas = [o for o in opcoes if o[0] != ultimo_id]
        if candidatas:
            return random.choice(candidatas)

    return random.choice(opcoes)
```

## Criterios de Aceite

1. **Sem repeticao:** Evita mesma abertura para mesmo medico
2. **Horario:** Usa "bom dia/tarde/noite" apropriado
3. **Cache:** Salva ultima usada
4. **Fallback:** Sempre retorna algo valido

## DoD

- [ ] `obter_abertura()` implementado
- [ ] Selecao por horario funciona
- [ ] Evita repeticao para mesmo medico
- [ ] Cache com TTL de 30 dias
- [ ] Salva no banco para persistencia

---

# S8.E6.3 - Integrar no fluxo de prospeccao

## Objetivo

> **Usar aberturas variadas no envio de campanhas/prospeccao.**

## Codigo Esperado

**Arquivo:** `app/services/campanha.py` (modificar)

```python
from app.services.abertura import obter_abertura


async def enviar_mensagem_prospeccao(
    cliente_id: str,
    telefone: str,
    nome: str,
    campanha_id: str = None
) -> dict:
    """
    Envia mensagem de prospeccao com abertura variada.
    """
    # Obter abertura personalizada
    mensagens = await obter_abertura(
        cliente_id=cliente_id,
        nome=nome
    )

    # Enviar em sequencia com timing
    from app.services.agente import enviar_mensagens_sequencia

    resultados = await enviar_mensagens_sequencia(
        telefone=telefone,
        mensagens=mensagens
    )

    # Registrar envio
    # ...

    return {
        "success": True,
        "mensagens_enviadas": len(mensagens),
        "primeira_mensagem": mensagens[0] if mensagens else None
    }
```

**Arquivo:** `app/core/prompts.py` (adicionar instrucao)

```python
INSTRUCAO_PRIMEIRA_MSG_COM_VARIACAO = """
Esta e a PRIMEIRA interacao com este medico.

IMPORTANTE: A mensagem de abertura JA FOI ENVIADA pelo sistema.
Voce NAO precisa se apresentar novamente.

A abertura que foi enviada incluiu:
- Saudacao
- Apresentacao (Julia da Revoluna)
- Contexto (escalas medicas)
- Pergunta de interesse

Sua tarefa e CONTINUAR a conversa a partir da resposta do medico.
NAO repita a apresentacao.
NAO diga "Oi, sou a Julia" novamente.
"""
```

## Criterios de Aceite

1. **Prospeccao usa:** Campanha usa abertura variada
2. **Prompt atualizado:** Julia sabe que abertura ja foi enviada
3. **Sequencia natural:** Mensagens enviadas com timing

## DoD

- [ ] `enviar_mensagem_prospeccao()` usa `obter_abertura()`
- [ ] Prompt instrui Julia a nao repetir apresentacao
- [ ] Mensagens enviadas em sequencia
- [ ] Logs mostram qual abertura foi usada

---

## Resumo do Epic

| Story | Descricao | Complexidade |
|-------|-----------|--------------|
| S8.E6.1 | Banco de templates | Baixa |
| S8.E6.2 | Seletor inteligente | Media |
| S8.E6.3 | Integrar na prospeccao | Baixa |

## Arquivos Criados/Modificados

| Arquivo | Acao |
|---------|------|
| `app/templates/aberturas.py` | Criar |
| `app/services/abertura.py` | Criar |
| `app/services/campanha.py` | Modificar |
| `app/core/prompts.py` | Modificar |

---

## Migration Necessaria

**Arquivo:** `20251208_campo_ultima_abertura.sql`

```sql
-- Adiciona campo para rastrear ultima abertura usada por medico
-- Evita repeticao de mensagens de abertura

ALTER TABLE clientes
ADD COLUMN IF NOT EXISTS ultima_abertura JSONB DEFAULT NULL;

-- Exemplo de valor:
-- {
--   "saudacao": "s1",
--   "apresentacao": "a3",
--   "contexto": "c2",
--   "gancho": "g5",
--   "timestamp": "2025-12-08T10:30:00Z"
-- }

-- Indice para queries (opcional, se precisar buscar por abertura)
CREATE INDEX IF NOT EXISTS idx_clientes_ultima_abertura
ON clientes USING gin (ultima_abertura);

COMMENT ON COLUMN clientes.ultima_abertura IS 'Ultima abertura usada para este medico (evita repeticao)';
```

## Validacao Final

```
CENARIO: Enviar para 5 medicos

Medico 1: "Oi Dr Carlos! Tudo bem? Sou a Julia da Revoluna..."
Medico 2: "E ai Dr Ana, td certo? Julia aqui, da Revoluna..."
Medico 3: "Bom dia Dr Pedro! Aqui e a Julia..."
Medico 4: "Opa Dr Maria! Como vai? Sou Julia..."
Medico 5: "Dr Lucas, tudo tranquilo? Meu nome e Julia..."

Todas diferentes!
```
